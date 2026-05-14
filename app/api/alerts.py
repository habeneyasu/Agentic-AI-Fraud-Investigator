"""Alert intake endpoints."""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from app.api.deps import RequireApiKey
from app.models.alert import AlertFilter, AlertGenerateResponse, AlertListResponse
from app.repositories.alert_repository import (
    AlertRepository,
    fetch_postgres_alert_hashes,
    save_generated_alert_to_sql,
)
from app.services.alert_generation_service import AlertGenerationService
from app.shared.country_risk import corridor_severity
from app.shared.models import FraudAlertIngestRequest

router = APIRouter(tags=["alerts"])
alert_repository = AlertRepository()
alert_generation_service = AlertGenerationService()


@router.post("/alerts")
async def ingest_fraud_alert(body: FraudAlertIngestRequest, _: None = RequireApiKey):
    """Append a channel alert to the runtime queue; ``account_id`` → ``customer_id``."""
    inv_id = f"inv_{uuid.uuid4().hex[:12]}"
    md = dict(body.metadata or {})
    walk_alert = (md.pop("walkthrough_alert_id", None) or "").strip()
    alert_id = walk_alert if walk_alert else f"ALT-{uuid.uuid4().hex[:10].upper()}"

    cust = (body.account_id or "").strip() or "UNKNOWN"
    amt = float(body.amount or 0.0)
    country = (body.recipient_country or "").strip().upper() or "UNKNOWN"
    severity = corridor_severity(country, amt)

    row = {
        "alert_id": alert_id,
        "investigation_id": inv_id,
        "transaction_id": body.transaction_id,
        "customer_id": cust,
        "amount": amt,
        "currency": body.currency or "USD",
        "account_id": body.account_id,
        "recipient_country": country,
        "alert_hash": body.alert_hash,
        "timestamp": body.timestamp or datetime.utcnow().isoformat(),
        "status": "OPEN",
        "severity": severity,
        "metadata": md,
        "customer_context": {},
    }
    await alert_repository.create_alert(row)
    return {
        "success": True,
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Alert accepted for investigation",
        "investigation_id": inv_id,
        "alert_id": alert_id,
        "status": "QUEUED",
    }


@router.get(
    "/alerts/by-customer/{customer_id}",
    response_model=AlertListResponse,
    summary="List alerts for one customer",
)
async def get_alerts_by_customer(
    customer_id: str,
    _: None = RequireApiKey,
):
    """Alerts for one ``customer_id`` (stripped)."""
    cid = (customer_id or "").strip()
    if not cid:
        return AlertListResponse(alerts=[], total_count=0, filtered_count=0)
    return await alert_repository.get_alerts(AlertFilter(customer_id=cid))


@router.get("/alerts", response_model=AlertListResponse)
async def get_alerts(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    date_from: Optional[str] = Query(None, description="Filter from date"),
    date_to: Optional[str] = Query(None, description="Filter to date"),
    _: None = RequireApiKey,
):
    """List merged alerts (Postgres + runtime JSON, deduped by ``alert_hash``)."""
    filters = AlertFilter(
        status=status,
        severity=severity,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
    )
    return await alert_repository.get_alerts(filters)


@router.post("/alerts/generate", response_model=AlertGenerateResponse)
async def generate_alerts(
    customer_id: Optional[str] = Query(
        None,
        description="Optional ``customer_id`` to scope ``transactions`` / ``kyc_profiles``; omit for all rows.",
    ),
    _: None = RequireApiKey,
):
    """Generate alerts from policy evaluation; dedupe on ``alert_hash``."""
    cid = (customer_id or "").strip()
    existing = await alert_repository.get_alerts(None)
    known_hashes = {a.alert_hash for a in existing.alerts} | fetch_postgres_alert_hashes()
    generated = await alert_generation_service.generate_alerts_from_data(cid)
    created = 0
    postgres_inserted = 0
    skipped_duplicates = 0
    for alert in generated:
        if alert.alert_hash in known_hashes:
            skipped_duplicates += 1
            continue
        if save_generated_alert_to_sql(alert):
            postgres_inserted += 1
        await alert_repository.create_alert(alert.model_dump())
        known_hashes.add(alert.alert_hash)
        created += 1

    filters = AlertFilter(customer_id=cid) if cid else None
    base = await alert_repository.get_alerts(filters)
    return AlertGenerateResponse(
        alerts=base.alerts,
        total_count=base.total_count,
        filtered_count=base.filtered_count,
        created=created,
        postgres_inserted=postgres_inserted,
        skipped_duplicates=skipped_duplicates,
    )
