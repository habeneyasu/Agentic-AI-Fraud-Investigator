"""PostgreSQL ORM — fraud investigation domain tables."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.db_base import Base


class TransactionORM(Base):
    """Raw movement of funds (ledger / channel events)."""

    __tablename__ = "transactions"

    transaction_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(16), default="USD", nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_account: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    destination_account: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    destination_country: Mapped[Optional[str]] = mapped_column(String(8), nullable=True, index=True)
    narrative: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (Index("idx_transactions_customer_time", "customer_id", "occurred_at"),)


class KycProfileORM(Base):
    """Identity verification status per customer (e.g. legal name, verification tier)."""

    __tablename__ = "kyc_profiles"

    customer_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    legal_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False, index=True
    )
    risk_tier: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    profile_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SanctionsWatchlistORM(Base):
    """Reference list for banned / restricted entities and high-risk jurisdictions."""

    __tablename__ = "sanctions_watchlist"

    entry_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    country_codes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    lists: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    risk_tier: Mapped[str] = mapped_column(String(32), default="HIGH", nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reference_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("idx_sanctions_watchlist_name", "display_name"),
        Index("idx_sanctions_watchlist_type_tier", "entry_type", "risk_tier"),
    )


class CountryRiskORM(Base):
    """Jurisdiction-level sanctions / risk reference (aligned with ``sanctions_data.json`` ``country_risks``)."""

    __tablename__ = "country_risks"

    country_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    country_name: Mapped[str] = mapped_column(String(256), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    sanctions_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FraudMemoryORM(Base):
    """Long-term structured history for RAG / retrieval-augmented context."""

    __tablename__ = "fraud_memory"

    memory_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    scope: Mapped[str] = mapped_column(String(32), default="customer", nullable=False, index=True)
    customer_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    embedding_ref: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (Index("idx_fraud_memory_scope_customer", "scope", "customer_id"),)


class AlertORM(Base):
    """Trigger row: links a transaction, KYC profile context, and optional watchlist hit."""

    __tablename__ = "alerts"

    alert_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    transaction_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("transactions.transaction_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("kyc_profiles.customer_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sanctions_watchlist_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("sanctions_watchlist.entry_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(String(64), default="composite", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    trigger_context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class TriageAssessmentORM(Base):
    """Agent triage snapshot: current analysis and risk score for an alert."""

    __tablename__ = "triage_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(
        ForeignKey("alerts.alert_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    assessment: Mapped[dict] = mapped_column(JSONB, nullable=False)
    agent_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (Index("idx_triage_alert_created", "alert_id", "created_at"),)


class InvestigationLogORM(Base):
    """Step-by-step agent reasoning tied to an alert (investigation narrative)."""

    __tablename__ = "investigation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(
        ForeignKey("alerts.alert_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(128), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    step_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        Index("idx_investigation_logs_alert_step", "alert_id", "step_index"),
    )


class AuditTrailORM(Base):
    """Human approval / rejection / override of agent or system decisions."""

    __tablename__ = "audit_trail"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    actor_user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    related_alert_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("alerts.alert_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    related_triage_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("triage_assessments.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        Index("idx_audit_trail_actor_time", "actor_user_id", "created_at"),
    )
