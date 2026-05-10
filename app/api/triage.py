"""
Triage decision endpoints - Clean Architecture Implementation.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from app.core.config import settings
from app.services.triage_service import TriageService
from app.shared.models import TriageAnalysisRequest, TriageRequest

router = APIRouter(tags=["triage"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
triage_service = TriageService()


@router.post("/triage/analyze")
async def triage_analysis(
    request: TriageAnalysisRequest,
    x_api_key: str | None = Security(api_key_header),
):
    """Perform triage analysis on fraud investigation."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    triage_data = request.triage.dict()
    
    response = triage_service.analyze_case(triage_data)
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return response["data"]


@router.post("/triage/priority-calculation")
async def calculate_priority(
    risk_score: float,
    amount: float,
    customer_tier: str = "standard",
    alert_count: int = 1,
    x_api_key: str | None = Security(api_key_header),
):
    """Calculate investigation priority."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = triage_service.calculate_priority(risk_score, amount, customer_tier, alert_count)
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return response["data"]


@router.post("/triage/escalation-check")
async def check_escalation(
    risk_score: float,
    amount: float,
    alert_types: List[str],
    customer_history: Dict[str, Any],
    x_api_key: str | None = Security(api_key_header),
):
    """Check if case requires escalation."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = triage_service.check_escalation(risk_score, amount, alert_types, customer_history)
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return response["data"]


@router.post("/triage/auto-action")
async def determine_auto_action(
    risk_score: float,
    triage_decision: str,
    customer_risk_level: str = "low",
    x_api_key: str | None = Security(api_key_header),
):
    """Determine automatic action."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = triage_service.determine_auto_action(risk_score, triage_decision, customer_risk_level)
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return response["data"]


@router.get("/triage/rules")
async def get_triage_rules(
    x_api_key: str | None = Security(api_key_header),
):
    """Get current triage rules and thresholds."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return {
        "risk_thresholds": triage_service.risk_thresholds,
        "priority_weights": triage_service.priority_weights,
        "escalation_rules": triage_service.escalation_rules,
        "auto_action_rules": triage_service.auto_action_rules
    }


@router.get("/triage/health")
async def triage_health():
    return {"status": "ok", "endpoint": "triage"}
