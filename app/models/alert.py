"""Alert domain models."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AlertPolicy(BaseModel):
    """Alert policy definition."""
    policy_type: str
    name: str
    description: str
    conditions: Dict[str, Any]
    severity: str
    enabled: bool = True


class AlertGenerationRequest(BaseModel):
    """Request for generating alerts based on policies."""
    policy_type: str = Field(..., description="Policy type: transaction, kyc, or sanctions")
    customer_id: str = Field(..., description="Customer ID to check")
    transaction_data: Dict[str, Any] = Field(default_factory=dict, description="Transaction data for transaction-based alerts")
    kyc_data: Dict[str, Any] = Field(default_factory=dict, description="KYC data for KYC-based alerts")
    sanctions_data: Dict[str, Any] = Field(default_factory=dict, description="Sanctions data for sanctions-based alerts")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Alert(BaseModel):
    """Alert entity model."""
    alert_id: str
    investigation_id: str
    transaction_id: str
    customer_id: str
    amount: float
    currency: str = "USD"
    account_id: str
    recipient_country: str
    alert_hash: str
    timestamp: str
    status: str = "OPEN"
    severity: str = "medium"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    customer_context: Dict[str, Any] = Field(default_factory=dict)


class AlertListResponse(BaseModel):
    """Response model for alert list."""
    alerts: List[Alert]
    total_count: int
    filtered_count: int


class AlertFilter(BaseModel):
    """Filter for alert queries."""
    status: Optional[str] = None
    severity: Optional[str] = None
    customer_id: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    alert_type: Optional[str] = None
