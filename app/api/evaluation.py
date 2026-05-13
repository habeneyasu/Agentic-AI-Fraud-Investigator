"""Evaluation API (``/v1``): ``agent-result``, ``benchmarks``, ``results`` (optional ``?evaluation_id=``)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import RequireApiKey
from app.core.logging import get_logger
from app.shared.models import EvaluationRequest, EvaluationResponse

logger = get_logger(__name__)
router = APIRouter(tags=["evaluation"])

evaluation_results: Dict[str, Dict[str, Any]] = {}

_STATUS_KEYS = (
    "EXCEEDS_BENCHMARK",
    "MEETS_BENCHMARK",
    "BELOW_BENCHMARK",
    "CRITICAL_DEVIATION",
)


class BenchmarkMetrics(BaseModel):
    fraud_type: str
    historical_accuracy: float
    typical_risk_range: tuple[float, float]
    confidence_threshold: float
    false_positive_rate: float
    detection_rate: float


class AgentBenchmark(BaseModel):
    agent_type: str
    expected_accuracy: float
    risk_score_tolerance: float
    processing_time_threshold: float


BENCHMARKS = {
    "transaction_anomaly": BenchmarkMetrics(
        fraud_type="transaction_anomaly",
        historical_accuracy=0.89,
        typical_risk_range=(0.3, 0.9),
        confidence_threshold=0.75,
        false_positive_rate=0.08,
        detection_rate=0.92,
    ),
    "identity_theft": BenchmarkMetrics(
        fraud_type="identity_theft",
        historical_accuracy=0.94,
        typical_risk_range=(0.6, 0.95),
        confidence_threshold=0.80,
        false_positive_rate=0.04,
        detection_rate=0.96,
    ),
    "sanctions_violation": BenchmarkMetrics(
        fraud_type="sanctions_violation",
        historical_accuracy=0.99,
        typical_risk_range=(0.8, 1.0),
        confidence_threshold=0.95,
        false_positive_rate=0.01,
        detection_rate=0.99,
    ),
    "account_takeover": BenchmarkMetrics(
        fraud_type="account_takeover",
        historical_accuracy=0.91,
        typical_risk_range=(0.4, 0.85),
        confidence_threshold=0.78,
        false_positive_rate=0.06,
        detection_rate=0.93,
    ),
}

AGENT_BENCHMARKS = {
    "transaction": AgentBenchmark(
        agent_type="transaction",
        expected_accuracy=0.89,
        risk_score_tolerance=0.15,
        processing_time_threshold=3.0,
    ),
    "kyc_device": AgentBenchmark(
        agent_type="kyc_device",
        expected_accuracy=0.91,
        risk_score_tolerance=0.12,
        processing_time_threshold=2.5,
    ),
    "sanctions": AgentBenchmark(
        agent_type="sanctions",
        expected_accuracy=0.99,
        risk_score_tolerance=0.05,
        processing_time_threshold=1.0,
    ),
}


def _recommendations(
    status: str,
    risk_ok: bool,
    conf_ok: bool,
    proc_ok: bool,
) -> List[str]:
    out: List[str] = []
    if status == "CRITICAL_DEVIATION":
        out.extend(
            [
                "URGENT: Agent performance significantly deviates from benchmarks",
                "Immediate model retraining recommended",
            ]
        )
    if not risk_ok:
        out.append("Risk score outside typical range - review calibration")
    if not conf_ok:
        out.append("Confidence below threshold - improve model accuracy")
    if not proc_ok:
        out.append("Processing time exceeded threshold - optimize performance")
    if status == "EXCEEDS_BENCHMARK":
        out.append("Excellent performance - consider as new baseline")
    return out


def evaluate_agent_against_benchmark(
    agent_type: str,
    agent_result: Dict[str, Any],
    fraud_type: str,
) -> Dict[str, Any]:
    benchmark = BENCHMARKS.get(fraud_type)
    agent_benchmark = AGENT_BENCHMARKS.get(agent_type)
    if not benchmark or not agent_benchmark:
        raise HTTPException(status_code=400, detail="Invalid fraud type or agent type")

    agent_risk = float(agent_result.get("risk_score") or 0.0)
    agent_conf = float(agent_result.get("confidence") or 0.0)
    proc_t = float(agent_result.get("execution_time") or 0.0)
    lo, hi = benchmark.typical_risk_range
    mid = (lo + hi) / 2

    risk_ok = lo <= agent_risk <= hi
    conf_ok = agent_conf >= benchmark.confidence_threshold
    proc_ok = proc_t <= agent_benchmark.processing_time_threshold
    score = sum([0.3 if risk_ok else 0, 0.4 if conf_ok else 0, 0.3 if proc_ok else 0])

    if score >= 0.8:
        status = "EXCEEDS_BENCHMARK"
    elif score >= 0.6:
        status = "MEETS_BENCHMARK"
    elif score >= 0.4:
        status = "BELOW_BENCHMARK"
    else:
        status = "CRITICAL_DEVIATION"

    return {
        "agent_type": agent_type,
        "fraud_type": fraud_type,
        "evaluation_score": score,
        "status": status,
        "metrics": {
            "risk_score": agent_risk,
            "risk_deviation": abs(agent_risk - mid),
            "risk_within_range": risk_ok,
            "confidence": agent_conf,
            "confidence_threshold": benchmark.confidence_threshold,
            "meets_confidence_threshold": conf_ok,
            "processing_time": proc_t,
            "processing_threshold": agent_benchmark.processing_time_threshold,
            "processing_acceptable": proc_ok,
        },
        "benchmark_data": {
            "historical_accuracy": benchmark.historical_accuracy,
            "typical_risk_range": benchmark.typical_risk_range,
            "false_positive_rate": benchmark.false_positive_rate,
            "detection_rate": benchmark.detection_rate,
        },
        "recommendations": _recommendations(status, risk_ok, conf_ok, proc_ok),
    }


def _summary_counts(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {s: 0 for s in _STATUS_KEYS}
    total = 0.0
    for r in results:
        st = r["evaluation"]["status"]
        if st in counts:
            counts[st] += 1
        total += r["evaluation"]["evaluation_score"]
    n = len(results)
    return {
        "exceeds_benchmark": counts["EXCEEDS_BENCHMARK"],
        "meets_benchmark": counts["MEETS_BENCHMARK"],
        "below_benchmark": counts["BELOW_BENCHMARK"],
        "critical_deviation": counts["CRITICAL_DEVIATION"],
        "average_evaluation_score": total / n if n else 0.0,
    }


def _analytics_payload(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not results:
        return {
            "total_evaluations": 0,
            "performance_trends": {},
            "agent_performance": {},
            "benchmark_compliance": {},
        }

    perf: Dict[str, Dict[str, Any]] = {}
    for r in results:
        at = r["evaluation"]["agent_type"]
        p = perf.setdefault(
            at,
            {
                "evaluations": 0,
                "total_score": 0.0,
                "exceeds_count": 0,
                "meets_count": 0,
                "below_count": 0,
                "critical_count": 0,
            },
        )
        p["evaluations"] += 1
        p["total_score"] += r["evaluation"]["evaluation_score"]
        st = r["evaluation"]["status"]
        if st == "EXCEEDS_BENCHMARK":
            p["exceeds_count"] += 1
        elif st == "MEETS_BENCHMARK":
            p["meets_count"] += 1
        elif st == "BELOW_BENCHMARK":
            p["below_count"] += 1
        else:
            p["critical_count"] += 1

    for p in perf.values():
        n = p["evaluations"]
        p["average_score"] = p["total_score"] / n
        p["exceeds_rate"] = p["exceeds_count"] / n * 100
        p["meets_rate"] = p["meets_count"] / n * 100
        p["below_rate"] = p["below_count"] / n * 100
        p["critical_rate"] = p["critical_count"] / n * 100

    n = len(results)
    return {
        "total_evaluations": n,
        "agent_performance": perf,
        "benchmark_compliance": {
            "overall_compliance_rate": len([r for r in results if r["evaluation"]["evaluation_score"] >= 0.6])
            / n
            * 100,
            "excellence_rate": len([r for r in results if r["evaluation"]["status"] == "EXCEEDS_BENCHMARK"]) / n * 100,
            "critical_issues": len([r for r in results if r["evaluation"]["status"] == "CRITICAL_DEVIATION"]),
        },
        "performance_trends": {
            "average_evaluation_score": sum(r["evaluation"]["evaluation_score"] for r in results) / n,
            "top_performing_agent": max(perf.items(), key=lambda x: x[1]["average_score"])[0] if perf else None,
            "needs_improvement": [a for a, p in perf.items() if p["critical_rate"] > 20],
        },
    }


@router.post("/evaluation/agent-result", response_model=EvaluationResponse)
async def evaluate_agent_result(request: EvaluationRequest, _: None = RequireApiKey):
    try:
        eid = f"eval_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{request.agent_type}"
        ev = evaluate_agent_against_benchmark(request.agent_type, request.agent_result, request.fraud_type)
        evaluation_results[eid] = {
            "evaluation_id": eid,
            "investigation_id": request.investigation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "evaluation": ev,
        }
        logger.info("Agent evaluation completed", evaluation_id=eid, agent_type=request.agent_type, status=ev["status"])
        return EvaluationResponse(
            success=True,
            evaluation_id=eid,
            status=ev["status"],
            evaluation_score=ev["evaluation_score"],
            recommendations=ev["recommendations"],
            metrics=ev["metrics"],
            benchmark_data=ev["benchmark_data"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Agent evaluation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/evaluation/benchmarks")
async def get_benchmarks(_: None = RequireApiKey):
    return {
        "success": True,
        "data": {
            "fraud_type_benchmarks": {k: v.model_dump() for k, v in BENCHMARKS.items()},
            "agent_benchmarks": {k: v.model_dump() for k, v in AGENT_BENCHMARKS.items()},
        },
    }


@router.get("/evaluation/results")
async def get_evaluation_results(
    evaluation_id: Optional[str] = Query(default=None, description="Single evaluation id, or omit for full history."),
    _: None = RequireApiKey,
):
    if evaluation_id:
        row = evaluation_results.get(evaluation_id.strip())
        if not row:
            raise HTTPException(status_code=404, detail="Evaluation result not found")
        return {"success": True, "data": {"result": row}}

    results = list(evaluation_results.values())
    return {
        "success": True,
        "data": {
            "results": results,
            "total_count": len(results),
            "summary": _summary_counts(results),
            "analytics": _analytics_payload(results),
        },
    }
