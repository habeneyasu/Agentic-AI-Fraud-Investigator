"""Action engine for fraud investigation resolution actions."""

from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Available fraud resolution actions."""
    FREEZE = "freeze"
    REVERSE = "reverse"
    BLOCK = "block"
    SMS = "sms"


@dataclass
class ActionRequest:
    """Request for fraud resolution action."""
    action_type: ActionType
    case_id: str
    reason: str
    target_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ActionResult:
    """Result of action execution."""
    success: bool
    message: str
    action_id: str
    case_id: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


class ActionEngine:
    """Mock action engine for fraud investigation resolution."""
    
    def __init__(self):
        self.action_history: List[ActionResult] = []
        
    async def execute_action(self, request: ActionRequest) -> ActionResult:
        """Execute a fraud resolution action."""
        try:
            action_id = f"{request.action_type.value}_{request.case_id}_{datetime.utcnow().timestamp()}"
            
            if request.action_type == ActionType.FREEZE:
                result = await self._freeze_account(request)
            elif request.action_type == ActionType.REVERSE:
                result = await self._reverse_transaction(request)
            elif request.action_type == ActionType.BLOCK:
                result = await self._block_account(request)
            elif request.action_type == ActionType.SMS:
                result = await self._send_sms_notification(request)
            else:
                result = ActionResult(
                    success=False,
                    message=f"Unknown action type: {request.action_type}",
                    action_id=action_id,
                    case_id=request.case_id,
                    timestamp=datetime.utcnow()
                )
            
            self.action_history.append(result)
            logger.info(f"Action {request.action_type} executed for case {request.case_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing action {request.action_type}: {e}")
            return ActionResult(
                success=False,
                message=f"Action execution failed: {str(e)}",
                action_id=action_id,
                case_id=request.case_id,
                timestamp=datetime.utcnow()
            )
    
    async def _freeze_account(self, request: ActionRequest) -> ActionResult:
        """Freeze customer account."""
        return ActionResult(
            success=True,
            message=f"Account {request.target_id} frozen for case {request.case_id}",
            action_id=f"{request.action_type.value}_{request.case_id}",
            case_id=request.case_id,
            timestamp=datetime.utcnow(),
            details={
                "action": "account_frozen",
                "target_account": request.target_id,
                "reason": request.reason,
                "metadata": request.metadata
            }
        )
    
    async def _reverse_transaction(self, request: ActionRequest) -> ActionResult:
        """Reverse fraudulent transaction."""
        return ActionResult(
            success=True,
            message=f"Transaction {request.target_id} reversed for case {request.case_id}",
            action_id=f"{request.action_type.value}_{request.case_id}",
            case_id=request.case_id,
            timestamp=datetime.utcnow(),
            details={
                "action": "transaction_reversed",
                "target_transaction": request.target_id,
                "amount": request.metadata.get("amount") if request.metadata else None,
                "reason": request.reason
            }
        )
    
    async def _block_account(self, request: ActionRequest) -> ActionResult:
        """Block customer account."""
        return ActionResult(
            success=True,
            message=f"Account {request.target_id} blocked for case {request.case_id}",
            action_id=f"{request.action_type.value}_{request.case_id}",
            case_id=request.case_id,
            timestamp=datetime.utcnow(),
            details={
                "action": "account_blocked",
                "target_account": request.target_id,
                "reason": request.reason,
                "metadata": request.metadata
            }
        )
    
    async def _send_sms_notification(self, request: ActionRequest) -> ActionResult:
        """Send SMS notification to customer."""
        phone_number = request.metadata.get("phone_number") if request.metadata else None
        
        if not phone_number:
            return ActionResult(
                success=False,
                message="Phone number required for SMS notification",
                action_id=f"{request.action_type.value}_{request.case_id}",
                case_id=request.case_id,
                timestamp=datetime.utcnow()
            )
        
        return ActionResult(
            success=True,
            message=f"SMS notification sent to {phone_number} for case {request.case_id}",
            action_id=f"{request.action_type.value}_{request.case_id}",
            case_id=request.case_id,
            timestamp=datetime.utcnow(),
            details={
                "action": "sms_sent",
                "phone_number": phone_number,
                "message": request.reason,
                "metadata": request.metadata
            }
        )
    
    def get_action_history(self, case_id: Optional[str] = None) -> List[ActionResult]:
        """Get action history for a specific case or all actions."""
        if case_id:
            return [action for action in self.action_history if action.case_id == case_id]
        return self.action_history
    
    def get_action_by_id(self, action_id: str) -> Optional[ActionResult]:
        """Get specific action by ID."""
        for action in self.action_history:
            if action.action_id == action_id:
                return action
        return None