"""Triage HTTP routes."""

from typing import FrozenSet, Optional

from fastapi import APIRouter, Body, HTTPException, Query

from app.api.deps import RequireApiKey
from app.core.logging import get_logger
from app.models.triage import (
    TriageAssessBody,
    TriageAssessmentRequest,
    TriageAssessmentResponse,
)
from app.services.triage_service import TriageService

logger = get_logger(__name__)
router = APIRouter(tags=["triage"])
triage_service = TriageService()

_CUSTOMER_ID_PLACEHOLDERS: FrozenSet[str] = frozenset(
    {
        "string",
        "str",
        "customer_id",
        "your_customer_id",
        "example",
        "null",
        "none",
        "n/a",
        "na",
        "-",
    }
)


def _normalize_customer_id(value: Optional[str]) -> Optional[str]:
    s = (value or "").strip()
    if not s:
        return None
    if s.lower() in _CUSTOMER_ID_PLACEHOLDERS:
        return None
    return s


def _normalize_alert_id(value: Optional[str]) -> Optional[str]:
    s = (value or "").strip()
    return s if s else None


@router.post("/triage/assess", response_model=TriageAssessmentResponse)
async def assess_alerts(
    payload: Optional[TriageAssessBody] = Body(default=None),
    customer_id: Optional[str] = Query(default=None, description="Customer filter (query overrides body)."),
    alert_id: Optional[str] = Query(default=None, description="Optional alert id filter."),
    _: None = RequireApiKey,
):
    """Triage + optional narrative (scope: query ``customer_id`` / ``alert_id`` or body ``customer_id``)."""
    try:
        body = payload or TriageAssessBody()
        q_cust = _normalize_customer_id(customer_id)
        body_cust = _normalize_customer_id(getattr(body, "customer_id", None))
        effective_customer = q_cust or body_cust
        request = TriageAssessmentRequest(
            customer_id=effective_customer,
            alert_id=_normalize_alert_id(alert_id),
            include_initial_suspicion_note=body.include_initial_suspicion_note,
        )

        return await triage_service.assess(request)

    except Exception as e:
        logger.error("Triage assessment failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
