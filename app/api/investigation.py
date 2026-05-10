"""
Investigation workflow endpoints - Clean Architecture Implementation.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from app.core.config import settings
from app.services.investigation_service import InvestigationService
from app.shared.models import InvestigationRequest, InvestigationModel, AgentResult

router = APIRouter(tags=["investigation"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
investigation_service = InvestigationService()


@router.post("/investigation/start")
async def start_investigation(
    request: InvestigationRequest,
    x_api_key: str | None = Security(api_key_header),
):
    """Start complete fraud investigation workflow."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    investigation_data = request.investigation.dict()
    
    response = await investigation_service.start_investigation(investigation_data)
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return response["data"]


@router.get("/investigation/{investigation_id}/status")
async def get_investigation_status(
    investigation_id: str,
    x_api_key: str | None = Security(api_key_header),
):
    """Get current status of investigation."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = investigation_service.get_investigation_status(investigation_id)
    
    if not response["success"]:
        raise HTTPException(status_code=404, detail=response["data"].get("error"))
    
    return response["data"]


@router.post("/investigation/{investigation_id}/agents/{agent_type}")
async def run_agent(
    investigation_id: str,
    agent_type: str,
    agent_data: Dict[str, Any],
    x_api_key: str | None = Security(api_key_header),
):
    """Run specific investigation agent."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = await investigation_service.run_agent(investigation_id, agent_type, agent_data)
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return response["data"]


@router.post("/investigation/{investigation_id}/synthesize")
async def synthesize_investigation(
    investigation_id: str,
    agent_results: Dict[str, AgentResult],
    x_api_key: str | None = Security(api_key_header),
):
    """Synthesize results from all agents."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Convert AgentResult objects to dicts for service
    agent_results_dict = {
        agent_type: result.dict() 
        for agent_type, result in agent_results.items()
    }
    
    response = await investigation_service.synthesize_results(investigation_id, agent_results_dict)
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return response["data"]


@router.get("/investigation/{investigation_id}/evidence")
async def get_investigation_evidence(
    investigation_id: str,
    x_api_key: str | None = Security(api_key_header),
):
    """Get evidence collected during investigation."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = investigation_service.get_investigation_evidence(investigation_id)
    
    if not response["success"]:
        raise HTTPException(status_code=404, detail=response["data"].get("error"))
    
    return response["data"]


@router.get("/investigation/health")
async def investigation_health():
    return {"status": "ok", "endpoint": "investigation"}
