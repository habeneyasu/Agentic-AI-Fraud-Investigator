"""Sanctions watchlist and country-risk CRUD (sync SQLAlchemy)."""

from __future__ import annotations

from typing import Any, Dict, List, Union

from fastapi import APIRouter, HTTPException

from app.api.bulk_json import bulk_rows
from app.api.deps import RequireApiKey
from app.api.response_models import DataStatusResponse
from app.core.logging import get_logger
from app.db.sync_session import sync_session
from app.models.orm_tables import CountryRiskORM, SanctionsWatchlistORM

logger = get_logger(__name__)
router = APIRouter(tags=["sanctions"])


def _sanctions_orm_from_payload(row: Dict[str, Any]) -> SanctionsWatchlistORM:
    return SanctionsWatchlistORM(
        entry_id=row["entity_id"],
        entry_type=row["entity_type"],
        display_name=row["entity_name"],
        country_codes=row.get("countries", []),
        lists=row.get("sanctions_list", []),
        risk_tier=row.get("risk_level", "HIGH"),
        is_active=True,
        reference_payload={
            "date_added": row.get("date_added"),
            "reason": row.get("reason"),
            "risk_score": row.get("risk_score"),
            "sanction_type": row.get("sanction_type"),
            "aliases": row.get("aliases", []),
            "addresses": row.get("addresses", []),
            "identification_numbers": row.get("identification_numbers", []),
        },
    )


def _country_risk_orm_from_payload(row: Dict[str, Any]) -> CountryRiskORM:
    code = str(row["country_code"]).strip().upper()
    return CountryRiskORM(
        country_code=code,
        country_name=row["country_name"],
        risk_level=row["risk_level"],
        sanctions_active=bool(row.get("sanctions_active", False)),
        risk_score=float(row["risk_score"]),
    )


@router.get("/sanctions/list", response_model=DataStatusResponse)
async def list_sanctions_data(_: None = RequireApiKey):
    try:
        with sync_session() as session:
            rows = session.query(SanctionsWatchlistORM).filter(SanctionsWatchlistORM.is_active.is_(True)).all()
            data = [
                {
                    "entry_id": r.entry_id,
                    "entry_type": r.entry_type,
                    "display_name": r.display_name,
                    "country_codes": r.country_codes,
                    "lists": r.lists,
                    "risk_tier": r.risk_tier,
                    "is_active": r.is_active,
                    "reference_payload": r.reference_payload,
                }
                for r in rows
            ]
        return DataStatusResponse(success=True, count=len(data), message=f"Listed {len(data)} watchlist row(s)", data=data)
    except Exception as e:
        logger.error("list_sanctions_data failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/sanctions/create", response_model=DataStatusResponse)
async def create_sanctions_entry(sanctions_data: Dict[str, Any], _: None = RequireApiKey):
    eid = sanctions_data["entity_id"]
    try:
        with sync_session() as session:
            if session.query(SanctionsWatchlistORM).filter(SanctionsWatchlistORM.entry_id == eid).first():
                return DataStatusResponse(success=False, count=0, message=f"Sanctions entry {eid} already exists")
            session.add(_sanctions_orm_from_payload(sanctions_data))
            session.commit()
        return DataStatusResponse(success=True, count=1, message=f"Created sanctions entry {eid}")
    except Exception as e:
        logger.error("create_sanctions_entry failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/sanctions/create-bulk", response_model=DataStatusResponse)
async def create_sanctions_bulk(body: Union[List[Dict[str, Any]], Dict[str, Any]], _: None = RequireApiKey):
    rows = bulk_rows(
        body,
        "sanctions_entries",
        'Body must be a JSON array, or {"sanctions_entries": [...]}.',
    )
    inserted = 0
    skipped_ids: list[str] = []
    try:
        with sync_session() as session:
            for row in rows:
                eid = row.get("entity_id")
                if not eid:
                    raise HTTPException(status_code=400, detail="Each row must include entity_id")
                if session.query(SanctionsWatchlistORM).filter(SanctionsWatchlistORM.entry_id == eid).first():
                    skipped_ids.append(eid)
                    continue
                session.add(_sanctions_orm_from_payload(row))
                inserted += 1
            session.commit()
        msg = f"Inserted {inserted} watchlist row(s)"
        if skipped_ids:
            msg += f"; skipped duplicates: {', '.join(skipped_ids)}"
        return DataStatusResponse(
            success=True,
            count=inserted,
            message=msg,
            data=[{"skipped_entity_ids": skipped_ids}] if skipped_ids else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_sanctions_bulk failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sanctions/country-risks/list", response_model=DataStatusResponse)
async def list_country_risks(_: None = RequireApiKey):
    try:
        with sync_session() as session:
            rows = session.query(CountryRiskORM).order_by(CountryRiskORM.country_code).all()
            data = [
                {
                    "country_code": r.country_code,
                    "country_name": r.country_name,
                    "risk_level": r.risk_level,
                    "sanctions_active": r.sanctions_active,
                    "risk_score": r.risk_score,
                    "updated_at": r.updated_at.isoformat(),
                }
                for r in rows
            ]
        return DataStatusResponse(success=True, count=len(data), message=f"Listed {len(data)} country risk row(s)", data=data)
    except Exception as e:
        logger.error("list_country_risks failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/sanctions/country-risks/create", response_model=DataStatusResponse)
async def create_country_risk(row: Dict[str, Any], _: None = RequireApiKey):
    code = str(row["country_code"]).strip().upper()
    try:
        with sync_session() as session:
            if session.query(CountryRiskORM).filter(CountryRiskORM.country_code == code).first():
                return DataStatusResponse(success=False, count=0, message=f"Country risk for {code} already exists")
            session.add(_country_risk_orm_from_payload(row))
            session.commit()
        return DataStatusResponse(success=True, count=1, message=f"Created country risk for {code}")
    except Exception as e:
        logger.error("create_country_risk failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/sanctions/country-risks/create-bulk", response_model=DataStatusResponse)
async def create_country_risks_bulk(body: Union[List[Dict[str, Any]], Dict[str, Any]], _: None = RequireApiKey):
    rows = bulk_rows(
        body,
        "country_risks",
        'Body must be a JSON array, or {"country_risks": [...]}.',
    )
    inserted = 0
    skipped_codes: list[str] = []
    try:
        with sync_session() as session:
            for row in rows:
                code = str(row.get("country_code", "")).strip().upper()
                if not code:
                    raise HTTPException(status_code=400, detail="Each row must include country_code")
                if session.query(CountryRiskORM).filter(CountryRiskORM.country_code == code).first():
                    skipped_codes.append(code)
                    continue
                session.add(_country_risk_orm_from_payload(row))
                inserted += 1
            session.commit()
        msg = f"Inserted {inserted} country risk row(s)"
        if skipped_codes:
            msg += f"; skipped duplicates: {', '.join(skipped_codes)}"
        return DataStatusResponse(
            success=True,
            count=inserted,
            message=msg,
            data=[{"skipped_country_codes": skipped_codes}] if skipped_codes else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_country_risks_bulk failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
