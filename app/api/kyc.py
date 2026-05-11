"""KYC verification endpoints."""

from fastapi import APIRouter, HTTPException

from app.api.deps import RequireApiKey
from app.services.kyc_service import KYCService
from app.shared.models import DeviceInfo, GeoLocation, KycAnalysisApiRequest

router = APIRouter(tags=["kyc"])
kyc_service = KYCService()


@router.post("/kyc/analyze")
async def analyze_kyc_endpoint(request: KycAnalysisApiRequest, _: None = RequireApiKey):
    response = await kyc_service.analyze_kyc_event(request.event.dict())
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    return response["data"]


@router.post("/kyc/device-check")
async def check_device(customer_id: str, device_info: DeviceInfo, _: None = RequireApiKey):
    response = kyc_service.check_device(customer_id, device_info.dict())
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    return response["data"]


@router.post("/kyc/geo-check")
async def check_geo_location(customer_id: str, location: GeoLocation, _: None = RequireApiKey):
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
    _: None = RequireApiKey,
):
    response = kyc_service.check_impossible_travel(
        customer_id,
        from_location.dict(),
        to_location.dict(),
        timestamp_from,
        timestamp_to,
    )
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    return response["data"]


@router.get("/kyc/health")
async def kyc_health():
    return {"status": "ok", "endpoint": "kyc"}
