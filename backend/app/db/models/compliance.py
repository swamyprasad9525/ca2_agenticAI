import uuid
from typing import List, Optional
from sqlalchemy import String, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin


class ComplianceResult(Base, TimestampMixin):
    __tablename__ = "compliance_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id: Mapped[str] = mapped_column(String(36), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_id: Mapped[str] = mapped_column(String(36), ForeignKey("mandatory_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # PASS, FAIL, UNCLEAR
    findings: Mapped[str] = mapped_column(Text, nullable=False)
    is_disqualified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)

    # Relationships
    evaluation_run: Mapped["EvaluationRun"] = relationship("EvaluationRun", back_populates="compliance_results")
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="compliance_results")
    mandatory_requirement: Mapped["MandatoryRequirement"] = relationship("MandatoryRequirement", back_populates="compliance_results")
    evidence: Mapped[List["EvidenceReference"]] = relationship("EvidenceReference", back_populates="compliance_result", cascade="all, delete-orphan")

