"""
Prompt templates for fraud investigation AI reasoning.
All prompts are designed to return structured JSON responses.
"""

from typing import Any


def get_fraud_analysis_prompt(event: dict[str, Any]) -> str:
    return f"""You are an expert fraud analyst at a digital bank. Analyze the following fraud investigation findings and provide a structured risk assessment.

INVESTIGATION DATA:
{_format_dict(event)}

Respond ONLY with valid JSON in this exact format:
{{
  "risk_score": <float 0.0-1.0>,
  "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<2-3 sentence explanation of the key fraud signals>",
  "key_signals": ["<signal 1>", "<signal 2>", "<signal 3>"],
  "recommendation": "<APPROVE|MONITOR|REVIEW|FREEZE|ESCALATE>"
}}"""


def get_investigation_synthesis_prompt(
    transaction_result: dict,
    kyc_result: dict,
    sanctions_result: dict,
    customer_context: dict,
) -> str:
    return f"""You are a senior fraud investigator synthesizing evidence from three parallel AI agents. Provide a comprehensive risk assessment.

TRANSACTION AGENT FINDINGS:
{_format_dict(transaction_result)}

KYC / DEVICE AGENT FINDINGS:
{_format_dict(kyc_result)}

SANCTIONS AGENT FINDINGS:
{_format_dict(sanctions_result)}

CUSTOMER CONTEXT:
{_format_dict(customer_context)}

Analyze all evidence holistically. Consider how signals compound each other.

Respond ONLY with valid JSON:
{{
  "final_risk_score": <float 0.0-1.0>,
  "risk_tier": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "confidence": <float 0.0-1.0>,
  "executive_summary": "<3-4 sentence narrative explaining the fraud risk in plain English>",
  "evidence_chain": [
    {{"signal": "<signal name>", "source": "<agent name>", "weight": <float>, "detail": "<explanation>"}}
  ],
  "recommendation": "<APPROVE|MONITOR|REVIEW|FREEZE|ESCALATE>",
  "requires_human_review": <true|false>,
  "reasoning_steps": [
    "<step 1 of reasoning>",
    "<step 2 of reasoning>",
    "<step 3 of reasoning>"
  ]
}}"""


def get_triage_prompt(alert_data: dict, customer_context: dict) -> str:
    return f"""You are a fraud triage specialist. Quickly assess this alert and decide whether to auto-close or escalate for full investigation.

ALERT:
{_format_dict(alert_data)}

CUSTOMER CONTEXT:
{_format_dict(customer_context)}

Apply these rules before using AI judgment:
- Amount < $100 → AUTO_CLOSE
- Amount > $1000 + high-risk country → ESCALATE
- New device + geo mismatch → ESCALATE
- Known fraud memory hit → ESCALATE

Respond ONLY with valid JSON:
{{
  "decision": "<AUTO_CLOSE|ESCALATE_FOR_ANALYSIS>",
  "priority": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "risk_score": <float 0.0-1.0>,
  "confidence": <float 0.0-1.0>,
  "reasoning": "<1-2 sentence explanation>",
  "key_flags": ["<flag 1>", "<flag 2>"]
}}"""


def get_hitl_recommendation_prompt(
    investigation_summary: dict,
    agent_findings: dict,
    risk_result: dict,
) -> str:
    return f"""You are a senior fraud analyst providing a recommendation to a human analyst who must make the final decision.

INVESTIGATION SUMMARY:
{_format_dict(investigation_summary)}

AGENT FINDINGS:
{_format_dict(agent_findings)}

RISK ASSESSMENT:
{_format_dict(risk_result)}

Provide a clear, concise recommendation for the human analyst.

Respond ONLY with valid JSON:
{{
  "recommended_action": "<CONFIRM_FRAUD|FALSE_POSITIVE|REQUEST_MORE_INFO>",
  "confidence": <float 0.0-1.0>,
  "analyst_briefing": "<3-4 sentence briefing for the analyst explaining what they're looking at>",
  "supporting_evidence": ["<evidence point 1>", "<evidence point 2>", "<evidence point 3>"],
  "risk_if_wrong": "<brief description of consequences if the recommendation is incorrect>"
}}"""


def _format_dict(d: dict, indent: int = 0) -> str:
    """Format a dict for prompt inclusion."""
    import json
    try:
        return json.dumps(d, indent=2, default=str)
    except Exception:
        return str(d)
