import uuid
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, Text, Integer, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin


class Scorecard(Base, TimestampMixin):
    __tablename__ = "scorecards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id: Mapped[str] = mapped_column(String(36), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("evaluation_criteria.id", ondelete="SET NULL"), nullable=True, index=True)
    score_type: Mapped[str] = mapped_column(String(50), nullable=False)  # TECHNICAL, COMMERCIAL, COMPOSITE
    raw_points: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    max_points: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    weighted_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    normalized_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)  # Scale of 0-100
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)

    # Relationships
    evaluation_run: Mapped["EvaluationRun"] = relationship("EvaluationRun", back_populates="scorecards")
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="scorecards")
    criterion: Mapped[Optional["EvaluationCriterion"]] = relationship("EvaluationCriterion", back_populates="scorecards")
    evidence: Mapped[List["EvidenceReference"]] = relationship("EvidenceReference", back_populates="scorecard", cascade="all, delete-orphan")

