"""Human-in-the-loop (HITL) decision endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import RequireAnalyst, RequireApiKey
from app.api.fraud_memory import fraud_memory_service
from app.core.logging import get_logger
from app.services.action_engine import ActionEngine
from app.services.ai_reasoning_service import InvestigationReasoningService
from app.shared.enums import DecisionType, FraudPattern
from app.shared.models import ActionRequest, ActionResult, AnalystCaseDecision

logger = get_logger(__name__)
router = APIRouter(prefix="/api/hitl", tags=["hitl"])

hitl_decisions: Dict[str, Dict[str, Any]] = {}

_ai_reasoning = InvestigationReasoningService()

_DEMO_AGENT_FINDINGS = {
    "transaction_analysis": [
        {
            "agent": "transaction",
            "findings": "High-value transaction velocity spike detected",
            "anomalies": [
                {"pattern": "velocity_spike", "severity": "high", "count": 5},
                {"pattern": "high_value_rush", "severity": "critical", "count": 2},
            ],
            "risk_score": 0.92,
        }
    ],
    "kyc_analysis": [
        {
            "agent": "kyc",
            "findings": "Geographic location anomaly detected",
            "anomaly_type": "geo_location_mismatch",
            "location": "RU - Moscow",
            "risk_score": 0.78,
        }
    ],
    "sanctions_analysis": [
        {
            "agent": "sanctions",
            "findings": "Potential sanctions list match",
            "sanction_type": "FINANCIAL",
            "entity_matched": "Global Trading Corp",
            "risk_score": 0.65,
        }
    ],
}


async def _build_investigation_review_payload(investigation_id: str) -> Dict[str, Any]:
    ai_result = await _ai_reasoning.analyze_investigation_findings(
        investigation_id=investigation_id,
        agent_findings=_DEMO_AGENT_FINDINGS,
        customer_context={"customer_id": "CUST003"},
    )
    return {
        "investigation_id": investigation_id,
        "status": "ASSESSMENT",
        "customer_id": "CUST003",
        "risk_score": 0.85,
        "risk_level": "HIGH",
        "created_at": datetime.utcnow().isoformat(),
        "agent_findings": _DEMO_AGENT_FINDINGS,
        "ai_reasoning": {
            "overall_risk_score": ai_result.risk_score,
            "risk_level": ai_result.risk_level,
            "confidence": ai_result.confidence,
            "explanation": ai_result.explanation,
            "recommendation": "ESCALATE_FOR_ANALYSIS" if ai_result.risk_score > 0.7 else "AUTO_CLOSE",
            "factors": [f.factor for f in ai_result.factors],
            "scoring_mode": ai_result.scoring_mode,
        },
    }


class AnalystReviewRequest(BaseModel):
    investigation_id: str
    analyst_id: str
    analyst_notes: Optional[str] = None
    decision: Optional[str] = None
    recommended_actions: Optional[List[str]] = None


class AnalystReviewResponse(BaseModel):
    success: bool
    investigation_id: str
    analyst_decision: str
    ai_recommendation: Dict[str, Any]
    reasoning: str


class InvestigationReviewResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]


@router.get("/{investigation_id}/review", response_model=InvestigationReviewResponse)
async def get_investigation_for_review(
    investigation_id: str,
    _: None = RequireApiKey,
    __: None = RequireAnalyst,
):
    data = await _build_investigation_review_payload(investigation_id)
    return InvestigationReviewResponse(
        success=True,
        message="Investigation retrieved for review",
        data=data,
    )


@router.post("/{investigation_id}/review", response_model=AnalystReviewResponse)
async def submit_analyst_review(
    investigation_id: str,
    request: AnalystReviewRequest,
    _: None = RequireApiKey,
    __: None = RequireAnalyst,
):
    investigation_data = await _build_investigation_review_payload(investigation_id)

    analyst_decision = {
        "investigation_id": investigation_id,
        "analyst_id": request.analyst_id,
        "decision": request.decision or "REVIEW",
        "analyst_notes": request.analyst_notes,
        "recommended_actions": request.recommended_actions or [],
        "review_timestamp": datetime.utcnow().isoformat(),
        "ai_recommendation": investigation_data["ai_reasoning"],
        "final_decision": None,
    }

    ai_recommendation = investigation_data["ai_reasoning"]["recommendation"]

    if request.decision == "APPROVE":
        analyst_decision["final_decision"] = "CASE_APPROVED"
        reasoning = f"Analyst approved case despite AI recommendation to {ai_recommendation}."
    elif request.decision == "ESCALATE":
        analyst_decision["final_decision"] = "CASE_ESCALATED"
        reasoning = f"Analyst escalated case, aligning with AI recommendation to {ai_recommendation}."
    elif request.decision == "REJECT":
        analyst_decision["final_decision"] = "CASE_REJECTED"
        reasoning = f"Analyst rejected case, overriding AI recommendation to {ai_recommendation}."
    else:
        analyst_decision["final_decision"] = "UNDER_REVIEW"
        reasoning = "Analyst marked case for further review."

    if request.analyst_notes:
        reasoning += f" Analyst notes: {request.analyst_notes}"

    analyst_decision["reasoning"] = reasoning
    hitl_decisions[investigation_id] = analyst_decision

    logger.info("Analyst review submitted", investigation_id=investigation_id, decision=request.decision)

    dec = request.decision or "REVIEW"
    if dec in ("APPROVE", "ESCALATE", "REJECT"):
        cust = investigation_data["customer_id"]
        risk = float(investigation_data.get("risk_score", 0.75))
        conf = float(investigation_data.get("ai_reasoning", {}).get("confidence", 0.75))
        pt = FraudPattern.VELOCITY_ANOMALY.value
        if dec == "ESCALATE":
            pt = FraudPattern.KNOWN_FRAUDSTER.value
        elif dec == "REJECT":
            pt = FraudPattern.LOCATION_ANOMALY.value
            risk = min(risk, 0.35)
        elif dec == "APPROVE":
            risk = min(risk, 0.22)
        await fraud_memory_service.persist_hitl_outcome(
            entity_id=cust,
            entity_type="customer",
            risk_score=risk,
            confidence=conf,
            pattern_type=pt,
            metadata={
                "source": "hitl_analyst_review",
                "investigation_id": investigation_id,
                "analyst_decision": dec,
                "analyst_id": request.analyst_id,
                "final_decision": analyst_decision.get("final_decision"),
            },
        )

    return AnalystReviewResponse(
        success=True,
        investigation_id=investigation_id,
        analyst_decision=request.decision or "REVIEW",
        ai_recommendation=investigation_data["ai_reasoning"],
        reasoning=reasoning,
    )


@router.post("/{investigation_id}/decision")
async def submit_decision(
    investigation_id: str,
    payload: AnalystCaseDecision,
    _: None = RequireApiKey,
    __: None = RequireAnalyst,
):
    status_map = {
        DecisionType.CONFIRM_FRAUD: "RESOLUTION_IN_PROGRESS",
        DecisionType.FALSE_POSITIVE: "CLOSED_FALSE_POSITIVE",
        DecisionType.REQUEST_MORE_INFO: "AWAITING_HUMAN",
    }
    logger.info(
        "HITL decision received",
        investigation_id=investigation_id,
        decision=payload.decision,
        analyst=payload.analyst_id,
    )
    inv = await _build_investigation_review_payload(investigation_id)
    cust = inv["customer_id"]
    risk = float(inv.get("risk_score", 0.8))
    conf = float(inv.get("ai_reasoning", {}).get("confidence", 0.75))

    if payload.decision == DecisionType.CONFIRM_FRAUD:
        await fraud_memory_service.persist_hitl_outcome(
            entity_id=cust,
            entity_type="customer",
            risk_score=max(risk, 0.85),
            confidence=conf,
            pattern_type=FraudPattern.KNOWN_FRAUDSTER.value,
            metadata={
                "source": "hitl_decision",
                "investigation_id": investigation_id,
                "decision": payload.decision.value,
                "analyst_id": payload.analyst_id,
                "notes": payload.notes,
            },
        )
    elif payload.decision == DecisionType.FALSE_POSITIVE:
        await fraud_memory_service.persist_hitl_outcome(
            entity_id=cust,
            entity_type="customer",
            risk_score=min(risk, 0.25),
            confidence=min(conf, 0.5),
            pattern_type=FraudPattern.SYNTHETIC_IDENTITY.value,
            metadata={
                "source": "hitl_decision",
                "investigation_id": investigation_id,
                "decision": payload.decision.value,
                "analyst_id": payload.analyst_id,
                "notes": payload.notes,
            },
        )

    return {
        "investigation_id": investigation_id,
        "status": status_map[payload.decision],
        "decision": payload.decision.value,
    }


@router.post("/{investigation_id}/execute-actions")
async def execute_final_actions(
    investigation_id: str,
    actions: List[ActionRequest],
    _: None = RequireApiKey,
    __: None = RequireAnalyst,
):
    action_engine = ActionEngine()
    executed_actions: List[ActionResult] = []

    for action_request in actions:
        try:
            result = await action_engine.execute_action(action_request)
            executed_actions.append(result)
            logger.info("Action executed", action=action_request.action_type, investigation_id=investigation_id)
        except Exception as e:
            logger.error("Action failed", action=action_request.action_type, error=str(e))
            executed_actions.append(
                ActionResult(
                    success=False,
                    message=f"Action failed: {str(e)}",
                    action_id=f"failed_{action_request.action_type.value}",
                    case_id=investigation_id,
                    timestamp=datetime.utcnow(),
                )
            )

    successful_actions = [a for a in executed_actions if a.success]

    final_resolution = {
        "investigation_id": investigation_id,
        "resolution_timestamp": datetime.utcnow().isoformat(),
        "actions_executed": len(executed_actions),
        "successful_actions": len(successful_actions),
        "failed_actions": len(executed_actions) - len(successful_actions),
        "final_decision": "RESOLVED" if successful_actions else "PARTIALLY_RESOLVED",
        "resolution_summary": (
            f"Executed {len(executed_actions)} actions with {len(successful_actions)} successful"
        ),
    }

    if investigation_id in hitl_decisions:
        hitl_decisions[investigation_id]["final_resolution"] = final_resolution

    return {
        "success": True,
        "investigation_id": investigation_id,
        "actions_executed": executed_actions,
        "final_resolution": final_resolution,
    }


def _base_timeline_events(investigation_id: str) -> List[Dict[str, Any]]:
    ts = datetime.utcnow().isoformat()
    return [
        {
            "timestamp": ts,
            "event": "Alert Generated",
            "description": "Suspicious transaction triggered fraud alert",
            "details": {"alert_id": f"ALERT_{investigation_id}", "severity": "high"},
        },
        {
            "timestamp": ts,
            "event": "Triage Analysis",
            "description": "Automated triage completed",
            "details": {"decision": "ESCALATE_FOR_ANALYSIS", "risk_score": 0.85},
        },
        {
            "timestamp": ts,
            "event": "Agent Investigation",
            "description": "Parallel agents launched",
            "details": {"agents": ["transaction", "kyc", "sanctions"], "duration": "45 seconds"},
        },
        {
            "timestamp": ts,
            "event": "AI Reasoning",
            "description": "AI analysis completed",
            "details": {"risk_score": 0.85, "confidence": 0.89, "recommendation": "ESCALATE"},
        },
        {
            "timestamp": ts,
            "event": "Analyst Review",
            "description": "Human analyst review completed",
            "details": {"analyst_id": "ANALYST001", "decision": "ESCALATE"},
        },
    ]


@router.get("/{investigation_id}/timeline")
async def get_investigation_timeline(
    investigation_id: str,
    _: None = RequireApiKey,
    __: None = RequireAnalyst,
):
    timeline_events = _base_timeline_events(investigation_id)
    if investigation_id in hitl_decisions:
        decision = hitl_decisions[investigation_id]
        timeline_events.append(
            {
                "timestamp": decision["review_timestamp"],
                "event": "HITL Decision",
                "description": f"Analyst {decision['analyst_id']} made decision",
                "details": {
                    "decision": decision["decision"],
                    "notes": decision["analyst_notes"],
                    "final_decision": decision["final_decision"],
                },
            }
        )

    return {
        "success": True,
        "message": "Timeline retrieved successfully",
        "data": {
            "investigation_id": investigation_id,
            "timeline": timeline_events,
            "total_events": len(timeline_events),
            "investigation_duration": "2 minutes 15 seconds",
        },
    }


@router.get("/decisions")
async def get_all_hitl_decisions(_: None = RequireApiKey, __: None = RequireAnalyst):
    vals = list(hitl_decisions.values())
    return {
        "success": True,
        "message": "HITL decisions retrieved successfully",
        "data": {
            "decisions": vals,
            "total_count": len(hitl_decisions),
            "approved_count": len([d for d in vals if d.get("final_decision") == "CASE_APPROVED"]),
            "escalated_count": len([d for d in vals if d.get("final_decision") == "CASE_ESCALATED"]),
            "rejected_count": len([d for d in vals if d.get("final_decision") == "CASE_REJECTED"]),
        },
    }


@router.get("/analytics")
async def get_hitl_analytics(_: None = RequireApiKey, __: None = RequireAnalyst):
    decisions = list(hitl_decisions.values())
    if not decisions:
        return {
            "success": True,
            "message": "No HITL decisions available",
            "data": {
                "total_reviews": 0,
                "ai_alignment_rate": 0.0,
                "average_review_time": 0,
                "decision_distribution": {},
            },
        }

    total_reviews = len(decisions)
    aligned_with_ai = len([d for d in decisions if d.get("decision", "") in ("ESCALATE", "REJECT")])
    ai_alignment_rate = (aligned_with_ai / total_reviews) * 100 if total_reviews > 0 else 0

    decision_counts: Dict[str, int] = {}
    for d in decisions:
        fd = d.get("final_decision", "UNKNOWN")
        decision_counts[fd] = decision_counts.get(fd, 0) + 1

    return {
        "success": True,
        "message": "HITL analytics retrieved successfully",
        "data": {
            "total_reviews": total_reviews,
            "ai_alignment_rate": round(ai_alignment_rate, 2),
            "average_review_time": "3 minutes 45 seconds",
            "decision_distribution": decision_counts,
            "analyst_performance": {
                "most_active_analyst": "ANALYST001",
                "highest_accuracy": "ANALYST002",
                "fastest_reviewer": "ANALYST003",
            },
        },
    }
