"""Audit API request/response models for fraud investigation."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class AuditRequest(BaseModel):
    """Request model for audit filtering."""
    case_id: Optional[str] = Field(None, description="Filter by specific case ID")
    action_type: Optional[str] = Field(None, description="Filter by action type")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    start_date: Optional[datetime] = Field(None, description="Start date for filtering")
    end_date: Optional[datetime] = Field(None, description="End date for filtering")
    limit: Optional[int] = Field(100, ge=1, le=1000, description="Maximum results to return")


class AuditResponse(BaseModel):
    """Response model for audit trail."""
    success: bool
    message: str
    total_count: int
    audit_trail: List[Dict[str, Any]]
    filters_applied: Dict[str, Any]


class AuditEntry(BaseModel):
    """Single audit entry model."""
    action_id: str
    case_id: str
    action_type: str
    success: bool
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    executed_by: Optional[str] = None


class AuditSummary(BaseModel):
    """Audit summary statistics model."""
    total_actions: int
    successful_actions: int
    failed_actions: int
    success_rate: float
    action_breakdown: Dict[str, int]
    recent_actions_24h: int
    last_updated: Optional[datetime]
