"""Fraud memory service for PostgreSQL operations."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import asyncpg

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class MemoryType(str, Enum):
    """Types of fraud memory entries."""
    PATTERN = "pattern"
    ENTITY = "entity"
    TRANSACTION = "transaction"
    DEVICE = "device"
    LOCATION = "location"


class MemoryStatus(str, Enum):
    """Memory entry status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    ARCHIVED = "archived"


@dataclass
class FraudMemoryEntry:
    """Fraud memory entry structure."""
    memory_id: str
    memory_type: MemoryType
    entity_id: str
    entity_type: str
    pattern_type: str
    confidence: float
    risk_score: float
    frequency: int
    last_seen: datetime
    first_seen: datetime
    expires_at: Optional[datetime]
    status: MemoryStatus
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PostgreSQLFraudMemory:
    """PostgreSQL fraud memory operations."""
    
    def __init__(self):
        self.connection_string = settings.database_url
        self.ttl_days = settings.fraud_memory_ttl_days
        self._pool = None
        
    async def _get_pool(self):
        """Get PostgreSQL connection pool."""
        if not self._pool:
            self._pool = await asyncpg.create_pool(self.connection_string)
        return self._pool
    
    async def _execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute PostgreSQL query."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetch(query, *args)
            return [dict(row) for row in result]
    
    async def _execute_command(self, command: str, *args) -> str:
        """Execute PostgreSQL command."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            return await conn.execute(command, *args)
    
    async def write_entry(self, entry: FraudMemoryEntry) -> bool:
        """Write fraud memory entry to PostgreSQL."""
        query = """
            INSERT INTO fraud_memory (
                memory_id, memory_type, entity_id, entity_type, pattern_type,
                confidence, risk_score, frequency, last_seen, first_seen,
                expires_at, status, metadata, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                $11, $12, $13, $14, $15
            )
        """
        
        try:
            await self._execute_command(
                query, entry.memory_id, entry.memory_type.value, entry.entity_id,
                entry.entity_type, entry.pattern_type, entry.confidence,
                entry.risk_score, entry.frequency, entry.last_seen,
                entry.first_seen, entry.expires_at, entry.status.value,
                entry.metadata, entry.created_at, entry.updated_at
            )
            logger.info(f"Writing fraud memory entry: {entry.memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to write fraud memory entry: {e}")
            return False
    
    async def read_entry(self, memory_id: str) -> Optional[FraudMemoryEntry]:
        """Read fraud memory entry from PostgreSQL."""
        query = """
            SELECT * FROM fraud_memory WHERE memory_id = $1
        """
        
        try:
            result = await self._execute_query(query, memory_id)
            if result:
                return FraudMemoryEntry(**result[0])
            return None
        except Exception as e:
            logger.error(f"Failed to read fraud memory entry: {e}")
            return None
    
    async def query_by_entity(self, entity_id: str, 
                            entity_type: Optional[str] = None) -> List[FraudMemoryEntry]:
        """Query fraud memory entries by entity."""
        if entity_type:
            query = """
                SELECT * FROM fraud_memory 
                WHERE entity_id = $1 AND entity_type = $2 AND status = 'active'
                ORDER BY last_seen DESC
            """
            args = [entity_id, entity_type]
        else:
            query = """
                SELECT * FROM fraud_memory 
                WHERE entity_id = $1 AND status = 'active'
                ORDER BY last_seen DESC
            """
            args = [entity_id]
        
        try:
            result = await self._execute_query(query, *args)
            return [FraudMemoryEntry(**row) for row in result]
        except Exception as e:
            logger.error(f"Failed to query fraud memory by entity: {e}")
            return []
    
    async def query_by_pattern(self, pattern_type: str, 
                             min_confidence: float = 0.0) -> List[FraudMemoryEntry]:
        """Query fraud memory entries by pattern type."""
        query = """
            SELECT * FROM fraud_memory 
            WHERE pattern_type = $1 AND confidence >= $2 AND status = 'active'
            ORDER BY risk_score DESC
        """
        
        try:
            result = await self._execute_query(query, pattern_type, min_confidence)
            return [FraudMemoryEntry(**row) for row in result]
        except Exception as e:
            logger.error(f"Failed to query fraud memory by pattern: {e}")
            return []
    
    async def update_frequency(self, memory_id: str) -> bool:
        """Update frequency count for memory entry."""
        query = """
            UPDATE fraud_memory 
            SET frequency = frequency + 1, last_seen = $1, updated_at = $2
            WHERE memory_id = $3
        """
        
        try:
            await self._execute_command(query, datetime.utcnow(), datetime.utcnow(), memory_id)
            logger.info(f"Updating frequency for memory entry: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update memory frequency: {e}")
            return False
    
    async def expire_entries(self, before_date: datetime) -> int:
        """Expire old memory entries."""
        query = """
            UPDATE fraud_memory 
            SET status = 'expired', updated_at = $1
            WHERE expires_at < $2 AND status = 'active'
        """
        
        try:
            result = await self._execute_command(query, datetime.utcnow(), before_date)
            logger.info(f"Expiring entries before: {before_date}")
            return int(result.split()[-1]) if result else 0
        except Exception as e:
            logger.error(f"Failed to expire memory entries: {e}")
            return 0


class FraudMemoryService:
    """Fraud memory service with PostgreSQL backend."""
    
    def __init__(self):
        self.db = PostgreSQLFraudMemory()
        
    async def add_pattern(self, entity_id: str, entity_type: str,
                         pattern_type: str, confidence: float,
                         risk_score: float, metadata: Dict[str, Any] = None) -> Optional[str]:
        """Add fraud pattern to memory."""
        now = datetime.utcnow()
        memory_id = f"{entity_type}_{entity_id}_{pattern_type}_{int(now.timestamp())}"
        
        entry = FraudMemoryEntry(
            memory_id=memory_id,
            memory_type=MemoryType.PATTERN,
            entity_id=entity_id,
            entity_type=entity_type,
            pattern_type=pattern_type,
            confidence=confidence,
            risk_score=risk_score,
            frequency=1,
            last_seen=now,
            first_seen=now,
            expires_at=now + timedelta(days=self.db.ttl_days),
            status=MemoryStatus.ACTIVE,
            metadata=metadata or {},
            created_at=now,
            updated_at=now
        )
        
        success = await self.db.write_entry(entry)
        return memory_id if success else None
    
    async def get_entity_patterns(self, entity_id: str, 
                                entity_type: Optional[str] = None) -> List[FraudMemoryEntry]:
        """Get all patterns for an entity."""
        return await self.db.query_by_entity(entity_id, entity_type)
    
    async def get_high_risk_patterns(self, min_risk_score: float = 0.7) -> List[FraudMemoryEntry]:
        """Get high-risk patterns."""
        pattern_types = ['velocity_anomaly', 'device_anomaly', 'geo_anomaly', 'sanctions_hit']
        all_patterns = []
        
        for pattern_type in pattern_types:
            patterns = await self.db.query_by_pattern(pattern_type)
            all_patterns.extend(patterns)
        
        return [p for p in all_patterns if p.risk_score >= min_risk_score]
    
    async def update_pattern_frequency(self, memory_id: str) -> bool:
        """Update pattern frequency."""
        return await self.db.update_frequency(memory_id)
    
    async def cleanup_expired(self) -> int:
        """Clean up expired memory entries."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.db.ttl_days)
        return await self.db.expire_entries(cutoff_date)
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        queries = {
            'total': "SELECT COUNT(*) FROM fraud_memory",
            'active': "SELECT COUNT(*) FROM fraud_memory WHERE status = 'active'",
            'expired': "SELECT COUNT(*) FROM fraud_memory WHERE status = 'expired'",
            'patterns': "SELECT pattern_type, COUNT(*) FROM fraud_memory GROUP BY pattern_type",
            'entities': "SELECT entity_type, COUNT(*) FROM fraud_memory GROUP BY entity_type",
            'avg_risk': "SELECT AVG(risk_score) FROM fraud_memory WHERE status = 'active'"
        }
        
        try:
            total = await self.db._execute_query(queries['total'])
            active = await self.db._execute_query(queries['active'])
            expired = await self.db._execute_query(queries['expired'])
            patterns = await self.db._execute_query(queries['patterns'])
            entities = await self.db._execute_query(queries['entities'])
            avg_risk = await self.db._execute_query(queries['avg_risk'])
            
            return {
                'total_entries': total[0]['count'] if total else 0,
                'active_entries': active[0]['count'] if active else 0,
                'expired_entries': expired[0]['count'] if expired else 0,
                'pattern_types': {p['pattern_type']: p['count'] for p in patterns} if patterns else {},
                'entity_types': {e['entity_type']: e['count'] for e in entities} if entities else {},
                'avg_risk_score': float(avg_risk[0]['avg']) if avg_risk and avg_risk[0]['avg'] else 0.0,
                'last_updated': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {
                'total_entries': 0,
                'active_entries': 0,
                'expired_entries': 0,
                'pattern_types': {},
                'entity_types': {},
                'avg_risk_score': 0.0,
                'last_updated': datetime.utcnow().isoformat()
            }


# Global fraud memory service instance
fraud_memory_service = FraudMemoryService()


def get_fraud_memory_service() -> FraudMemoryService:
    """Get global fraud memory service instance."""
    return fraud_memory_service


async def add_fraud_pattern(entity_id: str, entity_type: str,
                           pattern_type: str, confidence: float,
                           risk_score: float, metadata: Dict[str, Any] = None) -> Optional[str]:
    """Add fraud pattern using global service."""
    return await get_fraud_memory_service().add_pattern(
        entity_id, entity_type, pattern_type, confidence, risk_score, metadata
    )


async def get_entity_patterns(entity_id: str, 
                            entity_type: Optional[str] = None) -> List[FraudMemoryEntry]:
    """Get entity patterns using global service."""
    return await get_fraud_memory_service().get_entity_patterns(entity_id, entity_type)


async def get_high_risk_patterns(min_risk_score: float = 0.7) -> List[FraudMemoryEntry]:
    """Get high-risk patterns using global service."""
    return await get_fraud_memory_service().get_high_risk_patterns(min_risk_score)