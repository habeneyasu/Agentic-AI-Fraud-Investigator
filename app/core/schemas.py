"""
Core schemas - Clean Architecture Implementation.
"""

# Import all schemas from centralized location
from app.shared.models import (
    TriageAnalysis, TriageResult, CaseInput, HistoricalContext
)

# Re-export for backward compatibility
__all__ = [
    'TriageAnalysis',
    'TriageResult', 
    'CaseInput',
    'HistoricalContext'
]
