"""
Transaction analysis endpoints - Clean Architecture Implementation.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from app.core.config import settings
from app.services.transaction_service import TransactionService
from app.shared.models import TransactionAnalysisRequest, TransactionModel

router = APIRouter(tags=["transactions"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
transaction_service = TransactionService()


@router.post("/transactions/analyze")
async def analyze_transaction_endpoint(
    request: TransactionAnalysisRequest,
    x_api_key: str | None = Security(api_key_header),
):
    """Analyze transaction for fraud risk."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
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
    x_api_key: str | None = Security(api_key_header),
):
    """Calculate transaction velocity metrics."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
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
    x_api_key: str | None = Security(api_key_header),
):
    """Add fraud pattern to memory."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = transaction_service.add_fraud_pattern(key, pattern, confidence, risk_score, metadata)
    
    if not response["success"]:
        raise HTTPException(status_code=400, detail=response["data"].get("error"))
    
    return response["data"]


@router.get("/transactions/health")
async def transactions_health():
    return {"status": "ok", "endpoint": "transactions"}
