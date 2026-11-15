from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class EvidenceReferenceBase(BaseModel):
    document_id: str = Field(..., description="ID of the source document")
    document_name: str = Field(..., min_length=1, description="Filename of the source document")
    page_number: int = Field(..., ge=1, description="Page number where the evidence is cited")
    section_reference: Optional[str] = Field(default=None, description="Section heading or clause")
    verbatim_quote: str = Field(..., min_length=5, description="Exact verbatim text from the document")
    confidence_score: Decimal = Field(default=Decimal("1.0000"), ge=Decimal("0.0"), le=Decimal("1.0"))


class EvidenceReferenceCreate(EvidenceReferenceBase):
    pass


class EvidenceReferenceRead(EvidenceReferenceBase):
    id: str
    compliance_result_id: Optional[str] = None
    scorecard_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

