"""Fraud memory — consolidated read/write surface.

- ``GET /v1/fraud-memory`` — ``view=patterns|stats``; for patterns use ``filter`` to slice
  (all, entity, high_risk, type, search). Replaces the former multiple GET routes.
- ``POST /v1/fraud-memory`` — ``operation`` for add_pattern, cleanup, bump_frequency, delete.
- ``GET /v1/fraud-memory/health`` — liveness (no API key).
"""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import RequireApiKey
from app.services.fraud_memory_service import FraudMemoryService
from app.shared.models import (
    FraudMemoryMutationRequest,
    FraudPatternResponse,
    PatternSearchResponse,
)

router = APIRouter(tags=["fraud_memory"])
fraud_memory_service = FraudMemoryService()


@router.get("/fraud-memory")
async def fraud_memory_read(
    view: Literal["patterns", "stats"] = Query("patterns"),
    pattern_filter: Literal["all", "entity", "high_risk", "type", "search"] = Query("all", alias="filter"),
    limit: int = Query(200, ge=1, le=2000),
    active_only: bool = Query(True),
    entity_id: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    min_risk_score: float = Query(0.7, ge=0.0, le=1.0),
    pattern_type: Optional[str] = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    query: Optional[str] = Query(None),
    search_field: str = Query("entity_id"),
    _: None = RequireApiKey,
):
    if view == "stats":
        response = fraud_memory_service.get_memory_stats()
        if not response["success"]:
            raise HTTPException(status_code=500, detail=response["data"].get("error"))
        return {"success": True, "view": "stats", "data": response["data"]}

    pf = pattern_filter
    if pf == "all":
        response = fraud_memory_service.list_all_patterns(limit=limit, active_only=active_only)
        if not response["success"]:
            raise HTTPException(status_code=500, detail=response["data"].get("error"))
        return {"success": True, "view": "patterns", "filter": "all", "data": response["data"]}

    if pf == "entity":
        if not entity_id or not str(entity_id).strip():
            raise HTTPException(status_code=422, detail="entity_id is required when filter=entity")
        response = fraud_memory_service.get_entity_patterns(entity_id.strip(), entity_type)
        if not response["success"]:
            raise HTTPException(status_code=500, detail=response["data"].get("error"))
        return {"success": True, "view": "patterns", "filter": "entity", "data": response["data"]}

    if pf == "high_risk":
        response = fraud_memory_service.get_high_risk_patterns(min_risk_score)
        if not response["success"]:
            raise HTTPException(status_code=500, detail=response["data"].get("error"))
        return {"success": True, "view": "patterns", "filter": "high_risk", "data": response["data"]}

    if pf == "type":
        if not pattern_type or not str(pattern_type).strip():
            raise HTTPException(status_code=422, detail="pattern_type is required when filter=type")
        response = fraud_memory_service.get_patterns_by_type(pattern_type.strip(), min_confidence)
        if not response["success"]:
            raise HTTPException(status_code=500, detail=response["data"].get("error"))
        return {"success": True, "view": "patterns", "filter": "type", "data": response["data"]}

    if not query or not str(query).strip():
        raise HTTPException(status_code=422, detail="query is required when filter=search")
    response = fraud_memory_service.search_patterns(query=query.strip(), search_field=search_field)
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response["data"].get("error"))
    pr = PatternSearchResponse(**response["data"])
    return {"success": True, "view": "patterns", "filter": "search", "data": pr.model_dump(mode="json")}


@router.post("/fraud-memory")
async def fraud_memory_mutate(body: FraudMemoryMutationRequest, _: None = RequireApiKey):
    if body.operation == "add_pattern":
        assert body.pattern is not None
        p = body.pattern
        response = await fraud_memory_service.add_pattern(
            entity_id=p.entity_id,
            entity_type=p.entity_type,
            pattern_type=p.pattern_type.value,
            confidence=p.confidence,
            risk_score=p.risk_score,
            metadata=p.metadata,
        )
        if not response["success"]:
            raise HTTPException(status_code=500, detail=response["data"].get("error"))
        return FraudPatternResponse(**response["data"])

    if body.operation == "cleanup":
        response = fraud_memory_service.cleanup_expired()
        if not response["success"]:
            raise HTTPException(status_code=500, detail=response["data"].get("error"))
        return {"success": True, "operation": "cleanup", "data": response["data"]}

    if body.operation == "bump_frequency":
        mid = (body.memory_id or "").strip()
        response = await fraud_memory_service.update_pattern_frequency(mid)
        if not response["success"]:
            raise HTTPException(status_code=404, detail=response["data"].get("error"))
        return {"success": True, "operation": "bump_frequency", "data": response["data"]}

    mid = (body.memory_id or "").strip()
    response = fraud_memory_service.delete_pattern(mid)
    if not response["success"]:
        raise HTTPException(status_code=404, detail=response["data"].get("error"))
    return {"success": True, "operation": "delete", "data": response["data"]}


@router.get("/fraud-memory/health")
async def fraud_memory_health():
    return {"status": "ok", "endpoint": "fraud_memory"}
