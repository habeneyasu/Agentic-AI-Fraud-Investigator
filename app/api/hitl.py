"""
Human-in-the-Loop decision endpoint - Clean Architecture Implementation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.shared.models import HITLDecision, ActionRequest, ActionResult
from app.services.action_engine import ActionEngine

logger = get_logger(__name__)
router = APIRouter(prefix="/api/hitl", tags=["hitl"])

# In-memory storage for HITL decisions
hitl_decisions: Dict[str, Dict[str, Any]] = {}


class AnalystReviewRequest(BaseModel):
    """Request for analyst review."""
    investigation_id: str
    analyst_id: str
    analyst_notes: Optional[str] = None
    decision: Optional[str] = None  # APPROVE, REJECT, ESCALATE
    recommended_actions: Optional[List[str]] = None


class AnalystReviewResponse(BaseModel):
    """Response for analyst review."""
    success: bool
    investigation_id: str
    analyst_decision: str
    ai_recommendation: Dict[str, Any]
    reasoning: str


class InvestigationReviewResponse(BaseModel):
    """Response for investigation review."""
    success: bool
    message: str
    data: Dict[str, Any]


@router.get("/{investigation_id}/review", response_model=InvestigationReviewResponse)
async def get_investigation_for_review(
    investigation_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Get investigation details for analyst review."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if x_user_role != "Analyst":
        raise HTTPException(status_code=403, detail="Forbidden — Analyst role required")

    # Mock investigation data for demo
    agent_findings = {
        "transaction_analysis": [
            {
                "agent": "transaction",
                "findings": "High-value transaction velocity spike detected",
                "anomalies": [
                    {"pattern": "velocity_spike", "severity": "high", "count": 5},
                    {"pattern": "high_value_rush", "severity": "critical", "count": 2}
                ],
                "risk_score": 0.92
            }
        ],
        "kyc_analysis": [
            {
                "agent": "kyc",
                "findings": "Geographic location anomaly detected",
                "anomaly_type": "geo_location_mismatch",
                "location": "RU - Moscow",
                "risk_score": 0.78
            }
        ],
        "sanctions_analysis": [
            {
                "agent": "sanctions",
                "findings": "Potential sanctions list match",
                "sanction_type": "FINANCIAL",
                "entity_matched": "Global Trading Corp",
                "risk_score": 0.65
            }
        ]
    }
    
    # Use AI reasoning service
    ai_reasoning_service = AIReasoningService()
    ai_result = await ai_reasoning_service.analyze_investigation_findings(
        investigation_id=investigation_id,
        agent_findings=agent_findings,
        customer_context={"customer_id": "CUST003"}
    )
    
    # Complete investigation data
    investigation_data = {
        "investigation_id": investigation_id,
        "status": "ASSESSMENT",
        "customer_id": "CUST003",
        "risk_score": 0.85,
        "risk_level": "HIGH",
        "created_at": datetime.utcnow().isoformat(),
        "agent_findings": agent_findings,
        "ai_reasoning": {
            "overall_risk_score": ai_result.risk_score,
            "risk_level": ai_result.risk_level,
            "confidence": ai_result.confidence,
            "explanation": ai_result.explanation,
            "recommendation": "ESCALATE_FOR_ANALYSIS" if ai_result.risk_score > 0.7 else "AUTO_CLOSE",
            "factors": [f.factor for f in ai_result.factors],
            "scoring_mode": ai_result.scoring_mode
        }
    }

    return InvestigationReviewResponse(
        success=True,
        message="Investigation retrieved for review",
        data=investigation_data
    )


@router.post("/{investigation_id}/review", response_model=AnalystReviewResponse)
async def submit_analyst_review(
    investigation_id: str,
    request: AnalystReviewRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Submit analyst review and decision."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if x_user_role != "Analyst":
        raise HTTPException(status_code=403, detail="Forbidden — Analyst role required")

    # Get investigation data
    investigation_response = await get_investigation_for_review(investigation_id, x_api_key, x_user_role)
    investigation_data = investigation_response.data

    # Process analyst decision
    analyst_decision = {
        "investigation_id": investigation_id,
        "analyst_id": request.analyst_id,
        "decision": request.decision or "REVIEW",
        "analyst_notes": request.analyst_notes,
        "recommended_actions": request.recommended_actions or [],
        "review_timestamp": datetime.utcnow().isoformat(),
        "ai_recommendation": investigation_data["ai_reasoning"],
        "final_decision": None
    }

    # Compare with AI recommendation
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

    # Store decision
    hitl_decisions[investigation_id] = analyst_decision

    logger.info(f"Analyst review submitted for investigation {investigation_id}: {request.decision}")

    return AnalystReviewResponse(
        success=True,
        investigation_id=investigation_id,
        analyst_decision=request.decision or "REVIEW",
        ai_recommendation=investigation_data["ai_reasoning"],
        reasoning=reasoning
    )


@router.post("/{investigation_id}/decision")
async def submit_decision(
    investigation_id: str,
    payload: HITLDecision,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Submit HITL decision (original endpoint)."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if x_user_role != "Analyst":
        raise HTTPException(status_code=403, detail="Forbidden — Analyst role required")

    status_map = {
        "CONFIRM_FRAUD":      "RESOLUTION_IN_PROGRESS",
        "FALSE_POSITIVE":     "CLOSED_FALSE_POSITIVE",
        "REQUEST_MORE_INFO":  "AWAITING_HUMAN",
    }

    logger.info("HITL decision received",
                investigation_id=investigation_id,
                decision=payload.decision,
                analyst=payload.analyst_id)

    return {
        "investigation_id": investigation_id,
        "status": status_map[payload.decision],
        "decision": payload.decision,
    }


@router.post("/{investigation_id}/execute-actions")
async def execute_final_actions(
    investigation_id: str,
    actions: List[ActionRequest],
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Execute final resolution actions."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if x_user_role != "Analyst":
        raise HTTPException(status_code=403, detail="Forbidden — Analyst role required")

    action_engine = ActionEngine()
    executed_actions = []

    # Execute each action
    for action_request in actions:
        try:
            result = await action_engine.execute_action(action_request)
            executed_actions.append(result)
            logger.info(f"Executed action {action_request.action_type} for investigation {investigation_id}")
        except Exception as e:
            logger.error(f"Failed to execute action {action_request.action_type}: {e}")
            executed_actions.append(ActionResult(
                success=False,
                message=f"Action failed: {str(e)}",
                action_id=f"failed_{action_request.action_type.value}",
                case_id=investigation_id,
                timestamp=datetime.utcnow()
            ))

    # Determine final resolution
    successful_actions = [a for a in executed_actions if a.success]
    failed_actions = [a for a in executed_actions if not a.success]

    final_resolution = {
        "investigation_id": investigation_id,
        "resolution_timestamp": datetime.utcnow().isoformat(),
        "actions_executed": len(executed_actions),
        "successful_actions": len(successful_actions),
        "failed_actions": len(failed_actions),
        "final_decision": "RESOLVED" if len(successful_actions) > 0 else "PARTIALLY_RESOLVED",
        "resolution_summary": f"Executed {len(executed_actions)} actions with {len(successful_actions)} successful"
    }

    # Update investigation status
    if investigation_id in hitl_decisions:
        hitl_decisions[investigation_id]["final_resolution"] = final_resolution

    return {
        "success": True,
        "investigation_id": investigation_id,
        "actions_executed": executed_actions,
        "final_resolution": final_resolution
    }


@router.get("/{investigation_id}/timeline")
async def get_investigation_timeline(
    investigation_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Get complete investigation timeline."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if x_user_role != "Analyst":
        raise HTTPException(status_code=403, detail="Forbidden — Analyst role required")

    # Generate comprehensive timeline
    timeline_events = [
        {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "Alert Generated",
            "description": "Suspicious transaction triggered fraud alert",
            "details": {"alert_id": f"ALERT_{investigation_id}", "severity": "high"}
        },
        {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "Triage Analysis",
            "description": "Automated triage completed",
            "details": {"decision": "ESCALATE_FOR_ANALYSIS", "risk_score": 0.85}
        },
        {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "Agent Investigation",
            "description": "Parallel agents launched",
            "details": {"agents": ["transaction", "kyc", "sanctions"], "duration": "45 seconds"}
        },
        {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "AI Reasoning",
            "description": "AI analysis completed",
            "details": {"risk_score": 0.85, "confidence": 0.89, "recommendation": "ESCALATE"}
        },
        {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "Analyst Review",
            "description": "Human analyst review completed",
            "details": {"analyst_id": "ANALYST001", "decision": "ESCALATE"}
        }
    ]

    # Add HITL decision if available
    if investigation_id in hitl_decisions:
        decision = hitl_decisions[investigation_id]
        timeline_events.append({
            "timestamp": decision["review_timestamp"],
            "event": "HITL Decision",
            "description": f"Analyst {decision['analyst_id']} made decision",
            "details": {
                "decision": decision["decision"],
                "notes": decision["analyst_notes"],
                "final_decision": decision["final_decision"]
            }
        })

    return {
        "success": True,
        "message": "Timeline retrieved successfully",
        "data": {
            "investigation_id": investigation_id,
            "timeline": timeline_events,
            "total_events": len(timeline_events),
            "investigation_duration": "2 minutes 15 seconds"
        }
    }


@router.get("/decisions")
async def get_all_hitl_decisions(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Get all HITL decisions."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if x_user_role != "Analyst":
        raise HTTPException(status_code=403, detail="Forbidden — Analyst role required")

    return {
        "success": True,
        "message": "HITL decisions retrieved successfully",
        "data": {
            "decisions": list(hitl_decisions.values()),
            "total_count": len(hitl_decisions),
            "approved_count": len([d for d in hitl_decisions.values() if d.get("final_decision") == "CASE_APPROVED"]),
            "escalated_count": len([d for d in hitl_decisions.values() if d.get("final_decision") == "CASE_ESCALATED"]),
            "rejected_count": len([d for d in hitl_decisions.values() if d.get("final_decision") == "CASE_REJECTED"])
        }
    }


@router.get("/analytics")
async def get_hitl_analytics(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Get HITL analytics and metrics."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if x_user_role != "Analyst":
        raise HTTPException(status_code=403, detail="Forbidden — Analyst role required")

    decisions = list(hitl_decisions.values())

    if not decisions:
        return {
            "success": True,
            "message": "No HITL decisions available",
            "data": {
                "total_reviews": 0,
                "ai_alignment_rate": 0.0,
                "average_review_time": 0,
                "decision_distribution": {}
            }
        }

    # Calculate analytics
    total_reviews = len(decisions)
    aligned_with_ai = len([d for d in decisions if d.get("decision", "") in ["ESCALATE", "REJECT"]])
    ai_alignment_rate = (aligned_with_ai / total_reviews) * 100 if total_reviews > 0 else 0

    # Decision distribution
    decision_counts = {}
    for decision in decisions:
        final_decision = decision.get("final_decision", "UNKNOWN")
        decision_counts[final_decision] = decision_counts.get(final_decision, 0) + 1

    return {
        "success": True,
        "message": "HITL analytics retrieved successfully",
        "data": {
            "total_reviews": total_reviews,
            "ai_alignment_rate": round(ai_alignment_rate, 2),
            "average_review_time": "3 minutes 45 seconds",  # Mock data
            "decision_distribution": decision_counts,
            "analyst_performance": {
                "most_active_analyst": "ANALYST001",
                "highest_accuracy": "ANALYST002",
                "fastest_reviewer": "ANALYST003"
            }
        }
    }
