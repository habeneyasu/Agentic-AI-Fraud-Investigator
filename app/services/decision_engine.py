"""Decision Engine - Domain logic for making investigation decisions."""

from datetime import datetime
from typing import Dict, Any

from app.models.triage import InvestigationAction, InvestigationDecision, RiskScore


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
        
        if score >= self.decision_thresholds["critical"]:
            action = InvestigationAction.ESCALATE_FOR_INVESTIGATION
            reasoning = f"Critical risk score ({score:.3f}) - immediate investigation required"
            confidence = self.confidence_mappings["critical"]
            
        elif score >= self.decision_thresholds["high"]:
            action = InvestigationAction.ESCALATE_FOR_INVESTIGATION
            reasoning = f"High risk score ({score:.3f}) - investigation required"
            confidence = self.confidence_mappings["high"]
            
        elif score >= self.decision_thresholds["medium"]:
            action = InvestigationAction.MONITOR
            reasoning = f"Medium risk score ({score:.3f}) - monitoring recommended"
            confidence = self.confidence_mappings["medium"]
            
        else:
            action = InvestigationAction.AUTO_CLOSE
            reasoning = f"Low risk score ({score:.3f}) - can be automatically closed"
            confidence = self.confidence_mappings["low"]
        
        # Add decision context
        decision_context = {
            "score_threshold_used": self.decision_thresholds["high"],
            "severity_based_decision": severity.value,
            "auto_close_eligible": risk_score.auto_close_eligible
        }
        
        return InvestigationDecision(
            action=action,
            reasoning=reasoning,
            confidence=confidence,
            decision_timestamp=datetime.utcnow()
        )
