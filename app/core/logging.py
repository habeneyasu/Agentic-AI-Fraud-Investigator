import logging
import structlog
from typing import Any, Dict
import sys
from pathlib import Path

from app.core.config import settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.log_format == "json" 
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class FraudInvestigationLogger:
    """Specialized logger for fraud investigation events."""
    
    def __init__(self):
        self.logger = get_logger("fraud_investigation")
    
    def log_transaction_analysis(self, transaction_id: str, risk_score: float, 
                              flags: list, investigator_id: str = None) -> None:
        """Log transaction analysis results."""
        self.logger.info(
            "transaction_analysis_completed",
            transaction_id=transaction_id,
            risk_score=risk_score,
            flags=flags,
            investigator_id=investigator_id,
        )
    
    def log_investigation_started(self, case_id: str, case_type: str, 
                                priority: str, investigator_id: str) -> None:
        """Log investigation initiation."""
        self.logger.info(
            "investigation_started",
            case_id=case_id,
            case_type=case_type,
            priority=priority,
            investigator_id=investigator_id,
        )
    
    def log_investigation_completed(self, case_id: str, outcome: str, 
                                  duration_hours: float, actions_taken: list) -> None:
        """Log investigation completion."""
        self.logger.info(
            "investigation_completed",
            case_id=case_id,
            outcome=outcome,
            duration_hours=duration_hours,
            actions_taken=actions_taken,
        )
    
    def log_alert_generated(self, alert_id: str, alert_type: str, 
                          severity: str, details: Dict[str, Any]) -> None:
        """Log fraud alert generation."""
        self.logger.warning(
            "fraud_alert_generated",
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            details=details,
        )
    
    def log_api_access(self, endpoint: str, method: str, user_id: str = None, 
                      status_code: int = 200, response_time_ms: float = None) -> None:
        """Log API access for audit purposes."""
        self.logger.info(
            "api_access",
            endpoint=endpoint,
            method=method,
            user_id=user_id,
            status_code=status_code,
            response_time_ms=response_time_ms,
        )
    
    def log_security_event(self, event_type: str, user_id: str = None, 
                         ip_address: str = None, details: Dict[str, Any] = None) -> None:
        """Log security-related events."""
        self.logger.warning(
            "security_event",
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            details=details or {},
        )
    
    def log_error(self, error_type: str, error_message: str, 
                 context: Dict[str, Any] = None) -> None:
        """Log application errors."""
        self.logger.error(
            "application_error",
            error_type=error_type,
            error_message=error_message,
            context=context or {},
        )


# Global logger instances
fraud_logger = FraudInvestigationLogger()
audit_logger = get_logger("audit")
security_logger = get_logger("security")
performance_logger = get_logger("performance")


def log_performance_metrics(operation: str, duration_ms: float, 
                         metadata: Dict[str, Any] = None) -> None:
    """Log performance metrics."""
    performance_logger.info(
        "performance_metric",
        operation=operation,
        duration_ms=duration_ms,
        metadata=metadata or {},
    )


def log_audit_event(event_type: str, user_id: str, resource: str, 
                  action: str, details: Dict[str, Any] = None) -> None:
    """Log audit events for compliance."""
    audit_logger.info(
        "audit_event",
        event_type=event_type,
        user_id=user_id,
        resource=resource,
        action=action,
        details=details or {},
    )