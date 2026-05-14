"""Resolution actions (freeze, reverse, notify, etc.)."""

from typing import Any, Dict, List, Optional
import logging
from datetime import datetime

from app.shared.enums import ActionType
from app.shared.models import ActionRequest, ActionResult

logger = logging.getLogger(__name__)


class ActionEngine:
    """Mock action engine for fraud investigation resolution."""
    
    def __init__(self):
        self.action_history: List[ActionResult] = []
        
    def _coerce_action_type(self, raw: Any) -> ActionType | None:
        if isinstance(raw, ActionType):
            return raw
        if isinstance(raw, str):
            for member in ActionType:
                if member.value == raw:
                    return member
        return None

    async def execute_action(self, request: ActionRequest) -> ActionResult:
        """Execute a fraud resolution action."""
        action_id = "pending"
        try:
            at = self._coerce_action_type(request.action_type)
            if at is None:
                return ActionResult(
                    success=False,
                    message=f"Unknown action type: {request.action_type!r}",
                    action_id=f"unknown_{request.case_id}",
                    case_id=request.case_id,
                    timestamp=datetime.utcnow(),
                )
            action_id = f"{at.value}_{request.case_id}_{datetime.utcnow().timestamp()}"

            if at == ActionType.FREEZE:
                result = await self._freeze_account(request, at)
            elif at == ActionType.REVERSE:
                result = await self._reverse_transaction(request, at)
            elif at == ActionType.BLOCK:
                result = await self._block_account(request, at)
            elif at == ActionType.SMS:
                result = await self._send_sms_notification(request, at)
            elif at == ActionType.CASE_CLOSED:
                result = await self._close_case(request, at)
            else:
                result = ActionResult(
                    success=False,
                    message=f"Unhandled action type: {at}",
                    action_id=action_id,
                    case_id=request.case_id,
                    timestamp=datetime.utcnow(),
                )

            self.action_history.append(result)
            logger.info("Action %s executed for case %s", at, request.case_id)

            return result

        except Exception as e:
            logger.error("Error executing action %s: %s", getattr(request, "action_type", "?"), e)
            return ActionResult(
                success=False,
                message=f"Action execution failed: {str(e)}",
                action_id=action_id,
                case_id=request.case_id,
                timestamp=datetime.utcnow(),
            )
    
    async def _freeze_account(self, request: ActionRequest, at: ActionType) -> ActionResult:
        """Freeze customer account."""
        return ActionResult(
            success=True,
            message=f"Account {request.target_id} frozen for case {request.case_id}",
            action_id=f"{at.value}_{request.case_id}",
            case_id=request.case_id,
            timestamp=datetime.utcnow(),
            details={
                "action": "account_frozen",
                "target_account": request.target_id,
                "reason": request.reason,
                "metadata": request.metadata,
            },
        )

    async def _reverse_transaction(self, request: ActionRequest, at: ActionType) -> ActionResult:
        """Reverse fraudulent transaction."""
        return ActionResult(
            success=True,
            message=f"Transaction {request.target_id} reversed for case {request.case_id}",
            action_id=f"{at.value}_{request.case_id}",
            case_id=request.case_id,
            timestamp=datetime.utcnow(),
            details={
                "action": "transaction_reversed",
                "target_transaction": request.target_id,
                "amount": request.metadata.get("amount") if request.metadata else None,
                "reason": request.reason,
            },
        )

    async def _block_account(self, request: ActionRequest, at: ActionType) -> ActionResult:
        """Block customer account."""
        return ActionResult(
            success=True,
            message=f"Account {request.target_id} blocked for case {request.case_id}",
            action_id=f"{at.value}_{request.case_id}",
            case_id=request.case_id,
            timestamp=datetime.utcnow(),
            details={
                "action": "account_blocked",
                "target_account": request.target_id,
                "reason": request.reason,
                "metadata": request.metadata,
            },
        )

    async def _send_sms_notification(self, request: ActionRequest, at: ActionType) -> ActionResult:
        """Send SMS notification to customer."""
        phone_number = request.metadata.get("phone_number") if request.metadata else None

        if not phone_number:
            return ActionResult(
                success=False,
                message="Phone number required for SMS notification",
                action_id=f"{at.value}_{request.case_id}",
                case_id=request.case_id,
                timestamp=datetime.utcnow(),
            )

        return ActionResult(
            success=True,
            message=f"SMS notification sent to {phone_number} for case {request.case_id}",
            action_id=f"{at.value}_{request.case_id}",
            case_id=request.case_id,
            timestamp=datetime.utcnow(),
            details={
                "action": "sms_sent",
                "phone_number": phone_number,
                "message": request.reason,
                "metadata": request.metadata,
            },
        )

    async def _close_case(self, request: ActionRequest, at: ActionType) -> ActionResult:
        """Close investigation after false-positive disposition (no remediation)."""
        return ActionResult(
            success=True,
            message=f"Case {request.case_id} closed — no further action",
            action_id=f"{at.value}_{request.case_id}",
            case_id=request.case_id,
            timestamp=datetime.utcnow(),
            details={
                "action": "case_closed",
                "reason": request.reason,
                "metadata": request.metadata,
            },
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