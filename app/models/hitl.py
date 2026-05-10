"""HITL (Human-in-the-Loop) request and response models."""

from pydantic import BaseModel, Field
from typing import Optional


class DecisionRequest(BaseModel):
    """Request model for human decision."""
    decision: str = Field(..., description="Human decision: APPROVE, REJECT, or ESCALATE")
    reasoning: str = Field(..., description="Human reasoning for the decision")
    additional_notes: Optional[str] = Field(None, description="Additional notes or observations")
    confidence: Optional[int] = Field(None, ge=1, le=10, description="Confidence level 1-10")


class DecisionResponse(BaseModel):
    """Response model for decision submission."""
    success: bool
    message: str
    case_id: str
    decision: str
    new_status: str


class CaseStatusResponse(BaseModel):
    """Response model for case status inquiry."""
    case_id: str
    status: str
    created_at: Optional[str]
    updated_at: Optional[str]
    requires_review: bool
    ai_recommendation: Optional[str]
    human_decision: Optional[str]
    confidence: Optional[float]


class ResumeResponse(BaseModel):
    """Response model for investigation resumption."""
    success: bool
    message: str
    case_id: str
    new_status: str
