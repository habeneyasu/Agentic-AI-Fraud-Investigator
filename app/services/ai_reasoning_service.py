"""
AI Reasoning and Risk Scoring Service - Clean Architecture Implementation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import re

from app.services.base import BaseService
from app.shared.enums import RiskLevel, FraudPattern, AnomalyType, SanctionType
from app.shared.models import RiskFactor, ScoringResult


class AIReasoningService(BaseService):
    """AI reasoning service for fraud investigation analysis."""
    
    def __init__(self):
        super().__init__()
        self.risk_weights = {
            "transaction_anomalies": 0.35,
            "kyc_anomalies": 0.25,
            "sanctions_hits": 0.30,
            "historical_patterns": 0.10
        }
        
        self.risk_thresholds = {
            "critical": 0.8,
            "high": 0.6,
            "medium": 0.4,
            "low": 0.0
        }
    
    def generate_executive_summary(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary for alert."""
        try:
            # Extract key information from alert
            customer_id = alert.get("customer_id", "Unknown")
            amount = alert.get("amount", 0)
            severity = alert.get("severity", "medium")
            alert_type = alert.get("alert_type", "UNKNOWN")
            
            # Generate contextual summary based on alert characteristics
            if severity == "high" and amount > 10000:
                summary = f"High-value transaction alert for customer {customer_id}. Amount of ${amount:,.2f} exceeds typical transaction patterns and requires immediate investigation. Risk factors include unusual transaction size and potential sanctions exposure."
            elif severity == "high":
                summary = f"High-risk alert detected for customer {customer_id}. {alert_type} requires immediate attention due to multiple risk indicators present in the transaction pattern."
            elif severity == "medium":
                summary = f"Medium-risk alert for customer {customer_id}. ${amount:,.2f} transaction shows some concerning patterns that warrant review but do not require immediate action."
            else:
                summary = f"Low-risk alert for customer {customer_id}. ${amount:,.2f} transaction shows minor anomalies but appears within normal parameters."
            
            return {
                "summary": summary,
                "risk_score": 0.8 if severity == "high" else 0.6 if severity == "medium" else 0.3,
                "confidence": 0.85,
                "recommendation": "ESCALATE_FOR_ANALYSIS" if severity in ["high", "medium"] else "AUTO_CLOSE"
            }
        except Exception as e:
            self.logger.error(f"Error generating executive summary: {e}")
            return {
                "summary": "AI analysis temporarily unavailable. Please review alert manually.",
                "risk_score": 0.5,
                "confidence": 0.5,
                "recommendation": "MANUAL_REVIEW"
            }

    async def analyze_investigation_findings(
        self,
        investigation_id: str,
        agent_findings: Dict[str, Any],
        customer_context: Dict[str, Any]
    ) -> ScoringResult:
        """Analyze all agent findings and generate AI reasoning."""
        self._log_operation("analyze_investigation_findings", 
                          investigation_id=investigation_id)
        
        try:
            # Extract findings from each agent
            transaction_findings = agent_findings.get("transaction_analysis", [])
            kyc_findings = agent_findings.get("kyc_analysis", [])
            sanctions_findings = agent_findings.get("sanctions_analysis", [])
            
            # Calculate component scores
            transaction_score = self._analyze_transaction_risk(transaction_findings)
            kyc_score = self._analyze_kyc_risk(kyc_findings)
            sanctions_score = self._analyze_sanctions_risk(sanctions_findings)
            historical_score = self._analyze_historical_patterns(customer_context)
            
            # Calculate overall risk score
            overall_score = (
                transaction_score * self.risk_weights["transaction_anomalies"] +
                kyc_score * self.risk_weights["kyc_anomalies"] +
                sanctions_score * self.risk_weights["sanctions_hits"] +
                historical_score * self.risk_weights["historical_patterns"]
            )
            
            # Determine risk level
            risk_level = self._determine_risk_level(overall_score)
            
            # Generate risk factors
            risk_factors = self._generate_risk_factors(
                transaction_findings, kyc_findings, sanctions_findings, 
                customer_context, overall_score
            )
            
            # Generate AI explanation
            explanation = self._generate_ai_explanation(
                overall_score, risk_level, risk_factors, agent_findings
            )
            
            # Calculate confidence
            confidence = self._calculate_confidence(
                transaction_findings, kyc_findings, sanctions_findings
            )
            
            result = ScoringResult(
                risk_score=overall_score,
                risk_level=risk_level,
                confidence=confidence,
                factors=risk_factors,
                explanation=explanation,
                scoring_mode="hybrid",
                timestamp=datetime.utcnow(),
                rule_score=overall_score,  # In demo, same as overall
                ai_score=overall_score     # In demo, same as overall
            )
            
            self._log_operation("ai_analysis_completed", 
                              investigation_id=investigation_id,
                              risk_score=overall_score,
                              risk_level=risk_level)
            
            return result
            
        except Exception as e:
            self._log_error("analyze_investigation_findings", e)
            # Return default result on error
            return ScoringResult(
                risk_score=0.5,
                risk_level=RiskLevel.MEDIUM,
                confidence=0.0,
                factors=[],
                explanation="AI analysis failed - default medium risk assigned",
                scoring_mode="hybrid",
                timestamp=datetime.utcnow()
            )
    
    def _analyze_transaction_risk(self, transaction_findings: List[Dict[str, Any]]) -> float:
        """Analyze transaction risk."""
        if not transaction_findings:
            return 0.0
        
        risk_score = 0.0
        
        for finding in transaction_findings:
            anomalies = finding.get("anomalies", [])
            for anomaly in anomalies:
                # High-risk patterns
                if anomaly.get("pattern") == "high_value_rush":
                    risk_score += 0.4
                elif anomaly.get("pattern") == "velocity_spike":
                    risk_score += 0.3
                elif anomaly.get("pattern") == "unusual_destination":
                    risk_score += 0.35
                elif anomaly.get("pattern") == "odd_time_transfer":
                    risk_score += 0.25
                else:
                    risk_score += 0.15
        
        return min(risk_score, 1.0)
    
    def _analyze_kyc_risk(self, kyc_findings: List[Dict[str, Any]]) -> float:
        """Analyze KYC risk."""
        if not kyc_findings:
            return 0.0
        
        risk_score = 0.0
        
        for finding in kyc_findings:
            anomaly_type = finding.get("anomaly_type", "")
            
            # High-risk KYC anomalies
            if anomaly_type == "geo_location_mismatch":
                risk_score += 0.45
            elif anomaly_type == "brute_force_attempt":
                risk_score += 0.5
            elif anomaly_type == "new_device":
                risk_score += 0.2
            elif anomaly_type == "multiple_failed_attempts":
                risk_score += 0.35
            else:
                risk_score += 0.1
        
        return min(risk_score, 1.0)
    
    def _analyze_sanctions_risk(self, sanctions_findings: List[Dict[str, Any]]) -> float:
        """Analyze sanctions risk."""
        if not sanctions_findings:
            return 0.0
        
        risk_score = 0.0
        
        for finding in sanctions_findings:
            finding_risk = finding.get("risk_score", 0.0)
            sanction_type = finding.get("sanction_type", "")
            
            # Critical sanctions types
            if sanction_type == SanctionType.TERRORISM:
                risk_score += 0.8
            elif sanction_type == SanctionType.FINANCIAL:
                risk_score += 0.6
            elif sanction_type == SanctionType.TRADE:
                risk_score += 0.4
            else:
                risk_score += 0.2
            
            # Add finding-specific risk
            risk_score += finding_risk * 0.3
        
        return min(risk_score, 1.0)
    
    def _analyze_historical_patterns(self, customer_context: Dict[str, Any]) -> float:
        """Analyze historical fraud patterns."""
        fraud_patterns = customer_context.get("fraud_patterns", [])
        
        if not fraud_patterns:
            return 0.0
        
        risk_score = 0.0
        
        for pattern in fraud_patterns:
            pattern_risk = pattern.get("risk_score", 0.0)
            frequency = pattern.get("frequency", 1)
            pattern_type = pattern.get("pattern_type", "")
            
            # High-risk historical patterns
            if pattern_type == FraudPattern.VELOCITY_SPIKE:
                risk_score += 0.3 * min(frequency / 3, 1.0)
            elif pattern_type == FraudPattern.GEO_ANOMALY:
                risk_score += 0.25 * min(frequency / 2, 1.0)
            elif pattern_type == FraudPattern.DEVICE_ANOMALY:
                risk_score += 0.2 * min(frequency / 2, 1.0)
            else:
                risk_score += 0.1 * min(frequency / 5, 1.0)
            
            # Add pattern-specific risk
            risk_score += pattern_risk * 0.2
        
        return min(risk_score, 1.0)
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level based on score."""
        if risk_score >= self.risk_thresholds["critical"]:
            return RiskLevel.CRITICAL
        elif risk_score >= self.risk_thresholds["high"]:
            return RiskLevel.HIGH
        elif risk_score >= self.risk_thresholds["medium"]:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_risk_factors(
        self,
        transaction_findings: List[Dict[str, Any]],
        kyc_findings: List[Dict[str, Any]],
        sanctions_findings: List[Dict[str, Any]],
        customer_context: Dict[str, Any],
        overall_score: float
    ) -> List[RiskFactor]:
        """Generate detailed risk factors."""
        risk_factors = []
        
        # Transaction risk factors
        for finding in transaction_findings:
            anomalies = finding.get("anomalies", [])
            for anomaly in anomalies:
                risk_factors.append(RiskFactor(
                    category="transaction",
                    factor=anomaly.get("pattern", "unknown"),
                    weight=0.35,
                    value=0.8 if anomaly.get("severity") == "high" else 0.5,
                    description=f"Transaction anomaly: {anomaly.get('description', 'No description')}"
                ))
        
        # KYC risk factors
        for finding in kyc_findings:
            risk_factors.append(RiskFactor(
                category="kyc",
                factor=finding.get("anomaly_type", "unknown"),
                weight=0.25,
                value=0.7 if finding.get("severity") == "high" else 0.4,
                description=f"KYC anomaly detected: {finding.get('description', 'No description')}"
            ))
        
        # Sanctions risk factors
        for finding in sanctions_findings:
            risk_factors.append(RiskFactor(
                category="sanctions",
                factor=finding.get("sanction_type", "unknown"),
                weight=0.30,
                value=finding.get("risk_score", 0.5),
                description=f"Sanctions risk: {finding.get('reason', 'No reason provided')}"
            ))
        
        # Historical pattern risk factors
        fraud_patterns = customer_context.get("fraud_patterns", [])
        for pattern in fraud_patterns:
            risk_factors.append(RiskFactor(
                category="historical",
                factor=pattern.get("pattern_type", "unknown"),
                weight=0.10,
                value=pattern.get("risk_score", 0.3),
                description=f"Historical pattern: {pattern.get('description', 'No description')}"
            ))
        
        return risk_factors
    
    def _generate_ai_explanation(
        self,
        overall_score: float,
        risk_level: str,
        risk_factors: List[RiskFactor],
        agent_findings: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """Generate AI explanation for the risk assessment."""
        
        # Count findings by category
        tx_anomalies = len(agent_findings.get("transaction_analysis", []))
        kyc_anomalies = len(agent_findings.get("kyc_analysis", []))
        sanctions_hits = len(agent_findings.get("sanctions_analysis", []))
        
        # Generate explanation
        explanation_parts = []
        
        # Overall assessment
        explanation_parts.append(
            f"AI analysis indicates {risk_level.lower()} risk (score: {overall_score:.2f}) "
            f"based on comprehensive investigation findings."
        )
        
        # Transaction analysis
        if tx_anomalies > 0:
            explanation_parts.append(
                f"Transaction agent identified {tx_anomalies} anomalies, "
                f"including unusual transaction patterns and velocity spikes."
            )
        
        # KYC analysis
        if kyc_anomalies > 0:
            explanation_parts.append(
                f"KYC agent detected {kyc_anomalies} anomalies, "
                f"such as geographic location mismatches and device changes."
            )
        
        # Sanctions analysis
        if sanctions_hits > 0:
            explanation_parts.append(
                f"Sanctions agent found {sanctions_hits} potential matches, "
                f"requiring immediate attention."
            )
        
        # Risk factor summary
        high_risk_factors = [rf for rf in risk_factors if rf.value > 0.7]
        if high_risk_factors:
            explanation_parts.append(
                f"Key risk factors include: {', '.join([rf.factor for rf in high_risk_factors[:3]])}."
            )
        
        # Recommendation
        if overall_score > 0.8:
            explanation_parts.append(
                "Recommendation: Immediate escalation and account freeze required."
            )
        elif overall_score > 0.6:
            explanation_parts.append(
                "Recommendation: Detailed manual review and enhanced monitoring recommended."
            )
        elif overall_score > 0.4:
            explanation_parts.append(
                "Recommendation: Standard investigation protocol with enhanced monitoring."
            )
        else:
            explanation_parts.append(
                "Recommendation: Low risk - can be auto-closed with routine monitoring."
            )
        
        return " ".join(explanation_parts)
    
    def _calculate_confidence(
        self,
        transaction_findings: List[Dict[str, Any]],
        kyc_findings: List[Dict[str, Any]],
        sanctions_findings: List[Dict[str, Any]]
    ) -> float:
        """Calculate confidence in the AI assessment."""
        
        total_findings = len(transaction_findings) + len(kyc_findings) + len(sanctions_findings)
        
        if total_findings == 0:
            return 0.0
        
        # Base confidence from number of findings
        base_confidence = min(total_findings / 10.0, 1.0)
        
        # Adjust for finding quality (presence of detailed data)
        quality_bonus = 0.0
        
        for finding in transaction_findings:
            if finding.get("anomalies") and len(finding["anomalies"]) > 0:
                quality_bonus += 0.1
        
        for finding in kyc_findings:
            if finding.get("anomaly_type") and finding.get("geo_location"):
                quality_bonus += 0.1
        
        for finding in sanctions_findings:
            if finding.get("risk_score") is not None:
                quality_bonus += 0.1
        
        quality_bonus = min(quality_bonus, 0.3)
        
        return min(base_confidence + quality_bonus, 1.0)
    
    async def get_risk_explanation(self, investigation_id: str) -> Dict[str, Any]:
        """Get detailed risk explanation for investigation."""
        self._log_operation("get_risk_explanation", investigation_id=investigation_id)
        
        try:
            # In a real implementation, this would fetch stored analysis
            # For demo, return a structured explanation
            explanation = {
                "investigation_id": investigation_id,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "risk_methodology": {
                    "approach": "Hybrid AI reasoning with rule-based validation",
                    "data_sources": ["Transaction analysis", "KYC verification", "Sanctions screening", "Historical patterns"],
                    "weight_distribution": self.risk_weights,
                    "confidence_calculation": "Based on data quality and quantity of findings"
                },
                "key_indicators": {
                    "transaction_velocity": "High transaction frequency detected",
                    "geographic_anomaly": "Login from high-risk location",
                    "device_anomaly": "New device or suspicious device fingerprint",
                    "sanctions_match": "Potential match with sanctions database"
                },
                "recommendations": [
                    "Immediate account freeze for critical risk cases",
                    "Enhanced monitoring for high-risk cases",
                    "Standard investigation protocol for medium risk",
                    "Auto-close with monitoring for low risk cases"
                ]
            }
            
            return self._generate_response(explanation)
            
        except Exception as e:
            self._log_error("get_risk_explanation", e)
            return self._generate_response({"error": str(e)}, success=False)
