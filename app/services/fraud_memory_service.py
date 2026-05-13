"""Fraud pattern memory store (in-process demo)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.services.base import BaseService
from app.shared.enums import FraudPattern, MemoryStatus, MemoryType
from app.shared.models import FraudMemoryEntry

logger = get_logger(__name__)


def _serialize_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(entry)
    for k in ("last_seen", "first_seen", "expires_at", "created_at", "updated_at"):
        v = out.get(k)
        if isinstance(v, datetime):
            out[k] = v.isoformat() + "Z" if v.tzinfo is None else v.isoformat()
    return out


def _coerce_pattern(value: str) -> FraudPattern:
    try:
        return FraudPattern(value)
    except ValueError:
        return FraudPattern.VELOCITY_ANOMALY


def _entry_to_model(entry: Dict[str, Any]) -> FraudMemoryEntry:
    return FraudMemoryEntry(
        memory_id=entry["memory_id"],
        memory_type=entry["memory_type"],
        entity_id=entry["entity_id"],
        entity_type=entry["entity_type"],
        pattern_type=_coerce_pattern(str(entry["pattern_type"])),
        confidence=float(entry["confidence"]),
        risk_score=float(entry["risk_score"]),
        frequency=int(entry["frequency"]),
        last_seen=entry["last_seen"],
        first_seen=entry["first_seen"],
        expires_at=entry.get("expires_at"),
        status=entry["status"],
        metadata=dict(entry.get("metadata") or {}),
        created_at=entry["created_at"],
        updated_at=entry["updated_at"],
    )


class FraudMemoryService(BaseService):
    def __init__(self) -> None:
        super().__init__()
        self.memory_storage: Dict[str, Dict[str, Any]] = {}
        self.ttl_days = 30

    def list_all_patterns(self, *, limit: int = 200, active_only: bool = True) -> Dict[str, Any]:
        rows = list(self.memory_storage.values())
        if active_only:
            rows = [e for e in rows if e["status"] == MemoryStatus.ACTIVE]
        rows.sort(key=lambda x: x["last_seen"], reverse=True)
        rows = rows[:limit]
        return self._generate_response(
            {"patterns": [_serialize_entry(e) for e in rows], "count": len(rows)}
        )

    async def add_pattern(
        self,
        entity_id: str,
        entity_type: str,
        pattern_type: str,
        confidence: float,
        risk_score: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._log_operation("add_pattern", entity_id=entity_id, pattern_type=pattern_type)
        try:
            now = datetime.utcnow()
            memory_id = f"{entity_type}_{entity_id}_{pattern_type}_{int(now.timestamp())}"
            entry = {
                "memory_id": memory_id,
                "memory_type": MemoryType.PATTERN,
                "entity_id": entity_id,
                "entity_type": entity_type,
                "pattern_type": pattern_type,
                "confidence": confidence,
                "risk_score": risk_score,
                "frequency": 1,
                "last_seen": now,
                "first_seen": now,
                "expires_at": now + timedelta(days=self.ttl_days),
                "status": MemoryStatus.ACTIVE,
                "metadata": metadata or {},
                "created_at": now,
                "updated_at": now,
            }
            self.memory_storage[memory_id] = entry
            return self._generate_response(
                {
                    "memory_id": memory_id,
                    "entity_id": entity_id,
                    "pattern_type": _coerce_pattern(pattern_type),
                    "confidence": confidence,
                    "risk_score": risk_score,
                    "created_at": now,
                }
            )
        except Exception as e:
            self._log_error("add_pattern", e)
            return self._generate_response({"error": str(e)}, success=False)

    async def persist_hitl_outcome(
        self,
        *,
        entity_id: str,
        entity_type: str,
        risk_score: float,
        confidence: float,
        pattern_type: str,
        metadata: Dict[str, Any],
    ) -> None:
        try:
            r = await self.add_pattern(
                entity_id=entity_id,
                entity_type=entity_type,
                pattern_type=pattern_type,
                confidence=min(1.0, max(0.0, confidence)),
                risk_score=min(1.0, max(0.0, risk_score)),
                metadata=metadata,
            )
            if not r.get("success"):
                logger.warning("fraud_memory_persist_failed", detail=r.get("data"))
        except Exception as e:
            logger.warning("fraud_memory_persist_exception", error=str(e))

    def get_entity_patterns(
        self,
        entity_id: str,
        entity_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._log_operation("get_entity_patterns", entity_id=entity_id)
        try:
            patterns = [
                e
                for e in self.memory_storage.values()
                if e["entity_id"] == entity_id
                and e["status"] == MemoryStatus.ACTIVE
                and (entity_type is None or e["entity_type"] == entity_type)
            ]
            patterns.sort(key=lambda x: x["last_seen"], reverse=True)
            return self._generate_response(
                {
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "patterns": [_serialize_entry(p) for p in patterns],
                    "count": len(patterns),
                }
            )
        except Exception as e:
            self._log_error("get_entity_patterns", e)
            return self._generate_response({"error": str(e)}, success=False)

    def get_high_risk_patterns(self, min_risk_score: float) -> Dict[str, Any]:
        rows = [
            e
            for e in self.memory_storage.values()
            if e["status"] == MemoryStatus.ACTIVE and float(e.get("risk_score") or 0) >= min_risk_score
        ]
        rows.sort(key=lambda x: x["last_seen"], reverse=True)
        return self._generate_response(
            {"patterns": [_serialize_entry(e) for e in rows], "count": len(rows)}
        )

    def get_patterns_by_type(self, pattern_type: str, min_confidence: float) -> Dict[str, Any]:
        rows = [
            e
            for e in self.memory_storage.values()
            if e["status"] == MemoryStatus.ACTIVE
            and str(e.get("pattern_type")) == pattern_type
            and float(e.get("confidence") or 0) >= min_confidence
        ]
        rows.sort(key=lambda x: x["last_seen"], reverse=True)
        return self._generate_response(
            {"pattern_type": pattern_type, "patterns": [_serialize_entry(e) for e in rows], "count": len(rows)}
        )

    async def update_pattern_frequency(self, memory_id: str) -> Dict[str, Any]:
        entry = self.memory_storage.get(memory_id)
        if not entry:
            return self._generate_response({"error": "Not found"}, success=False)
        entry["frequency"] = int(entry.get("frequency") or 1) + 1
        entry["last_seen"] = datetime.utcnow()
        entry["updated_at"] = datetime.utcnow()
        return self._generate_response({"memory_id": memory_id, "frequency": entry["frequency"]})

    def cleanup_expired(self) -> Dict[str, Any]:
        now = datetime.utcnow()
        n = 0
        for e in self.memory_storage.values():
            exp = e.get("expires_at")
            if isinstance(exp, datetime) and exp < now and e["status"] == MemoryStatus.ACTIVE:
                e["status"] = MemoryStatus.EXPIRED
                n += 1
        return self._generate_response({"expired_marked": n})

    def search_patterns(self, query: str, search_field: str) -> Dict[str, Any]:
        q = (query or "").strip().lower()
        rows: List[Dict[str, Any]] = []
        for e in self.memory_storage.values():
            if e["status"] != MemoryStatus.ACTIVE:
                continue
            hay = ""
            if search_field == "entity_id":
                hay = str(e.get("entity_id", "")).lower()
            elif search_field == "pattern_type":
                hay = str(e.get("pattern_type", "")).lower()
            else:
                hay = str(e.get("metadata", {})).lower()
            if q in hay:
                rows.append(e)
        rows.sort(key=lambda x: x["last_seen"], reverse=True)
        models = [_entry_to_model(e) for e in rows[:100]]
        return self._generate_response(
            {"query": query, "search_field": search_field, "patterns": models, "count": len(models)}
        )

    def delete_pattern(self, memory_id: str) -> Dict[str, Any]:
        if memory_id not in self.memory_storage:
            return self._generate_response({"error": "Not found"}, success=False)
        del self.memory_storage[memory_id]
        return self._generate_response({"memory_id": memory_id, "deleted": True})

    def get_memory_stats(self) -> Dict[str, Any]:
        self._log_operation("get_memory_stats")
        try:
            entries = list(self.memory_storage.values())
            active = [e for e in entries if e["status"] == MemoryStatus.ACTIVE]
            expired = [e for e in entries if e["status"] == MemoryStatus.EXPIRED]
            pt: Dict[str, int] = {}
            et: Dict[str, int] = {}
            rs_sum = 0.0
            for e in active:
                pt[str(e.get("pattern_type", "unknown"))] = pt.get(str(e.get("pattern_type", "unknown")), 0) + 1
                et[str(e.get("entity_type", "unknown"))] = et.get(str(e.get("entity_type", "unknown")), 0) + 1
                rs_sum += float(e.get("risk_score") or 0)
            n_active = len(active)
            avg_risk = rs_sum / n_active if n_active else 0.0
            now = datetime.utcnow()
            return self._generate_response(
                {
                    "total_entries": len(entries),
                    "active_entries": n_active,
                    "expired_entries": len(expired),
                    "pattern_types": pt,
                    "entity_types": et,
                    "avg_risk_score": avg_risk,
                    "last_updated": now,
                }
            )
        except Exception as e:
            self._log_error("get_memory_stats", e)
            return self._generate_response({"error": str(e)}, success=False)
