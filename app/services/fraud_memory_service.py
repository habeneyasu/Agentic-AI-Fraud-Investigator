"""
Fraud memory service - Clean Architecture Implementation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.services.base import BaseService
from app.shared.enums import MemoryType, MemoryStatus
from app.shared.models import FraudPatternRequest, FraudPatternResponse, MemoryStatsResponse, PatternSearchRequest, PatternSearchResponse


class FraudMemoryService(BaseService):
    """Service for fraud memory operations."""
    
    def __init__(self):
        super().__init__()
        self.memory_storage = {}  # In-memory storage for demo
        self.ttl_days = 30  # Default TTL
    
    async def add_pattern(
        self,
        entity_id: str,
        entity_type: str,
        pattern_type: str,
        confidence: float,
        risk_score: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add fraud pattern to memory."""
        self._log_operation("add_pattern", 
                          entity_id=entity_id, 
                          pattern_type=pattern_type)
        
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
                "updated_at": now
            }
            
            # Store in memory (in production, this would be database)
            self.memory_storage[memory_id] = entry
            
            return self._generate_response({
                "memory_id": memory_id,
                "entity_id": entity_id,
                "pattern_type": pattern_type,
                "confidence": confidence,
                "risk_score": risk_score
            })
        except Exception as e:
            self._log_error("add_pattern", e)
            return self._generate_response({"error": str(e)}, success=False)
    
    def get_entity_patterns(
        self,
        entity_id: str,
        entity_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all patterns for an entity."""
        self._log_operation("get_entity_patterns", entity_id=entity_id)
        
        try:
            patterns = []
            for entry in self.memory_storage.values():
                if (entry["entity_id"] == entity_id and 
                    entry["status"] == MemoryStatus.ACTIVE and
                    (entity_type is None or entry["entity_type"] == entity_type)):
                    patterns.append(entry)
            
            # Sort by last_seen descending
            patterns.sort(key=lambda x: x["last_seen"], reverse=True)
            
            return self._generate_response({
                "entity_id": entity_id,
                "entity_type": entity_type,
                "patterns": patterns,
                "count": len(patterns)
            })
        except Exception as e:
            self._log_error("get_entity_patterns", e)
            return self._generate_response({"error": str(e)}, success=False)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        self._log_operation("get_memory_stats")
        
        try:
            total_entries = len(self.memory_storage)
            active_entries = sum(1 for entry in self.memory_storage.values() 
                               if entry["status"] == MemoryStatus.ACTIVE)
            expired_entries = sum(1 for entry in self.memory_storage.values() 
                                if entry["status"] == MemoryStatus.EXPIRED)
            
            return self._generate_response({
                "total_entries": total_entries,
                "active_entries": active_entries,
                "expired_entries": expired_entries,
                "last_updated": datetime.utcnow().isoformat()
            })
        except Exception as e:
            self._log_error("get_memory_stats", e)
            return self._generate_response({"error": str(e)}, success=False)
