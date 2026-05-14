"""Pydantic domain models and API contracts for fraud investigations."""

from datetime import datetime
from typing import Any, Callable, Dict, List, Literal, Optional

from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.shared.enums import (
    ActionRecommendation,
    AlertType,
    AnomalyType,
    DecisionType,
    FraudPattern,
    InvestigationStatus,
    MemoryStatus,
    MemoryType,
    RiskLevel,
    SanctionType,
    TriageCategory,
    TriagePriority,
)


class ApiMessageResponse(BaseModel):
    """Standard API envelope for success and list responses."""

    success: bool = True
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    message: Optional[str] = None
    data: Optional[Any] = None


class ApiErrorResponse(ApiMessageResponse):
    """Standard API envelope for errors."""

    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None


class TransactionRecord(BaseModel):
    """Normalized transaction payload for analysis agents."""
    transaction_id: str
    customer_id: str
    amount: float
    currency: str = "USD"
    timestamp: datetime
    merchant_id: str
    location: str
    device_id: str
    ip_address: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeviceInfo(BaseModel):
    """Device information model."""
    device_id: str
    device_type: str
    user_agent: str
    ip_address: str
    fingerprint: Dict[str, Any] = Field(default_factory=dict)


class GeoLocation(BaseModel):
    """Geo-location model."""
    ip_address: str
    country: str
    city: str
    latitude: float
    longitude: float
    isp: str
    is_proxy: bool = False
    is_vpn: bool = False


class SanctionsParty(BaseModel):
    """Counterparty or entity submitted for sanctions / watchlist screening."""
    name: str
    country_code: str
    entity_type: str = "unknown"
    description: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Investigation Models
class InvestigationCase(BaseModel):
    """Canonical investigation case opened from an alert or manual review."""
    investigation_id: str
    transaction_id: str
    customer_id: str
    amount: float
    currency: str = "USD"
    timestamp: datetime
    recipient_country: str
    device_info: Optional[DeviceInfo] = None
    location: Optional[GeoLocation] = None
    transaction_history: List[Dict[str, Any]] = Field(default_factory=list)
    customer_profile: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InvestigationResult(BaseModel):
    """Investigation result."""
    investigation_id: str
    status: InvestigationStatus
    risk_score: float = Field(ge=0.0, le=1.0)
    agent_results: Dict[str, Any]
    final_recommendation: ActionRecommendation
    requires_human_review: bool
    investigation_timestamp: datetime
    completed_timestamp: Optional[datetime] = None


class AgentResult(BaseModel):
    """Agent analysis result."""
    agent_type: str
    risk_score: float = Field(ge=0.0, le=1.0)
    anomalies: List[Dict[str, Any]]
    recommendation: ActionRecommendation
    confidence: float = Field(ge=0.0, le=1.0)
    analysis_timestamp: datetime


# Alert Models
class FraudAlertRecord(BaseModel):
    """Persisted fraud alert metadata (queue / case management)."""
    alert_id: str
    investigation_id: str
    alert_type: AlertType
    severity: RiskLevel
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# KYC Models
class KycEventRecord(BaseModel):
    """KYC / authentication telemetry tied to a customer session."""
    customer_id: str
    event_type: str = "login"
    device_info: Optional[DeviceInfo] = None
    location: Optional[GeoLocation] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KYCAnalysisResult(BaseModel):
    """KYC analysis result."""
    customer_id: str
    event_type: str
    risk_score: float = Field(ge=0.0, le=1.0)
    anomalies: List[Dict[str, Any]]
    recommendation: ActionRecommendation
    analysis_timestamp: datetime


# Transaction Analysis Models
class TransactionAnalysisResult(BaseModel):
    """Transaction analysis result."""
    transaction_id: str
    customer_id: str
    risk_score: float = Field(ge=0.0, le=1.0)
    velocity_metrics: List[Dict[str, Any]]
    velocity_anomalies: List[Dict[str, Any]]
    fraud_patterns: List[FraudPattern]
    recommendation: ActionRecommendation
    analysis_timestamp: datetime


# Sanctions Models
class SanctionsAnalysisResult(BaseModel):
    """Sanctions analysis result."""
    entity_name: str
    country_code: str
    entity_type: str
    risk_score: float = Field(ge=0.0, le=1.0)
    alerts: List[Dict[str, Any]]
    recommendation: ActionRecommendation
    analysis_timestamp: datetime


# Triage Models
class CaseTriageContext(BaseModel):
    """Structured case context for deterministic triage services."""

    investigation_id: str
    customer_id: str
    transaction_id: str
    amount: float
    risk_score: float = Field(ge=0.0, le=1.0)
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    customer_risk_profile: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Fraud Memory Models
class FraudMemoryEntry(BaseModel):
    """Fraud memory entry structure."""
    memory_id: str
    memory_type: MemoryType
    entity_id: str
    entity_type: str
    pattern_type: FraudPattern
    confidence: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    frequency: int = Field(ge=1)
    last_seen: datetime
    first_seen: datetime
    expires_at: Optional[datetime] = None
    status: MemoryStatus = MemoryStatus.ACTIVE
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FraudPatternRequest(BaseModel):
    """Request to add fraud pattern."""
    entity_id: str
    entity_type: str
    pattern_type: FraudPattern
    confidence: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FraudPatternResponse(BaseModel):
    """Response for fraud pattern operations."""
    memory_id: str
    entity_id: str
    pattern_type: FraudPattern
    confidence: float
    risk_score: float
    created_at: datetime


