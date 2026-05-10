"""
KYC verification endpoints - Clean Architecture Implementation.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from app.core.config import settings
from app.services.kyc_service import KYCService
from app.shared.models import KYCAnalysisRequest, KYCEventModel, DeviceInfo, GeoLocation

router = APIRouter(tags=["kyc"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
kyc_service = KYCService()


@router.post("/kyc/analyze")
async def analyze_kyc_endpoint(
    request: KYCAnalysisRequest,
    x_api_key: str | None = Security(api_key_header),
):
    """Analyze KYC event for anomalies."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    event_data = request.event.dict()
    
    response = await kyc_service.analyze_kyc_event(event_data)
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return response["data"]


@router.post("/kyc/device-check")
async def check_device(
    customer_id: str,
    device_info: DeviceInfo,
    x_api_key: str | None = Security(api_key_header),
):
    """Check device for suspicious activity."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = kyc_service.check_device(customer_id, device_info.dict())
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return response["data"]


@router.post("/kyc/geo-check")
async def check_geo_location(
    customer_id: str,
    location: GeoLocation,
    x_api_key: str | None = Security(api_key_header),
):
    """Check geo-location for anomalies."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = kyc_service.check_geo_location(customer_id, location.dict())
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return response["data"]


@router.post("/kyc/impossible-travel")
async def check_impossible_travel(
    customer_id: str,
    from_location: GeoLocation,
    to_location: GeoLocation,
    timestamp_from: str,
    timestamp_to: str,
    x_api_key: str | None = Security(api_key_header),
):
    """Check for impossible travel between locations."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = kyc_service.check_impossible_travel(
        customer_id, 
        from_location.dict(), 
        to_location.dict(), 
        timestamp_from, 
        timestamp_to
    )
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return response["data"]


@router.get("/kyc/health")
async def kyc_health():
    return {"status": "ok", "endpoint": "kyc"}
