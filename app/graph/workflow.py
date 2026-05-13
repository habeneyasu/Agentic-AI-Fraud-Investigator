"""LangGraph workflow — sequential fraud pipeline with conditional routing (LangGraph 0.1.x)."""

from __future__ import annotations

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


async def _node_start(state: dict) -> dict:
    """Carry full dict between LangGraph 0.1.x nodes."""
    s = dict(state)
    cid = s.get("case_id") or s.get("correlation_id") or "unknown"
    logger.info("graph_node", node="start", case_id=cid)
    s["graph_started_at"] = datetime.now(timezone.utc).isoformat()
    return s


async def _node_transaction(state: dict) -> dict:
    s = dict(state)
    txs = s.get("transaction_data") or []
    hist = s.get("customer_history") or {}
    cust_tx = hist.get("transactions") if isinstance(hist, dict) else []
    if not isinstance(cust_tx, list):
        cust_tx = []
    anomalies: list = []
    for t in txs:
        r = await _tx.analyze_transaction(t, cust_tx)
        body = _unwrap_service_response(r)
        anomalies.extend(body.get("anomalies") or [])
    s["anomalies"] = anomalies
    return s


async def _node_kyc(state: dict) -> dict:
    s = dict(state)
    events = s.get("kyc_data") or []
    kyc_an: list = []
    for ev in events:
        r = await _kyc.analyze_kyc_event(ev)
        body = _unwrap_service_response(r)
        kyc_an.extend(body.get("anomalies") or [])
    s["kyc_anomalies"] = kyc_an
    return s


async def _node_sanctions(state: dict) -> dict:
    s = dict(state)
    entities = s.get("entities") or []
    hits: list = []
    for ent in entities:
        r = await _san.analyze_sanctions_risk(ent)
        body = _unwrap_service_response(r)
        if float(body.get("risk_score") or 0) > 0.5:
            hits.append(body)
    s["sanctions_hits"] = hits
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
    return s


async def _node_investigation(state: dict) -> dict:
    s = dict(state)
    s["investigation_branch"] = True
    s["investigator_id"] = "graph_runner"
    return s


async def _node_escalation(state: dict) -> dict:
    s = dict(state)
    s["escalated"] = True
    s["escalation_reason"] = "graph_risk_threshold"
    s["escalated_to"] = "senior_queue"
    return s


async def _node_resolution(state: dict) -> dict:
    s = dict(state)
    s["resolved"] = True
    s["resolution_notes"] = "LangGraph pipeline completed"
    s["closed_at"] = datetime.now(timezone.utc).isoformat()
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


def _compile_fraud_graph():
    g: StateGraph = StateGraph(dict)
    g.add_node(NodeType.START.value, _node_start)
    g.add_node(NodeType.TRANSACTION_ANALYSIS.value, _node_transaction)
    g.add_node(NodeType.KYC_ANALYSIS.value, _node_kyc)
    g.add_node(NodeType.SANCTIONS_CHECK.value, _node_sanctions)
    g.add_node(NodeType.RISK_SCORING.value, _node_risk)
    g.add_node(NodeType.DECISION.value, _node_decision)
    g.add_node(NodeType.INVESTIGATION.value, _node_investigation)
    g.add_node(NodeType.ESCALATION.value, _node_escalation)
    g.add_node(NodeType.RESOLUTION.value, _node_resolution)

    g.add_edge(NodeType.START.value, NodeType.TRANSACTION_ANALYSIS.value)
    g.add_edge(NodeType.TRANSACTION_ANALYSIS.value, NodeType.KYC_ANALYSIS.value)
    g.add_edge(NodeType.KYC_ANALYSIS.value, NodeType.SANCTIONS_CHECK.value)
    g.add_edge(NodeType.SANCTIONS_CHECK.value, NodeType.RISK_SCORING.value)
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
