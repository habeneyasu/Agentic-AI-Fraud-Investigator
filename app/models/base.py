"""Base database model."""

from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TimestampMixin:
    """Mixin for timestamp fields."""
    
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        comment="Timestamp when record was created"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False,
        comment="Timestamp when record was last updated"
    )


class BaseModel(Base, TimestampMixin):
    """Base model with common fields."""
    
    __abstract__ = True
    
    id = Column(
        Integer, 
        primary_key=True, 
        autoincrement=True,
        comment="Unique identifier for the record"
    )
