"""Investigation endpoints: triage, full parallel-agent run, HITL recommendation."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import RequireApiKey
from app.core.logging import get_logger
from app.data.data_loader import DataLoader
from app.services.transaction_service import TransactionService
from app.services.kyc_service import KYCService
from app.services.sanctions_service import SanctionsService
from app.services.ai_reasoning_service import InvestigationReasoningService
from app.llm.orchestration import synthesize_investigation, triage_alert, get_hitl_recommendation

logger = get_logger(__name__)
router = APIRouter(tags=["investigate"])

_data_loader = DataLoader()
_tx_service = TransactionService()
_kyc_service = KYCService()
_san_service = SanctionsService()
_ai_service = InvestigationReasoningService()


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


class OrchestratedTriageApiRequest(BaseModel):
    alert_id: str
    customer_id: str
    amount: float
    currency: str = "USD"
    destination_country: str
    device_id: str = ""
    risk_indicators: list[str] = Field(default_factory=list)


class AnalystBriefingApiRequest(BaseModel):
    investigation_id: str
    customer_id: str
    amount: float
    destination_country: str
    agent_results: dict[str, Any]
    risk_result: dict[str, Any]


@router.post("/investigate/triage")
async def run_triage(request: OrchestratedTriageApiRequest, _: None = RequireApiKey):
    customer_context = _data_loader.get_customer_context(request.customer_id) or {}

    alert_data = {
        "alert_id": request.alert_id,
        "customer_id": request.customer_id,
        "amount": request.amount,
        "currency": request.currency,
        "destination_country": request.destination_country,
        "device_id": request.device_id,
        "risk_indicators": request.risk_indicators,
    }

    result = await triage_alert(alert_data, customer_context)
    return {"success": True, "data": result}


@router.post("/investigate/full")
async def run_full_investigation(request: FullInvestigationApiRequest, _: None = RequireApiKey):
    investigation_id = f"inv_{uuid.uuid4().hex[:12]}"
    logger.info(f"Starting full investigation {investigation_id} for {request.customer_id}")

    # Load customer context
    customer_context = _data_loader.get_customer_context(request.customer_id) or {}
    customer_txns    = customer_context.get("transactions", [])

    # Build agent inputs
    transaction_data = {
        "transaction_id": request.transaction_id,
        "customer_id":    request.customer_id,
        "amount":         request.amount,
        "currency":       request.currency,
        "timestamp":      request.timestamp,
        "merchant_id":    "MERCHANT_UNKNOWN",
        "location":       request.destination_country,
        "device_id":      request.device_id,
        "ip_address":     request.ip_address,
        "metadata":       request.metadata,
    }

    kyc_event_data = {
        "customer_id":  request.customer_id,
        "event_type":   "transaction_attempt",
        "timestamp":    request.timestamp,
        "ip_address":   request.ip_address,
        "device_info":  {"device_id": request.device_id, **request.metadata.get("device_info", {})},
        "geo_location": {"country": request.destination_country, "ip_address": request.ip_address,
                         "city": "Unknown", "latitude": 0.0, "longitude": 0.0, "isp": "Unknown"},
    }

    entity_data = {
        "name":         request.metadata.get("recipient_name", "Unknown Recipient"),
        "country_code": request.destination_country,
        "entity_type":  "financial_institution",
        "description":  f"Transfer destination in {request.destination_country}",
    }

    # ── Parallel agent execution ──────────────────────────────────────────────
    tx_task  = _tx_service.analyze_transaction(transaction_data, customer_txns)
    kyc_task = _kyc_service.analyze_kyc_event(kyc_event_data)
    san_task = _san_service.analyze_sanctions_risk(entity_data)

    tx_resp, kyc_resp, san_resp = await asyncio.gather(
        tx_task, kyc_task, san_task, return_exceptions=True
    )

    def _safe(resp: Any, label: str) -> dict:
        if isinstance(resp, Exception):
            logger.error(f"{label} agent failed: {resp}")
            return {"error": str(resp), "risk_score": 0.5}
        return resp.get("data", resp) if isinstance(resp, dict) and "data" in resp else resp

    tx_result  = _safe(tx_resp,  "Transaction")
    kyc_result = _safe(kyc_resp, "KYC")
    san_result = _safe(san_resp, "Sanctions")

    ai_synthesis = await synthesize_investigation(
        transaction_result=tx_result,
        kyc_result=kyc_result,
        sanctions_result=san_result,
        customer_context=customer_context,
    )

    agent_findings = {
        "transaction_analysis": [tx_result] if tx_result else [],
        "kyc_analysis":         [kyc_result] if kyc_result else [],
        "sanctions_analysis":   [san_result] if san_result else [],
    }
    scoring_result = await _ai_service.analyze_investigation_findings(
        investigation_id, agent_findings, customer_context
    )

    # Prefer LLM synthesis score; fall back to rule-based
    final_score = ai_synthesis.get("final_risk_score", scoring_result.risk_score)
    risk_tier   = ai_synthesis.get("risk_tier", scoring_result.risk_level)
    confidence  = ai_synthesis.get("confidence", scoring_result.confidence)

    return {
        "success": True,
        "data": {
            "investigation_id":  investigation_id,
            "customer_id":       request.customer_id,
            "transaction_id":    request.transaction_id,
            "status":            "COMPLETED",
            "agent_results": {
                "transaction": tx_result,
                "kyc":         kyc_result,
                "sanctions":   san_result,
            },
            "risk_result": {
                "final_risk_score":  final_score,
                "risk_tier":         risk_tier,
                "confidence":        confidence,
                "rule_based_score":  scoring_result.rule_score,
                "ai_context_score":  scoring_result.ai_score,
                "executive_summary": ai_synthesis.get("executive_summary", scoring_result.explanation),
                "evidence_chain":    ai_synthesis.get("evidence_chain", []),
                "reasoning_steps":   ai_synthesis.get("reasoning_steps", []),
                "recommendation":    ai_synthesis.get("recommendation", "REVIEW"),
                "requires_human_review": ai_synthesis.get("requires_human_review", final_score >= 0.7),
                "risk_factors":      [f.dict() for f in scoring_result.factors],
            },
            "ai_synthesis": ai_synthesis,
            "investigation_timestamp": request.timestamp,
            "completed_timestamp":     datetime.utcnow().isoformat(),
        },
    }


@router.post("/investigate/hitl-recommendation")
async def get_hitl_recommendation_endpoint(
    request: AnalystBriefingApiRequest,
    _: None = RequireApiKey,
):
    summary = {
        "investigation_id":    request.investigation_id,
        "customer_id":         request.customer_id,
        "amount":              request.amount,
        "destination_country": request.destination_country,
    }

    result = await get_hitl_recommendation(summary, request.agent_results, request.risk_result)
    return {"success": True, "data": result}


@router.get("/investigate/health")
async def investigate_health():
    return {"status": "ok", "endpoint": "investigate"}
