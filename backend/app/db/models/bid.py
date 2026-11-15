import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, DateTime, Numeric, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin


class Bid(Base, TimestampMixin):
    __tablename__ = "bids"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id: Mapped[str] = mapped_column(String(36), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    submission_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    total_quoted_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="SUBMITTED", nullable=False)

    # Relationships
    tender: Mapped["Tender"] = relationship("Tender", back_populates="bids")
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="bids")
    documents: Mapped[List["BidDocument"]] = relationship("BidDocument", back_populates="bid", cascade="all, delete-orphan")


class BidDocument(Base, TimestampMixin):
    __tablename__ = "bid_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    bid_id: Mapped[str] = mapped_column(String(36), ForeignKey("bids.id", ondelete="CASCADE"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), default="TECHNICAL_BID", nullable=False)
    page_count: Mapped[int] = mapped_column(nullable=False, default=1)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    # Relationship
    bid: Mapped["Bid"] = relationship("Bid", back_populates="documents")

