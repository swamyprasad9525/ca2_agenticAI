import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, Text, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin


class EvaluationRun(Base, TimestampMixin):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="INITIALIZED", nullable=False, index=True)
    current_step: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    eligible_vendors_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    disqualified_vendors_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    tender: Mapped["Tender"] = relationship("Tender", back_populates="evaluation_runs")
    agent_executions: Mapped[List["AgentExecution"]] = relationship("AgentExecution", back_populates="evaluation_run", cascade="all, delete-orphan")
    scorecards: Mapped[List["Scorecard"]] = relationship("Scorecard", back_populates="evaluation_run", cascade="all, delete-orphan")
    compliance_results: Mapped[List["ComplianceResult"]] = relationship("ComplianceResult", back_populates="evaluation_run", cascade="all, delete-orphan")
    award_recommendation: Mapped[Optional["AwardRecommendation"]] = relationship("AwardRecommendation", back_populates="evaluation_run", uselist=False, cascade="all, delete-orphan")


class AgentExecution(Base, TimestampMixin):
    __tablename__ = "agent_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)  # CriteriaAgent, ComplianceAgent, TechnicalScorer, CommercialScorer, AwardManager
    vendor_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)  # PENDING, RUNNING, COMPLETED, FAILED, RETRYING
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    evaluation_run: Mapped["EvaluationRun"] = relationship("EvaluationRun", back_populates="agent_executions")
    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor")


class AwardRecommendation(Base, TimestampMixin):
    __tablename__ = "award_recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    recommended_vendor_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    recommended_vendor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    winning_composite_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    runner_up_vendor_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    runner_up_vendor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    award_justification: Mapped[str] = mapped_column(Text, nullable=False)
    risk_assessment: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON-encoded list of risks
    status: Mapped[str] = mapped_column(String(50), default="RECOMMENDED_AWAITING_APPROVAL", nullable=False)

    # Governance Human Sign-Off fields
    officer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    officer_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    selected_vendor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    justification_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    signature_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    evaluation_run: Mapped["EvaluationRun"] = relationship("EvaluationRun", back_populates="award_recommendation")
    tender: Mapped["Tender"] = relationship("Tender")
    recommended_vendor: Mapped[Optional["Vendor"]] = relationship("Vendor", foreign_keys=[recommended_vendor_id])
    runner_up_vendor: Mapped[Optional["Vendor"]] = relationship("Vendor", foreign_keys=[runner_up_vendor_id])

