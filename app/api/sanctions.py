"""
Sanctions screening endpoints - Clean Architecture Implementation.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from app.core.config import settings
from app.services.sanctions_service import SanctionsService
from app.shared.models import SanctionsAnalysisRequest, EntityModel

router = APIRouter(tags=["sanctions"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
sanctions_service = SanctionsService()


@router.post("/sanctions/analyze")
async def analyze_sanctions_endpoint(
    request: SanctionsAnalysisRequest,
    x_api_key: str | None = Security(api_key_header),
):
    """Analyze entity for sanctions risk."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    entity_data = request.entity.dict()
    
    response = await sanctions_service.analyze_sanctions_risk(entity_data)
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return response["data"]


@router.post("/sanctions/country-risk")
async def get_country_risk(
    country_code: str,
    x_api_key: str | None = Security(api_key_header),
):
    """Get country risk assessment."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = sanctions_service.get_country_risk(country_code)
    
    if not response["success"]:
        raise HTTPException(status_code=404, detail=response["data"].get("error"))
    
    return response["data"]


@router.post("/sanctions/entity-check")
async def check_entity_sanctions(
    entity_name: str,
    country: str,
    x_api_key: str | None = Security(api_key_header),
):
    """Check if entity is on sanctions list."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = sanctions_service.check_entity_sanctions(entity_name, country)
    
    return response["data"]


@router.post("/sanctions/keyword-check")
async def check_watchlist_keywords(
    text: str,
    x_api_key: str | None = Security(api_key_header),
):
    """Check text for watchlist keywords."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = sanctions_service.check_watchlist_keywords(text)
    
    return response["data"]


@router.get("/sanctions/high-risk-countries")
async def get_high_risk_countries(
    x_api_key: str | None = Security(api_key_header),
):
    """Get list of high-risk countries."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = sanctions_service.get_high_risk_countries()
    
    return response["data"]


@router.get("/sanctions/health")
async def sanctions_health():
    return {"status": "ok", "endpoint": "sanctions"}
