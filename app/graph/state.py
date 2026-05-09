"""Enterprise investigation state management for LangGraph."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator

from app.core.schemas import TriagePriority


class InvestigationStatus(str, Enum):
    """Investigation workflow status."""
    INITIAL = "initial"
    DATA_COLLECTION = "data_collection"
    ANALYSIS = "analysis"
    ASSESSMENT = "assessment"
    DECISION = "decision"
    ACTION = "action"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    IN_PROGRESS = "in_progress"
    ESCALATED = "escalated"
    LOW_PRIORITY = "low_priority"
    RESOLVED = "resolved"


class InvestigationState(BaseModel):
    """Enterprise investigation state for LangGraph workflow."""
    
    # Core identifiers
    case_id: str = Field(..., description="Unique case identifier")
    investigation_id: Optional[str] = Field(None, description="Investigation identifier")
    correlation_id: str = Field(..., description="Request correlation ID")
    status: InvestigationStatus = Field(..., description="Current investigation status")
    previous_status: Optional[InvestigationStatus] = Field(None, description="Previous status")
    status_changed_at: Optional[datetime] = Field(None, description="When status last changed")
    
    # Case information
    case_type: str = Field(..., description="Type of fraud case")
    priority: TriagePriority = Field(..., description="Case priority level")
    risk_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Risk assessment score")
    
    # Investigation details
    title: str = Field(..., description="Investigation title")
    description: str = Field(..., description="Investigation description")
    assigned_investigator: Optional[str] = Field(None, description="Assigned investigator ID")
    estimated_duration_hours: Optional[float] = Field(None, ge=0.0, description="Estimated duration")
    
    # Evidence and analysis
    evidence_collected: List[Dict[str, Any]] = Field(default_factory=list, description="Collected evidence")
    analysis_results: Dict[str, Any] = Field(default_factory=dict, description="Analysis results")
    
    # Risk assessment
    risk_factors: List[str] = Field(default_factory=list, description="Identified risk factors")
    urgency_indicators: List[str] = Field(default_factory=list, description="Urgency indicators")
    
    # Actions and decisions
    actions_taken: List[str] = Field(default_factory=list, description="Actions performed")
    pending_actions: List[str] = Field(default_factory=list, description="Pending actions")
    escalation_reason: Optional[str] = Field(None, description="Reason for escalation")
    escalated_to: Optional[str] = Field(None, description="Escalation target")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")
    closed_at: Optional[datetime] = Field(None, description="Case closure time")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Workflow data
    transaction_data: Optional[List[Dict[str, Any]]] = Field(None, description="Transaction data")
    kyc_data: Optional[List[Dict[str, Any]]] = Field(None, description="KYC data")
    entities: Optional[List[Dict[str, Any]]] = Field(None, description="Entity data")
    customer_history: Optional[Dict[str, Any]] = Field(None, description="Customer history")
    anomalies: List[Dict[str, Any]] = Field(default_factory=list, description="Detected anomalies")
    kyc_anomalies: List[Dict[str, Any]] = Field(default_factory=list, description="KYC anomalies")
    sanctions_hits: List[Dict[str, Any]] = Field(default_factory=list, description="Sanctions hits")
    investigator_id: Optional[str] = Field(None, description="Investigator ID")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="State creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        use_enum_values = True
    
    @validator('status_changed_at', pre=True, always=True)
    def set_status_timestamp(cls, v, values):
        """Set status timestamp when status changes."""
        if 'status' in values and values.get('previous_status') != values['status']:
            return datetime.utcnow()
        return v
    
    def transition_to(self, new_status: InvestigationStatus, reason: Optional[str] = None) -> 'InvestigationState':
        """Create new state with status transition."""
        return self.copy(
            previous_status=self.status,
            status=new_status,
            status_changed_at=datetime.utcnow(),
            escalation_reason=reason if new_status == InvestigationStatus.ESCALATE else self.escalation_reason
        )
    
    def add_evidence(self, evidence: Dict[str, Any]) -> 'InvestigationState':
        """Add evidence to investigation."""
        return self.copy(
            evidence_collected=[*self.evidence_collected, evidence],
            updated_at=datetime.utcnow()
        )
    
    def add_action(self, action: str) -> 'InvestigationState':
        """Add action to investigation."""
        return self.copy(
            actions_taken=[*self.actions_taken, action],
            updated_at=datetime.utcnow()
        )
    
    def update_risk_assessment(self, risk_score: float, risk_factors: List[str]) -> 'InvestigationState':
        """Update risk assessment."""
        return self.copy(
            risk_score=risk_score,
            risk_factors=risk_factors,
            updated_at=datetime.utcnow()
        )
    
    def assign_investigator(self, investigator_id: str) -> 'InvestigationState':
        """Assign investigator to case."""
        return self.copy(
            assigned_investigator=investigator_id,
            updated_at=datetime.utcnow()
        )
    
    def add_analysis_result(self, key: str, value: Any) -> 'InvestigationState':
        """Add analysis result."""
        return self.copy(
            analysis_results={**self.analysis_results, key: value},
            updated_at=datetime.utcnow()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for LangGraph."""
        return {
            'case_id': self.case_id,
            'investigation_id': self.investigation_id,
            'correlation_id': self.correlation_id,
            'status': self.status,
            'case_type': self.case_type,
            'priority': self.priority.value,
            'risk_score': self.risk_score,
            'title': self.title,
            'description': self.description,
            'assigned_investigator': self.assigned_investigator,
            'evidence_collected': self.evidence_collected,
            'analysis_results': self.analysis_results,
            'risk_factors': self.risk_factors,
            'urgency_indicators': self.urgency_indicators,
            'actions_taken': self.actions_taken,
            'pending_actions': self.pending_actions,
            'escalation_reason': self.escalation_reason,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def create_initial(cls, case_id: str, case_type: str, title: str, 
                     description: str, priority: TriagePriority,
                     correlation_id: str) -> 'InvestigationState':
        """Create initial investigation state."""
        return cls(
            case_id=case_id,
            case_type=case_type,
            title=title,
            description=description,
            priority=priority,
            correlation_id=correlation_id,
            status=InvestigationStatus.INITIAL
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InvestigationState':
        """Create state from dictionary."""
        return cls(**data)


class StateManager:
    """Enterprise state management for investigation workflow."""
    
    def __init__(self):
        self._states: Dict[str, InvestigationState] = {}
    
    def get_state(self, case_id: str) -> Optional[InvestigationState]:
        """Get investigation state by case ID."""
        return self._states.get(case_id)
    
    def set_state(self, state: InvestigationState) -> None:
        """Set investigation state."""
        self._states[state.case_id] = state
    
    def update_state(self, case_id: str, **updates) -> Optional[InvestigationState]:
        """Update investigation state with new values."""
        current_state = self.get_state(case_id)
        if current_state:
            updated_state = current_state.copy(update=updates)
            self.set_state(updated_state)
            return updated_state
        return None
    
    def remove_state(self, case_id: str) -> bool:
        """Remove investigation state."""
        if case_id in self._states:
            del self._states[case_id]
            return True
        return False
    
    def list_states(self) -> List[InvestigationState]:
        """List all investigation states."""
        return list(self._states.values())
    
    def clear_completed(self) -> int:
        """Clear completed investigations."""
        completed_cases = [
            case_id for case_id, state in self._states.items()
            if state.status == InvestigationStatus.COMPLETED
        ]
        for case_id in completed_cases:
            del self._states[case_id]
        return len(completed_cases)


# Global state manager
state_manager = StateManager()


def get_investigation_state(case_id: str) -> Optional[InvestigationState]:
    """Get investigation state."""
    return state_manager.get_state(case_id)


def create_investigation_state(case_id: str, case_type: str, title: str,
                             description: str, priority: TriagePriority,
                             correlation_id: str) -> InvestigationState:
    """Create new investigation state."""
    state = InvestigationState.create_initial(
        case_id=case_id,
        case_type=case_type,
        title=title,
        description=description,
        priority=priority,
        correlation_id=correlation_id
    )
    state_manager.set_state(state)
    return state


def update_investigation_state(case_id: str, **updates) -> Optional[InvestigationState]:
    """Update investigation state."""
    return state_manager.update_state(case_id, **updates)