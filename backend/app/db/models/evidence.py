import uuid
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Text, Integer, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin


class EvidenceReference(Base, TimestampMixin):
    __tablename__ = "evidence_references"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    section_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verbatim_quote: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("1.0000"))

    # Foreign keys for parent associations
    compliance_result_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("compliance_results.id", ondelete="CASCADE"), nullable=True, index=True
    )
    scorecard_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("scorecards.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Relationships
    compliance_result: Mapped[Optional["ComplianceResult"]] = relationship("ComplianceResult", back_populates="evidence")
    scorecard: Mapped[Optional["Scorecard"]] = relationship("Scorecard", back_populates="evidence")

