"""
Triage Service - Enterprise-grade orchestration layer.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.orchestration import draft_triage_initial_suspicion
from app.models.alert import Alert, AlertFilter
from app.models.triage import (
    AlertPolicy,
    AssessedAlert,
    InvestigationAction,
    InvestigationDecision,
    RiskScore,
    TriageAssessmentRequest,
    TriageAssessmentResponse,
    TriageSummary,
)
from app.repositories.alert_repository import AlertRepository, save_triage_assessment_to_sql
from app.services.decision_engine import DecisionEngine
from app.services.risk_scoring_engine import RiskScoringEngine

logger = get_logger(__name__)


def _scope_customer_key(customer_id: Optional[str]) -> Optional[str]:
    """Lowercase trimmed id for consistent comparisons across DB / JSON / query."""
    s = (customer_id or "").strip()
    return s.lower() if s else None


def _llm_credentials_configured() -> bool:
    return settings.llm_narrative_credentials_configured()


def _status_after_decision(decision: InvestigationDecision) -> str:
    """Persisted / API workflow status aligned with ``InvestigationAction`` (not severity alone)."""
    action = decision.action
    if action == InvestigationAction.AUTO_CLOSE:
        return "CLOSED"
    if action == InvestigationAction.MONITOR:
        return "MONITORING"
    return "OPEN_FOR_INVESTIGATION"


def _narrative_engine_status(
    want_narrative: bool,
    assessed_alerts: List[AssessedAlert],
    *,
    empty_batch: bool,
) -> Optional[str]:
    if not want_narrative:
        return "off"
    if empty_batch:
        return "no_provider" if not _llm_credentials_configured() else "no_alerts_in_scope"
    if not _llm_credentials_configured():
        return "no_provider"
    if any(a.initial_suspicion_source == "llm" for a in assessed_alerts):
        return "llm"
    return "llm_no_valid_note"


def _alert_summary_for_narrative(alert: Alert) -> Dict[str, Any]:
    """Compact, non-sensitive facts for the narrative model (token discipline)."""
    md = alert.metadata or {}
    return {
        "alert_id": alert.alert_id,
        "customer_id": alert.customer_id,
        "transaction_id": alert.transaction_id,
        "amount": alert.amount,
        "currency": alert.currency,
        "recipient_country": alert.recipient_country,
        "policy": md.get("policy"),
        "severity": alert.severity,
        "sanctioned_country": md.get("sanctioned_country"),
        "anomaly_type": md.get("anomaly_type"),
    }


class TriageService:
    """Enterprise-grade triage service orchestrating assessment workflow."""

    def __init__(self):
        self.repository = AlertRepository()
        self.risk_scorer = RiskScoringEngine()
        self.decision_engine = DecisionEngine()

    @staticmethod
    def _narrative_requested(request: TriageAssessmentRequest) -> bool:
        if request.include_initial_suspicion_note is not None:
            return bool(request.include_initial_suspicion_note)
        return bool(settings.triage_narrative_enabled)

    @staticmethod
    def _deterministic_suspicion_line(alert: Alert, risk_score: RiskScore, decision: InvestigationDecision) -> str:
        policy = (alert.metadata or {}).get("policy") or "unspecified"
        severity = risk_score.severity.value
        lead = decision.reasoning.strip()
        return (
            f"{lead} Policy `{policy}` at {severity} severity. "
            "This summary is rule-generated when the narrative model is unavailable."
        )

    async def _initial_suspicion_narrative(
        self,
        alert: Alert,
        risk_score: RiskScore,
        decision: InvestigationDecision,
    ) -> Tuple[str, List[str], str]:
        summary = _alert_summary_for_narrative(alert)
        rs = risk_score.model_dump(mode="json")
        dec = decision.model_dump(mode="json")
        try:
            out = await asyncio.wait_for(
                draft_triage_initial_suspicion(summary, rs, dec),
                timeout=settings.triage_narrative_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning("triage_narrative_timeout", alert_id=alert.alert_id)
            out = {"initial_suspicion_note": "", "key_observations": []}
        except Exception as e:
            logger.warning("triage_narrative_error", alert_id=alert.alert_id, error=str(e))
            out = {"initial_suspicion_note": "", "key_observations": []}

        note = str(out.get("initial_suspicion_note", "")).strip()
        obs_raw = out.get("key_observations") or []
        obs: List[str] = []
        if isinstance(obs_raw, list):
            obs = [str(x).strip() for x in obs_raw if str(x).strip()][:8]

        if note:
            return note, obs, "llm"

        fb = self._deterministic_suspicion_line(alert, risk_score, decision)
        logger.info("triage_narrative_fallback", alert_id=alert.alert_id, reason="empty_or_missing_llm_output")
        return fb, [], "deterministic_fallback"

    async def assess(self, request: TriageAssessmentRequest) -> TriageAssessmentResponse:
        """Load merged alerts, deterministic score + decision, optional Phase-1 LLM narrative, persist."""
        scope_customer = (request.customer_id or "").strip() or None
        alert_filter = AlertFilter(customer_id=scope_customer)
        alerts_response = await self.repository.get_alerts(alert_filter)
        alerts = list(alerts_response.alerts)

        want_key = _scope_customer_key(scope_customer)
        if want_key is not None:
            before = len(alerts)
            alerts = [a for a in alerts if _scope_customer_key(a.customer_id) == want_key]
            if before != len(alerts):
                logger.warning(
                    "triage_customer_scope_mismatch_filtered",
                    requested_customer=scope_customer,
                    dropped=before - len(alerts),
                )
        logger.info(
            "triage_alerts_in_scope",
            customer_id=scope_customer,
            count=len(alerts),
        )

        want_narrative = self._narrative_requested(request)

        if not alerts:
            return self._build_empty_response(scope_customer, want_narrative)

        # Process each alert through the pipeline
        assessed_alerts = []
        investigation_decisions = []

        for alert in alerts:
            risk_score = self.risk_scorer.score(alert)
            decision = self.decision_engine.decide(risk_score)

            alert.status = _status_after_decision(decision)

            md_update: Dict[str, Any] = {
                "triage_assessment": risk_score.model_dump(mode="json"),
                "investigation_decision": decision.model_dump(mode="json"),
            }

            suspicion_note: Optional[str] = None
            suspicion_src: Optional[str] = None
            suspicion_obs: List[str] = []
            if want_narrative:
                suspicion_note, suspicion_obs, suspicion_src = await self._initial_suspicion_narrative(
                    alert, risk_score, decision
                )
                md_update["initial_suspicion_note"] = suspicion_note
                md_update["initial_suspicion_source"] = suspicion_src
                md_update["initial_suspicion_generated_at"] = datetime.now(timezone.utc).isoformat()
                if suspicion_obs:
                    md_update["initial_suspicion_key_observations"] = suspicion_obs

            alert.metadata.update(md_update)

            assessed_alert = AssessedAlert(
                alert_id=alert.alert_id,
                customer_id=alert.customer_id,
                policy=AlertPolicy(alert.metadata.get("policy", "")),
                risk_score=risk_score,
                decision=decision,
                investigation_required=decision.action.value == "ESCALATE_FOR_INVESTIGATION",
                status=alert.status,
                initial_suspicion_note=suspicion_note if want_narrative else None,
                initial_suspicion_source=suspicion_src if want_narrative else None,
            )

            assessed_alerts.append(assessed_alert)
            investigation_decisions.append(decision.action.value)

            await self.repository.update_alert(alert.alert_id, alert.model_dump(mode="json"))

            assessment_row: Dict[str, Any] = {
                "triage_assessment": risk_score.model_dump(mode="json"),
                "investigation_decision": decision.model_dump(mode="json"),
                "source": "POST /v1/triage/assess",
            }
            if want_narrative and suspicion_note is not None:
                assessment_row["initial_suspicion_note"] = suspicion_note
                assessment_row["initial_suspicion_source"] = suspicion_src
                assessment_row["initial_suspicion_generated_at"] = md_update.get("initial_suspicion_generated_at")
                if md_update.get("initial_suspicion_key_observations"):
                    assessment_row["initial_suspicion_key_observations"] = md_update["initial_suspicion_key_observations"]

            save_triage_assessment_to_sql(
                alert.alert_id,
                risk_score.score,
                assessment_row,
            )

        return self._build_response(assessed_alerts, investigation_decisions, scope_customer, want_narrative)

    def _build_empty_response(
        self, customer_id: Optional[str], want_narrative: bool
    ) -> TriageAssessmentResponse:
        """Build response for no alerts found."""
        scope = "single_customer" if customer_id else "all_customers"
        if customer_id:
            hint = (
                f"No alerts in the merged store matched customer `{customer_id}`. "
                "Confirm that customer exists in ``kyc_profiles``, run ``POST /v1/alerts/generate?customer_id=...``, "
                "or omit the query parameter to triage the full queue."
            )
        else:
            hint = (
                "No alerts in the merged store (Postgres ``alerts`` + runtime JSON). "
                "Call POST /v1/alerts/generate first (requires ``kyc_profiles`` for each customer), "
                "then POST /v1/triage/assess again."
            )
        engine = _narrative_engine_status(want_narrative, [], empty_batch=True)
        return TriageAssessmentResponse(
            success=True,
            total_alerts_assessed=0,
            auto_closed_count=0,
            monitor_count=0,
            investigation_required_count=0,
            auto_close_rate=0.0,
            escalation_rate=0.0,
            average_risk_score=0.0,
            assessed_alerts=[],
            initial_suspicion_engine_status=engine,
            hint=hint,
            triage_summary=TriageSummary(
                total_alerts_processed=0,
                auto_closed_count=0,
                monitor_count=0,
                escalated_count=0,
                auto_close_rate=0.0,
                escalation_rate=0.0,
                average_risk_score=0.0,
                customer_id=customer_id,
                assessment_scope=scope,
                policy_breakdown={},
                severity_distribution={"critical": 0, "high": 0, "medium": 0, "low": 0},
            )
        )

    def _build_response(
        self,
        assessed_alerts: List[AssessedAlert],
        investigation_decisions: List[str],
        customer_id: Optional[str],
        want_narrative: bool,
    ) -> TriageAssessmentResponse:
        """Build comprehensive triage assessment response."""
        all_assessed = assessed_alerts
        total_assessed = len(all_assessed)
        auto_closed = len([d for d in investigation_decisions if d == "AUTO_CLOSE"])
        monitored = len([d for d in investigation_decisions if d == "MONITOR"])
        escalated = len([d for d in investigation_decisions if d == "ESCALATE_FOR_INVESTIGATION"])

        # Calculate statistics
        average_risk = sum(alert.risk_score.score for alert in all_assessed) / total_assessed
        auto_close_rate = (auto_closed / total_assessed) * 100 if total_assessed > 0 else 0
        escalation_rate = (escalated / total_assessed) * 100 if total_assessed > 0 else 0

        # Build breakdown statistics
        policy_breakdown = self._build_policy_breakdown(all_assessed)
        severity_distribution = self._build_severity_distribution(all_assessed)

        scope = "single_customer" if customer_id else "all_customers"
        engine = _narrative_engine_status(want_narrative, all_assessed, empty_batch=False)
        return TriageAssessmentResponse(
            success=True,
            total_alerts_assessed=total_assessed,
            auto_closed_count=auto_closed,
            monitor_count=monitored,
            investigation_required_count=escalated,
            auto_close_rate=round(auto_close_rate, 2),
            escalation_rate=round(escalation_rate, 2),
            average_risk_score=round(average_risk, 3),
            assessed_alerts=all_assessed,
            initial_suspicion_engine_status=engine,
            hint=None,
            triage_summary=TriageSummary(
                total_alerts_processed=total_assessed,
                auto_closed_count=auto_closed,
                monitor_count=monitored,
                escalated_count=escalated,
                auto_close_rate=round(auto_close_rate, 2),
                escalation_rate=round(escalation_rate, 2),
                average_risk_score=round(average_risk, 3),
                customer_id=customer_id,
                assessment_scope=scope,
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
            bucket = alert.risk_score.severity.value.lower()
            if bucket in distribution:
                distribution[bucket] += 1

        return distribution
