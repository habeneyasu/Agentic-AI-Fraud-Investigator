"""
Repository layer for data access patterns.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TypeVar, Generic
from datetime import datetime

from app.data.models import (
    InvestigationModel, InvestigationResult, AlertModel, EvidenceModel,
    TransactionModel, KYCEventModel, EntityModel
)
from app.core.logging import get_logger

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """Base repository with common functionality."""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self._storage: Dict[str, T] = {}
    
    def save(self, entity: T) -> bool:
        """Save entity to storage."""
        try:
            entity_id = self._get_entity_id(entity)
            self._storage[entity_id] = entity
            self.logger.debug(f"Saved entity {entity_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save entity: {e}")
            return False
    
    def get(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        return self._storage.get(entity_id)
    
    def get_all(self) -> List[T]:
        """Get all entities."""
        return list(self._storage.values())
    
    def delete(self, entity_id: str) -> bool:
        """Delete entity by ID."""
        if entity_id in self._storage:
            del self._storage[entity_id]
            self.logger.debug(f"Deleted entity {entity_id}")
            return True
        return False
    
    def exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        return entity_id in self._storage
    
    @abstractmethod
    def _get_entity_id(self, entity: T) -> str:
        """Get entity ID from entity object."""
        pass


class InvestigationRepository(BaseRepository[InvestigationModel]):
    """Repository for investigation data."""
    
    def _get_entity_id(self, entity: InvestigationModel) -> str:
        return entity.investigation_id
    
    def get_by_customer(self, customer_id: str) -> List[InvestigationModel]:
        """Get investigations by customer ID."""
        return [
            inv for inv in self._storage.values() 
            if inv.customer_id == customer_id
        ]
    
    def get_by_status(self, status: str) -> List[InvestigationModel]:
        """Get investigations by status."""
        return [
            inv for inv in self._storage.values() 
            if inv.metadata.get("status") == status
        ]
    
    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[InvestigationModel]:
        """Get investigations within date range."""
        return [
            inv for inv in self._storage.values()
            if start_date <= inv.timestamp <= end_date
        ]


class InvestigationResultRepository(BaseRepository[InvestigationResult]):
    """Repository for investigation results."""
    
    def _get_entity_id(self, entity: InvestigationResult) -> str:
        return entity.investigation_id
    
    def get_by_risk_score(self, min_score: float, max_score: float) -> List[InvestigationResult]:
        """Get investigations by risk score range."""
        return [
            result for result in self._storage.values()
            if min_score <= result.risk_score <= max_score
        ]
    
    def get_by_recommendation(self, recommendation: str) -> List[InvestigationResult]:
        """Get investigations by recommendation."""
        return [
            result for result in self._storage.values()
            if result.final_recommendation == recommendation
        ]


class AlertRepository(BaseRepository[AlertModel]):
    """Repository for alert data."""
    
    def _get_entity_id(self, entity: AlertModel) -> str:
        return entity.alert_id
    
    def get_by_investigation(self, investigation_id: str) -> List[AlertModel]:
        """Get alerts by investigation ID."""
        return [
            alert for alert in self._storage.values()
            if alert.investigation_id == investigation_id
        ]
    
    def get_by_type(self, alert_type: str) -> List[AlertModel]:
        """Get alerts by type."""
        return [
            alert for alert in self._storage.values()
            if alert.alert_type.value == alert_type
        ]
    
    def get_by_severity(self, severity: str) -> List[AlertModel]:
        """Get alerts by severity."""
        return [
            alert for alert in self._storage.values()
            if alert.severity.value == severity
        ]


class EvidenceRepository(BaseRepository[EvidenceModel]):
    """Repository for evidence data."""
    
    def _get_entity_id(self, entity: EvidenceModel) -> str:
        return entity.evidence_id
    
    def get_by_investigation(self, investigation_id: str) -> List[EvidenceModel]:
        """Get evidence by investigation ID."""
        return [
            evidence for evidence in self._storage.values()
            if evidence.investigation_id == investigation_id
        ]
    
    def get_by_category(self, category: str) -> List[EvidenceModel]:
        """Get evidence by category."""
        return [
            evidence for evidence in self._storage.values()
            if evidence.category == category
        ]
    
    def get_by_type(self, evidence_type: str) -> List[EvidenceModel]:
        """Get evidence by type."""
        return [
            evidence for evidence in self._storage.values()
            if evidence.type == evidence_type
        ]


class TransactionRepository(BaseRepository[TransactionModel]):
    """Repository for transaction data."""
    
    def _get_entity_id(self, entity: TransactionModel) -> str:
        return entity.transaction_id
    
    def get_by_customer(self, customer_id: str) -> List[TransactionModel]:
        """Get transactions by customer ID."""
        return [
            tx for tx in self._storage.values()
            if tx.customer_id == customer_id
        ]
    
    def get_by_amount_range(self, min_amount: float, max_amount: float) -> List[TransactionModel]:
        """Get transactions by amount range."""
        return [
            tx for tx in self._storage.values()
            if min_amount <= tx.amount <= max_amount
        ]
    
    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[TransactionModel]:
        """Get transactions within date range."""
        return [
            tx for tx in self._storage.values()
            if start_date <= tx.timestamp <= end_date
        ]


class KYCEventRepository(BaseRepository[KYCEventModel]):
    """Repository for KYC event data."""
    
    def _get_entity_id(self, entity: KYCEventModel) -> str:
        return f"{entity.customer_id}_{entity.event_type}_{entity.timestamp.isoformat()}"
    
    def get_by_customer(self, customer_id: str) -> List[KYCEventModel]:
        """Get KYC events by customer ID."""
        return [
            event for event in self._storage.values()
            if event.customer_id == customer_id
        ]
    
    def get_by_event_type(self, event_type: str) -> List[KYCEventModel]:
        """Get KYC events by type."""
        return [
            event for event in self._storage.values()
            if event.event_type == event_type
        ]


class EntityRepository(BaseRepository[EntityModel]):
    """Repository for entity data."""
    
    def _get_entity_id(self, entity: EntityModel) -> str:
        return f"{entity.name}_{entity.country_code}"
    
    def get_by_country(self, country_code: str) -> List[EntityModel]:
        """Get entities by country code."""
        return [
            entity for entity in self._storage.values()
            if entity.country_code == country_code
        ]
    
    def get_by_type(self, entity_type: str) -> List[EntityModel]:
        """Get entities by type."""
        return [
            entity for entity in self._storage.values()
            if entity.entity_type == entity_type
        ]


# Repository Factory
class RepositoryFactory:
    """Factory for creating repository instances."""
    
    _repositories = {
        "investigation": InvestigationRepository,
        "investigation_result": InvestigationResultRepository,
        "alert": AlertRepository,
        "evidence": EvidenceRepository,
        "transaction": TransactionRepository,
        "kyc_event": KYCEventRepository,
        "entity": EntityRepository
    }
    
    @classmethod
    def get_repository(cls, repository_type: str):
        """Get repository instance."""
        repository_class = cls._repositories.get(repository_type)
        if not repository_class:
            raise ValueError(f"Unknown repository type: {repository_type}")
        return repository_class()
    
    @classmethod
    def get_investigation_repository(cls) -> InvestigationRepository:
        """Get investigation repository."""
        return cls.get_repository("investigation")
    
    @classmethod
    def get_alert_repository(cls) -> AlertRepository:
        """Get alert repository."""
        return cls.get_repository("alert")
    
    @classmethod
    def get_evidence_repository(cls) -> EvidenceRepository:
        """Get evidence repository."""
        return cls.get_repository("evidence")
    
    @classmethod
    def get_transaction_repository(cls) -> TransactionRepository:
        """Get transaction repository."""
        return cls.get_repository("transaction")
