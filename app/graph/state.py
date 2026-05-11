"""Investigation graph state."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator

from app.shared.enums import InvestigationStatus, TriagePriority
from app.shared.models import InvestigationWorkflowState


class StateManager:
    """In-memory store for investigation workflow snapshots."""
    
    def __init__(self):
        self._states: Dict[str, InvestigationWorkflowState] = {}
    
    def get_state(self, case_id: str) -> Optional[InvestigationWorkflowState]:
        """Get investigation state by case ID."""
        return self._states.get(case_id)
    
    def set_state(self, state: InvestigationWorkflowState) -> None:
        """Set investigation state."""
        self._states[state.case_id] = state
    
    def update_state(self, case_id: str, **updates) -> Optional[InvestigationWorkflowState]:
        """Update investigation state with new values."""
        current_state = self.get_state(case_id)
        if current_state:
            updated_state = current_state.model_copy(update=updates)
            self.set_state(updated_state)
            return updated_state
        return None
    
    def remove_state(self, case_id: str) -> bool:
        """Remove investigation state."""
        if case_id in self._states:
            del self._states[case_id]
            return True
        return False
    
    def list_states(self) -> List[InvestigationWorkflowState]:
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


def get_investigation_state(case_id: str) -> Optional[InvestigationWorkflowState]:
    """Get investigation state."""
    return state_manager.get_state(case_id)


def create_investigation_state(case_id: str, case_type: str, title: str,
                             description: str, priority: TriagePriority,
                             correlation_id: str) -> InvestigationWorkflowState:
    """Create new investigation state."""
    state = InvestigationWorkflowState.create_initial(
        case_id=case_id,
        case_type=case_type,
        title=title,
        description=description,
        priority=priority,
        correlation_id=correlation_id
    )
    state_manager.set_state(state)
    return state


def update_investigation_state(case_id: str, **updates) -> Optional[InvestigationWorkflowState]:
    """Update investigation state."""
    return state_manager.update_state(case_id, **updates)