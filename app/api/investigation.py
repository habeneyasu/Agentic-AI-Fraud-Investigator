"""Investigation workflow endpoints."""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.api.deps import RequireApiKey
from app.services.investigation_service import InvestigationService
from app.shared.models import AgentResult, OpenInvestigationApiRequest

router = APIRouter(tags=["investigation"])
investigation_service = InvestigationService()


@router.post("/investigation/start")
async def start_investigation(request: OpenInvestigationApiRequest, _: None = RequireApiKey):
    response = await investigation_service.start_investigation(request.investigation.dict())
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    return response["data"]


@router.get("/investigation/{investigation_id}/status")
async def get_investigation_status(investigation_id: str, _: None = RequireApiKey):
    response = investigation_service.get_investigation_status(investigation_id)
    if not response["success"]:
        raise HTTPException(status_code=404, detail=response["data"].get("error"))
    return response["data"]


@router.post("/investigation/{investigation_id}/agents/{agent_type}")
async def run_agent(
    investigation_id: str,
    agent_type: str,
    agent_data: Dict[str, Any],
    _: None = RequireApiKey,
):
    response = await investigation_service.run_agent(investigation_id, agent_type, agent_data)
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    return response["data"]


@router.post("/investigation/{investigation_id}/synthesize")
async def synthesize_investigation(
    investigation_id: str,
    agent_results: Dict[str, AgentResult],
    _: None = RequireApiKey,
):
    agent_results_dict = {agent_type: result.dict() for agent_type, result in agent_results.items()}
    response = await investigation_service.synthesize_results(investigation_id, agent_results_dict)
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    return response["data"]


@router.get("/investigation/{investigation_id}/evidence")
async def get_investigation_evidence(investigation_id: str, _: None = RequireApiKey):
    response = investigation_service.get_investigation_evidence(investigation_id)
    if not response["success"]:
        raise HTTPException(status_code=404, detail=response["data"].get("error"))
    return response["data"]


@router.get("/investigation/health")
async def investigation_health():
    return {"status": "ok", "endpoint": "investigation"}
