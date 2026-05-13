"""Enterprise-grade Triage API - Clean HTTP routing layer."""

from typing import Optional

from fastapi import APIRouter, HTTPException

from app.api.deps import RequireApiKey
from app.core.logging import get_logger
from app.models.triage import TriageAssessmentRequest, TriageAssessmentResponse
from app.services.triage_service import TriageService

logger = get_logger(__name__)
router = APIRouter(tags=["triage"])
triage_service = TriageService()


@router.post("/triage/assess", response_model=TriageAssessmentResponse)
async def assess_alerts(
    customer_id: Optional[str] = None,
    _: None = RequireApiKey,
):
    """
    Assess alerts and provide investigation decisions.

    Reads alerts from the **in-memory** `AlertRepository` inside this API process only.
    That store is **empty on startup** until you populate it (e.g. `POST /v1/alerts/generate?customer_id=CUST003`).
    JSON shown in the Streamlit app or in files is **not** visible to this endpoint unless it was ingested through the API.

    Args:
        customer_id: Optional customer ID to assess alerts for specific customer.
                   If not provided, assesses all alerts.

    Usage:
        - POST /v1/alerts/generate?customer_id=CUST003 — seed alerts from packaged transaction/KYC data
        - POST /v1/triage/assess?customer_id=CUST003 — run triage on those alerts
    """
    try:
        # Create request object
        request = TriageAssessmentRequest(customer_id=customer_id)

        # Delegate to service layer - API only handles HTTP
        return await triage_service.assess(request)

    except Exception as e:
        logger.error("Triage assessment failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
