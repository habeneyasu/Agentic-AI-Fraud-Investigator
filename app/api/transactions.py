"""Transaction CRUD (sync SQLAlchemy; same DB as async ORM)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Union

from fastapi import APIRouter, Body, HTTPException

from app.api.bulk_json import bulk_rows
from app.api.deps import RequireApiKey
from app.api.response_models import DataStatusResponse
from app.core.logging import get_logger
from app.db.sync_session import sync_session
from app.models.orm_tables import TransactionORM

logger = get_logger(__name__)
router = APIRouter(tags=["transactions"])


def _transaction_orm_from_payload(transaction_data: Dict[str, Any]) -> TransactionORM:
    return TransactionORM(
        transaction_id=transaction_data["transaction_id"],
        customer_id=transaction_data["customer_id"],
        amount=transaction_data["amount"],
        currency=transaction_data.get("currency", "USD"),
        occurred_at=datetime.fromisoformat(transaction_data["timestamp"].replace("Z", "+00:00")),
        transaction_type=transaction_data["transaction_type"],
        source_account=transaction_data.get("source_account"),
        destination_account=transaction_data.get("destination_account"),
        destination_country=transaction_data.get("destination_country"),
        narrative=transaction_data.get("description"),
        raw_payload={
            "ip_address": transaction_data.get("ip_address"),
            "device_id": transaction_data.get("device_id"),
            "risk_indicators": transaction_data.get("risk_indicators", []),
        },
    )


def _insert_transactions(rows: List[Dict[str, Any]]) -> DataStatusResponse:
    inserted = 0
    skipped_ids: list[str] = []
    staged_in_batch: set[str] = set()
    with sync_session() as session:
        for row in rows:
            tid = row.get("transaction_id")
            if not tid:
                raise HTTPException(status_code=400, detail="Each row must include transaction_id")
            if tid in staged_in_batch:
                skipped_ids.append(tid)
                continue
            if session.query(TransactionORM).filter(TransactionORM.transaction_id == tid).first():
                skipped_ids.append(tid)
                continue
            session.add(_transaction_orm_from_payload(row))
            staged_in_batch.add(tid)
            inserted += 1
        session.commit()
    msg = f"Inserted {inserted} transaction(s)"
    if skipped_ids:
        msg += f"; skipped (already in DB or repeated in this request): {', '.join(skipped_ids)}"
    return DataStatusResponse(
        success=True,
        count=inserted,
        message=msg,
        data=[{"skipped_transaction_ids": skipped_ids}] if skipped_ids else None,
    )


@router.get("/transactions/list", response_model=DataStatusResponse)
async def list_transactions(_: None = RequireApiKey):
    try:
        with sync_session() as session:
            rows = session.query(TransactionORM).all()
            data = [
                {
                    "transaction_id": tx.transaction_id,
                    "customer_id": tx.customer_id,
                    "amount": tx.amount,
                    "currency": tx.currency,
                    "occurred_at": tx.occurred_at.isoformat(),
                    "transaction_type": tx.transaction_type,
                    "source_account": tx.source_account,
                    "destination_account": tx.destination_account,
                    "destination_country": tx.destination_country,
                    "narrative": tx.narrative,
                }
                for tx in rows
            ]
        return DataStatusResponse(
            success=True,
            count=len(data),
            message=f"Listed {len(data)} transaction(s)",
            data=data,
        )
    except Exception as e:
        logger.error("list_transactions failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/transactions/create", response_model=DataStatusResponse)
async def create_transaction(
    body: Union[Dict[str, Any], List[Dict[str, Any]]] = Body(...),
    _: None = RequireApiKey,
):
    """Accept one transaction object, a raw array, or ``{\"transactions\": [...]}`` (same rows as create-bulk)."""
    try:
        if isinstance(body, dict):
            inner = body.get("transactions")
            if isinstance(inner, list):
                if not inner:
                    raise HTTPException(
                        status_code=422,
                        detail='Key "transactions" must be a non-empty array. For a wrapped single row use '
                        '`{"transactions": [{...}]}`.',
                    )
                rows = inner
            else:
                rows = [body]
        elif isinstance(body, list):
            if not body:
                raise HTTPException(
                    status_code=422,
                    detail="Provide a non-empty array of transactions, or use POST /v1/transactions/create-bulk "
                    'with {"transactions": [...]}.',
                )
            if not all(isinstance(x, dict) for x in body):
                raise HTTPException(status_code=422, detail="Array body must contain only transaction objects.")
            rows = body
        else:
            raise HTTPException(status_code=422, detail="Body must be a transaction object or an array of objects.")
        return _insert_transactions(rows)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_transaction failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/transactions/create-bulk", response_model=DataStatusResponse)
async def create_transactions_bulk(
    body: Union[List[Dict[str, Any]], Dict[str, Any]],
    _: None = RequireApiKey,
):
    rows = bulk_rows(
        body,
        "transactions",
        'Body must be a JSON array, or {"transactions": [...]}.',
    )
    try:
        return _insert_transactions(rows)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_transactions_bulk failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
