from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from backend.app.schemas.evidence import EvidenceReferenceCreate, EvidenceReferenceRead
from backend.app.schemas.compliance import ComplianceResultRead


class ScoreTypeEnum(str, Enum):
    TECHNICAL = "TECHNICAL"
    COMMERCIAL = "COMMERCIAL"
    COMPOSITE = "COMPOSITE"


class ScorecardCreate(BaseModel):
    run_id: str
    vendor_id: str
    criterion_id: Optional[str] = None
    score_type: ScoreTypeEnum
    raw_points: Optional[Decimal] = None
    max_points: Optional[Decimal] = None
    weight: Optional[Decimal] = None
    weighted_score: Optional[Decimal] = None
    normalized_score: Optional[Decimal] = None
    rank: Optional[int] = None
    justification: Optional[str] = None
    version: int = 1
    idempotency_key: Optional[str] = None
    evidence: List[EvidenceReferenceCreate] = Field(default_factory=list)


class ScorecardRead(BaseModel):
    id: str
    run_id: str
    vendor_id: str
    criterion_id: Optional[str] = None
    score_type: str
    raw_points: Optional[Decimal] = None
    max_points: Optional[Decimal] = None
    weight: Optional[Decimal] = None
    weighted_score: Optional[Decimal] = None
    normalized_score: Optional[Decimal] = None
    rank: Optional[int] = None
    justification: Optional[str] = None
    version: int
    idempotency_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    evidence: List[EvidenceReferenceRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class VendorScorecardSummary(BaseModel):
    vendor_id: str
    vendor_name: str
    is_disqualified: bool = False
    disqualification_reasons: List[str] = Field(default_factory=list)
    requires_human_review: bool = False
    compliance_status: str = "PENDING"
    compliance_items: List[ComplianceResultRead] = Field(default_factory=list)
    technical_scores: List[ScorecardRead] = Field(default_factory=list)
    commercial_score: Optional[ScorecardRead] = None
    composite_score: Optional[Decimal] = None
    rank: Optional[int] = None


class SharedScorecardResponse(BaseModel):
    run_id: str
    tender_id: str
    status: str
    current_step: Optional[str] = None
    total_vendors: int = 0
    eligible_vendors_count: int = 0
    disqualified_vendors_count: int = 0
    vendor_summaries: List[VendorScorecardSummary] = Field(default_factory=list)
    agent_executions: List[Dict[str, Any]] = Field(default_factory=list)
    updated_at: datetime

