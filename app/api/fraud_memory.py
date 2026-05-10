"""
Fraud memory endpoints - Clean Architecture Implementation.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Security, Query
from fastapi.security.api_key import APIKeyHeader

from app.core.config import settings
from app.services.fraud_memory_service import FraudMemoryService
from app.shared.models import (
    FraudPatternRequest, FraudPatternResponse, MemoryStatsResponse,
    PatternSearchRequest, PatternSearchResponse
)

router = APIRouter(tags=["fraud_memory"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
fraud_memory_service = FraudMemoryService()


@router.post("/fraud-memory/patterns", response_model=FraudPatternResponse)
async def add_fraud_pattern(
    request: FraudPatternRequest,
    x_api_key: str | None = Security(api_key_header),
):
    """Add fraud pattern to memory."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = await fraud_memory_service.add_pattern(
        entity_id=request.entity_id,
        entity_type=request.entity_type,
        pattern_type=request.pattern_type.value,
        confidence=request.confidence,
        risk_score=request.risk_score,
        metadata=request.metadata
    )
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return FraudPatternResponse(**response["data"])


@router.get("/fraud-memory/patterns/entity/{entity_id}")
async def get_entity_patterns(
    entity_id: str,
    entity_type: Optional[str] = Query(None),
    x_api_key: str | None = Security(api_key_header),
):
    """Get all patterns for an entity."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = fraud_memory_service.get_entity_patterns(entity_id, entity_type)
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return response["data"]


@router.get("/fraud-memory/patterns/high-risk")
async def get_high_risk_patterns(
    min_risk_score: float = Query(0.7, ge=0.0, le=1.0),
    x_api_key: str | None = Security(api_key_header),
):
    """Get high-risk patterns."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = fraud_memory_service.get_high_risk_patterns(min_risk_score)
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return response["data"]


@router.get("/fraud-memory/patterns/type/{pattern_type}")
async def get_patterns_by_type(
    pattern_type: str,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    x_api_key: str | None = Security(api_key_header),
):
    """Get patterns by type."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = fraud_memory_service.get_patterns_by_type(pattern_type, min_confidence)
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return response["data"]


@router.put("/fraud-memory/patterns/{memory_id}/frequency")
async def update_pattern_frequency(
    memory_id: str,
    x_api_key: str | None = Security(api_key_header),
):
    """Update pattern frequency."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = await fraud_memory_service.update_pattern_frequency(memory_id)
    
    if not response["success"]:
        raise HTTPException(status_code=404, detail=response["data"].get("error"))
    
    return response["data"]


@router.post("/fraud-memory/cleanup")
async def cleanup_expired_patterns(
    x_api_key: str | None = Security(api_key_header),
):
    """Clean up expired memory entries."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = await fraud_memory_service.cleanup_expired()
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return response["data"]


@router.get("/fraud-memory/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(
    x_api_key: str | None = Security(api_key_header),
):
    """Get memory statistics."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = fraud_memory_service.get_memory_stats()
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return MemoryStatsResponse(**response["data"])


@router.post("/fraud-memory/search", response_model=PatternSearchResponse)
async def search_patterns(
    request: PatternSearchRequest,
    x_api_key: str | None = Security(api_key_header),
):
    """Search patterns by query."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = fraud_memory_service.search_patterns(
        query=request.query,
        search_field=request.search_field
    )
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    
    return PatternSearchResponse(**response["data"])


@router.delete("/fraud-memory/patterns/{memory_id}")
async def delete_pattern(
    memory_id: str,
    x_api_key: str | None = Security(api_key_header),
):
    """Delete pattern from memory."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    response = fraud_memory_service.delete_pattern(memory_id)
    
    if not response["success"]:
        raise HTTPException(status_code=404, detail=response["data"].get("error"))
    
    return response["data"]


@router.get("/fraud-memory/health")
async def fraud_memory_health():
    return {"status": "ok", "endpoint": "fraud_memory"}
