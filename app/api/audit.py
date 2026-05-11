"""Audit trail retrieval."""

from fastapi import APIRouter

from app.api.deps import RequireAnalystOrAuditor, RequireApiKey

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/{investigation_id}")
async def get_audit_trail(
    investigation_id: str,
    _: None = RequireApiKey,
    __: None = RequireAnalystOrAuditor,
):
    return {
        "investigation_id": investigation_id,
        "events": [
            {"event": "RECEIVED", "timestamp": "2026-05-08T02:15:00.000Z"},
            {"event": "TRIAGE", "timestamp": "2026-05-08T02:15:00.050Z"},
            {"event": "INVESTIGATING", "timestamp": "2026-05-08T02:15:00.100Z"},
        ],
        "note": "Placeholder audit payload for demo",
    }
