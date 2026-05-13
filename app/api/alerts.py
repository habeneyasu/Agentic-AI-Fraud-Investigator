"""Alert intake endpoints."""

import uuid
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
from app.shared.models import FraudAlertIngestRequest, FraudAlertIngestResponse

router = APIRouter(tags=["alerts"])
alert_repository = AlertRepository()
alert_generation_service = AlertGenerationService()


@router.get(
    "/alerts/by-customer/{customer_id}",
    response_model=AlertListResponse,
    summary="List alerts for one customer",
)
async def get_alerts_by_customer(
    customer_id: str,
    _: None = RequireApiKey,
):
    """Return every alert whose ``customer_id`` matches (after strip)."""
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
    """List merged alerts: Postgres ``alerts`` table plus ``runtime_alerts.json`` (dedupe by ``alert_hash``; SQL wins)."""
    filters = AlertFilter(
        status=status,
        severity=severity,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to
    )

    response = await alert_repository.get_alerts(filters)
    return response


@router.post("/alerts/generate", response_model=AlertGenerateResponse)
async def generate_alerts(
    customer_id: Optional[str] = Query(
        None,
        description="Optional ``customer_id`` to scope ``transactions`` / ``kyc_profiles``; omit for all rows.",
    ),
    _: None = RequireApiKey,
):
    """Evaluate policies on Postgres ``transactions`` / ``kyc_profiles`` / sanctions tables, insert into ``alerts``, and append to the runtime JSON queue.

    Deduplicates on ``alert_hash`` across both the ``alerts`` table and the JSON queue. Response fields:
    ``postgres_inserted`` (SQL rows), ``created`` (JSON queue rows).
    """
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
