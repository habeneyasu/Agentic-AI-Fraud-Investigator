"""LangGraph workflow — parallel fraud pipeline with conditional routing (LangGraph 0.1.x).

Fix 1: Transaction, KYC, and Sanctions agents now run in parallel via asyncio.gather
        inside a single combined node (_node_agents_parallel), replacing the three
        sequential edges START→TX→KYC→SANCTIONS.
Fix 4: Investigation and Escalation nodes now perform meaningful work — recording
        assigned investigator, pending actions, escalation metadata, and status updates.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict

from langgraph.graph import StateGraph

from app.core.logging import get_logger
from app.graph.scoring import calculate_risk_score
from app.services.kyc_service import KYCService
from app.services.sanctions_service import SanctionsService
from app.services.transaction_service import TransactionService
from app.shared.enums import InvestigationStatus, NodeType, ScoringMode
from app.shared.models import InvestigationWorkflowState

logger = get_logger(__name__)

_tx = TransactionService()
_kyc = KYCService()
_san = SanctionsService()


def _unwrap_service_response(resp: Any) -> dict:
    if not isinstance(resp, dict):
        return {}
    if resp.get("success") and isinstance(resp.get("data"), dict):
        return resp["data"]
    return resp


async def _run_transaction_agent(state: dict) -> list:
    """Run transaction agent; returns anomalies list."""
    txs = state.get("transaction_data") or []
    hist = state.get("customer_history") or {}
    cust_tx = hist.get("transactions") if isinstance(hist, dict) else []
    if not isinstance(cust_tx, list):
        cust_tx = []
    anomalies: list = []
    for t in txs:
        r = await _tx.analyze_transaction(t, cust_tx)
        body = _unwrap_service_response(r)
        anomalies.extend(body.get("anomalies") or [])
    logger.info("agent_complete", agent="transaction", anomaly_count=len(anomalies))
    return anomalies


async def _run_kyc_agent(state: dict) -> list:
    """Run KYC/device agent; returns kyc_anomalies list."""
    events = state.get("kyc_data") or []
    kyc_an: list = []
    for ev in events:
        r = await _kyc.analyze_kyc_event(ev)
        body = _unwrap_service_response(r)
        kyc_an.extend(body.get("anomalies") or [])
    logger.info("agent_complete", agent="kyc", anomaly_count=len(kyc_an))
    return kyc_an


async def _run_sanctions_agent(state: dict) -> list:
    """Run sanctions agent; returns sanctions_hits list (risk_score > 0.5 only)."""
    entities = state.get("entities") or []
    hits: list = []
    for ent in entities:
        r = await _san.analyze_sanctions_risk(ent)
        body = _unwrap_service_response(r)
        if float(body.get("risk_score") or 0) > 0.5:
            hits.append(body)
    logger.info("agent_complete", agent="sanctions", hit_count=len(hits))
    return hits


async def _node_start(state: dict) -> dict:
    s = dict(state)
    cid = s.get("case_id") or s.get("correlation_id") or "unknown"
    logger.info("graph_node", node="start", case_id=cid)
    s["graph_started_at"] = datetime.now(timezone.utc).isoformat()
    return s


# Fix 1: single node that fans out to all three agents concurrently then merges results.
async def _node_agents_parallel(state: dict) -> dict:
    """Run Transaction, KYC, and Sanctions agents in parallel; merge into state."""
    s = dict(state)
    logger.info("graph_node", node="agents_parallel", case_id=s.get("case_id", "unknown"))

    anomalies, kyc_anomalies, sanctions_hits = await asyncio.gather(
        _run_transaction_agent(s),
        _run_kyc_agent(s),
        _run_sanctions_agent(s),
    )

    s["anomalies"] = anomalies
    s["kyc_anomalies"] = kyc_anomalies
    s["sanctions_hits"] = sanctions_hits
    s["agents_completed_at"] = datetime.now(timezone.utc).isoformat()
    return s


async def _node_risk(state: dict) -> dict:
    s = dict(state)
    combined = {
        "transaction_anomalies": s.get("anomalies") or [],
        "kyc_anomalies": s.get("kyc_anomalies") or [],
        "sanctions_hits": s.get("sanctions_hits") or [],
        "case_metadata": {**(s.get("metadata") or {}), "source": "langgraph"},
    }
    res = await calculate_risk_score(combined, mode=ScoringMode.RULES_ONLY)
    s["risk_score"] = float(res.risk_score or 0.0)
    s["risk_level"] = res.risk_level
    s["confidence"] = float(res.confidence or 0.0)
    logger.info(
        "graph_node",
        node="risk_scoring",
        risk_score=s["risk_score"],
        risk_level=s["risk_level"],
    )
    return s


async def _node_decision(state: dict) -> dict:
    s = dict(state)
    rs = float(s.get("risk_score") or 0.0)
    if rs >= 0.8:
        dec = "ESCALATE"
    elif rs >= 0.6:
        dec = "INVESTIGATE"
    else:
        dec = "MONITOR"
    s["workflow_decision"] = dec
    logger.info("graph_node", node="decision", decision=dec, risk_score=rs)
    return s


# Fix 4a: Investigation node — records assignment and pending actions instead of a no-op.
async def _node_investigation(state: dict) -> dict:
    s = dict(state)
    case_id = s.get("case_id", "unknown")
    risk_score = float(s.get("risk_score") or 0.0)

    s["investigation_branch"] = True
    s["investigator_id"] = "graph_runner"
    s["investigation_started_at"] = datetime.now(timezone.utc).isoformat()

    # Determine pending actions based on what the agents surfaced.
    pending: list[str] = []
    if s.get("sanctions_hits"):
        pending.append("compliance_review_required")
    if s.get("kyc_anomalies"):
        pending.append("enhanced_kyc_verification")
    if s.get("anomalies"):
        pending.append("transaction_pattern_review")
    if risk_score >= 0.7:
        pending.append("senior_analyst_assignment")

    s["pending_actions"] = pending
    s["risk_factors"] = (
        [a.get("type", "unknown") for a in (s.get("anomalies") or [])]
        + [a.get("anomaly_type", "unknown") for a in (s.get("kyc_anomalies") or [])]
        + ["sanctions_hit" for _ in (s.get("sanctions_hits") or [])]
    )

    logger.info(
        "graph_node",
        node="investigation",
        case_id=case_id,
        pending_actions=pending,
    )
    return s


# Fix 4b: Escalation node — records escalation reason, target queue, and urgency metadata.
async def _node_escalation(state: dict) -> dict:
    s = dict(state)
    case_id = s.get("case_id", "unknown")
    risk_score = float(s.get("risk_score") or 0.0)

    s["escalated"] = True
    s["escalated_at"] = datetime.now(timezone.utc).isoformat()

    # Derive the most specific escalation reason from agent outputs.
    if s.get("sanctions_hits"):
        reason = "sanctions_hit_critical_threshold"
        target = "compliance_and_legal_queue"
    elif risk_score >= 0.9:
        reason = "critical_risk_score"
        target = "senior_fraud_analyst_queue"
    else:
        reason = "high_risk_score_threshold"
        target = "fraud_investigation_queue"

    s["escalation_reason"] = reason
    s["escalated_to"] = target
    s["escalation_metadata"] = {
        "risk_score": risk_score,
        "sanctions_hits": len(s.get("sanctions_hits") or []),
        "transaction_anomalies": len(s.get("anomalies") or []),
        "kyc_anomalies": len(s.get("kyc_anomalies") or []),
        "escalated_by": "langgraph_workflow",
        "requires_human_review": True,
    }

    logger.info(
        "graph_node",
        node="escalation",
        case_id=case_id,
        reason=reason,
        target=target,
    )
    return s


async def _node_resolution(state: dict) -> dict:
    s = dict(state)
    risk_score = float(s.get("risk_score") or 0.0)

    s["resolved"] = True
    s["closed_at"] = datetime.now(timezone.utc).isoformat()

    if s.get("escalated"):
        s["resolution_notes"] = (
            f"Case escalated to {s.get('escalated_to')} — "
            f"risk {risk_score:.2f}, reason: {s.get('escalation_reason')}. "
            "Awaiting human review."
        )
    elif s.get("investigation_branch"):
        s["resolution_notes"] = (
            f"Investigation completed — risk {risk_score:.2f}. "
            f"Pending actions: {', '.join(s.get('pending_actions') or []) or 'none'}."
        )
    else:
        s["resolution_notes"] = (
            f"Case auto-resolved — risk {risk_score:.2f}, "
            f"level {s.get('risk_level', 'UNKNOWN')}. No escalation required."
        )

    logger.info(
        "graph_node",
        node="resolution",
        resolved=True,
        escalated=s.get("escalated", False),
    )
    return s


def _route_after_decision(state: dict) -> str:
    return (
        NodeType.INVESTIGATION.value
        if float(state.get("risk_score") or 0) > 0.7
        else NodeType.RESOLUTION.value
    )


def _route_after_investigation(state: dict) -> str:
    return (
        NodeType.ESCALATION.value
        if float(state.get("risk_score") or 0) > 0.8
        else NodeType.RESOLUTION.value
    )


# Fix 1 (continued): graph wiring — START → AGENTS_PARALLEL replaces three sequential edges.
def _compile_fraud_graph():
    g: StateGraph = StateGraph(dict)
    g.add_node(NodeType.START.value, _node_start)
    g.add_node("agents_parallel", _node_agents_parallel)
    g.add_node(NodeType.RISK_SCORING.value, _node_risk)
    g.add_node(NodeType.DECISION.value, _node_decision)
    g.add_node(NodeType.INVESTIGATION.value, _node_investigation)
    g.add_node(NodeType.ESCALATION.value, _node_escalation)
    g.add_node(NodeType.RESOLUTION.value, _node_resolution)

    g.add_edge(NodeType.START.value, "agents_parallel")
    g.add_edge("agents_parallel", NodeType.RISK_SCORING.value)
    g.add_edge(NodeType.RISK_SCORING.value, NodeType.DECISION.value)

    g.add_conditional_edges(
        NodeType.DECISION.value,
        _route_after_decision,
        {
            NodeType.INVESTIGATION.value: NodeType.INVESTIGATION.value,
            NodeType.RESOLUTION.value: NodeType.RESOLUTION.value,
        },
    )
    g.add_conditional_edges(
        NodeType.INVESTIGATION.value,
        _route_after_investigation,
        {
            NodeType.ESCALATION.value: NodeType.ESCALATION.value,
            NodeType.RESOLUTION.value: NodeType.RESOLUTION.value,
        },
    )
    g.add_edge(NodeType.ESCALATION.value, NodeType.RESOLUTION.value)

    g.set_entry_point(NodeType.START.value)
    g.set_finish_point(NodeType.RESOLUTION.value)
    return g.compile()


_compiled_graph = _compile_fraud_graph()


async def execute_fraud_workflow(initial_state: InvestigationWorkflowState) -> InvestigationWorkflowState:
    """Run the LangGraph fraud pipeline and merge outputs onto the input state."""
    base: Dict[str, Any] = initial_state.model_dump(mode="json")
    base.setdefault("anomalies", [])
    base.setdefault("kyc_anomalies", [])
    base.setdefault("sanctions_hits", [])
    base.setdefault("transaction_data", base.get("transaction_data") or [])
    base.setdefault("kyc_data", base.get("kyc_data") or [])
    base.setdefault("entities", base.get("entities") or [])
    base.setdefault("metadata", base.get("metadata") or {})

    try:
        out = await _compiled_graph.ainvoke(base)
        merged = {**initial_state.model_dump(), **out}
        parsed = InvestigationWorkflowState.model_validate(merged)
        parsed.status = InvestigationStatus.COMPLETED
        return parsed
    except Exception as e:
        logger.error("graph_execute_failed", error=str(e))
        return initial_state.model_copy(
            update={
                "status": InvestigationStatus.CLOSED,
                "error_message": str(e),
            }
        )


class LangGraphWorkflow:
    """Thin wrapper exposing the compiled graph (back-compat for imports/tests)."""

    def __init__(self) -> None:
        self.compiled_graph = _compiled_graph

    async def execute_workflow(self, initial_state: InvestigationWorkflowState) -> InvestigationWorkflowState:
        return await execute_fraud_workflow(initial_state)


fraud_workflow = LangGraphWorkflow()


def get_fraud_workflow() -> LangGraphWorkflow:
    return fraud_workflow
