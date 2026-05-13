"""KYC profile CRUD (sync SQLAlchemy)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.api.deps import RequireApiKey
from app.api.response_models import DataStatusResponse
from app.core.logging import get_logger
from app.db.sync_session import sync_session
from app.models.orm_tables import KycProfileORM

logger = get_logger(__name__)
router = APIRouter(tags=["kyc"])


def _kyc_orm_from_payload(kyc_data: Dict[str, Any]) -> KycProfileORM:
    return KycProfileORM(
        customer_id=kyc_data["customer_id"],
        legal_name=kyc_data.get("legal_name"),
        verification_status=kyc_data.get("verification_status", "pending"),
        risk_tier="MEDIUM" if kyc_data.get("risk_score", 0.0) < 0.5 else "HIGH",
        last_reviewed_at=(
            datetime.fromisoformat(kyc_data["timestamp"].replace("Z", "+00:00"))
            if kyc_data.get("timestamp")
            else None
        ),
        profile_payload={
            "event_type": kyc_data.get("event_type"),
            "timestamp": kyc_data.get("timestamp"),
            "ip_address": kyc_data.get("ip_address"),
            "device_info": kyc_data.get("device_info", {}),
            "geo_location": kyc_data.get("geo_location", {}),
            "anomaly_type": kyc_data.get("anomaly_type"),
            "risk_score": kyc_data.get("risk_score", 0.0),
        },
    )


@router.get("/kyc/list", response_model=DataStatusResponse)
async def list_kyc_profiles(_: None = RequireApiKey):
    try:
        with sync_session() as session:
            profiles = session.query(KycProfileORM).all()
            data = [
                {
                    "customer_id": p.customer_id,
                    "legal_name": p.legal_name,
                    "verification_status": p.verification_status,
                    "risk_tier": p.risk_tier,
                    "last_reviewed_at": p.last_reviewed_at.isoformat() if p.last_reviewed_at else None,
                    "updated_at": p.updated_at.isoformat(),
                    "profile_payload": p.profile_payload,
                }
                for p in profiles
            ]
        return DataStatusResponse(success=True, count=len(data), message=f"Listed {len(data)} KYC profile(s)", data=data)
    except Exception as e:
        logger.error("list_kyc_profiles failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/kyc/create", response_model=DataStatusResponse)
async def create_kyc_profile(kyc_data: Dict[str, Any], _: None = RequireApiKey):
    try:
        cid = kyc_data["customer_id"]
        with sync_session() as session:
            if session.query(KycProfileORM).filter(KycProfileORM.customer_id == cid).first():
                return DataStatusResponse(success=False, count=0, message=f"KYC profile for {cid} already exists")
            session.add(_kyc_orm_from_payload(kyc_data))
            session.commit()
        return DataStatusResponse(success=True, count=1, message=f"Created KYC profile for {cid}")
    except Exception as e:
        logger.error("create_kyc_profile failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
