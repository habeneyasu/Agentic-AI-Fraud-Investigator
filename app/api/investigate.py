"""Investigation API (``/v1``): ``customer-langgraph-deep``, ``hitl-recommendation``, ``health``.
Successful LLM HITL briefing persists a row via ``/v1/fraud-memory`` (see ``persist_fraud_memory`` on the request body).
Triage: ``POST /v1/triage/assess`` in ``app/api/triage.py``."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import RequireApiKey
from app.api.fraud_memory import fraud_memory_service
from app.core.logging import get_logger
from app.data.data_loader import DataLoader
from app.graph.workflow import execute_fraud_workflow
from app.llm.orchestration import get_hitl_recommendation, synthesize_investigation
from app.models.alert import Alert, AlertFilter
from app.repositories.alert_repository import AlertRepository
from app.shared.enums import FraudPattern, TriagePriority
from app.shared.models import InvestigationWorkflowState

logger = get_logger(__name__)
router = APIRouter(tags=["investigation"])

_data_loader = DataLoader()
_alert_repository = AlertRepository()


class FullInvestigationApiRequest(BaseModel):
    transaction_id: str
    customer_id: str
    amount: float
    currency: str = "USD"
    destination_country: str
    device_id: str = ""
    ip_address: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    risk_indicators: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalystBriefingApiRequest(BaseModel):
    investigation_id: str
    customer_id: str
    amount: float
    destination_country: str
    agent_results: dict[str, Any]
    risk_result: dict[str, Any]


class CustomerLangGraphDeepRequest(BaseModel):
    customer_id: str
    alert_id: str | None = None
    include_hitl_recommendation: bool = True
    persist_fraud_memory: bool = True


def _full_investigation_request_from_alert(alert: Alert) -> FullInvestigationApiRequest:
    md = dict(alert.metadata or {})
    dest = (alert.recipient_country or "").strip() or str(md.get("sanctioned_country") or "UNKNOWN")
    tx_id = (alert.transaction_id or "").strip() or alert.alert_id
    return FullInvestigationApiRequest(
        transaction_id=tx_id,
        customer_id=alert.customer_id,
        amount=float(alert.amount or 0.0),
        currency=alert.currency or "USD",
        destination_country=dest,
        device_id=str(md.get("device_id", "") or ""),
        ip_address=str(md.get("ip_address", "") or ""),
        timestamp=alert.timestamp or datetime.utcnow().isoformat(),
        risk_indicators=list(md.get("risk_indicators") or []) if isinstance(md.get("risk_indicators"), list) else [],
        metadata=md,
    )


def _agent_payloads_from_full(request: FullInvestigationApiRequest) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    transaction_data = {
        "transaction_id": request.transaction_id,
        "customer_id": request.customer_id,
        "amount": request.amount,
        "currency": request.currency,
        "timestamp": request.timestamp,
        "merchant_id": "MERCHANT_UNKNOWN",
        "location": request.destination_country,
        "device_id": request.device_id,
        "ip_address": request.ip_address,
        "metadata": request.metadata,
    }
    kyc_event_data = {
        "customer_id": request.customer_id,
        "event_type": "transaction_attempt",
        "timestamp": request.timestamp,
        "ip_address": request.ip_address,
        "device_info": {"device_id": request.device_id, **request.metadata.get("device_info", {})},
        "geo_location": {
            "country": request.destination_country,
            "ip_address": request.ip_address,
            "city": "Unknown",
            "latitude": 0.0,
            "longitude": 0.0,
            "isp": "Unknown",
        },
    }
    entity_data = {
        "name": request.metadata.get("recipient_name", "Unknown Recipient"),
        "country_code": request.destination_country,
        "entity_type": "financial_institution",
        "description": f"Transfer destination in {request.destination_country}",
    }
    return transaction_data, kyc_event_data, entity_data


_SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _severity_rank(alert: Alert) -> int:
    return _SEVERITY_ORDER.get((alert.severity or "").strip().lower(), 0)


async def _pick_alert_for_customer(customer_id: str, explicit_alert_id: str | None) -> Alert:
    cid = customer_id.strip()
    if explicit_alert_id and explicit_alert_id.strip():
        aid = explicit_alert_id.strip()
        alert = await _alert_repository.get_alert_by_id(aid)
        if alert is None:
            raise HTTPException(status_code=404, detail=f"Alert `{aid}` not found.")
        if (alert.customer_id or "").strip().casefold() != cid.casefold():
            raise HTTPException(status_code=400, detail="alert_id does not belong to this customer_id")
        return alert
    lst = await _alert_repository.get_alerts(AlertFilter(customer_id=cid))
    if not lst.alerts:
        raise HTTPException(
            status_code=404,
            detail=f"No alerts for customer `{cid}`. Run POST /v1/triage/assess after alerts exist in the merged store.",
        )
    ranked = sorted(
        lst.alerts,
        key=lambda a: (_severity_rank(a), float(a.amount or 0.0), a.timestamp or ""),
        reverse=True,
    )
    return ranked[0]


def _agent_results_from_graph_state(final: InvestigationWorkflowState) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    hits = list(final.sanctions_hits or [])
    max_san = max((float(h.get("risk_score") or 0) for h in hits), default=0.0)
    rs = float(final.risk_score or 0.0)
    tx = {
        "risk_score": rs,
        "anomalies": list(final.anomalies or []),
        "source": "langgraph_transaction_analysis",
    }
    kyc = {
        "risk_score": min(1.0, rs * 0.95 + 0.02),
        "anomalies": list(final.kyc_anomalies or []),
        "source": "langgraph_kyc_analysis",
    }
    san = {
        "risk_score": max(max_san, min(1.0, rs * 0.9)),
        "hits": hits,
        "anomalies": hits,
        "source": "langgraph_sanctions",
    }
    return tx, kyc, san


def _hitl_summary_fields(inv_id: str, request: FullInvestigationApiRequest) -> dict[str, Any]:
    return {
        "investigation_id": inv_id,
        "customer_id": request.customer_id,
        "amount": request.amount,
        "destination_country": request.destination_country,
    }


async def _langgraph_final_state(
    request: FullInvestigationApiRequest,
    investigation_id: str | None = None,
) -> tuple[str, InvestigationWorkflowState, dict[str, Any]]:
    investigation_id = investigation_id or f"inv_{uuid.uuid4().hex[:12]}"
    logger.info(
        "Starting LangGraph investigation",
        investigation_id=investigation_id,
        customer_id=request.customer_id,
    )

    customer_context = _data_loader.get_customer_context(request.customer_id) or {}
    transaction_data, kyc_event_data, entity_data = _agent_payloads_from_full(request)

    initial = InvestigationWorkflowState.create_initial(
        case_id=investigation_id,
        case_type="langgraph_investigation",
        title=f"Investigation {investigation_id}",
        description=f"Customer {request.customer_id} transaction {request.transaction_id}",
        priority=TriagePriority.HIGH,
        correlation_id=investigation_id,
    ).model_copy(
        update={
            "investigation_id": investigation_id,
            "transaction_data": [transaction_data],
            "kyc_data": [kyc_event_data],
            "entities": [entity_data],
            "customer_history": customer_context,
        }
    )

    final = await execute_fraud_workflow(initial)
    return investigation_id, final, customer_context


async def _run_langgraph_with_deep_synthesis(
    request: FullInvestigationApiRequest,
    *,
    investigation_id: str | None = None,
    include_hitl_recommendation: bool = True,
    persist_fraud_memory: bool = True,
) -> dict[str, Any]:
    inv_id, final, customer_context = await _langgraph_final_state(request, investigation_id)
    graph_dump = final.model_dump(mode="json")
    tx_r, kyc_r, san_r = _agent_results_from_graph_state(final)
    ai_synthesis = await synthesize_investigation(
        transaction_result=tx_r,
        kyc_result=kyc_r,
        sanctions_result=san_r,
        customer_context=customer_context,
    )
    graph_risk = float(final.risk_score or 0.0)
    final_score = float(ai_synthesis.get("final_risk_score", graph_risk))

    risk_result = {
        "final_risk_score": final_score,
        "risk_tier": str(ai_synthesis.get("risk_tier") or "MEDIUM"),
        "confidence": float(ai_synthesis.get("confidence", 0.75)),
        "rule_based_score": graph_risk,
        "ai_context_score": final_score,
        "executive_summary": ai_synthesis.get("executive_summary", ""),
        "evidence_chain": ai_synthesis.get("evidence_chain", []),
        "reasoning_steps": ai_synthesis.get("reasoning_steps", []),
        "recommendation": ai_synthesis.get("recommendation", "REVIEW"),
        "requires_human_review": bool(ai_synthesis.get("requires_human_review", final_score >= 0.6)),
        "langgraph_snapshot": {
            "risk_score": graph_risk,
            "workflow_status": str(final.status),
        },
    }
    agent_results = {"transaction": tx_r, "kyc": kyc_r, "sanctions": san_r}
    party = _hitl_summary_fields(inv_id, request)
    hitl_ready = {**party, "agent_results": agent_results, "risk_result": risk_result}
    hitl_rec: dict[str, Any] | None = None
    if include_hitl_recommendation:
        try:
            hitl_rec = await get_hitl_recommendation(party, agent_results, risk_result)
        except Exception as e:
            logger.warning("hitl_recommendation_failed", error=str(e))
            hitl_rec = None

    if persist_fraud_memory and hitl_rec is not None:
        await fraud_memory_service.persist_hitl_outcome(
            entity_id=request.customer_id,
            entity_type="customer",
            risk_score=float(risk_result["final_risk_score"]),
            confidence=float(risk_result["confidence"]),
            pattern_type=FraudPattern.VELOCITY_ANOMALY.value,
            metadata={
                "source": "investigation_llm_hitl",
                "investigation_id": inv_id,
                "transaction_id": request.transaction_id,
            },
        )

    return {
        "success": True,
        "engine": "langgraph_deep_synthesis",
        "data": {
            "investigation_id": inv_id,
            "customer_id": request.customer_id,
            "transaction_id": request.transaction_id,
            "status": "COMPLETED",
            "langgraph_state": graph_dump,
            "llm_investigation_synthesis": ai_synthesis,
            "agent_results": agent_results,
            "risk_result": risk_result,
            "hitl_ready": hitl_ready,
            "hitl_recommendation": hitl_rec,
            "completed_timestamp": datetime.utcnow().isoformat(),
        },
    }


@router.post("/investigation/customer-langgraph-deep", tags=["investigation"])
async def customer_langgraph_deep_investigation(
    body: CustomerLangGraphDeepRequest,
    _: None = RequireApiKey,
):
    alert = await _pick_alert_for_customer(body.customer_id, body.alert_id)
    req = _full_investigation_request_from_alert(alert)
    out = await _run_langgraph_with_deep_synthesis(
        req,
        include_hitl_recommendation=body.include_hitl_recommendation,
        persist_fraud_memory=body.persist_fraud_memory,
    )
    return {"alert_id": alert.alert_id, "phase": "customer_langgraph_deep", **out}


@router.post("/investigation/hitl-recommendation", tags=["investigation"])
async def get_hitl_recommendation_endpoint(
    request: AnalystBriefingApiRequest,
    _: None = RequireApiKey,
):
    summary = {
        "investigation_id": request.investigation_id,
        "customer_id": request.customer_id,
        "amount": request.amount,
        "destination_country": request.destination_country,
    }
    result = await get_hitl_recommendation(summary, request.agent_results, request.risk_result)
    await fraud_memory_service.persist_hitl_outcome(
        entity_id=request.customer_id,
        entity_type="customer",
        risk_score=float(request.risk_result.get("final_risk_score", 0.65)),
        confidence=float(request.risk_result.get("confidence", 0.7)),
        pattern_type=FraudPattern.VELOCITY_ANOMALY.value,
        metadata={
            "source": "hitl_recommendation_endpoint",
            "investigation_id": request.investigation_id,
        },
    )
    return {"success": True, "data": result}


@router.get("/investigation/health", tags=["investigation"])
async def investigation_health():
    return {"status": "ok", "endpoint": "investigation"}
