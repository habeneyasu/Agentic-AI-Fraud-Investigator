"""Human-in-the-loop API endpoints for fraud investigation."""

from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
import logging

from app.core.security import get_current_user, verify_role
from app.models.case import Case, CaseStatus
from app.models.hitl import DecisionRequest, DecisionResponse, CaseStatusResponse, ResumeResponse
from app.services.fraud_memory import FraudMemory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/hitl", tags=["HITL"])


@router.post("/{case_id}/decision", response_model=DecisionResponse)
async def submit_decision(
    case_id: str,
    decision: DecisionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> DecisionResponse:
    """Submit human decision for fraud investigation case."""
    try:
        verify_role(current_user, ["ANALYST", "ADMIN"])
        
        fraud_memory = FraudMemory()
        case_data = await fraud_memory.get_case(case_id)
        
        if not case_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found"
            )
        
        valid_decisions = ["APPROVE", "REJECT", "ESCALATE"]
        if decision.decision.upper() not in valid_decisions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid decision. Must be one of: {valid_decisions}"
            )
        
        new_status = "CLOSED" if decision.decision.upper() != "ESCALATE" else "UNDER_REVIEW"
        
        case = Case(
            id=case_id,
            status=CaseStatus.CLOSED if decision.decision.upper() != "ESCALATE" else CaseStatus.UNDER_REVIEW,
            human_decision=decision.decision.upper(),
            human_reasoning=decision.reasoning,
            human_notes=decision.additional_notes,
            human_confidence=decision.confidence,
            reviewed_by=current_user.get("id"),
            reviewed_at=datetime.utcnow()
        )
        
        await fraud_memory.update_case(case)
        logger.info(f"Decision {decision.decision} submitted for case {case_id} by user {current_user.get('id')}")
        
        return DecisionResponse(
            success=True,
            message=f"Decision {decision.decision} recorded for case {case_id}",
            case_id=case_id,
            decision=decision.decision,
            new_status=new_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting decision for case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit decision"
        )


@router.get("/{case_id}/status", response_model=CaseStatusResponse)
async def get_case_status(
    case_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> CaseStatusResponse:
    """Get current status of a fraud investigation case."""
    try:
        verify_role(current_user, ["ANALYST", "ADMIN"])
        
        fraud_memory = FraudMemory()
        case_data = await fraud_memory.get_case(case_id)
        
        if not case_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found"
            )
        
        return CaseStatusResponse(
            case_id=case_data.id,
            status=case_data.status.value,
            created_at=case_data.created_at.isoformat() if case_data.created_at else None,
            updated_at=case_data.updated_at.isoformat() if case_data.updated_at else None,
            requires_review=case_data.status in [CaseStatus.PENDING_REVIEW, CaseStatus.UNDER_REVIEW],
            ai_recommendation=case_data.ai_recommendation,
            human_decision=case_data.human_decision,
            confidence=case_data.ai_confidence
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status for case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get case status"
        )


@router.post("/{case_id}/resume", response_model=ResumeResponse)
async def resume_investigation(
    case_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ResumeResponse:
    """Resume investigation for a case that was previously escalated."""
    try:
        verify_role(current_user, ["ANALYST", "ADMIN"])
        
        fraud_memory = FraudMemory()
        case_data = await fraud_memory.get_case(case_id)
        
        if not case_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found"
            )
        
        case = Case(
            id=case_id,
            status=CaseStatus.UNDER_REVIEW,
            resumed_by=current_user.get("id"),
            resumed_at=datetime.utcnow()
        )
        
        await fraud_memory.update_case(case)
        logger.info(f"Investigation resumed for case {case_id} by user {current_user.get('id')}")
        
        return ResumeResponse(
            success=True,
            message=f"Investigation resumed for case {case_id}",
            case_id=case_id,
            new_status="UNDER_REVIEW"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming investigation for case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume investigation"
        )
