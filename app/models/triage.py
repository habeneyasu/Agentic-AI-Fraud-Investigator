"""Triage domain models for enterprise-grade fraud investigation."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


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
    """One alert after deterministic triage (and optional initial-suspicion narrative)."""
    alert_id: str = Field(..., description="Stable alert identifier.")
    customer_id: str = Field(..., description="Customer owning the underlying activity.")
    policy: AlertPolicy
    risk_score: RiskScore
    decision: InvestigationDecision
    investigation_required: bool
    status: str = Field(
        ...,
        description="Workflow state after triage: ``CLOSED`` (AUTO_CLOSE), ``MONITORING`` (MONITOR), ``OPEN_FOR_INVESTIGATION`` (ESCALATE_FOR_INVESTIGATION).",
    )
    initial_suspicion_note: Optional[str] = Field(
        default=None,
        description="Phase-1 narrative: human-readable explanation of why deterministic triage fired.",
    )
    initial_suspicion_source: Optional[str] = Field(
        default=None,
        description="``llm`` when the fast model produced the note, ``deterministic_fallback`` otherwise.",
    )


class TriageSummary(BaseModel):
    """Aggregate view of the batch that was triaged in this response."""

    total_alerts_processed: int = Field(..., description="Count of alerts evaluated in this run.")
    auto_closed_count: int = Field(..., description="Alerts closed by AUTO_CLOSE decision.")
    monitor_count: int = Field(
        ...,
        description="Alerts with MONITOR decision (watch / enhanced monitoring; not counted in ``escalated_count``).",
    )
    escalated_count: int = Field(..., description="Alerts with ESCALATE_FOR_INVESTIGATION.")
    auto_close_rate: float = Field(..., description="Percent of batch auto-closed.")
    escalation_rate: float = Field(..., description="Percent of batch escalated for investigation.")
    average_risk_score: float = Field(..., description="Mean deterministic risk score across the batch.")
    customer_id: Optional[str] = Field(
        default=None,
        description="When ``assessment_scope`` is ``single_customer``, the ``customer_id`` query parameter that was applied; otherwise null.",
    )
    assessment_scope: Literal["single_customer", "all_customers"] = Field(
        ...,
        description="``single_customer`` when ``?customer_id=`` was provided; otherwise all customers in the merged queue.",
    )
    policy_breakdown: Dict[str, int] = Field(..., description="Counts by coarse policy family.")
    severity_distribution: Dict[str, int] = Field(
        ...,
        description="Counts by severity tier (``critical`` / ``high`` / ``medium`` / ``low``, lower-case keys).",
    )


class TriageAssessBody(BaseModel):
    """JSON body for ``POST /v1/triage/assess``. Customer scope is **only** ``?customer_id=`` on the URL (not in this body)."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"include_initial_suspicion_note": True},
                {},
            ]
        }
    )

    include_initial_suspicion_note: Optional[bool] = Field(
        default=None,
        description="If set, overrides ``TRIAGE_NARRATIVE_ENABLED`` for this request only.",
    )


class TriageAssessmentRequest(BaseModel):
    """Internal triage request (router fills from query + body flags only)."""

    customer_id: Optional[str] = Field(
        default=None,
        description="Customer filter from the **query** parameter ``customer_id`` only.",
    )
    include_initial_suspicion_note: Optional[bool] = Field(
        default=None,
        description="If set, overrides ``TRIAGE_NARRATIVE_ENABLED`` for this request only.",
    )


class TriageAssessmentResponse(BaseModel):
    """Outcome of ``POST /v1/triage/assess`` for the merged Postgres + JSON alert queue."""

    success: bool = Field(..., description="False only on transport/application errors; empty batch still returns success with counts of zero.")
    total_alerts_assessed: int = Field(
        ...,
        description="Count of alerts triaged in this run — same length as ``assessed_alerts``. With ``?customer_id=``, only that customer's alerts are in scope.",
    )
    auto_closed_count: int = Field(..., description="Count of AUTO_CLOSE decisions in this run.")
    monitor_count: int = Field(
        ...,
        description="Count of MONITOR decisions (watch path; see per-row ``status`` ``MONITORING``).",
    )
    investigation_required_count: int = Field(
        ...,
        description="Count of ESCALATE_FOR_INVESTIGATION decisions (same as ``triage_summary.escalated_count``).",
    )
    auto_close_rate: float
    escalation_rate: float
    average_risk_score: float
    assessed_alerts: List[AssessedAlert] = Field(
        ...,
        description="Per-alert outcomes for every alert evaluated in this run (full queue, or only the customer given by ``?customer_id=``).",
    )
    triage_summary: TriageSummary
    initial_suspicion_engine_status: Optional[str] = Field(
        default=None,
        description=(
            "Batch narrative diagnostics when ``include_initial_suspicion_note`` is used: "
            "``off`` — narrative not requested; "
            "``llm`` — at least one alert received model text; "
            "``no_provider`` — ``CEREBRAS_API_KEY`` / ``GEMINI_API_KEY`` not set; "
            "``no_alerts_in_scope`` — narrative requested but zero alerts matched the filter; "
            "``llm_no_valid_note`` — keys were set but no parseable narrative was returned for any alert."
        ),
    )
    hint: Optional[str] = Field(
        default=None,
        description="When no alerts were assessed, explains how to populate the merged Postgres + JSON alert store.",
    )
