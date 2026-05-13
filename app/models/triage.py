"""Triage domain models for enterprise-grade fraud investigation."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AlertPolicy(str, Enum):
    """Alert policy types."""
    HIGH_VALUE_TRANSACTION = "high_value_transaction_amount"
    NEW_DEVICE_LOGIN = "new_device_login"
    SANCTIONED_COUNTRY = "transfer_to_sanctioned_country"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class InvestigationAction(str, Enum):
    """Investigation decision actions."""
    ESCALATE_FOR_INVESTIGATION = "ESCALATE_FOR_INVESTIGATION"
    AUTO_CLOSE = "AUTO_CLOSE"
    MONITOR = "MONITOR"


class RiskScore(BaseModel):
    """Risk score result with metadata."""
    score: float = Field(ge=0.0, le=1.0, description="Risk score between 0.0 and 1.0")
    severity: AlertSeverity
    auto_close_eligible: bool
    assessment_timestamp: datetime
    scoring_factors: Dict[str, Any] = Field(default_factory=dict)


class InvestigationDecision(BaseModel):
    """Investigation decision result."""
    action: InvestigationAction
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence level between 0.0 and 1.0")
    decision_timestamp: datetime


class AssessedAlert(BaseModel):
    """Assessed alert with all decision information."""
    alert_id: str
    customer_id: str
    policy: AlertPolicy
    risk_score: RiskScore
    decision: InvestigationDecision
    investigation_required: bool
    status: str


class TriageSummary(BaseModel):
    """Summary statistics for triage assessment."""
    total_alerts_processed: int
    auto_closed_count: int
    escalated_count: int
    auto_close_rate: float
    escalation_rate: float
    average_risk_score: float
    customer_id: Optional[str] = None
    assessment_scope: str
    policy_breakdown: Dict[str, int]
    severity_distribution: Dict[str, int]


class TriageAssessmentRequest(BaseModel):
    """Request model for triage assessment."""
    customer_id: Optional[str] = None


class TriageAssessmentResponse(BaseModel):
    """Response model for triage assessment."""
    success: bool
    total_alerts_assessed: int
    auto_closed_count: int
    investigation_required_count: int
    auto_close_rate: float
    escalation_rate: float
    average_risk_score: float
    assessed_alerts: List[AssessedAlert]
    triage_summary: TriageSummary
    hint: Optional[str] = Field(
        default=None,
        description="When no alerts were assessed, explains how to populate the in-memory alert store.",
    )
