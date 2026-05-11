"""Base service with shared logging and response helpers."""

from datetime import datetime
from typing import Any, Dict

from app.core.logging import get_logger


class BaseService:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def _log_operation(self, operation: str, **kwargs):
        self.logger.info(operation, **kwargs)

    def _log_error(self, operation: str, error: Exception, **kwargs):
        self.logger.error(f"{operation} failed", error=str(error), **kwargs)

    def _generate_response(self, data: Dict[str, Any], success: bool = True) -> Dict[str, Any]:
        return {
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }
