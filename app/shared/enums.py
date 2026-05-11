"""Domain enumerations for fraud investigations, triage, and compliance."""

from enum import Enum


class RiskLevel(str, Enum):
    """Customer / transaction risk tier."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InvestigationStatus(str, Enum):
    """Lifecycle status for an investigation record."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CLOSED = "closed"


class CasePriority(str, Enum):
    """Routing priority from rules-based triage (distinct from alert triage tier)."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Alert and Fraud Enums
class AlertType(str, Enum):
    """Types of fraud alerts."""
    TRANSACTION_FRAUD = "transaction_fraud"
    ACCOUNT_TAKEOVER = "account_takeover"
    IDENTITY_THEFT = "identity_theft"
    MONEY_LAUNDERING = "money_laundering"
    SANCTIONS_VIOLATION = "sanctions_violation"
    KYC_ISSUES = "kyc_issues"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class FraudPattern(str, Enum):
    """Fraud pattern types."""
    VELOCITY_ANOMALY = "velocity_anomaly"
    FREQUENCY_SPIKE = "frequency_spike"
    AMOUNT_ANOMALY = "amount_anomaly"
    LOCATION_ANOMALY = "location_anomaly"
    DEVICE_ANOMALY = "device_anomaly"
    KNOWN_FRAUDSTER = "known_fraudster"
    SYNTHETIC_IDENTITY = "synthetic_identity"


# KYC and Device Enums
class AnomalyType(str, Enum):
    """KYC anomaly types."""
    NEW_DEVICE = "new_device"
    SUSPICIOUS_DEVICE = "suspicious_device"
    GEO_LOCATION_ANOMALY = "geo_location_anomaly"
    IMPOSSIBLE_TRAVEL = "impossible_travel"
    HIGH_RISK_LOCATION = "high_risk_location"
    UNUSUAL_TIME = "unusual_time"
    MULTIPLE_FAILED_ATTEMPTS = "multiple_failed_attempts"
    ACCOUNT_TAKEOVER = "account_takeover"


# Sanctions Enums
class SanctionType(str, Enum):
    """Types of sanctions."""
    COUNTRY_SANCTION = "country_sanction"
    ENTITY_SANCTION = "entity_sanction"
    INDIVIDUAL_SANCTION = "individual_sanction"
    TRADE_RESTRICTION = "trade_restriction"
    FINANCIAL_SANCTION = "financial_sanction"


class CountryRiskLevel(str, Enum):
    """Country risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Memory and Storage Enums
class MemoryType(str, Enum):
    """Types of fraud memory entries."""
    PATTERN = "pattern"
    ENTITY = "entity"
    TRANSACTION = "transaction"
    DEVICE = "device"
    LOCATION = "location"


class MemoryStatus(str, Enum):
    """Memory entry status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    ARCHIVED = "archived"


# Triage Enums
class TriageCategory(str, Enum):
    """Triage categories."""
    TRANSACTION_FRAUD = "transaction_fraud"
    ACCOUNT_TAKEOVER = "account_takeover"
    IDENTITY_THEFT = "identity_theft"
    MONEY_LAUNDERING = "money_laundering"
    SANCTIONS_VIOLATION = "sanctions_violation"
    KYC_ISSUES = "kyc_issues"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class TriagePriority(str, Enum):
    """Triage priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# Decision Enums
class DecisionType(str, Enum):
    """Human-in-the-loop decision types."""
    CONFIRM_FRAUD = "confirm_fraud"
    FALSE_POSITIVE = "false_positive"
    REQUEST_MORE_INFO = "request_more_info"


class ActionRecommendation(str, Enum):
    """System action recommendations."""
    BLOCK_TRANSACTION = "block_transaction"
    FREEZE_ACCOUNT = "freeze_account"
    FLAG_FOR_REVIEW = "flag_for_review"
    MONITOR_CLOSELY = "monitor_closely"
    ENHANCED_DUE_DILIGENCE = "enhanced_due_diligence"
    REQUIRE_ADDITIONAL_VERIFICATION = "require_additional_verification"
    COMPLIANCE_REVIEW = "compliance_review"
    PROCEED = "proceed"
    ALLOW_ACCESS = "allow_access"
    BLOCK_ACCESS = "block_access"


# Scoring Enums
class ScoringMode(str, Enum):
    """Scoring mode types."""
    RULES_ONLY = "rules_only"
    AI_ONLY = "ai_only"
    HYBRID = "hybrid"


class RiskCategory(str, Enum):
    """Risk categories."""
    TRANSACTION = "transaction"
    DEVICE = "device"
    GEO = "geo"
    SANCTIONS = "sanctions"
    BEHAVIOR = "behavior"
    AI_CONTEXT = "ai_context"


# Workflow Enums
class NodeType(str, Enum):
    """LangGraph node types."""
    START = "start"
    TRANSACTION_ANALYSIS = "transaction_analysis"
    KYC_ANALYSIS = "kyc_analysis"
    SANCTIONS_CHECK = "sanctions_check"
    RISK_SCORING = "risk_scoring"
    DECISION = "decision"
    INVESTIGATION = "investigation"
    ESCALATION = "escalation"
    RESOLUTION = "resolution"
    END = "end"


class EdgeType(str, Enum):
    """LangGraph edge types."""
    CONDITIONAL = "conditional"
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    RETRY = "retry"


# Action Engine Enums
class ActionType(str, Enum):
    """Available fraud resolution actions."""
    FREEZE = "freeze"
    REVERSE = "reverse"
    BLOCK = "block"
    SMS = "sms"
