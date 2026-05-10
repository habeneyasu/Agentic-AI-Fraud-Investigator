"""
Base service class with common functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.logging import get_logger


class BaseService(ABC):
    """Base service with common functionality."""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    def _log_operation(self, operation: str, **kwargs):
        """Log service operation."""
        self.logger.info(f"{operation}", **kwargs)
    
    def _log_error(self, operation: str, error: Exception, **kwargs):
        """Log service error."""
        self.logger.error(f"{operation} failed", error=str(error), **kwargs)
    
    def _generate_response(self, data: Dict[str, Any], success: bool = True) -> Dict[str, Any]:
        """Generate standard response format."""
        return {
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
