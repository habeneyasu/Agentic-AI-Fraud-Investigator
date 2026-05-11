"""Alert intake endpoints."""

import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.api.deps import RequireApiKey
from app.core.logging import get_logger
from app.data.data_loader import data_loader
from app.shared.models import ApiMessageResponse, FraudAlertIngestRequest, FraudAlertIngestResponse

logger = get_logger(__name__)
router = APIRouter(tags=["alerts"])

demo_alerts: List[Dict[str, Any]] = []


@router.post("/alerts", response_model=FraudAlertIngestResponse, status_code=202)
async def ingest_alert(
    payload: FraudAlertIngestRequest,
    _: None = RequireApiKey,
):
    """Receive a fraud alert; stores demo alert and returns investigation id."""
    investigation_id = f"inv_{uuid.uuid4().hex[:12]}"

    alert_data = {
        "alert_id": f"ALERT_{payload.transaction_id}_{len(demo_alerts) + 1}",
        "investigation_id": investigation_id,
        "transaction_id": payload.transaction_id,
        "amount": payload.amount,
        "currency": payload.currency,
        "account_id": payload.account_id,
        "recipient_country": payload.recipient_country,
        "alert_hash": payload.alert_hash,
        "metadata": payload.metadata or {},
        "timestamp": payload.timestamp,
        "status": "OPEN",
        "severity": payload.metadata.get("severity", "medium") if payload.metadata else "medium",
        "customer_context": data_loader.get_customer_context(payload.account_id),
    }
    demo_alerts.append(alert_data)

    logger.info(
        "Alert received",
        transaction_id=payload.transaction_id,
        amount=payload.amount,
        country=payload.recipient_country,
        investigation_id=investigation_id,
    )

    return FraudAlertIngestResponse(
        success=True,
        investigation_id=investigation_id,
        status="RECEIVED",
        message="Investigation dispatched",
    )


@router.get("/alerts", response_model=ApiMessageResponse)
async def get_alerts(_: None = RequireApiKey):
    return ApiMessageResponse(
        success=True,
        message="Alerts retrieved successfully",
        data={
            "alerts": demo_alerts,
            "total_count": len(demo_alerts),
            "open_count": len([a for a in demo_alerts if a["status"] == "OPEN"]),
            "high_risk_count": len([a for a in demo_alerts if a.get("severity") == "high"]),
        },
    )


@router.get("/alerts/{alert_id}", response_model=ApiMessageResponse)
async def get_alert(alert_id: str, _: None = RequireApiKey):
    alert = next((a for a in demo_alerts if a["alert_id"] == alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return ApiMessageResponse(success=True, message="Alert retrieved successfully", data=alert)


@router.put("/alerts/{alert_id}/status", response_model=ApiMessageResponse)
async def update_alert_status(alert_id: str, status: str, _: None = RequireApiKey):
    alert = next((a for a in demo_alerts if a["alert_id"] == alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert["status"] = status
    logger.info("Alert status updated", alert_id=alert_id, status=status)

    return ApiMessageResponse(
        success=True,
        message=f"Alert status updated to {status}",
        data={"alert_id": alert_id, "new_status": status},
    )


@router.get("/alerts/health", tags=["alerts"])
async def alerts_health():
    return {"status": "ok", "endpoint": "alerts"}
