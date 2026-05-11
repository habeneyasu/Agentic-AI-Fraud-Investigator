"""
LLM orchestration — coordinates multi-step AI reasoning for fraud investigations.
Uses Claude Sonnet for synthesis and Haiku for fast triage scoring.
"""

from __future__ import annotations

from typing import Any

from app.llm.client import call_fast_json, call_reasoning_json
from app.llm.prompts import (
    get_investigation_synthesis_prompt,
    get_triage_prompt,
    get_hitl_recommendation_prompt,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


async def synthesize_investigation(
    transaction_result: dict[str, Any],
    kyc_result: dict[str, Any],
    sanctions_result: dict[str, Any],
    customer_context: dict[str, Any],
) -> dict[str, Any]:
    """
    Use Claude Sonnet to synthesize all agent findings into a final risk assessment.
    Returns structured JSON with risk_score, reasoning, evidence_chain, etc.
    """
    prompt = get_investigation_synthesis_prompt(
        transaction_result, kyc_result, sanctions_result, customer_context
    )
    result = await call_reasoning_json(prompt, max_tokens=1500)

    if not result:
        # Fallback: rule-based synthesis
        logger.warning("LLM synthesis failed — using rule-based fallback")
        return _rule_based_fallback(transaction_result, kyc_result, sanctions_result)

    return result


async def triage_alert(
    alert_data: dict[str, Any],
    customer_context: dict[str, Any],
) -> dict[str, Any]:
    """
    Use Claude Haiku for fast triage classification.
    Returns decision (AUTO_CLOSE | ESCALATE_FOR_ANALYSIS), priority, risk_score.
    """
    prompt = get_triage_prompt(alert_data, customer_context)
    result = await call_fast_json(prompt, max_tokens=512)

    if not result:
        logger.warning("LLM triage failed — using rule-based fallback")
        return _triage_fallback(alert_data)

    return result


async def get_hitl_recommendation(
    investigation_summary: dict[str, Any],
    agent_findings: dict[str, Any],
    risk_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Use Claude Sonnet to generate a recommendation for the human analyst.
    """
    prompt = get_hitl_recommendation_prompt(investigation_summary, agent_findings, risk_result)
    result = await call_reasoning_json(prompt, max_tokens=1024)

    if not result:
        return {
            "recommended_action": "REQUEST_MORE_INFO",
            "confidence": 0.5,
            "analyst_briefing": "AI recommendation unavailable. Please review manually.",
            "supporting_evidence": [],
            "risk_if_wrong": "Unknown — manual review required.",
        }

    return result


# ─── Rule-based fallbacks ────────────────────────────────────────────────────

def _rule_based_fallback(tx: dict, kyc: dict, san: dict) -> dict[str, Any]:
    score = 0.0
    signals = []

    tx_risk = tx.get("risk_score", 0)
    if isinstance(tx_risk, (int, float)) and tx_risk > 0.5:
        score += tx_risk * 0.35
        signals.append(f"Transaction risk: {tx_risk:.2f}")

    kyc_risk = kyc.get("risk_score", 0)
    if isinstance(kyc_risk, (int, float)) and kyc_risk > 0.3:
        score += kyc_risk * 0.25
        signals.append(f"KYC anomaly: {kyc_risk:.2f}")

    san_risk = san.get("risk_score", 0)
    if isinstance(san_risk, (int, float)) and san_risk > 0.3:
        score += san_risk * 0.40
        signals.append(f"Sanctions risk: {san_risk:.2f}")

    score = min(score, 1.0)
    tier = "CRITICAL" if score >= 0.8 else "HIGH" if score >= 0.6 else "MEDIUM" if score >= 0.4 else "LOW"

    return {
        "final_risk_score": round(score, 3),
        "risk_tier": tier,
        "confidence": 0.7,
        "executive_summary": f"Rule-based assessment: {tier} risk ({score:.0%}). " + " ".join(signals),
        "evidence_chain": [{"signal": s, "source": "rule_engine", "weight": 0.33, "detail": s} for s in signals],
        "recommendation": "FREEZE" if score >= 0.8 else "REVIEW" if score >= 0.6 else "MONITOR",
        "requires_human_review": score >= 0.6,
        "reasoning_steps": signals or ["No significant signals detected"],
    }


def _triage_fallback(alert: dict) -> dict[str, Any]:
    HIGH_RISK = {"IR", "KP", "SY", "CU", "VE", "MM", "BY"}
    amount = alert.get("amount", 0)
    country = alert.get("destination_country", "")

    if amount < 100:
        return {"decision": "AUTO_CLOSE", "priority": "LOW", "risk_score": 0.1,
                "confidence": 0.95, "reasoning": "Amount below threshold.", "key_flags": []}

    if amount > 1000 and country in HIGH_RISK:
        return {"decision": "ESCALATE_FOR_ANALYSIS", "priority": "CRITICAL", "risk_score": 0.9,
                "confidence": 0.9, "reasoning": "High-value transfer to sanctioned country.",
                "key_flags": ["high_value", "sanctioned_country"]}

    score = 0.3 + (0.3 if amount > 1000 else 0) + (0.2 if country in HIGH_RISK else 0)
    return {
        "decision": "ESCALATE_FOR_ANALYSIS" if score > 0.5 else "AUTO_CLOSE",
        "priority": "HIGH" if score > 0.7 else "MEDIUM" if score > 0.5 else "LOW",
        "risk_score": round(score, 2),
        "confidence": 0.75,
        "reasoning": "Rule-based triage assessment.",
        "key_flags": [],
    }
