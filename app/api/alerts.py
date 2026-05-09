from typing import List, Dict, Any
from datetime import datetime
from enum import Enum
import asyncio

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.triage import get_fraud_triage, TriagePriority
from app.core.schemas import CaseInput, HistoricalContext, TriageResult, TriageCategory
from app.core.logging import get_logger
from app.core.langsmith import track_langsmith
from app.llm.client import LLMProvider
from app.graph.workflow import execute_fraud_workflow
from app.graph.state import InvestigationState

logger = get_logger(__name__)


class AlertStatus(str, Enum):
    """Alert processing status."""
    RECEIVED = "received"
    PROCESSING = "processing"
    TRIAGED = "triaged"
    ESCALATED = "escalated"
    ERROR = "error"


class AlertType(str, Enum):
    """Types of fraud alerts - aligned with triage categories."""
    TRANSACTION_FRAUD = "transaction_fraud"
    ACCOUNT_TAKEOVER = "account_takeover"
    IDENTITY_THEFT = "identity_theft"
    MONEY_LAUNDERING = "money_laundering"
    SANCTIONS_VIOLATION = "sanctions_violation"
    KYC_ISSUES = "kyc_issues"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class AlertInput(BaseModel):
    """Input model for fraud alerts."""
    alert_id: str = Field(..., description="Unique alert identifier")
    alert_type: AlertType = Field(..., description="Type of alert")
    severity: str = Field(..., description="Alert severity level")
    source: str = Field(..., description="Alert source system")
    timestamp: str = Field(..., description="When alert was generated")
    case_data: Dict[str, Any] = Field(..., description="Case information for triage")
    historical_context: Optional[Dict[str, Any]] = Field(None, description="Historical context")


class AlertResponse(BaseModel):
    """Response model for alert processing."""
    alert_id: str = Field(..., description="Alert identifier")
    status: str = Field(..., description="Processing status")
    case_id: Optional[str] = Field(None, description="Generated case identifier")
    risk_score: Optional[float] = Field(None, description="Calculated risk score")
    triage_result: Optional[TriageResult] = Field(None, description="Triage analysis result")
    investigation_status: Optional[str] = Field(None, description="Investigation workflow status")
    timestamp: str = Field(..., description="Response timestamp")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")


