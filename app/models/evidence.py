"""Evidence model for fraud investigation evidence."""

from sqlalchemy import Column, String, Text, Enum, JSON, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel


class EvidenceType(str, enum.Enum):
    """Types of evidence."""
    TRANSACTION_RECORD = "transaction_record"
    DOCUMENT = "document"
    SCREENSHOT = "screenshot"
    LOG_FILE = "log_file"
    EMAIL = "email"
    CHAT_MESSAGE = "chat_message"
    PHONE_RECORD = "phone_record"
    VIDEO = "video"
    AUDIO = "audio"
    SYSTEM_LOG = "system_log"
    USER_REPORT = "user_report"
    OTHER = "other"


class Evidence(BaseModel):
    """Evidence model for fraud investigations."""
    
    __tablename__ = "evidence"
    
    # Evidence identification
    evidence_id = Column(
        String(100), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="Unique evidence identifier"
    )
    
    # Evidence metadata
    evidence_type = Column(
        Enum(EvidenceType), 
        nullable=False,
        comment="Type of evidence"
    )
    title = Column(
        String(500), 
        nullable=False,
        comment="Evidence title or description"
    )
    description = Column(
        Text, 
        nullable=True,
        comment="Detailed evidence description"
    )
    
    # Source information
    source = Column(
        String(200), 
        nullable=False,
        comment="Source of the evidence"
    )
    source_timestamp = Column(
        String(50), 
        nullable=True,
        comment="Timestamp when evidence was created/collected"
    )
    collected_by = Column(
        String(200), 
        nullable=True,
        comment="Who collected the evidence"
    )
    collected_at = Column(
        String(50), 
        nullable=True,
        comment="Timestamp when evidence was collected"
    )
    
    # Evidence content
    content = Column(
        Text, 
        nullable=True,
        comment="Evidence content (text-based)"
    )
    file_path = Column(
        String(1000), 
        nullable=True,
        comment="Path to evidence file (if applicable)"
    )
    file_name = Column(
        String(500), 
        nullable=True,
        comment="Original file name"
    )
    file_size = Column(
        Float, 
        nullable=True,
        comment="File size in bytes"
    )
    file_hash = Column(
        String(128), 
        nullable=True,
        comment="File hash for integrity verification"
    )
    
    # Evidence metadata
    metadata = Column(
        JSON, 
        nullable=True,
        comment="Additional evidence metadata (JSON)"
    )
    tags = Column(
        JSON, 
        nullable=True,
        comment="Evidence tags for categorization (JSON)"
    )
    
    # Verification and authenticity
    is_verified = Column(
        Boolean, 
        default=False,
        comment="Whether evidence has been verified"
    )
    verification_method = Column(
        String(100), 
        nullable=True,
        comment="Method used for verification"
    )
    verification_notes = Column(
        Text, 
        nullable=True,
        comment="Notes on verification process"
    )
    
    # Chain of custody
    chain_of_custody = Column(
        JSON, 
        nullable=True,
        comment="Chain of custody records (JSON)"
    )
    custody_transfers = Column(
        JSON, 
        nullable=True,
        comment="Record of custody transfers (JSON)"
    )
    
    # Classification and sensitivity
    classification = Column(
        String(50), 
        nullable=True,
        comment="Evidence classification level"
    )
    is_sensitive = Column(
        Boolean, 
        default=False,
        comment="Whether evidence contains sensitive information"
    )
    
    # Relationships
    case_id = Column(
        String(100), 
        ForeignKey("cases.case_id"), 
        nullable=False,
        comment="Associated case identifier"
    )
    investigation_id = Column(
        String(100), 
        ForeignKey("investigations.investigation_id"), 
        nullable=True,
        comment="Associated investigation identifier"
    )
    
    def __repr__(self):
        return f"<Evidence(id={self.id}, evidence_id={self.evidence_id}, type={self.evidence_type})>"
