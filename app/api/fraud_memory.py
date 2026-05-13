"""Fraud memory endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import RequireApiKey
from app.services.fraud_memory_service import FraudMemoryService
from app.shared.models import (
    FraudPatternRequest,
    FraudPatternResponse,
    MemoryStatsResponse,
    PatternSearchRequest,
    PatternSearchResponse,
)

router = APIRouter(tags=["fraud_memory"])
fraud_memory_service = FraudMemoryService()


@router.get("/fraud-memory/patterns")
async def list_fraud_memories(
    limit: int = Query(200, ge=1, le=2000),
    active_only: bool = Query(True),
    _: None = RequireApiKey,
):
    """All stored fraud-memory patterns (newest first)."""
    response = fraud_memory_service.list_all_patterns(limit=limit, active_only=active_only)
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    return {"success": True, "data": response["data"]}


@router.post("/fraud-memory/patterns", response_model=FraudPatternResponse)
async def add_fraud_pattern(request: FraudPatternRequest, _: None = RequireApiKey):
    response = await fraud_memory_service.add_pattern(
        entity_id=request.entity_id,
        entity_type=request.entity_type,
        pattern_type=request.pattern_type.value,
        confidence=request.confidence,
        risk_score=request.risk_score,
        metadata=request.metadata,
    )
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    return FraudPatternResponse(**response["data"])


@router.get("/fraud-memory/patterns/entity/{entity_id}")
async def get_entity_patterns(
    entity_id: str,
    entity_type: Optional[str] = Query(None),
    _: None = RequireApiKey,
):
    response = fraud_memory_service.get_entity_patterns(entity_id, entity_type)
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    return response["data"]


@router.get("/fraud-memory/patterns/high-risk")
async def get_high_risk_patterns(
    min_risk_score: float = Query(0.7, ge=0.0, le=1.0),
    _: None = RequireApiKey,
):
    response = fraud_memory_service.get_high_risk_patterns(min_risk_score)
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    return response["data"]


@router.get("/fraud-memory/patterns/type/{pattern_type}")
async def get_patterns_by_type(
    pattern_type: str,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    _: None = RequireApiKey,
):
    response = fraud_memory_service.get_patterns_by_type(pattern_type, min_confidence)
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    return response["data"]


@router.put("/fraud-memory/patterns/{memory_id}/frequency")
async def update_pattern_frequency(memory_id: str, _: None = RequireApiKey):
    response = await fraud_memory_service.update_pattern_frequency(memory_id)
    if not response["success"]:
        raise HTTPException(status_code=404, detail=response["data"].get("error"))
    return response["data"]


@router.post("/fraud-memory/cleanup")
async def cleanup_expired_patterns(_: None = RequireApiKey):
    response = fraud_memory_service.cleanup_expired()
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    return response["data"]


@router.get("/fraud-memory/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(_: None = RequireApiKey):
    response = fraud_memory_service.get_memory_stats()
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    return MemoryStatsResponse(**response["data"])


@router.post("/fraud-memory/search", response_model=PatternSearchResponse)
async def search_patterns(request: PatternSearchRequest, _: None = RequireApiKey):
    response = fraud_memory_service.search_patterns(
        query=request.query,
        search_field=request.search_field,
    )
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    return PatternSearchResponse(**response["data"])


@router.delete("/fraud-memory/patterns/{memory_id}")
async def delete_pattern(memory_id: str, _: None = RequireApiKey):
    response = fraud_memory_service.delete_pattern(memory_id)
    if not response["success"]:
        raise HTTPException(status_code=404, detail=response["data"].get("error"))
    return response["data"]


@router.get("/fraud-memory/health")
async def fraud_memory_health():
    return {"status": "ok", "endpoint": "fraud_memory"}
