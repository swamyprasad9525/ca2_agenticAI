import uuid
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from sqlalchemy import String, Text, Numeric, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin


class Tender(Base, TimestampMixin):
    __tablename__ = "tenders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    issuing_organization: Mapped[str] = mapped_column(String(255), nullable=False)
    submission_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_budget: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False)

    # Relationships
    documents: Mapped[List["TenderDocument"]] = relationship("TenderDocument", back_populates="tender", cascade="all, delete-orphan")
    criteria: Mapped[List["EvaluationCriterion"]] = relationship("EvaluationCriterion", back_populates="tender", cascade="all, delete-orphan")
    mandatory_requirements: Mapped[List["MandatoryRequirement"]] = relationship("MandatoryRequirement", back_populates="tender", cascade="all, delete-orphan")
    bids: Mapped[List["Bid"]] = relationship("Bid", back_populates="tender", cascade="all, delete-orphan")
    evaluation_runs: Mapped[List["EvaluationRun"]] = relationship("EvaluationRun", back_populates="tender", cascade="all, delete-orphan")


class TenderDocument(Base, TimestampMixin):
    __tablename__ = "tender_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), default="TENDER_RFP", nullable=False)
    page_count: Mapped[int] = mapped_column(nullable=False, default=1)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    # Relationship
    tender: Mapped["Tender"] = relationship("Tender", back_populates="documents")

