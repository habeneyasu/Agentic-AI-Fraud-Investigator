"""Sanctions screening endpoints."""

from fastapi import APIRouter, HTTPException

from app.api.deps import RequireApiKey
from app.services.sanctions_service import SanctionsService
from app.shared.models import SanctionsScreeningApiRequest

router = APIRouter(tags=["sanctions"])
sanctions_service = SanctionsService()


@router.post("/sanctions/analyze")
async def analyze_sanctions_endpoint(request: SanctionsScreeningApiRequest, _: None = RequireApiKey):
    response = await sanctions_service.analyze_sanctions_risk(request.entity.dict())
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    return response["data"]


@router.post("/sanctions/country-risk")
async def get_country_risk(country_code: str, _: None = RequireApiKey):
    response = sanctions_service.get_country_risk(country_code)
    if not response["success"]:
        raise HTTPException(status_code=404, detail=response["data"].get("error"))
    return response["data"]


@router.post("/sanctions/entity-check")
async def check_entity_sanctions(entity_name: str, country: str, _: None = RequireApiKey):
    response = sanctions_service.check_entity_sanctions(entity_name, country)
    return response["data"]


@router.post("/sanctions/keyword-check")
async def check_watchlist_keywords(text: str, _: None = RequireApiKey):
    response = sanctions_service.check_watchlist_keywords(text)
    return response["data"]


@router.get("/sanctions/high-risk-countries")
async def get_high_risk_countries(_: None = RequireApiKey):
    response = sanctions_service.get_high_risk_countries()
    return response["data"]


@router.get("/sanctions/health")
async def sanctions_health():
    return {"status": "ok", "endpoint": "sanctions"}
