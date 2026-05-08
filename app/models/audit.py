"""Audit log model for system auditing."""

from sqlalchemy import Column, String, Text, Enum, JSON, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel


class AuditAction(str, enum.Enum):
    """Audit action types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    ESCALATE = "escalate"
    ASSIGN = "assign"
    COMPLETE = "complete"
    APPROVE = "approve"
    REJECT = "reject"
    SYSTEM = "system"


class AuditLog(BaseModel):
    """Audit log model for tracking system activities."""
    
    __tablename__ = "audit_logs"
    
    # Audit identification
    audit_id = Column(
        String(100), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="Unique audit record identifier"
    )
    
    # Action information
    action = Column(
        Enum(AuditAction), 
        nullable=False,
        comment="Type of action performed"
    )
    entity_type = Column(
        String(100), 
        nullable=False,
        comment="Type of entity affected (alert, case, investigation, etc.)"
    )
    entity_id = Column(
        String(100), 
        nullable=True,
        comment="ID of the entity affected"
    )
    
    # User information
    user_id = Column(
        String(100), 
        nullable=True,
        comment="ID of user who performed the action"
    )
    username = Column(
        String(200), 
        nullable=True,
        comment="Username of user who performed the action"
    )
    user_role = Column(
        String(100), 
        nullable=True,
        comment="Role of user who performed the action"
    )
    
    # Action details
    action_description = Column(
        Text, 
        nullable=False,
        comment="Description of the action performed"
    )
    details = Column(
        JSON, 
        nullable=True,
        comment="Additional action details (JSON)"
    )
    
    # System information
    ip_address = Column(
        String(45), 
        nullable=True,
        comment="IP address of the user"
    )
    user_agent = Column(
        String(500), 
        nullable=True,
        comment="User agent string"
    )
    session_id = Column(
        String(100), 
        nullable=True,
        comment="Session identifier"
    )
    
    # Request information
    request_id = Column(
        String(100), 
        nullable=True,
        comment="Request ID for tracing"
    )
    endpoint = Column(
        String(500), 
        nullable=True,
        comment="API endpoint called"
    )
    method = Column(
        String(10), 
        nullable=True,
        comment="HTTP method used"
    )
    
    # Changes
    old_values = Column(
        JSON, 
        nullable=True,
        comment="Previous values before update (JSON)"
    )
    new_values = Column(
        JSON, 
        nullable=True,
        comment="New values after update (JSON)"
    )
    
    # Result
    success = Column(
        Boolean, 
        default=True,
        comment="Whether the action was successful"
    )
    error_message = Column(
        Text, 
        nullable=True,
        comment="Error message if action failed"
    )
    
    # Timing
    processing_time_ms = Column(
        Float, 
        nullable=True,
        comment="Processing time in milliseconds"
    )
    
    # Security
    is_sensitive = Column(
        Boolean, 
        default=False,
        comment="Whether this is a sensitive action"
    )
    requires_approval = Column(
        Boolean, 
        default=False,
        comment="Whether action required approval"
    )
    approved_by = Column(
        String(200), 
        nullable=True,
        comment="Who approved the action"
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, entity={self.entity_type}, user={self.username})>"
