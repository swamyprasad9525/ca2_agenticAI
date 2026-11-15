import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator
from backend.app.schemas.evidence import EvidenceReferenceBase


class MandatoryRequirementCategory(str, Enum):
    LEGAL = "LEGAL"
    FINANCIAL = "FINANCIAL"
    TECHNICAL_ELIGIBILITY = "TECHNICAL_ELIGIBILITY"
    CERTIFICATION = "CERTIFICATION"
    SECURITY_CLEARANCE = "SECURITY_CLEARANCE"
    EXPERIENCE = "EXPERIENCE"


class MandatoryRequirementBase(BaseModel):
    requirement_code: str = Field(..., description="Unique code e.g. 'MR-01'")
    category: MandatoryRequirementCategory = MandatoryRequirementCategory.LEGAL
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=10)
    pass_criteria: str = Field(..., min_length=5)


class MandatoryRequirementCreate(MandatoryRequirementBase):
    pass


class MandatoryRequirementRead(MandatoryRequirementBase):
    id: str
    tender_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CriterionType(str, Enum):
    TECHNICAL = "TECHNICAL"
    COMMERCIAL = "COMMERCIAL"


class EvaluationCriterionBase(BaseModel):
    criterion_code: str = Field(..., description="Unique code e.g. 'TC-01'")
    criterion_type: CriterionType = CriterionType.TECHNICAL
    section: str = Field(..., description="Section e.g. 'Architecture & Scalability'")
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=10)
    max_points: Decimal = Field(..., gt=Decimal("0.0"))
    weight: Decimal = Field(..., gt=Decimal("0.0"), le=Decimal("1.0"))
    scoring_rubric: str = Field(..., min_length=10)


class EvaluationCriterionCreate(EvaluationCriterionBase):
    pass


class EvaluationCriterionRead(EvaluationCriterionBase):
    id: str
    tender_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommercialFormulaType(str, Enum):
    RELATIVE_LOWEST_COST = "RELATIVE_LOWEST_COST"
    LINEAR_INVERSE = "LINEAR_INVERSE"
    TIERED_FLAT = "TIERED_FLAT"
    TOTAL_COST_OF_OWNERSHIP = "TOTAL_COST_OF_OWNERSHIP"


class CommercialFormulaSpec(BaseModel):
    formula_type: CommercialFormulaType = CommercialFormulaType.RELATIVE_LOWEST_COST
    formula_description: str
    currency: str = "USD"
    required_line_items: List[str] = Field(default_factory=list)


class EvaluationPlanDTO(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tender_id: str
    version: int = 1
    technical_weight: Decimal = Decimal("0.70")
    commercial_weight: Decimal = Decimal("0.30")
    minimum_technical_qualifying_score: Optional[Decimal] = Decimal("70.0")
    mandatory_requirements: List[MandatoryRequirementCreate] = Field(default_factory=list)
    technical_criteria: List[EvaluationCriterionCreate] = Field(default_factory=list)
    commercial_formula: CommercialFormulaSpec
    tie_breaking_rule: Optional[str] = "Highest technical score breaks ties"
    disqualification_rules: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    evidence_citations: List[EvidenceReferenceBase] = Field(default_factory=list)
    is_approved_by_human: bool = False
    approved_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def validate_weights_sum(self) -> "EvaluationPlanDTO":
        eff_tech = self.technical_weight if self.technical_weight <= Decimal("1.0") else (self.technical_weight / Decimal("100.0"))
        eff_comm = self.commercial_weight if self.commercial_weight <= Decimal("1.0") else (self.commercial_weight / Decimal("100.0"))
        total = eff_tech + eff_comm
        if abs(total - Decimal("1.0")) > Decimal("0.0001"):
            raise ValueError(f"Technical weight and commercial weight must sum to 1.0 (got {total})")
        return self


TenderCriteriaSpec = EvaluationPlanDTO


class EvaluationPlanApprovalRequest(BaseModel):
    approved_by: str = Field(..., min_length=2)
    decision: str = Field(default="APPROVED")  # APPROVED or REJECTED
    comments: Optional[str] = None
    adjusted_technical_weight: Optional[Decimal] = None
    adjusted_commercial_weight: Optional[Decimal] = None

