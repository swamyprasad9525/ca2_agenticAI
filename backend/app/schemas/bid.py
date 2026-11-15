from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.schemas.vendor import VendorRead


class BidDocumentRead(BaseModel):
    id: str
    bid_id: str
    filename: str
    file_path: str
    document_type: str
    page_count: int
    file_size_bytes: int
    sha256_checksum: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BidBase(BaseModel):
    tender_id: str
    vendor_id: str
    total_quoted_price: Optional[Decimal] = Field(default=None, ge=Decimal("0.0"))
    currency: str = Field(default="USD", min_length=3, max_length=3)


class BidCreate(BidBase):
    pass


class BidRead(BidBase):
    id: str
    submission_timestamp: datetime
    status: str
    created_at: datetime
    updated_at: datetime
    documents: List[BidDocumentRead] = Field(default_factory=list)
    vendor: Optional[VendorRead] = None

    model_config = ConfigDict(from_attributes=True)

