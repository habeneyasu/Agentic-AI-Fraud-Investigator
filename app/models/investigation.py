"""Investigation model for fraud case investigations."""

from sqlalchemy import Column, String, Text, Enum, JSON, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel


class InvestigationStatus(str, enum.Enum):
    """Investigation status."""
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    AWAITING_INFO = "awaiting_info"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Investigation(BaseModel):
    """Fraud investigation model."""
    
    __tablename__ = "investigations"
    
    # Investigation identification
    investigation_id = Column(
        String(100), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="Unique investigation identifier"
    )
    
    # Investigation metadata
    status = Column(
        Enum(InvestigationStatus), 
        nullable=False, 
        default=InvestigationStatus.ASSIGNED,
        comment="Current investigation status"
    )
    
    # Assignment
    assigned_to = Column(
        String(200), 
        nullable=False,
        comment="Investigator assigned to the case"
    )
    assigned_at = Column(
        String(50), 
        nullable=False,
        comment="Timestamp when investigation was assigned"
    )
    
    # Investigation details
    title = Column(
        String(500), 
        nullable=False,
        comment="Investigation title"
    )
    summary = Column(
        Text, 
        nullable=False,
        comment="Investigation summary"
    )
    
    # Investigation data
    investigation_data = Column(
        JSON, 
        nullable=True,
        comment="Investigation findings and data (JSON)"
    )
    evidence_collected = Column(
        JSON, 
        nullable=True,
        comment="Evidence collected during investigation (JSON)"
    )
    notes = Column(
        Text, 
        nullable=True,
        comment="Investigator notes"
    )
    
    # Timeline and duration
    started_at = Column(
        String(50), 
        nullable=True,
        comment="Timestamp when investigation started"
    )
    completed_at = Column(
        String(50), 
        nullable=True,
        comment="Timestamp when investigation completed"
    )
    estimated_duration_hours = Column(
        Float, 
        nullable=True,
        comment="Estimated investigation duration in hours"
    )
    actual_duration_hours = Column(
        Float, 
        nullable=True,
        comment="Actual investigation duration in hours"
    )
    
    # Findings and results
    findings = Column(
        JSON, 
        nullable=True,
        comment="Investigation findings (JSON)"
    )
    conclusions = Column(
        Text, 
        nullable=True,
        comment="Investigation conclusions"
    )
    recommendations = Column(
        JSON, 
        nullable=True,
        comment="Investigation recommendations (JSON)"
    )
    
    # Risk assessment
    risk_level = Column(
        String(20), 
        nullable=True,
        comment="Final risk level assessment"
    )
    risk_score = Column(
        Float, 
        nullable=True,
        comment="Final risk score (0.0-1.0)"
    )
    
    # Actions taken
    actions_taken = Column(
        JSON, 
        nullable=True,
        comment="List of actions taken during investigation (JSON)"
    )
    follow_up_required = Column(
        Boolean, 
        default=False,
        comment="Whether follow-up is required"
    )
    follow_up_details = Column(
        Text, 
        nullable=True,
        comment="Details of required follow-up"
    )
    
    # Relationships
    case_id = Column(
        String(100), 
        ForeignKey("cases.case_id"), 
        nullable=False,
        comment="Associated case identifier"
    )
    case = relationship("Case", back_populates="investigations")
    
    def __repr__(self):
        return f"<Investigation(id={self.id}, investigation_id={self.investigation_id}, status={self.status})>"
