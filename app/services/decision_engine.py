"""Decision Engine - Domain logic for making investigation decisions."""

from datetime import datetime, timezone
from typing import Any, Dict

from app.models.triage import InvestigationAction, InvestigationDecision, RiskScore


def _factor_context(factors: Dict[str, Any]) -> str:
    """One short clause tying the numeric score to concrete signals (matches risk scorer payloads)."""
    if not factors:
        return "engine scoring"
    if factors.get("sanctioned_country"):
        cc = factors["sanctioned_country"]
        tier = factors.get("country_tier") or "unknown"
        return f"sanctioned destination {cc} ({tier} tier)"
    if factors.get("transaction_amount") is not None:
        amt = factors["transaction_amount"]
        tier = factors.get("amount_tier") or "unknown"
        return f"transaction amount ${amt:,.0f} ({tier} tier)"
    if factors.get("anomaly_type"):
        return f"device / login anomaly ({factors['anomaly_type']})"
    return "policy-weighted signals"


class DecisionEngine:
    """Enterprise-grade decision engine with configurable rules."""
    
    def __init__(self):
        # Decision thresholds - can be made configurable
        self.decision_thresholds = {
            "critical": 0.8,
            "high": 0.6,
            "medium": 0.4
        }
        
        self.confidence_mappings = {
            "critical": 0.95,
            "high": 0.85,
            "medium": 0.75,
            "low": 0.65
        }
    
    def decide(self, risk_score: RiskScore) -> InvestigationDecision:
        """
        Make investigation decision based on risk score.
        
        Args:
            risk_score: RiskScore object with calculated score and metadata
            
        Returns:
            InvestigationDecision with action, reasoning, and confidence
        """
        score = risk_score.score
        severity = risk_score.severity
        ctx = _factor_context(risk_score.scoring_factors or {})
        sev = severity.value
        
        if score >= self.decision_thresholds["critical"]:
            action = InvestigationAction.ESCALATE_FOR_INVESTIGATION
            reasoning = (
                f"{sev} severity, score {score:.3f} ({ctx}) — at or above the critical "
                f"threshold ({self.decision_thresholds['critical']:.2f}); immediate investigation required."
            )
            confidence = self.confidence_mappings["critical"]
            
        elif score >= self.decision_thresholds["high"]:
            action = InvestigationAction.ESCALATE_FOR_INVESTIGATION
            reasoning = (
                f"{sev} severity, score {score:.3f} ({ctx}) — at or above the high-risk "
                f"threshold ({self.decision_thresholds['high']:.2f}); investigation required."
            )
            confidence = self.confidence_mappings["high"]
            
        elif score >= self.decision_thresholds["medium"]:
            action = InvestigationAction.MONITOR
            lo, hi = self.decision_thresholds["medium"], self.decision_thresholds["high"]
            reasoning = (
                f"{sev} severity, score {score:.3f} ({ctx}) — monitor band "
                f"(score ≥ {lo:.2f} and below escalation at {hi:.2f}); enhanced monitoring recommended."
            )
            confidence = self.confidence_mappings["medium"]
            
        else:
            action = InvestigationAction.AUTO_CLOSE
            reasoning = (
                f"{sev} severity, score {score:.3f} ({ctx}) — below the monitor threshold "
                f"({self.decision_thresholds['medium']:.2f}); within auto-close policy."
            )
            confidence = self.confidence_mappings["low"]
        
        return InvestigationDecision(
            action=action,
            reasoning=reasoning,
            confidence=confidence,
            decision_timestamp=datetime.now(timezone.utc),
        )
