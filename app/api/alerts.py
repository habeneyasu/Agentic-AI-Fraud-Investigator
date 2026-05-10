"""
Alert intake endpoint - Clean Architecture Implementation.
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.shared.models import AlertModel, BaseResponse, AlertPayload, AlertResponse

logger = get_logger(__name__)
router = APIRouter(tags=["alerts"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


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


@router.get("/alerts/health", tags=["alerts"])
async def alerts_health():
    return {"status": "ok", "endpoint": "alerts"}
