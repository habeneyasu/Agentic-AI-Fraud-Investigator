"""Structured logging for fraud investigation system."""

import logging
import structlog
import uuid
import threading
from typing import Any, Dict
import sys
from pathlib import Path
from contextlib import contextmanager

from app.core.config import settings


class RequestContext:
    """Thread-local request context for correlation tracking."""
    
    _context = threading.local()
    
    @classmethod
    def set_context(cls, **kwargs):
        """Set context values for current request."""
        for key, value in kwargs.items():
            setattr(cls._context, key, value)
    
    @classmethod
    def get_context(cls) -> Dict[str, Any]:
        """Get current request context."""
        return {
            attr: getattr(cls._context, attr, None)
            for attr in ['request_id', 'user_id', 'session_id', 'correlation_id']
            if hasattr(cls._context, attr)
        }
    
    @classmethod
    def clear_context(cls):
        """Clear current request context."""
        cls._context.__dict__.clear()


def setup_logging() -> None:
    """Configure structured logging."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        add_request_context,
        add_environment_context,
    ]
    
    processors.append(
        structlog.processors.JSONRenderer() if settings.log_format == "json" 
        else structlog.dev.ConsoleRenderer(colors=True)
    )
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    configure_stdlib_logging(log_dir)


def configure_stdlib_logging(log_dir: Path) -> None:
    """Configure standard library logging."""
    json_formatter = logging.Formatter('%(message)s')
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if not settings.debug:
        for log_file, level in [
            ("error.log", logging.ERROR),
            ("app.log", logging.INFO),
            ("security.log", logging.INFO),
        ]:
            handler = logging.FileHandler(log_dir / log_file, mode='a', encoding='utf-8')
            handler.setLevel(level)
            handler.setFormatter(json_formatter)
            if log_file == "security.log":
                handler.addFilter(SecurityFilter())
            handlers.append(handler)
    
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        handlers=handlers,
        force=True
    )


def add_request_context(logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add request context to log entries."""
    event_dict.update(RequestContext.get_context())
    return event_dict


def add_environment_context(logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add environment context to log entries."""
    event_dict.update({
        'environment': settings.environment,
        'service': 'fraud_investigator',
        'version': '1.0.0'
    })
    return event_dict


class SecurityFilter(logging.Filter):
    """Filter for security-related logs."""
    
    def filter(self, record):
        return hasattr(record, 'security') or 'security' in record.getMessage().lower()


@contextmanager
def correlation_context(correlation_id: str = None, **kwargs):
    """Context manager for correlation tracking."""
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    
    RequestContext.set_context(correlation_id=correlation_id, **kwargs)
    try:
        yield correlation_id
    finally:
        RequestContext.clear_context()


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class FraudInvestigationLogger:
    """Logger for fraud investigation events."""
    
    def __init__(self):
        self.logger = get_logger("fraud_investigation")
    
    def log_transaction_analysis(self, transaction_id: str, risk_score: float, 
                              flags: list, investigator_id: str = None, 
                              correlation_id: str = None) -> None:
        """Log transaction analysis results."""
        with correlation_context(correlation_id):
            self.logger.info(
                "transaction_analysis_completed",
                transaction_id=transaction_id,
                risk_score=risk_score,
                flags=flags,
                investigator_id=investigator_id,
            )
    
    def log_investigation_started(self, case_id: str, case_type: str, 
                                priority: str, investigator_id: str,
                                correlation_id: str = None) -> None:
        """Log investigation initiation."""
        with correlation_context(correlation_id):
            self.logger.info(
                "investigation_started",
                case_id=case_id,
                case_type=case_type,
                priority=priority,
                investigator_id=investigator_id,
            )
    
    def log_investigation_completed(self, case_id: str, outcome: str, 
                                  duration_hours: float, actions_taken: list,
                                  correlation_id: str = None) -> None:
        """Log investigation completion."""
        with correlation_context(correlation_id):
            self.logger.info(
                "investigation_completed",
                case_id=case_id,
                outcome=outcome,
                duration_hours=duration_hours,
                actions_taken=actions_taken,
            )
    
    def log_alert_generated(self, alert_id: str, alert_type: str, 
                          severity: str, details: Dict[str, Any],
                          correlation_id: str = None) -> None:
        """Log fraud alert generation."""
        with correlation_context(correlation_id):
            self.logger.warning(
                "fraud_alert_generated",
                alert_id=alert_id,
                alert_type=alert_type,
                severity=severity,
                details=details,
            )
    
    def log_api_access(self, endpoint: str, method: str, user_id: str = None, 
                      status_code: int = 200, response_time_ms: float = None,
                      correlation_id: str = None) -> None:
        """Log API access for audit purposes."""
        with correlation_context(correlation_id, user_id=user_id):
            self.logger.info(
                "api_access",
                endpoint=endpoint,
                method=method,
                user_id=user_id,
                status_code=status_code,
                response_time_ms=response_time_ms,
            )
    
    def log_security_event(self, event_type: str, user_id: str = None, 
                         ip_address: str = None, details: Dict[str, Any] = None,
                         correlation_id: str = None) -> None:
        """Log security-related events."""
        with correlation_context(correlation_id):
            security_logger = get_logger("security")
            security_logger.warning(
                "security_event",
                event_type=event_type,
                user_id=user_id,
                ip_address=ip_address,
                details=details or {},
                security=True
            )
    
    def log_error(self, error_type: str, error_message: str, 
                 context: Dict[str, Any] = None, correlation_id: str = None) -> None:
        """Log application errors."""
        with correlation_context(correlation_id):
            self.logger.error(
                "application_error",
                error_type=error_type,
                error_message=error_message,
                context=context or {},
                exc_info=True
            )


# Global logger instances
fraud_logger = FraudInvestigationLogger()
audit_logger = get_logger("audit")
security_logger = get_logger("security")
performance_logger = get_logger("performance")


def log_performance_metrics(operation: str, duration_ms: float, 
                         metadata: Dict[str, Any] = None,
                         correlation_id: str = None) -> None:
    """Log performance metrics."""
    with correlation_context(correlation_id):
        performance_logger.info(
            "performance_metric",
            operation=operation,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )


def log_audit_event(event_type: str, user_id: str, resource: str, 
                  action: str, details: Dict[str, Any] = None,
                  correlation_id: str = None) -> None:
    """Log audit events for compliance."""
    with correlation_context(correlation_id, user_id=user_id):
        audit_logger.info(
            "audit_event",
            event_type=event_type,
            user_id=user_id,
            resource=resource,
            action=action,
            details=details or {},
        )


def log_business_event(event_type: str, entity_type: str, entity_id: str,
                    details: Dict[str, Any] = None,
                    correlation_id: str = None) -> None:
    """Log business events for analytics."""
    business_logger = get_logger("business")
    with correlation_context(correlation_id):
        business_logger.info(
            "business_event",
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
        )


def log_system_event(event_type: str, component: str, 
                  details: Dict[str, Any] = None,
                  correlation_id: str = None) -> None:
    """Log system events for monitoring."""
    system_logger = get_logger("system")
    with correlation_context(correlation_id):
        system_logger.info(
            "system_event",
            event_type=event_type,
            component=component,
            details=details or {},
        )