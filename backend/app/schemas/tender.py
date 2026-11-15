from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.schemas.criteria import MandatoryRequirementRead, EvaluationCriterionRead


class TenderDocumentRead(BaseModel):
    id: str
    tender_id: str
    filename: str
    file_path: str
    document_type: str
    page_count: int
    file_size_bytes: int
    sha256_checksum: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenderBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    reference_number: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    issuing_organization: str = Field(..., min_length=2, max_length=255)
    submission_deadline: Optional[datetime] = None
    estimated_budget: Optional[Decimal] = Field(default=None, ge=Decimal("0.0"))
    currency: str = Field(default="USD", min_length=3, max_length=3)


class TenderCreate(TenderBase):
    pass


class TenderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    issuing_organization: Optional[str] = None
    submission_deadline: Optional[datetime] = None
    estimated_budget: Optional[Decimal] = None
    currency: Optional[str] = None
    status: Optional[str] = None


class TenderRead(TenderBase):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime
    documents: List[TenderDocumentRead] = Field(default_factory=list)
    criteria: List[EvaluationCriterionRead] = Field(default_factory=list)
    mandatory_requirements: List[MandatoryRequirementRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

