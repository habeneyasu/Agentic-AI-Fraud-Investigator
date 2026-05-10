"""Audit API endpoints for fraud investigation audit trails."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status, Query
import logging

from app.core.security import get_current_user, verify_role
from app.services.action_engine import ActionEngine, ActionResult
from app.models.case import Case, CaseStatus
from app.models.audit_api import AuditRequest, AuditResponse, AuditEntry, AuditSummary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/audit", tags=["Audit"])


@router.get("/{id}", response_model=AuditResponse)
async def get_audit_trail(
    audit_id: str,
    filters: AuditRequest = Query(),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AuditResponse:
    """Get comprehensive audit trail for a specific case or all cases."""
    try:
        # Verify user has appropriate role
        verify_role(current_user, ["ANALYST", "ADMIN"])
        
        action_engine = ActionEngine()
        
        # Get audit trail from action engine
        action_history = action_engine.get_action_history(audit_id)
        
        # Apply filters
        filtered_trail = action_history
        
        if filters.case_id:
            filtered_trail = [action for action in filtered_trail 
                            if action.case_id == filters.case_id]
        
        if filters.action_type:
            filtered_trail = [action for action in filtered_trail 
                            if filters.action_type.lower() in action.action_id.lower()]
        
        if filters.user_id:
            filtered_trail = [action for action in filtered_trail 
                            if action.details and action.details.get("executed_by") == filters.user_id]
        
        if filters.start_date:
            filtered_trail = [action for action in filtered_trail 
                            if action.timestamp >= filters.start_date]
        
        if filters.end_date:
            filtered_trail = [action for action in filtered_trail 
                            if action.timestamp <= filters.end_date]
        
        # Apply limit
        if filters.limit:
            filtered_trail = filtered_trail[:filters.limit]
        
        # Get case details if case_id provided
        case_details = None
        if audit_id and audit_id != "all":
            from app.services.fraud_memory import FraudMemory
            fraud_memory = FraudMemory()
            case_details = await fraud_memory.get_case(audit_id)
        
        logger.info(f"Audit trail retrieved for {audit_id} with {len(filtered_trail)} entries")
        
        return AuditResponse(
            success=True,
            message=f"Retrieved {len(filtered_trail)} audit entries",
            total_count=len(filtered_trail),
            audit_trail=[
                {
                    "action_id": action.action_id,
                    "case_id": action.case_id,
                    "action_type": action.action_id.split("_")[0] if "_" in action.action_id else action.action_id,
                    "success": action.success,
                    "message": action.message,
                    "timestamp": action.timestamp.isoformat(),
                    "details": action.details,
                    "executed_by": action.details.get("executed_by") if action.details else None
                }
                for action in filtered_trail
            ],
            filters_applied={
                "case_id": filters.case_id,
                "action_type": filters.action_type,
                "user_id": filters.user_id,
                "start_date": filters.start_date.isoformat() if filters.start_date else None,
                "end_date": filters.end_date.isoformat() if filters.end_date else None,
                "limit": filters.limit
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving audit trail for {audit_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit trail"
        )


@router.get("/summary")
async def get_audit_summary(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get audit summary statistics."""
    try:
        # Verify user has appropriate role
        verify_role(current_user, ["ANALYST", "ADMIN"])
        
        action_engine = ActionEngine()
        action_history = action_engine.get_action_history()
        
        # Calculate summary statistics
        total_actions = len(action_history)
        successful_actions = len([action for action in action_history if action.success])
        failed_actions = total_actions - successful_actions
        
        # Action type breakdown
        action_types = {}
        for action in action_history:
            action_type = action.action_id.split("_")[0] if "_" in action.action_id else action.action_id
            action_types[action_type] = action_types.get(action_type, 0) + 1
        
        # Recent actions (last 24 hours)
        recent_cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        recent_actions = len([action for action in action_history if action.timestamp >= recent_cutoff])
        
        logger.info(f"Audit summary retrieved: {total_actions} total actions")
        
        return {
            "total_actions": total_actions,
            "successful_actions": successful_actions,
            "failed_actions": failed_actions,
            "success_rate": successful_actions / total_actions if total_actions > 0 else 0,
            "action_breakdown": action_types,
            "recent_actions_24h": recent_actions,
            "last_updated": max([action.timestamp for action in action_history]).isoformat() if action_history else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving audit summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit summary"
        )