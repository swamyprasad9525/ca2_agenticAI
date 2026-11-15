from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.schemas.evidence import EvidenceReferenceCreate, EvidenceReferenceRead


class ComplianceStatusEnum(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNCLEAR = "UNCLEAR"


class ComplianceResultBase(BaseModel):
    run_id: str
    vendor_id: str
    requirement_id: str
    status: ComplianceStatusEnum
    findings: str = Field(..., min_length=5)
    is_disqualified: bool = False
    requires_human_review: bool = False
    idempotency_key: Optional[str] = None


class ComplianceResultCreate(ComplianceResultBase):
    evidence: List[EvidenceReferenceCreate] = Field(default_factory=list)


class ComplianceResultRead(ComplianceResultBase):
    id: str
    created_at: datetime
    evidence: List[EvidenceReferenceRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

