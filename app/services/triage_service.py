"""
Triage Service - Enterprise-grade orchestration layer.
"""

from typing import List, Optional, Dict, Any

from app.models.alert import AlertFilter
from app.models.triage import (
    AlertPolicy,
    TriageAssessmentRequest,
    TriageAssessmentResponse,
    AssessedAlert,
    TriageSummary,
)
from app.repositories.alert_repository import AlertRepository
from app.services.risk_scoring_engine import RiskScoringEngine
from app.services.decision_engine import DecisionEngine


class TriageService:
    """Enterprise-grade triage service orchestrating assessment workflow."""

    def __init__(self):
        self.repository = AlertRepository()
        self.risk_scorer = RiskScoringEngine()
        self.decision_engine = DecisionEngine()

    async def assess(self, request: TriageAssessmentRequest) -> TriageAssessmentResponse:
        """
        Perform complete triage assessment workflow.

        Args:
            request: TriageAssessmentRequest with optional customer_id

        Returns:
            TriageAssessmentResponse with complete assessment results
        """
        # Get alerts from repository
        alert_filter = AlertFilter(customer_id=request.customer_id)
        alerts_response = await self.repository.get_alerts(alert_filter)
        alerts = alerts_response.alerts

        if not alerts:
            return self._build_empty_response(request.customer_id)

        # Process each alert through the pipeline
        assessed_alerts = []
        investigation_decisions = []

        for alert in alerts:
            # Step 1: Risk scoring
            risk_score = self.risk_scorer.score(alert)

            # Step 2: Decision making
            decision = self.decision_engine.decide(risk_score)

            # Step 3: Update alert status
            alert.status = "CLOSED" if decision.action.value == "AUTO_CLOSE" else "OPEN_FOR_INVESTIGATION"
            alert.metadata.update({
                "triage_assessment": risk_score.dict(),
                "investigation_decision": decision.dict()
            })

            # Step 4: Create assessed alert object
            assessed_alert = AssessedAlert(
                alert_id=alert.alert_id,
                customer_id=alert.customer_id,
                policy=AlertPolicy(alert.metadata.get("policy", "")),
                risk_score=risk_score,
                decision=decision,
                investigation_required=decision.action.value == "ESCALATE_FOR_INVESTIGATION",
                status=alert.status
            )

            assessed_alerts.append(assessed_alert)
            investigation_decisions.append(decision.action.value)

            # Update alert in repository
            await self.repository.update_alert(alert.alert_id, alert.dict())

        # Build comprehensive response
        return self._build_response(assessed_alerts, investigation_decisions, request.customer_id)

    def _build_empty_response(self, customer_id: Optional[str]) -> TriageAssessmentResponse:
        """Build response for no alerts found."""
        return TriageAssessmentResponse(
            success=True,
            total_alerts_assessed=0,
            auto_closed_count=0,
            investigation_required_count=0,
            auto_close_rate=0.0,
            escalation_rate=0.0,
            average_risk_score=0.0,
            assessed_alerts=[],
            hint=(
                "No alerts in the API process memory. The triage store is filled only by this service "
                "(e.g. POST /v1/alerts/generate?customer_id=CUST003). JSON in Streamlit or on disk is not read here. "
                "Call generate first, then POST /v1/triage/assess again."
            ),
            triage_summary=TriageSummary(
                total_alerts_processed=0,
                auto_closed_count=0,
                escalated_count=0,
                auto_close_rate=0.0,
                escalation_rate=0.0,
                average_risk_score=0.0,
                customer_id=customer_id,
                assessment_scope="customer_specific" if customer_id else "all_alerts",
                policy_breakdown={},
                severity_distribution={}
            )
        )

    def _build_response(
        self,
        assessed_alerts: List[AssessedAlert],
        investigation_decisions: List[str],
        customer_id: Optional[str]
    ) -> TriageAssessmentResponse:
        """Build comprehensive triage assessment response."""
        total_assessed = len(assessed_alerts)
        auto_closed = len([d for d in investigation_decisions if d == "AUTO_CLOSE"])
        escalated = len([d for d in investigation_decisions if d == "ESCALATE_FOR_INVESTIGATION"])

        # Calculate statistics
        average_risk = sum(alert.risk_score.score for alert in assessed_alerts) / total_assessed
        auto_close_rate = (auto_closed / total_assessed) * 100 if total_assessed > 0 else 0
        escalation_rate = (escalated / total_assessed) * 100 if total_assessed > 0 else 0

        # Build breakdown statistics
        policy_breakdown = self._build_policy_breakdown(assessed_alerts)
        severity_distribution = self._build_severity_distribution(assessed_alerts)

        return TriageAssessmentResponse(
            success=True,
            total_alerts_assessed=total_assessed,
            auto_closed_count=auto_closed,
            investigation_required_count=escalated,
            auto_close_rate=round(auto_close_rate, 2),
            escalation_rate=round(escalation_rate, 2),
            average_risk_score=round(average_risk, 3),
            assessed_alerts=assessed_alerts,
            hint=None,
            triage_summary=TriageSummary(
                total_alerts_processed=total_assessed,
                auto_closed_count=auto_closed,
                escalated_count=escalated,
                auto_close_rate=round(auto_close_rate, 2),
                escalation_rate=round(escalation_rate, 2),
                average_risk_score=round(average_risk, 3),
                customer_id=customer_id,
                assessment_scope="customer_specific" if customer_id else "all_alerts",
                policy_breakdown=policy_breakdown,
                severity_distribution=severity_distribution
            )
        )

    def _build_policy_breakdown(self, assessed_alerts: List[AssessedAlert]) -> dict:
        """Build policy type breakdown statistics."""
        breakdown = {
            "high_value_transactions": 0,
            "new_device_logins": 0,
            "sanctioned_countries": 0
        }

        for alert in assessed_alerts:
            if alert.policy == AlertPolicy.HIGH_VALUE_TRANSACTION:
                breakdown["high_value_transactions"] += 1
            elif alert.policy == AlertPolicy.NEW_DEVICE_LOGIN:
                breakdown["new_device_logins"] += 1
            elif alert.policy == AlertPolicy.SANCTIONED_COUNTRY:
                breakdown["sanctioned_countries"] += 1

        return breakdown

    def _build_severity_distribution(self, assessed_alerts: List[AssessedAlert]) -> dict:
        """Build severity distribution statistics."""
        distribution = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }

        for alert in assessed_alerts:
            severity = alert.risk_score.severity.value
            if severity in distribution:
                distribution[severity] += 1

        return distribution
