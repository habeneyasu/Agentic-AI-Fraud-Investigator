"""
Human-in-the-Loop decision endpoint - Clean Architecture Implementation.
"""

from fastapi import APIRouter, HTTPException, Header

from app.core.config import settings
from app.core.logging import get_logger
from app.shared.models import HITLDecision

logger = get_logger(__name__)
router = APIRouter(prefix="/api/hitl", tags=["hitl"])


@router.post("/{investigation_id}/decision")
async def submit_decision(
    investigation_id: str,
    payload: HITLDecision,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if x_user_role != "Analyst":
        raise HTTPException(status_code=403, detail="Forbidden — Analyst role required")

    status_map = {
        "CONFIRM_FRAUD":      "RESOLUTION_IN_PROGRESS",
        "FALSE_POSITIVE":     "CLOSED_FALSE_POSITIVE",
        "REQUEST_MORE_INFO":  "AWAITING_HUMAN",
    }

    logger.info("HITL decision received",
                investigation_id=investigation_id,
                decision=payload.decision,
                analyst=payload.analyst_id)

    return {
        "investigation_id": investigation_id,
        "status": status_map[payload.decision],
        "decision": payload.decision,
    }