class FraudAlertProcessor:
    """Concise fraud alert processing system."""
    
    def __init__(self, provider: LLMProvider = LLMProvider.OPENAI):
        self.triage_service = get_fraud_triage()
        self.provider = provider
    
    @track_langsmith(
        name="fraud_alert_processing",
        run_type="chain",
        tags=["alerts", "fraud", "processing"],
        metadata={"task": "alert_processing"}
    )
    async def process_alert(self, alert_input: AlertInput) -> AlertResponse:
        """Process fraud alert with intelligent triage."""
        
        start_time = datetime.utcnow()
        
        try:
            # Validate and triage
            validated_case = CaseInput(**alert_input.case_data)
            validated_context = HistoricalContext(**(alert_input.historical_context or {}))
            
            triage_result = await self.triage_service.triage_case(
                validated_case,
                validated_context
            )
            
            # Determine status based on triage priority
            status = AlertStatus.ESCALATED if triage_result.auto_escalation else AlertStatus.TRIAGED
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.info(
                "Alert processed",
                alert_id=alert_input.alert_id,
                priority=triage_result.priority.value,
                processing_time_ms=processing_time
            )
            
            return AlertResponse(
                alert_id=alert_input.alert_id,
                status=status,
                triage_result=triage_result,
                processing_time_ms=processing_time,
                error_message=None
            )
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error("Alert processing failed", alert_id=alert_input.alert_id, error=str(e))
            
            return AlertResponse(
                alert_id=alert_input.alert_id,
                status=AlertStatus.ERROR,
                processing_time_ms=processing_time,
                error_message=str(e)
            )
    
    async def process_batch_alerts(self, alerts: List[AlertInput]) -> List[AlertResponse]:
        """Process alerts concurrently."""
        
        semaphore = asyncio.Semaphore(10)
        tasks = [asyncio.create_task(self.process_alert(alert)) for alert in alerts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [
            result if not isinstance(result, Exception) else AlertResponse(
                alert_id=alerts[i].alert_id,
                status=AlertStatus.ERROR,
                processing_time_ms=0.0,
                error_message=str(result)
            )
            for i, result in enumerate(results)
        ]


# Global instance
fraud_alert_processor = FraudAlertProcessor()


def get_fraud_alert_processor() -> FraudAlertProcessor:
    return fraud_alert_processor


# Utility: Create alert from transaction data
async def create_alert_from_transaction(
    transaction_data: Dict[str, Any],
    anomaly_score: float,
    source_system: str = "transaction_monitoring"
) -> AlertInput:
    """Create fraud alert from transaction data."""
    
    # Map anomaly to alert type (aligned with triage categories)
    alert_type_map = {
        (0.9, 1.0): AlertType.REPORTED_FRAUD,
        (0.7, 0.9): AlertType.TRANSACTION_FRAUD,
        (0.5, 0.7): AlertType.SUSPICIOUS_ACTIVITY,
        (0.0, 0.5): AlertType.KYC_ISSUES
    }
    
    alert_type = next(
        (atype for score, atype in alert_type_map.items() if score >= score),
        AlertType.SUSPICIOUS_ACTIVITY
    )
    
    severity = "critical" if anomaly_score > 0.8 else "high" if anomaly_score > 0.6 else "medium"
    
    return AlertInput(
        alert_id=f"ALERT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        alert_type=alert_type,
        severity=severity,
        source=source_system,
        timestamp=datetime.utcnow().isoformat(),
        case_data={
            "case_id": f"CASE-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "case_type": alert_type.value,
            "reported_date": datetime.utcnow().isoformat(),
            "amount": transaction_data.get("amount"),
            "description": f"Transaction anomaly detected: {transaction_data.get('description', 'Suspicious activity')}",
            "reporter": source_system,
            "affected_parties": transaction_data.get("customer_id", "unknown"),
            "evidence": [transaction_data]
        }
    )


router = APIRouter()
@router.post("/process", response_model=AlertResponse)
async def process_alert(alert: AlertInput) -> AlertResponse:
    """Process a fraud alert with intelligent triage."""
    processor = get_fraud_alert_processor()
    return await processor.process_alert(alert)


@router.post("/trigger-workflow", response_model=AlertResponse)
async def trigger_workflow(alert: AlertInput) -> AlertResponse:
    """Trigger LangGraph workflow for fraud investigation."""
    try:
        # Convert alert to investigation state
        investigation_state = InvestigationState(
            case_id=alert.alert_id,
            case_type=alert.alert_type,
            title=f"Fraud Alert: {alert.alert_type}",
            description=alert.case_data.get("description", f"Alert of type {alert.alert_type}"),
            priority=TriagePriority.HIGH,
            metadata=alert.case_data,
            transaction_data=alert.case_data.get("transactions", []),
            kyc_data=alert.case_data.get("kyc_events", []),
            entities=alert.case_data.get("entities", []),
            customer_history=alert.historical_context or {}
        )
        
        # Execute workflow asynchronously
        final_state = await execute_fraud_workflow(investigation_state)
        
        return AlertResponse(
            alert_id=alert.alert_id,
            status="workflow_triggered",
            case_id=final_state.case_id,
            risk_score=final_state.risk_score or 0.0,
            triage_result=TriageResult(
                category=TriageCategory.HIGH_RISK,
                priority=TriagePriority.HIGH,
                requires_investigation=True,
                urgency_indicators=["Automated workflow triggered"],
                recommended_action="Full investigation via LangGraph"
            ).dict(),
            investigation_status=final_state.status.value,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger workflow for alert {alert.alert_id}: {e}")
        return AlertResponse(
            alert_id=alert.alert_id,
            status="error",
            error_message=str(e),
            timestamp=datetime.utcnow().isoformat()
        )


@router.post("/batch", response_model=List[AlertResponse])
async def process_batch_alerts(alerts: List[AlertInput]) -> List[AlertResponse]:
    """Process multiple fraud alerts concurrently."""
    processor = get_fraud_alert_processor()
    return await processor.process_batch_alerts(alerts)


@router.post("/from-transaction", response_model=AlertInput)
async def create_alert_from_transaction_endpoint(
    transaction_data: Dict[str, Any],
    anomaly_score: float,
    source_system: str = "transaction_monitoring"
) -> AlertInput:
    """Create a fraud alert from transaction data."""
    return await create_alert_from_transaction(transaction_data, anomaly_score, source_system)


@router.get("/types", response_model=List[str])
async def get_alert_types() -> List[str]:
    """Get available alert types."""
    return [alert_type.value for alert_type in AlertType]


@router.get("/statuses", response_model=List[str])
async def get_alert_statuses() -> List[str]:
    """Get available alert statuses."""
    return [status.value for status in AlertStatus]