class MemoryStatsResponse(BaseModel):
    """Memory statistics response."""
    total_entries: int
    active_entries: int
    expired_entries: int
    pattern_types: Dict[str, int]
    entity_types: Dict[str, int]
    avg_risk_score: float
    last_updated: datetime


# Evidence Models
class EvidenceRecord(BaseModel):
    """Evidence artifact captured during an investigation."""
    evidence_id: str
    investigation_id: str
    type: str
    category: str
    description: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# API Request/Response Models
class TransactionAnalysisRequest(BaseModel):
    """API: run transaction fraud agent on a single transaction."""

    transaction: TransactionRecord
    customer_history: List[Dict[str, Any]] = Field(default_factory=list)


class KycAnalysisApiRequest(BaseModel):
    """API: analyze a KYC / device event."""

    event: KycEventRecord


class SanctionsScreeningApiRequest(BaseModel):
    """API: screen a party for sanctions / country risk."""

    entity: SanctionsParty


class OpenInvestigationApiRequest(BaseModel):
    """API: start a full investigation workflow from a populated case."""

    investigation: InvestigationCase


class CaseTriageRulesApiRequest(BaseModel):
    """API: deterministic triage over structured case context."""

    triage: CaseTriageContext


class SynthesisRequest(BaseModel):
    """Synthesis API request."""
    investigation_id: str
    agent_results: Dict[str, AgentResult]


class SanctionsWriteRequest(BaseModel):
    """Append watchlist rows and/or country-risk rows.

    **Canonical:** ``resource`` (``watchlist`` | ``country_risks``) + non-empty ``items``.

    **Legacy (``sanctions_data.json``):** ``sanctions_entries`` and/or ``country_risks`` at the top level.
    When both keys are present, watchlist and country tables are both updated in one call.
    """

    model_config = ConfigDict(extra="ignore")

    resource: Optional[Literal["watchlist", "country_risks"]] = None
    items: Optional[List[Dict[str, Any]]] = None
    sanctions_entries: Optional[List[Dict[str, Any]]] = None
    country_risks: Optional[List[Dict[str, Any]]] = None

    @model_validator(mode="after")
    def _validate_shape(self) -> "SanctionsWriteRequest":
        has_se = self.sanctions_entries is not None
        has_cr = self.country_risks is not None
        if self.resource is not None:
            if not self.items or len(self.items) < 1:
                raise ValueError("When resource is set, items must be a non-empty list")
            if has_se or has_cr:
                raise ValueError("Do not mix resource/items with sanctions_entries/country_risks")
            return self
        if has_se or has_cr:
            return self
        raise ValueError(
            "Provide resource+items, or at least one of sanctions_entries / country_risks (legacy import)"
        )


class PatternSearchRequest(BaseModel):
    """Pattern search request."""
    query: str
    search_field: str = "entity_id"


class FraudMemoryMutationRequest(BaseModel):
    """Single POST surface for fraud-memory mutations (add, bump, delete, cleanup)."""

    operation: Literal["add_pattern", "cleanup", "bump_frequency", "delete"]
    pattern: Optional[FraudPatternRequest] = None
    memory_id: Optional[str] = None

    @model_validator(mode="after")
    def _validate_operation_payload(self) -> "FraudMemoryMutationRequest":
        if self.operation == "add_pattern":
            if self.pattern is None:
                raise ValueError("add_pattern requires 'pattern'")
        elif self.operation in ("bump_frequency", "delete"):
            if not (self.memory_id and str(self.memory_id).strip()):
                raise ValueError(f"{self.operation} requires non-empty memory_id")
        return self


class PatternSearchResponse(BaseModel):
    """Pattern search response."""
    query: str
    search_field: str
    patterns: List[FraudMemoryEntry]
    count: int


# Human-in-the-Loop Models
class AnalystCaseDecision(BaseModel):
    """Analyst disposition for a case under human review (HITL)."""

    decision: DecisionType
    analyst_id: str
    notes: str = ""


class AnalystCaseDecisionAck(BaseModel):
    """Acknowledgement payload after persisting an analyst decision."""

    investigation_id: str
    status: str
    decision: DecisionType
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FraudAlertIngestRequest(BaseModel):
    """API: ingest a fraud alert from channels / rules engine."""

    transaction_id: str
    amount: float
    currency: str = "USD"
    timestamp: str  # ISO format string
    account_id: str
    recipient_country: str
    alert_hash: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FraudAlertIngestResponse(ApiMessageResponse):
    """API: response after alert is accepted for investigation."""

    investigation_id: str
    status: str


