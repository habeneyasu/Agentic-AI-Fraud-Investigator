"""Sanctions watchlist and country-risk CRUD (sync SQLAlchemy)."""

from __future__ import annotations

from typing import Any, Dict, List, Literal

from fastapi import APIRouter, Body, HTTPException, Query

from app.api.deps import RequireApiKey
from app.api.response_models import DataStatusResponse
from app.core.logging import get_logger
from app.db.sync_session import sync_session
from app.models.orm_tables import CountryRiskORM, SanctionsWatchlistORM
from app.shared.models import SanctionsWriteRequest

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


def _serialize_watchlist_rows(rows: List[SanctionsWatchlistORM]) -> list[dict[str, Any]]:
    return [
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


def _serialize_country_risk_rows(rows: List[CountryRiskORM]) -> list[dict[str, Any]]:
    return [
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


def _list_watchlist_active() -> list[dict[str, Any]]:
    with sync_session() as session:
        rows = session.query(SanctionsWatchlistORM).filter(SanctionsWatchlistORM.is_active.is_(True)).all()
        return _serialize_watchlist_rows(rows)


def _list_country_risks() -> list[dict[str, Any]]:
    with sync_session() as session:
        rows = session.query(CountryRiskORM).order_by(CountryRiskORM.country_code).all()
        return _serialize_country_risk_rows(rows)


def _insert_watchlist_items(items: List[Dict[str, Any]]) -> DataStatusResponse:
    inserted = 0
    skipped_ids: list[str] = []
    staged: set[str] = set()
    with sync_session() as session:
        for row in items:
            eid = row.get("entity_id")
            if not eid:
                raise HTTPException(status_code=400, detail="Each watchlist row must include entity_id")
            eid_s = str(eid)
            if eid_s in staged:
                skipped_ids.append(eid_s)
                continue
            if session.query(SanctionsWatchlistORM).filter(SanctionsWatchlistORM.entry_id == eid).first():
                skipped_ids.append(eid_s)
                continue
            session.add(_sanctions_orm_from_payload(row))
            staged.add(eid_s)
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


def _insert_country_risk_items(items: List[Dict[str, Any]]) -> DataStatusResponse:
    inserted = 0
    skipped_codes: list[str] = []
    staged: set[str] = set()
    with sync_session() as session:
        for row in items:
            code = str(row.get("country_code", "")).strip().upper()
            if not code:
                raise HTTPException(status_code=400, detail="Each country row must include country_code")
            if code in staged:
                skipped_codes.append(code)
                continue
            if session.query(CountryRiskORM).filter(CountryRiskORM.country_code == code).first():
                skipped_codes.append(code)
                continue
            session.add(_country_risk_orm_from_payload(row))
            staged.add(code)
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


@router.get("/sanctions", response_model=DataStatusResponse)
async def get_sanctions_reference(
    resource: Literal["watchlist", "country_risks", "all"] = Query("all"),
    _: None = RequireApiKey,
):
    try:
        if resource == "watchlist":
            data = _list_watchlist_active()
            return DataStatusResponse(
                success=True,
                count=len(data),
                message=f"Listed {len(data)} watchlist row(s)",
                data=data,
            )
        if resource == "country_risks":
            data = _list_country_risks()
            return DataStatusResponse(
                success=True,
                count=len(data),
                message=f"Listed {len(data)} country risk row(s)",
                data=data,
            )
        wl = _list_watchlist_active()
        cr = _list_country_risks()
        payload = {"watchlist": wl, "country_risks": cr}
        return DataStatusResponse(
            success=True,
            count=len(wl) + len(cr),
            message=f"Listed {len(wl)} watchlist and {len(cr)} country risk row(s)",
            data=payload,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_sanctions_reference failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


def _looks_like_kyc_event_row(d: dict[str, Any]) -> bool:
    return bool("customer_id" in d and "event_type" in d and "entity_id" not in d)


def _looks_like_sanctions_watchlist_row(d: dict[str, Any]) -> bool:
    return bool("entity_id" in d and ("entity_name" in d or "entity_type" in d))


def _looks_like_country_risk_row(d: dict[str, Any]) -> bool:
    return bool(
        "country_code" in d
        and "country_name" in d
        and "risk_level" in d
        and "entity_id" not in d
    )


def _parse_sanctions_write_body(raw: Any) -> SanctionsWriteRequest:
    if isinstance(raw, list):
        if not raw:
            raise HTTPException(status_code=422, detail="Empty array body.")
        if not all(isinstance(x, dict) for x in raw):
            raise HTTPException(status_code=422, detail="Array body must contain only objects.")
        sample = raw[0]
        if _looks_like_kyc_event_row(sample):
            raise HTTPException(
                status_code=422,
                detail=(
                    "Payload looks like KYC events (customer_id + event_type). "
                    "Use POST /v1/kyc/create with this JSON, not POST /v1/sanctions."
                ),
            )
        if _looks_like_sanctions_watchlist_row(sample):
            return SanctionsWriteRequest(sanctions_entries=list(raw))
        if _looks_like_country_risk_row(sample):
            return SanctionsWriteRequest(country_risks=list(raw))
        raise HTTPException(
            status_code=422,
            detail=(
                "Unrecognized array for POST /v1/sanctions. Expected watchlist rows "
                "(entity_id, entity_name, …) or country-risk rows (country_code, country_name, …), "
                'or an object with "resource"+"items" / sanctions_data.json keys.'
            ),
        )
    if isinstance(raw, dict):
        return SanctionsWriteRequest.model_validate(raw)
    raise HTTPException(status_code=422, detail="Body must be a JSON object or array.")


def _merge_write_responses(a: DataStatusResponse, b: DataStatusResponse) -> DataStatusResponse:
    return DataStatusResponse(
        success=bool(a.success and b.success),
        count=int(a.count or 0) + int(b.count or 0),
        message=f"Watchlist: {a.message} | Country risks: {b.message}",
        data=None,
    )


@router.post("/sanctions", response_model=DataStatusResponse)
async def post_sanctions_reference(body: Any = Body(...), _: None = RequireApiKey):
    try:
        req = _parse_sanctions_write_body(body)
        if req.resource is not None:
            if req.resource == "watchlist":
                return _insert_watchlist_items(list(req.items or []))
            return _insert_country_risk_items(list(req.items or []))
        if req.sanctions_entries is not None and req.country_risks is not None:
            wl = _insert_watchlist_items(list(req.sanctions_entries))
            cr = _insert_country_risk_items(list(req.country_risks))
            return _merge_write_responses(wl, cr)
        if req.sanctions_entries is not None:
            return _insert_watchlist_items(list(req.sanctions_entries))
        if req.country_risks is not None:
            return _insert_country_risk_items(list(req.country_risks))
        raise HTTPException(
            status_code=422,
            detail="Invalid sanctions write body (expected resource+items or legacy sanctions_entries / country_risks).",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("post_sanctions_reference failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
