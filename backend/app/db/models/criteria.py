import uuid
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, Text, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin


class MandatoryRequirement(Base, TimestampMixin):
    __tablename__ = "mandatory_requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_code: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="LEGAL", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    pass_criteria: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    tender: Mapped["Tender"] = relationship("Tender", back_populates="mandatory_requirements")
    compliance_results: Mapped[List["ComplianceResult"]] = relationship("ComplianceResult", back_populates="mandatory_requirement", cascade="all, delete-orphan")


class EvaluationCriterion(Base, TimestampMixin):
    __tablename__ = "evaluation_criteria"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion_code: Mapped[str] = mapped_column(String(50), nullable=False)
    criterion_type: Mapped[str] = mapped_column(String(50), default="TECHNICAL", nullable=False)  # TECHNICAL or COMMERCIAL
    section: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    max_points: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)  # 0.0000 to 1.0000
    scoring_rubric: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    tender: Mapped["Tender"] = relationship("Tender", back_populates="criteria")
    scorecards: Mapped[List["Scorecard"]] = relationship("Scorecard", back_populates="criterion", cascade="all, delete-orphan")


class EvaluationPlan(Base, TimestampMixin):
    __tablename__ = "evaluation_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    technical_weight: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False, default=Decimal("0.7000"))
    commercial_weight: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False, default=Decimal("0.3000"))
    min_technical_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    price_methodology: Mapped[str] = mapped_column(String(100), default="RELATIVE_LOWEST_COST", nullable=False)
    price_formula_desc: Mapped[str] = mapped_column(Text, default="Price Score = (Lowest Price / Vendor Price) * 100", nullable=False)
    tie_breaking_rule: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_approved: Mapped[bool] = mapped_column(nullable=False, default=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    plan_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON representation of criteria & citations