# Agent Data Classes
@dataclass
class TransactionVelocity:
    """Transaction velocity metrics."""
    transaction_count: int
    total_amount: float
    average_amount: float
    max_amount: float
    min_amount: float
    time_window_hours: int
    unique_merchants: int
    unique_locations: int
    unique_devices: int


@dataclass
class FraudMemory:
    """Fraud memory entry for deterministic lookup."""
    pattern: FraudPattern
    confidence: float
    last_seen: datetime
    frequency: int
    risk_score: float
    metadata: Dict[str, Any]


@dataclass
class LoginAttempt:
    """Login attempt information."""
    timestamp: datetime
    device_id: str
    ip_address: str
    location: GeoLocation
    success: bool
    failure_reason: Optional[str] = None


@dataclass
class KYCAnomaly:
    """KYC anomaly detection result."""
    anomaly_type: AnomalyType
    severity: str
    confidence: float
    description: str
    metadata: Dict[str, Any]


@dataclass
class CountryRisk:
    """Country risk assessment."""
    country_code: str
    country_name: str
    risk_level: RiskLevel
    risk_score: float
    sanctions_active: bool
    last_updated: datetime


@dataclass
class SanctionsEntry:
    """Sanctions list entry."""
    entity_id: str
    entity_name: str
    entity_type: str
    sanction_type: SanctionType
    country: str
    confidence: float
    last_seen: datetime


@dataclass
class SanctionsAlert:
    """Sanctions detection alert."""
    alert_type: SanctionType
    severity: str
    confidence: float
    description: str
    metadata: Dict[str, Any]


# Core Schemas
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


class CaseTriageAssessment(BaseModel):
    """Structured output from LLM-assisted triage for a case."""
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


class HistoricalContext(BaseModel):
    """Historical context for triage analysis."""
    similar_cases: int = Field(default=0, ge=0, description="Number of similar historical cases")
    historical_risk: Optional[str] = Field(None, description="Historical risk score")
    previous_escalations: int = Field(default=0, ge=0, description="Previous escalation count")
    avg_resolution_time: Optional[str] = Field(None, description="Average resolution time")
    customer_history: Optional[str] = Field(None, description="Customer historical data")
    previous_alerts: Optional[str] = Field(None, description="Previous fraud alerts")


# Scoring Models
@dataclass
class RiskFactor:
    """Risk factor for scoring."""
    category: str  # RiskCategory
    factor: str
    weight: float
    value: float
    description: str


@dataclass
class ScoringResult:
    """Scoring result."""
    risk_score: float
    risk_level: str
    confidence: float
    factors: List[RiskFactor]
    explanation: str
    scoring_mode: str  # ScoringMode
    timestamp: datetime
    rule_score: Optional[float] = None
    ai_score: Optional[float] = None


# State Management Models
class InvestigationWorkflowState(BaseModel):
    """Mutable LangGraph state for a single investigation run."""
    
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

    model_config = ConfigDict(use_enum_values=True)

    @classmethod
    def create_initial(
        cls,
        *,
        case_id: str,
        case_type: str,
        title: str,
        description: str,
        priority: TriagePriority,
        correlation_id: str,
    ) -> "InvestigationWorkflowState":
        """Factory for a new workflow run prior to graph execution."""
        return cls(
            case_id=case_id,
            case_type=case_type,
            title=title,
            description=description,
            priority=priority,
            correlation_id=correlation_id,
            status=InvestigationStatus.PENDING,
        )


# Workflow Models
@dataclass
class WorkflowNode:
    """Workflow node definition."""
    node_id: str
    node_type: str  # NodeType
    function: Optional[Callable]
    conditions: Optional[Dict[str, Any]]
    max_retries: int = 3
    timeout: float = 30.0
    semaphore_key: Optional[str] = None


@dataclass
class WorkflowEdge:
    """Workflow edge definition."""
    from_node: str
    to_node: str
    edge_type: str  # EdgeType
    condition: Optional[str] = None
    weight: float = 1.0


# Action Engine Models
@dataclass
class ActionRequest:
    """Request for fraud resolution action."""
    action_type: str  # ActionType
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


# Evaluation Models
class EvaluationRequest(BaseModel):
    """Request for agent evaluation against benchmarks."""
    investigation_id: str
    agent_type: str
    agent_result: Dict[str, Any]
    fraud_type: str
    metadata: Optional[Dict[str, Any]] = None


class EvaluationResponse(BaseModel):
    """Response from agent evaluation."""
    success: bool
    evaluation_id: str
    status: str  # EXCEEDS_BENCHMARK, MEETS_BENCHMARK, BELOW_BENCHMARK, CRITICAL_DEVIATION
    evaluation_score: float
    recommendations: List[str]
    metrics: Dict[str, Any]
    benchmark_data: Dict[str, Any]
