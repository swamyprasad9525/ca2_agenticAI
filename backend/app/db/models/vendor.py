import uuid
from typing import List, Optional
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin


class Vendor(Base, TimestampMixin):
    __tablename__ = "vendors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    registration_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    bids: Mapped[List["Bid"]] = relationship("Bid", back_populates="vendor", cascade="all, delete-orphan")
    scorecards: Mapped[List["Scorecard"]] = relationship("Scorecard", back_populates="vendor", cascade="all, delete-orphan")
    compliance_results: Mapped[List["ComplianceResult"]] = relationship("ComplianceResult", back_populates="vendor", cascade="all, delete-orphan")

