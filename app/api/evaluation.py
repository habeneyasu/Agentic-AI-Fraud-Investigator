"""Evaluation endpoints for agent benchmark comparison."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import RequireApiKey
from app.core.logging import get_logger
from app.data.data_loader import data_loader
from app.shared.models import EvaluationRequest, EvaluationResponse

logger = get_logger(__name__)
router = APIRouter(tags=["evaluation"])

# In-memory storage for evaluation results
evaluation_results: Dict[str, Dict[str, Any]] = {}


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


# Benchmark data for different fraud types
BENCHMARKS = {
    "transaction_anomaly": BenchmarkMetrics(
        fraud_type="transaction_anomaly",
        historical_accuracy=0.89,
        typical_risk_range=(0.3, 0.9),
        confidence_threshold=0.75,
        false_positive_rate=0.08,
        detection_rate=0.92
    ),
    "identity_theft": BenchmarkMetrics(
        fraud_type="identity_theft",
        historical_accuracy=0.94,
        typical_risk_range=(0.6, 0.95),
        confidence_threshold=0.80,
        false_positive_rate=0.04,
        detection_rate=0.96
    ),
    "sanctions_violation": BenchmarkMetrics(
        fraud_type="sanctions_violation",
        historical_accuracy=0.99,
        typical_risk_range=(0.8, 1.0),
        confidence_threshold=0.95,
        false_positive_rate=0.01,
        detection_rate=0.99
    ),
    "account_takeover": BenchmarkMetrics(
        fraud_type="account_takeover",
        historical_accuracy=0.91,
        typical_risk_range=(0.4, 0.85),
        confidence_threshold=0.78,
        false_positive_rate=0.06,
        detection_rate=0.93
    )
}

# Agent performance benchmarks
AGENT_BENCHMARKS = {
    "transaction": AgentBenchmark(
        agent_type="transaction",
        expected_accuracy=0.89,
        risk_score_tolerance=0.15,
        processing_time_threshold=3.0
    ),
    "kyc_device": AgentBenchmark(
        agent_type="kyc_device",
        expected_accuracy=0.91,
        risk_score_tolerance=0.12,
        processing_time_threshold=2.5
    ),
    "sanctions": AgentBenchmark(
        agent_type="sanctions",
        expected_accuracy=0.99,
        risk_score_tolerance=0.05,
        processing_time_threshold=1.0
    )
}


async def evaluate_agent_against_benchmark(
    agent_type: str,
    agent_result: Dict[str, Any],
    fraud_type: str
) -> Dict[str, Any]:
    """Evaluate agent result against benchmark data."""
    
    benchmark = BENCHMARKS.get(fraud_type)
    agent_benchmark = AGENT_BENCHMARKS.get(agent_type)
    
    if not benchmark or not agent_benchmark:
        raise HTTPException(status_code=400, detail="Invalid fraud type or agent type")
    
    # Extract agent metrics
    agent_risk_score = agent_result.get("risk_score", 0.0)
    agent_confidence = agent_result.get("confidence", 0.0)
    processing_time = agent_result.get("execution_time", 0.0)
    
    # Compare to benchmarks
    risk_deviation = abs(agent_risk_score - sum(benchmark.typical_risk_range) / 2)
    risk_within_range = benchmark.typical_risk_range[0] <= agent_risk_score <= benchmark.typical_risk_range[1]
    
    confidence_comparison = agent_confidence - benchmark.confidence_threshold
    meets_confidence_threshold = agent_confidence >= benchmark.confidence_threshold
    
    processing_acceptable = processing_time <= agent_benchmark.processing_time_threshold
    
    # Calculate evaluation score
    evaluation_score = 0.0
    if risk_within_range:
        evaluation_score += 0.3
    if meets_confidence_threshold:
        evaluation_score += 0.4
    if processing_acceptable:
        evaluation_score += 0.3
    
    # Determine status
    if evaluation_score >= 0.8:
        status = "EXCEEDS_BENCHMARK"
    elif evaluation_score >= 0.6:
        status = "MEETS_BENCHMARK"
    elif evaluation_score >= 0.4:
        status = "BELOW_BENCHMARK"
    else:
        status = "CRITICAL_DEVIATION"
    
    return {
        "agent_type": agent_type,
        "fraud_type": fraud_type,
        "evaluation_score": evaluation_score,
        "status": status,
        "metrics": {
            "risk_score": agent_risk_score,
            "risk_deviation": risk_deviation,
            "risk_within_range": risk_within_range,
            "confidence": agent_confidence,
            "confidence_threshold": benchmark.confidence_threshold,
            "meets_confidence_threshold": meets_confidence_threshold,
            "processing_time": processing_time,
            "processing_threshold": agent_benchmark.processing_time_threshold,
            "processing_acceptable": processing_acceptable
        },
        "benchmark_data": {
            "historical_accuracy": benchmark.historical_accuracy,
            "typical_risk_range": benchmark.typical_risk_range,
            "false_positive_rate": benchmark.false_positive_rate,
            "detection_rate": benchmark.detection_rate
        },
        "recommendations": generate_evaluation_recommendations(
            status, risk_within_range, meets_confidence_threshold, processing_acceptable
        )
    }


def generate_evaluation_recommendations(
    status: str,
    risk_within_range: bool,
    meets_confidence: bool,
    processing_acceptable: bool
) -> List[str]:
    """Generate recommendations based on evaluation results."""
    
    recommendations = []
    
    if status == "CRITICAL_DEVIATION":
        recommendations.append("URGENT: Agent performance significantly deviates from benchmarks")
        recommendations.append("Immediate model retraining recommended")
    
    if not risk_within_range:
        recommendations.append("Risk score outside typical range - review calibration")
    
    if not meets_confidence:
        recommendations.append("Confidence below threshold - improve model accuracy")
    
    if not processing_acceptable:
        recommendations.append("Processing time exceeded threshold - optimize performance")
    
    if status == "EXCEEDS_BENCHMARK":
        recommendations.append("Excellent performance - consider as new baseline")
    
    return recommendations


@router.post("/evaluation/agent-result", response_model=EvaluationResponse)
async def evaluate_agent_result(
    request: EvaluationRequest,
    _: None = RequireApiKey
):
    """Evaluate agent result against benchmarks."""
    
    try:
        evaluation_id = f"eval_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{request.agent_type}"
        
        # Perform evaluation
        evaluation = await evaluate_agent_against_benchmark(
            request.agent_type,
            request.agent_result,
            request.fraud_type
        )
        
        # Store evaluation result
        evaluation_results[evaluation_id] = {
            "evaluation_id": evaluation_id,
            "investigation_id": request.investigation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "evaluation": evaluation
        }
        
        logger.info(
            "Agent evaluation completed",
            evaluation_id=evaluation_id,
            agent_type=request.agent_type,
            status=evaluation["status"]
        )
        
        return EvaluationResponse(
            success=True,
            evaluation_id=evaluation_id,
            status=evaluation["status"],
            evaluation_score=evaluation["evaluation_score"],
            recommendations=evaluation["recommendations"],
            metrics=evaluation["metrics"],
            benchmark_data=evaluation["benchmark_data"]
        )
        
    except Exception as e:
        logger.error("Agent evaluation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/evaluation/batch", response_model=Dict[str, Any])
async def batch_evaluation(
    evaluations: List[EvaluationRequest],
    _: None = RequireApiKey
):
    """Evaluate multiple agent results against benchmarks."""
    
    results = []
    
    for evaluation_request in evaluations:
        try:
            evaluation = await evaluate_agent_against_benchmark(
                evaluation_request.agent_type,
                evaluation_request.agent_result,
                evaluation_request.fraud_type
            )
            
            results.append({
                "investigation_id": evaluation_request.investigation_id,
                "agent_type": evaluation_request.agent_type,
                "success": True,
                "evaluation": evaluation
            })
            
        except Exception as e:
            logger.error(
                "Batch evaluation item failed",
                investigation_id=evaluation_request.investigation_id,
                agent_type=evaluation_request.agent_type,
                error=str(e)
            )
            results.append({
                "investigation_id": evaluation_request.investigation_id,
                "agent_type": evaluation_request.agent_type,
                "success": False,
                "error": str(e)
            })
    
    successful_count = len([r for r in results if r["success"]])
    
    return {
        "success": True,
        "message": f"Batch evaluation completed for {len(evaluations)} agent results",
        "data": {
            "total_evaluations": len(evaluations),
            "successful": successful_count,
            "failed": len(evaluations) - successful_count,
            "results": results
        }
    }


@router.get("/evaluation/benchmarks")
async def get_benchmarks(_: None = RequireApiKey):
    """Get all available benchmarks."""
    
    return {
        "success": True,
        "message": "Benchmarks retrieved successfully",
        "data": {
            "fraud_type_benchmarks": {
                fraud_type: benchmark.model_dump()
                for fraud_type, benchmark in BENCHMARKS.items()
            },
            "agent_benchmarks": {
                agent_type: benchmark.model_dump()
                for agent_type, benchmark in AGENT_BENCHMARKS.items()
            }
        }
    }


@router.get("/evaluation/results/{evaluation_id}")
async def get_evaluation_result(evaluation_id: str, _: None = RequireApiKey):
    """Get specific evaluation result."""
    
    result = evaluation_results.get(evaluation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Evaluation result not found")
    
    return {
        "success": True,
        "message": "Evaluation result retrieved successfully",
        "data": result
    }


@router.get("/evaluation/results")
async def get_all_evaluation_results(_: None = RequireApiKey):
    """Get all evaluation results."""
    
    results = list(evaluation_results.values())
    
    return {
        "success": True,
        "message": "Evaluation results retrieved successfully",
        "data": {
            "results": results,
            "total_count": len(results),
            "summary": {
                "exceeds_benchmark": len([r for r in results if r["evaluation"]["status"] == "EXCEEDS_BENCHMARK"]),
                "meets_benchmark": len([r for r in results if r["evaluation"]["status"] == "MEETS_BENCHMARK"]),
                "below_benchmark": len([r for r in results if r["evaluation"]["status"] == "BELOW_BENCHMARK"]),
                "critical_deviation": len([r for r in results if r["evaluation"]["status"] == "CRITICAL_DEVIATION"]),
                "average_evaluation_score": sum(r["evaluation"]["evaluation_score"] for r in results) / len(results) if results else 0.0
            }
        }
    }


@router.get("/evaluation/analytics")
async def get_evaluation_analytics(_: None = RequireApiKey):
    """Get evaluation analytics and trends."""
    
    results = list(evaluation_results.values())
    if not results:
        return {
            "success": True,
            "message": "No evaluation data available",
            "data": {
                "total_evaluations": 0,
                "performance_trends": {},
                "agent_performance": {},
                "benchmark_compliance": {}
            }
        }
    
    # Agent performance analysis
    agent_performance: Dict[str, Dict[str, Any]] = {}
    for result in results:
        agent_type = result["evaluation"]["agent_type"]
        if agent_type not in agent_performance:
            agent_performance[agent_type] = {
                "evaluations": 0,
                "total_score": 0.0,
                "exceeds_count": 0,
                "meets_count": 0,
                "below_count": 0,
                "critical_count": 0
            }
        
        perf = agent_performance[agent_type]
        perf["evaluations"] += 1
        perf["total_score"] += result["evaluation"]["evaluation_score"]
        
        status = result["evaluation"]["status"]
        if status == "EXCEEDS_BENCHMARK":
            perf["exceeds_count"] += 1
        elif status == "MEETS_BENCHMARK":
            perf["meets_count"] += 1
        elif status == "BELOW_BENCHMARK":
            perf["below_count"] += 1
        else:
            perf["critical_count"] += 1
    
    # Calculate averages and rates
    for agent_type, perf in agent_performance.items():
        perf["average_score"] = perf["total_score"] / perf["evaluations"]
        perf["exceeds_rate"] = (perf["exceeds_count"] / perf["evaluations"]) * 100
        perf["meets_rate"] = (perf["meets_count"] / perf["evaluations"]) * 100
        perf["below_rate"] = (perf["below_count"] / perf["evaluations"]) * 100
        perf["critical_rate"] = (perf["critical_count"] / perf["evaluations"]) * 100
    
    return {
        "success": True,
        "message": "Evaluation analytics retrieved successfully",
        "data": {
            "total_evaluations": len(results),
            "agent_performance": agent_performance,
            "benchmark_compliance": {
                "overall_compliance_rate": len([r for r in results if r["evaluation"]["evaluation_score"] >= 0.6]) / len(results) * 100,
                "excellence_rate": len([r for r in results if r["evaluation"]["status"] == "EXCEEDS_BENCHMARK"]) / len(results) * 100,
                "critical_issues": len([r for r in results if r["evaluation"]["status"] == "CRITICAL_DEVIATION"])
            },
            "performance_trends": {
                "average_evaluation_score": sum(r["evaluation"]["evaluation_score"] for r in results) / len(results),
                "top_performing_agent": max(agent_performance.items(), key=lambda x: x[1]["average_score"])[0] if agent_performance else None,
                "needs_improvement": [agent for agent, perf in agent_performance.items() if perf["critical_rate"] > 20]
            }
        }
    }


@router.get("/evaluation/health")
async def evaluation_health():
    """Health check for evaluation service."""
    return {"status": "ok", "endpoint": "evaluation"}
