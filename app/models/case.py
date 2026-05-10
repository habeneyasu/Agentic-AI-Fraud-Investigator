"""Case model for fraud investigation cases."""

from sqlalchemy import Column, String, Text, Enum, JSON, Float, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from .base import BaseModel


class CaseStatus(str, enum.Enum):
    """Case investigation status."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    PENDING_ESCALATION = "pending_escalation"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ARCHIVED = "archived"


class CasePriority(str, enum.Enum):
    """Case priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Case(BaseModel):
    """Fraud investigation case model."""
    
    __tablename__ = "cases"
    
    # Case identification
    case_id = Column(
        String(100), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="Unique case identifier"
    )
    
    # Case metadata
    case_type = Column(
        String(100), 
        nullable=False,
        comment="Type of fraud case"
    )
    priority = Column(
        Enum(CasePriority), 
        nullable=False, 
        default=CasePriority.MEDIUM,
        comment="Case priority level"
    )
    status = Column(
        Enum(CaseStatus), 
        nullable=False, 
        default=CaseStatus.OPEN,
        comment="Current case status"
    )
    
    # Case details
    title = Column(
        String(500), 
        nullable=False,
        comment="Case title"
    )
    description = Column(
        Text, 
        nullable=False,
        comment="Detailed case description"
    )
    
    # Financial information
    amount = Column(
        Float, 
        nullable=True,
        comment="Amount involved in the case"
    )
    currency = Column(
        String(10), 
        nullable=True,
        comment="Currency code"
    )
    
    # Case parties
    reporter = Column(
        String(200), 
        nullable=False,
        comment="Who reported the case"
    )
    affected_parties = Column(
        JSON, 
        nullable=True,
        comment="List of affected parties/customers"
    )
    
    # Case data
    evidence = Column(
        JSON, 
        nullable=True,
        comment="Evidence data (JSON)"
    )
    case_data = Column(
        JSON, 
        nullable=True,
        comment="Additional case information (JSON)"
    )
    
    # Triage and analysis
    triage_result = Column(
        JSON, 
        nullable=True,
        comment="Triage analysis results (JSON)"
    )
    risk_factors = Column(
        JSON, 
        nullable=True,
        comment="Identified risk factors (JSON)"
    )
    urgency_indicators = Column(
        JSON, 
        nullable=True,
        comment="Urgency indicators (JSON)"
    )
    
    # Investigation metadata
    assigned_to = Column(
        String(200), 
        nullable=True,
        comment="Investigator assigned to the case"
    )
    estimated_investigation_time = Column(
        Float, 
        nullable=True,
        comment="Estimated investigation time in hours"
    )
    required_resources = Column(
        JSON, 
        nullable=True,
        comment="Required resources for investigation (JSON)"
    )
    
    # Escalation
    auto_escalation = Column(
        Boolean, 
        default=False,
        comment="Whether case was auto-escalated"
    )
    escalation_reason = Column(
        Text, 
        nullable=True,
        comment="Reason for escalation"
    )
    
    # Resolution
    resolution_notes = Column(
        Text, 
        nullable=True,
        comment="Notes on case resolution"
    )
    closed_at = Column(
        String(50), 
        nullable=True,
        comment="Timestamp when case was closed"
    )
    
    # Human-in-the-loop fields
    human_decision = Column(
        String(20),
        nullable=True,
        comment="Human decision: APPROVE, REJECT, ESCALATE"
    )
    human_reasoning = Column(
        Text,
        nullable=True,
        comment="Human reasoning for decision"
    )
    human_notes = Column(
        Text,
        nullable=True,
        comment="Additional human notes"
    )
    human_confidence = Column(
        Float,
        nullable=True,
        comment="Human confidence level 1-10"
    )
    reviewed_by = Column(
        String(200),
        nullable=True,
        comment="ID of user who reviewed the case"
    )
    reviewed_at = Column(
        DateTime,
        nullable=True,
        comment="Timestamp when case was reviewed"
    )
    
    # AI analysis fields
    ai_recommendation = Column(
        Text,
        nullable=True,
        comment="AI-generated recommendations"
    )
    ai_confidence = Column(
        Float,
        nullable=True,
        comment="AI confidence level 0-1"
    )
    
    # Investigation resumption
    resumed_by = Column(
        String(200),
        nullable=True,
        comment="ID of user who resumed the case"
    )
    resumed_at = Column(
        DateTime,
        nullable=True,
        comment="Timestamp when case was resumed"
    )
    
    # Relationships
    alerts = relationship("Alert", back_populates="case", cascade="all, delete-orphan")
    investigations = relationship("Investigation", back_populates="case", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Case(id={self.id}, case_id={self.case_id}, status={self.status}, priority={self.priority})>"
