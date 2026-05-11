"""Transaction analysis endpoints."""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.api.deps import RequireApiKey
from app.services.transaction_service import TransactionService
from app.shared.models import TransactionAnalysisRequest

router = APIRouter(tags=["transactions"])
transaction_service = TransactionService()


@router.post("/transactions/analyze")
async def analyze_transaction_endpoint(
    request: TransactionAnalysisRequest,
    _: None = RequireApiKey,
):
    transaction_data = request.transaction.dict()
    customer_history = request.customer_history

    response = await transaction_service.analyze_transaction(transaction_data, customer_history)

    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))

    return response["data"]


@router.post("/transactions/velocity")
async def calculate_velocity(
    customer_id: str,
    transactions: List[Dict[str, Any]],
    window_hours: int = 24,
    _: None = RequireApiKey,
):
    response = transaction_service.calculate_velocity(transactions, window_hours)

    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))

    return response["data"]


@router.post("/transactions/fraud-pattern")
async def add_fraud_pattern(
    key: str,
    pattern: str,
    confidence: float,
    risk_score: float,
    metadata: Dict[str, Any] = None,
    _: None = RequireApiKey,
):
    response = transaction_service.add_fraud_pattern(key, pattern, confidence, risk_score, metadata)

    if not response["success"]:
        raise HTTPException(status_code=400, detail=response["data"].get("error"))

    return response["data"]


@router.get("/transactions/health")
async def transactions_health():
    return {"status": "ok", "endpoint": "transactions"}
