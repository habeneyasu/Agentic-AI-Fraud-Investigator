"""KYC profile CRUD (sync SQLAlchemy)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Union

from fastapi import APIRouter, Body, HTTPException

from app.api.bulk_json import bulk_rows
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


def _insert_kyc_profiles(rows: List[Dict[str, Any]]) -> DataStatusResponse:
    inserted = 0
    skipped_ids: list[str] = []
    staged_in_batch: set[str] = set()
    with sync_session() as session:
        for row in rows:
            cid = row.get("customer_id")
            if not cid:
                raise HTTPException(status_code=400, detail="Each row must include customer_id")
            if cid in staged_in_batch:
                skipped_ids.append(cid)
                continue
            if session.query(KycProfileORM).filter(KycProfileORM.customer_id == cid).first():
                skipped_ids.append(cid)
                continue
            session.add(_kyc_orm_from_payload(row))
            staged_in_batch.add(cid)
            inserted += 1
        session.commit()
    msg = f"Inserted {inserted} KYC profile(s)"
    if skipped_ids:
        msg += (
            "; skipped customer_id(s) (already in DB or repeated later in this request): "
            + ", ".join(skipped_ids)
        )
    return DataStatusResponse(
        success=True,
        count=inserted,
        message=msg,
        data=[{"skipped_customer_ids": skipped_ids}] if skipped_ids else None,
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
async def create_kyc_profile(
    body: Union[Dict[str, Any], List[Dict[str, Any]]] = Body(...),
    _: None = RequireApiKey,
):
    """One KYC object, a raw array, or ``{\"kyc_profiles\": [...]}``; one DB row per ``customer_id``."""
    try:
        if isinstance(body, dict):
            inner = body.get("kyc_profiles")
            if isinstance(inner, list):
                if not inner:
                    raise HTTPException(
                        status_code=422,
                        detail='Key "kyc_profiles" must be a non-empty array.',
                    )
                rows = inner
            else:
                rows = [body]
        elif isinstance(body, list):
            if not body:
                raise HTTPException(
                    status_code=422,
                    detail="Provide a non-empty array of KYC objects, or use POST /v1/kyc/create-bulk "
                    'with {"kyc_profiles": [...]}.',
                )
            if not all(isinstance(x, dict) for x in body):
                raise HTTPException(status_code=422, detail="Array body must contain only objects.")
            rows = body
        else:
            raise HTTPException(status_code=422, detail="Body must be a KYC object or an array of objects.")
        return _insert_kyc_profiles(rows)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_kyc_profile failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/kyc/create-bulk", response_model=DataStatusResponse)
async def create_kyc_profiles_bulk(
    body: Union[List[Dict[str, Any]], Dict[str, Any]],
    _: None = RequireApiKey,
):
    rows = bulk_rows(
        body,
        "kyc_profiles",
        'Body must be a JSON array, or {"kyc_profiles": [...]}.',
    )
    try:
        return _insert_kyc_profiles(rows)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_kyc_profiles_bulk failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
