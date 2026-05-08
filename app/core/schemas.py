from typing import List, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum


class TriageCategory(str, Enum):
    """Categories for fraud triage."""
    TRANSACTION_FRAUD = "transaction_fraud"
    ACCOUNT_TAKEOVER = "account_takeover"
    IDENTITY_THEFT = "identity_theft"
    MONEY_LAUNDERING = "money_laundering"
    SANCTIONS_VIOLATION = "sanctions_violation"
    KYC_ISSUES = "kyc_issues"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class TriagePriority(str, Enum):
    """Triage priority levels for fraud cases."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class TriageAnalysis(BaseModel):
    """Pydantic model for LLM triage analysis output."""
    category: TriageCategory = Field(
        ..., 
        description="The fraud category classification"
    )
    risk_factors: List[str] = Field(
        default_factory=list,
        description="List of identified risk factors"
    )
    urgency_indicators: List[str] = Field(
        default_factory=list,
        description="List of urgency indicators"
    )
    estimated_time_hours: int = Field(
        default=24,
        ge=1,
        le=168,  # Max 1 week
        description="Estimated investigation time in hours"
    )
    required_resources: List[str] = Field(
        default_factory=lambda: ["investigator"],
        description="List of required resources"
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence score of the analysis"
    )
    raw_analysis: str = Field(
        default="",
        description="Detailed analysis explanation from LLM"
    )
    
    @validator('category')
    def validate_category(cls, v):
        """Validate category is one of the allowed values."""
        if isinstance(v, str):
            try:
                return TriageCategory(v.lower())
            except ValueError:
                return TriageCategory.SUSPICIOUS_ACTIVITY
        return v
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is within valid range."""
        return max(0.0, min(1.0, float(v)))


class TriageResult(BaseModel):
    """Complete triage result with all analysis and recommendations."""
    case_id: str = Field(..., description="Unique case identifier")
    triage_timestamp: str = Field(..., description="When triage was performed")
    priority: TriagePriority = Field(..., description="Final priority level")
    priority_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="Numerical priority score"
    )
    category: TriageCategory = Field(..., description="Fraud category")
    risk_factors: List[str] = Field(default_factory=list, description="Risk factors identified")
    urgency_indicators: List[str] = Field(default_factory=list, description="Urgency indicators")
    estimated_investigation_time: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Estimated investigation time in hours"
    )
    required_resources: List[str] = Field(default_factory=list, description="Required resources")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")
    auto_escalation: bool = Field(default=False, description="Whether case should be auto-escalated")
    llm_analysis: str = Field(default="", description="Raw LLM analysis")
    triage_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in triage decision"
    )


class CaseInput(BaseModel):
    """Input model for case triage."""
    case_id: str = Field(..., description="Unique case identifier")
    case_type: str = Field(..., description="Type of case")
    reported_date: str = Field(..., description="When case was reported")
    amount: Optional[float] = Field(None, description="Amount involved if applicable")
    currency: Optional[str] = Field(None, description="Currency code")
    description: str = Field(..., max_length=2000, description="Case description")
    reporter: str = Field(..., description="Who reported the case")
    affected_parties: str = Field(..., description="Affected parties")
    evidence: List[dict] = Field(default_factory=list, description="Evidence items")
    
    @validator('description')
    def validate_description_length(cls, v):
        """Ensure description doesn't exceed token limits."""
        # Rough estimate: 1 token ≈ 4 characters
        max_tokens = 500  # Reserve tokens for other prompt parts
        max_chars = max_tokens * 4
        
        if len(v) > max_chars:
            # Truncate with ellipsis
            return v[:max_chars-3] + "..."
        return v


class HistoricalContext(BaseModel):
    """Historical context for triage analysis."""
    similar_cases: int = Field(default=0, ge=0, description="Number of similar historical cases")
    historical_risk: Optional[str] = Field(None, description="Historical risk score")
    previous_escalations: int = Field(default=0, ge=0, description="Previous escalation count")
    avg_resolution_time: Optional[str] = Field(None, description="Average resolution time")
    customer_history: Optional[str] = Field(None, description="Customer historical data")
    previous_alerts: Optional[str] = Field(None, description="Previous fraud alerts")
