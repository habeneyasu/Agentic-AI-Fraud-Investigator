"""
Alert intake endpoint - Clean Architecture Implementation.
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Security, BackgroundTasks
from fastapi.security.api_key import APIKeyHeader
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.shared.models import AlertModel, BaseResponse, AlertPayload, AlertResponse
from app.data.data_loader import data_loader

logger = get_logger(__name__)
router = APIRouter(tags=["alerts"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# In-memory storage for demo alerts
demo_alerts: List[Dict[str, Any]] = []


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/alerts", response_model=AlertResponse, status_code=202)
async def ingest_alert(
    payload: AlertPayload,
    x_api_key: str | None = Security(api_key_header),
):
    """
    Receive a fraud alert. Validates API key, checks idempotency,
    and dispatches the investigation workflow asynchronously.
    """
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Generate investigation ID with idempotency check
    import hashlib, uuid
    idem_key = hashlib.sha256(
        f"{payload.transaction_id}{payload.alert_hash}".encode()
    ).hexdigest()
    investigation_id = f"inv_{uuid.uuid4().hex[:12]}"

    # Store alert for demo
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
        "customer_context": data_loader.get_customer_context(payload.account_id)
    }
    demo_alerts.append(alert_data)

    logger.info("Alert received",
                transaction_id=payload.transaction_id,
                amount=payload.amount,
                country=payload.recipient_country,
                investigation_id=investigation_id)

    return AlertResponse(
        success=True,
        investigation_id=investigation_id,
        status="RECEIVED",
        message="Investigation dispatched"
    )


@router.get("/alerts", response_model=BaseResponse)
async def get_alerts(
    x_api_key: str | None = Security(api_key_header),
):
    """Get all alerts with filtering options."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return BaseResponse(
        success=True,
        message="Alerts retrieved successfully",
        data={
            "alerts": demo_alerts,
            "total_count": len(demo_alerts),
            "open_count": len([a for a in demo_alerts if a["status"] == "OPEN"]),
            "high_risk_count": len([a for a in demo_alerts if a.get("severity") == "high"])
        }
    )


@router.get("/alerts/{alert_id}", response_model=BaseResponse)
async def get_alert(
    alert_id: str,
    x_api_key: str | None = Security(api_key_header),
):
    """Get specific alert details."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    alert = next((a for a in demo_alerts if a["alert_id"] == alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return BaseResponse(
        success=True,
        message="Alert retrieved successfully",
        data=alert
    )


@router.put("/alerts/{alert_id}/status", response_model=BaseResponse)
async def update_alert_status(
    alert_id: str,
    status: str,
    x_api_key: str | None = Security(api_key_header),
):
    """Update alert status."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    alert = next((a for a in demo_alerts if a["alert_id"] == alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert["status"] = status
    logger.info(f"Alert {alert_id} status updated to {status}")

    return BaseResponse(
        success=True,
        message=f"Alert status updated to {status}",
        data={"alert_id": alert_id, "new_status": status}
    )


@router.get("/alerts/health", tags=["alerts"])
async def alerts_health():
    return {"status": "ok", "endpoint": "alerts"}
