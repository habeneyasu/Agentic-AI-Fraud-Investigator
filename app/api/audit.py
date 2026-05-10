"""
GET /audit/{investigation_id} — Audit trail retrieval endpoint.
"""

from fastapi import APIRouter, HTTPException, Header

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/{investigation_id}")
async def get_audit_trail(
    investigation_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if x_user_role not in ("Analyst", "Auditor"):
        raise HTTPException(status_code=403, detail="Forbidden — Analyst or Auditor role required")

    # Placeholder — full DB-backed audit trail added in Day 3 implementation
    return {
        "investigation_id": investigation_id,
        "events": [
            {"event": "RECEIVED",    "timestamp": "2026-05-08T02:15:00.000Z"},
            {"event": "TRIAGE",      "timestamp": "2026-05-08T02:15:00.050Z"},
            {"event": "INVESTIGATING","timestamp": "2026-05-08T02:15:00.100Z"},
        ],
        "note": "Full audit trail available after Day 3 implementation",
    }
