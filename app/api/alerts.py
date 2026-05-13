"""Alert intake endpoints."""

import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.api.deps import RequireApiKey
from app.models.alert import AlertFilter, AlertListResponse
from app.repositories.alert_repository import AlertRepository
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
    """List alerts in the API investigation queue (``runtime_alerts.json`` + in-memory).

    This is **not** the raw transaction corpus in ``transactions.json``. The queue is empty
    on a fresh process until you call ``POST /v1/alerts`` or ``POST /v1/alerts/generate``.
    """
    filters = AlertFilter(
        status=status,
        severity=severity,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to
    )

    response = await alert_repository.get_alerts(filters)
    return response


@router.post("/alerts", response_model=FraudAlertIngestResponse)
async def ingest_fraud_alert(
    body: FraudAlertIngestRequest,
    _: None = RequireApiKey,
):
    """Accept a single alert from channels or the dashboard; persists to the same store as ``GET /v1/alerts``.

    Idempotent on ``alert_hash``: a duplicate hash returns the existing investigation id without
    appending another row. ``account_id`` is treated as ``customer_id`` (dashboard convention).
    """
    snapshot = await alert_repository.get_alerts(None)
    for a in snapshot.alerts:
        if a.alert_hash == body.alert_hash:
            return FraudAlertIngestResponse(
                message="Alert already ingested (duplicate alert_hash).",
                investigation_id=a.investigation_id,
                status=a.status,
            )

    investigation_id = f"inv_{body.transaction_id}_{uuid.uuid4().hex[:8]}"
    alert_id = f"INGEST_{body.transaction_id}_{uuid.uuid4().hex[:6].upper()}"
    customer_id = (body.metadata or {}).get("customer_id") or body.account_id
    payload = {
        "alert_id": alert_id,
        "investigation_id": investigation_id,
        "transaction_id": body.transaction_id,
        "customer_id": customer_id,
        "amount": body.amount,
        "currency": body.currency,
        "account_id": body.account_id,
        "recipient_country": body.recipient_country,
        "alert_hash": body.alert_hash,
        "timestamp": body.timestamp,
        "status": "OPEN",
        "severity": "medium",
        "metadata": {**(body.metadata or {}), "ingest_source": "api_post_alerts"},
    }
    await alert_repository.create_alert(payload)
    return FraudAlertIngestResponse(
        message="Alert accepted for investigation.",
        investigation_id=investigation_id,
        status="OPEN",
    )


@router.post("/alerts/generate", response_model=AlertListResponse)
async def generate_alerts(
    customer_id: Optional[str] = None,
    _: None = RequireApiKey,
):
    """Generate alerts based on actual database data using three policy rules; persists each to the alert store."""
    cid = (customer_id or "").strip()
    generated = await alert_generation_service.generate_alerts_from_data(cid)
    for alert in generated:
        await alert_repository.create_alert(alert.model_dump())

    filters = AlertFilter(customer_id=cid) if cid else None
    return await alert_repository.get_alerts(filters)
