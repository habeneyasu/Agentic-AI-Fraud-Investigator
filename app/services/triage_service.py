"""
Triage service for fraud case prioritization.
"""

from typing import Dict, Any, List
from datetime import datetime

from app.services.base import BaseService
from app.shared.enums import Priority


class TriageService(BaseService):
    """Service for fraud case triage and prioritization."""
    
    def __init__(self):
        super().__init__()
        self.risk_thresholds = {
            "critical": 0.8,
            "high": 0.6,
            "medium": 0.4,
            "low": 0.2
        }
        self.priority_weights = {
            "amount": 0.3,
            "risk_score": 0.4,
            "customer_tier": 0.2,
            "alert_count": 0.1
        }
        self.escalation_rules = {
            "critical_risk": 0.8,
            "high_amount": 50000,
            "multiple_alerts": 3
        }
        self.auto_action_rules = {
            "freeze_threshold": 0.9,
            "block_threshold": 0.7,
            "flag_threshold": 0.6
        }
    
    def analyze_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze case using deterministic rules."""
        self._log_operation("analyze_case", investigation_id=case_data.get("investigation_id"))
        
        try:
            risk_score = case_data.get("risk_score", 0.0)
            amount = case_data.get("amount", 0.0)
            customer_tier = case_data.get("customer_tier", "standard")
            alert_count = case_data.get("alert_count", 1)
            
            # Calculate priority score
            priority_score = self._calculate_priority_score(risk_score, amount, customer_tier, alert_count)
            
            # Determine triage decision
            triage_decision, priority = self._determine_triage_decision(priority_score)
            
            result = {
                "investigation_id": case_data.get("investigation_id"),
                "triage_decision": triage_decision,
                "priority": priority,
                "priority_score": priority_score,
                "escalation_required": priority_score >= 0.6,
                "auto_action": self._determine_auto_action(priority_score, risk_score),
                "human_review_required": priority_score >= 0.4,
                "reasoning": self._generate_reasoning(risk_score, amount, customer_tier, alert_count),
                "confidence": min(priority_score + 0.2, 1.0),
                "triage_timestamp": datetime.utcnow().isoformat()
            }
            
            return self._generate_response(result)
        except Exception as e:
            self._log_error("analyze_case", e)
            return self._generate_response({"error": str(e)}, success=False)
    
    def calculate_priority(
        self,
        risk_score: float,
        amount: float,
        customer_tier: str = "standard",
        alert_count: int = 1
    ) -> Dict[str, Any]:
        """Calculate investigation priority."""
        priority_score = self._calculate_priority_score(risk_score, amount, customer_tier, alert_count)
        priority_level = self._determine_priority_level(priority_score)
        
        return self._generate_response({
            "priority_score": priority_score,
            "priority_level": priority_level,
            "factors": {
                "risk_score": risk_score,
                "amount": amount,
                "customer_tier": customer_tier,
                "alert_count": alert_count
            }
        })
    
    def check_escalation(
        self,
        risk_score: float,
        amount: float,
        alert_types: List[str],
        customer_history: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if case requires escalation."""
        escalation_required = self._check_escalation_rules(risk_score, amount, alert_types)
        escalation_reasons = self._get_escalation_reasons(risk_score, amount, alert_types)
        escalation_level = self._determine_escalation_level(risk_score)
        
        return self._generate_response({
            "escalation_required": escalation_required,
            "escalation_reasons": escalation_reasons,
            "recommended_escalation_level": escalation_level
        })
    
    def determine_auto_action(
        self,
        risk_score: float,
        triage_decision: str,
        customer_risk_level: str = "low"
    ) -> Dict[str, Any]:
        """Determine automatic action."""
        action_data = {"risk_score": risk_score, "triage_decision": triage_decision, "customer_risk_level": customer_risk_level}
        
        auto_action = self._determine_auto_action(action_data)
        action_confidence = self._calculate_action_confidence(action_data)
        
        return self._generate_response({
            "auto_action": auto_action,
            "confidence": action_confidence,
            "requires_human_review": self._requires_human_review(action_data),
            "action_parameters": self._get_action_parameters(action_data)
        })
    
    def _calculate_priority_score(self, risk_score: float, amount: float, customer_tier: str, alert_count: int) -> float:
        """Calculate priority score."""
        return (
            self.priority_weights["risk_score"] * risk_score +
            self.priority_weights["amount"] * min(amount / 10000, 1.0) +
            self.priority_weights["customer_tier"] * self._get_tier_weight(customer_tier) +
            self.priority_weights["alert_count"] * min(alert_count / 5, 1.0)
        )
    
    def _get_tier_weight(self, tier: str) -> float:
        """Get weight based on customer tier."""
        tier_weights = {"vip": 1.0, "premium": 0.8, "standard": 0.6, "basic": 0.4}
        return tier_weights.get(tier.lower(), 0.6)
    
    def _determine_triage_decision(self, priority_score: float) -> tuple[str, Priority]:
        """Determine triage decision and priority."""
        if priority_score >= 0.8:
            return "ESCALATE_IMMEDIATELY", Priority.CRITICAL
        elif priority_score >= 0.6:
            return "INVESTIGATE_HIGH_PRIORITY", Priority.HIGH
        elif priority_score >= 0.4:
            return "STANDARD_INVESTIGATION", Priority.MEDIUM
        else:
            return "MONITOR_ONLY", Priority.LOW
    
    def _determine_auto_action(self, priority_score: float, risk_score: float) -> str:
        """Determine automatic action."""
        if risk_score >= 0.9:
            return "FREEZE_ACCOUNT"
        elif risk_score >= 0.7:
            return "BLOCK_TRANSACTION"
        elif priority_score >= 0.6:
            return "FLAG_FOR_REVIEW"
        else:
            return "MONITOR"
    
    def _generate_reasoning(self, risk_score: float, amount: float, tier: str, alert_count: int) -> str:
        """Generate reasoning for triage decision."""
        reasons = []
        
        if risk_score >= 0.8:
            reasons.append(f"High risk score ({risk_score:.2f})")
        if amount >= 10000:
            reasons.append(f"High transaction amount (${amount:,.2f})")
        if alert_count > 3:
            reasons.append(f"Multiple alerts ({alert_count})")
        if tier == "vip":
            reasons.append("VIP customer protection")
        
        return "; ".join(reasons) if reasons else "Standard risk assessment"
    
    def _determine_priority_level(self, score: float) -> Priority:
        """Determine priority level."""
        if score >= 0.8:
            return Priority.CRITICAL
        elif score >= 0.6:
            return Priority.HIGH
        elif score >= 0.4:
            return Priority.MEDIUM
        else:
            return Priority.LOW
    
    def _check_escalation_rules(self, risk_score: float, amount: float, alert_types: List[str]) -> bool:
        """Check if escalation is required."""
        return (risk_score >= self.escalation_rules["critical_risk"] or 
                amount >= self.escalation_rules["high_amount"] or
                len(alert_types) >= self.escalation_rules["multiple_alerts"])
    
    def _get_escalation_reasons(self, risk_score: float, amount: float, alert_types: List[str]) -> List[str]:
        """Get escalation reasons."""
        reasons = []
        
        if risk_score >= self.escalation_rules["critical_risk"]:
            reasons.append("Critical risk score")
        if amount >= self.escalation_rules["high_amount"]:
            reasons.append("High value transaction")
        if len(alert_types) >= self.escalation_rules["multiple_alerts"]:
            reasons.append("Multiple alert types")
        
        return reasons
    
    def _determine_escalation_level(self, risk_score: float) -> str:
        """Determine escalation level."""
        if risk_score >= 0.9:
            return "EXECUTIVE"
        elif risk_score >= 0.7:
            return "SENIOR_MANAGEMENT"
        else:
            return "TEAM_LEAD"
    
    def _calculate_action_confidence(self, action_data: Dict[str, Any]) -> float:
        """Calculate action confidence."""
        risk_score = action_data.get("risk_score", 0.0)
        return min(risk_score + 0.1, 1.0)
    
    def _requires_human_review(self, action_data: Dict[str, Any]) -> bool:
        """Check if human review is required."""
        risk_score = action_data.get("risk_score", 0.0)
        return risk_score >= 0.4
    
    def _get_action_parameters(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get action parameters."""
        return {
            "action_type": action_data.get("auto_action", "MONITOR"),
            "urgency": "HIGH" if action_data.get("risk_score", 0.0) >= 0.6 else "NORMAL"
        }
