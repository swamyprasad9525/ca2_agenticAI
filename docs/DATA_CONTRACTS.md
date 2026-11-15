# Data Contracts — Tender and Procurement Evaluation System

## 1. Overview and Design Principles

This document specifies the authoritative, strictly typed data structures exchanged between the five specialised agents, the orchestrator, the deterministic scoring engine, the persistence layer, and the user interface.

### Design Principles:
1. **Pydantic v2 as Single Source of Truth**: All data contracts are expressed as Pydantic v2 `BaseModel` classes with explicit type annotations, constraints, field validators, and schema examples.
2. **Deterministic Immutability**: Intermediate data contracts emitted by agents are treated as immutable values.
3. **Mandatory Evidence Traceability**: No score or compliance verdict is valid without at least one verifiable `EvidenceReference`.
4. **Zero Untyped Dictionaries**: Internal APIs and agent handoffs forbid generic Python `dict` or `Any` objects.

---

## 2. Evidence Reference Contract

The fundamental citation schema attached to all factual assertions, compliance evaluations, and technical/commercial scores.

```python
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field

class EvidenceReference(BaseModel):
    """Verifiable citation linking an agent assertion to a source document."""
    document_id: UUID = Field(
        ...,
        description="Unique identifier of the source tender or bid document file"
    )
    document_name: str = Field(
        ...,
        min_length=1,
        description="Human-readable filename of the document (e.g. 'VendorA_Technical_Proposal.pdf')"
    )
    page_number: int = Field(
        ...,
        ge=1,
        description="1-based page number where the cited evidence appears in the source document"
    )
    section_reference: Optional[str] = Field(
        default=None,
        description="Clause or section identifier if present (e.g., 'Section 4.3.2 Cybersecurity SLA')"
    )
    verbatim_quote: str = Field(
        ...,
        min_length=5,
        description="Exact verbatim excerpt from the document supporting the finding"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Extraction confidence level (0.0 to 1.0)"
    )

    class Config:
        frozen = True
```

---

## 3. Tender & Document Contracts

```python
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, HttpUrl

class DocumentType(str, Enum):
    TENDER_RFP = "TENDER_RFP"
    TENDER_ADDENDUM = "TENDER_ADDENDUM"
    VENDOR_TECHNICAL_BID = "VENDOR_TECHNICAL_BID"
    VENDOR_COMMERCIAL_BID = "VENDOR_COMMERCIAL_BID"
    VENDOR_COMPLIANCE_CERT = "VENDOR_COMPLIANCE_CERT"

class DocumentMetadata(BaseModel):
    """Metadata for uploaded files processed by the RAG subsystem."""
    document_id: UUID = Field(default_factory=uuid4)
    filename: str = Field(..., min_length=1)
    file_path: str = Field(..., description="Internal storage path")
    document_type: DocumentType
    page_count: int = Field(..., ge=1)
    file_size_bytes: int = Field(..., ge=1)
    sha256_checksum: str = Field(..., min_length=64, max_length=64)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

class Tender(BaseModel):
    """Core entity representing a procurement tender or RFP."""
    tender_id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., min_length=3, max_length=255)
    reference_number: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(default=None)
    issuing_organization: str = Field(..., min_length=2, max_length=255)
    submission_deadline: Optional[datetime] = None
    estimated_budget: Optional[float] = Field(default=None, ge=0.0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    documents: List[DocumentMetadata] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## 4. Vendor & Bid Contracts

```python
class Vendor(BaseModel):
    """Entity representing a competing commercial bidder."""
    vendor_id: UUID = Field(default_factory=uuid4)
    vendor_name: str = Field(..., min_length=2, max_length=255)
    registration_number: Optional[str] = Field(default=None, max_length=100)
    contact_email: Optional[str] = Field(default=None)
    country: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Bid(BaseModel):
    """Entity linking a vendor's submitted bid to a specific tender."""
    bid_id: UUID = Field(default_factory=uuid4)
    tender_id: UUID
    vendor_id: UUID
    submission_timestamp: datetime = Field(default_factory=datetime.utcnow)
    documents: List[DocumentMetadata] = Field(default_factory=list)
```

---

## 5. Evaluation Criteria Specification (Criteria Agent Output)

```python
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator

class MandatoryRequirementCategory(str, Enum):
    LEGAL = "LEGAL"
    FINANCIAL = "FINANCIAL"
    TECHNICAL_ELIGIBILITY = "TECHNICAL_ELIGIBILITY"
    CERTIFICATION = "CERTIFICATION"
    SECURITY_CLEARANCE = "SECURITY_CLEARANCE"
    EXPERIENCE = "EXPERIENCE"

class MandatoryRequirement(BaseModel):
    """Strict Pass/Fail requirement extracted from the tender."""
    requirement_id: str = Field(..., description="Unique code e.g. 'MR-01'")
    category: MandatoryRequirementCategory
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=10)
    pass_criteria: str = Field(..., description="Explicit condition that constitutes a Pass")
    evidence_citation: Optional[EvidenceReference] = None

class TechnicalCriterion(BaseModel):
    """Scored qualitative technical evaluation criterion."""
    criterion_id: str = Field(..., description="Unique code e.g. 'TC-01'")
    section: str = Field(..., description="Section title or number, e.g. 'Architecture & Scalability'")
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=10)
    max_points: float = Field(..., gt=0.0, description="Maximum raw points available")
    weight: float = Field(..., gt=0.0, le=1.0, description="Relative weight within technical category (summing to 1.0)")
    scoring_rubric: str = Field(..., description="Guideline for awarding points (e.g. 0-25 Poor, 26-50 Good, 51-100 Excellent)")
    evidence_citation: Optional[EvidenceReference] = None

class CommercialFormulaType(str, Enum):
    RELATIVE_LOWEST_COST = "RELATIVE_LOWEST_COST"  # (LowestPrice / VendorPrice) * CommercialWeight
    LINEAR_INVERSE = "LINEAR_INVERSE"
    TIERED_FLAT = "TIERED_FLAT"
    TOTAL_COST_OF_OWNERSHIP = "TOTAL_COST_OF_OWNERSHIP"

class CommercialFormulaSpec(BaseModel):
    """Specification of the commercial evaluation rules."""
    formula_type: CommercialFormulaType = Field(default=CommercialFormulaType.RELATIVE_LOWEST_COST)
    formula_description: str = Field(...)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    required_line_items: List[str] = Field(default_factory=list)
    evidence_citation: Optional[EvidenceReference] = None

class TenderCriteriaSpec(BaseModel):
    """Complete evaluation rubric extracted by the Criteria Agent."""
    tender_id: UUID
    mandatory_requirements: List[MandatoryRequirement] = Field(..., min_length=1)
    technical_criteria: List[TechnicalCriterion] = Field(..., min_length=1)
    commercial_formula: CommercialFormulaSpec
    technical_weight: float = Field(..., gt=0.0, lt=1.0, description="Overall technical weight, e.g. 0.70")
    commercial_weight: float = Field(..., gt=0.0, lt=1.0, description="Overall commercial weight, e.g. 0.30")
    is_confirmed_by_human: bool = Field(default=False)
    extracted_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def validate_weights(self) -> "TenderCriteriaSpec":
        total_weight = self.technical_weight + self.commercial_weight
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Technical ({self.technical_weight}) and Commercial ({self.commercial_weight}) weights must sum to 1.0 (got {total_weight:.4f})")
        
        tech_subtotal = sum(c.weight for c in self.technical_criteria)
        if abs(tech_subtotal - 1.0) > 0.001:
            raise ValueError(f"Technical criteria individual weights must sum to 1.0 (got {tech_subtotal:.4f})")
        return self
```

---

## 6. Compliance Evaluation Contract (Compliance Agent Output)

```python
class ComplianceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNCLEAR = "UNCLEAR"

class ComplianceItem(BaseModel):
    """Assessment of a single mandatory requirement for a specific vendor."""
    requirement_id: str
    requirement_title: str
    status: ComplianceStatus
    findings: str = Field(..., min_length=5, description="Factual rationale for the status")
    evidence: Optional[EvidenceReference] = None
    requires_human_review: bool = Field(default=False)

class ComplianceResult(BaseModel):
    """Aggregate compliance dossier for a vendor."""
    vendor_id: UUID
    vendor_name: str
    items: List[ComplianceItem] = Field(..., min_length=1)
    is_disqualified: bool = Field(default=False)
    disqualification_reasons: List[str] = Field(default_factory=list)
    requires_human_review: bool = Field(default=False)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def compute_disqualification_and_flags(self) -> "ComplianceResult":
        has_fail = any(item.status == ComplianceStatus.FAIL for item in self.items)
        has_unclear = any(item.status == ComplianceStatus.UNCLEAR for item in self.items)
        
        if has_fail:
            self.is_disqualified = True
            self.disqualification_reasons = [
                f"{item.requirement_id} ({item.requirement_title}): {item.findings}"
                for item in self.items if item.status == ComplianceStatus.FAIL
            ]
        if has_unclear:
            self.requires_human_review = True
        return self
```

---

## 7. Technical Scoring Contract (Technical Scorer Output)

```python
class TechnicalCriterionScore(BaseModel):
    """Detailed score for one technical criterion."""
    criterion_id: str
    section: str
    title: str
    max_points: float = Field(..., gt=0.0)
    allocated_points: float = Field(..., ge=0.0)
    weight: float = Field(..., gt=0.0, le=1.0)
    weighted_score: float = Field(..., ge=0.0)
    justification: str = Field(..., min_length=10)
    evidence: List[EvidenceReference] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_points(self) -> "TechnicalCriterionScore":
        if self.allocated_points > self.max_points:
            raise ValueError(f"Allocated points ({self.allocated_points}) cannot exceed max points ({self.max_points})")
        return self

class TechnicalEvaluationResult(BaseModel):
    """Aggregate technical evaluation for a vendor."""
    vendor_id: UUID
    vendor_name: str
    criteria_scores: List[TechnicalCriterionScore] = Field(..., min_length=1)
    total_raw_points: float = Field(..., ge=0.0)
    max_possible_points: float = Field(..., gt=0.0)
    normalized_technical_score: float = Field(..., ge=0.0, le=100.0, description="Score on 0-100 scale")
    weighted_technical_score: float = Field(..., ge=0.0, description="Normalized score multiplied by tender technical weight")
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## 8. Commercial Scoring Contract (Commercial Scorer Output)

```python
class PricingScheduleItem(BaseModel):
    """Line-item breakdown from vendor commercial proposal."""
    item_name: str
    quantity: float = Field(default=1.0, gt=0.0)
    unit_price: float = Field(..., ge=0.0)
    total_price: float = Field(..., ge=0.0)
    currency: str = Field(default="USD")
    evidence: Optional[EvidenceReference] = None

class CommercialEvaluationResult(BaseModel):
    """Commercial evaluation output for a vendor."""
    vendor_id: UUID
    vendor_name: str
    total_bid_amount: float = Field(..., ge=0.0)
    currency: str = Field(default="USD")
    line_items: List[PricingScheduleItem] = Field(default_factory=list)
    calculated_commercial_score: float = Field(..., ge=0.0, le=100.0, description="Normalized score on 0-100 scale")
    weighted_commercial_score: float = Field(..., ge=0.0, description="Calculated score multiplied by tender commercial weight")
    anomalies_detected: List[str] = Field(default_factory=list)
    evidence: List[EvidenceReference] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## 9. Shared Scorecard Contract (Award Manager Input & Output)

```python
class VendorScorecard(BaseModel):
    """Comprehensive evaluation record for an individual vendor."""
    vendor_id: UUID
    vendor_name: str
    compliance_status: ComplianceStatus
    is_disqualified: bool
    disqualification_reasons: List[str] = Field(default_factory=list)
    compliance_result: ComplianceResult
    technical_result: Optional[TechnicalEvaluationResult] = None
    commercial_result: Optional[CommercialEvaluationResult] = None
    composite_score: float = Field(default=0.0, ge=0.0, le=100.0)
    rank: Optional[int] = Field(default=None, ge=1)
    key_strengths: List[str] = Field(default_factory=list)
    key_weaknesses: List[str] = Field(default_factory=list)
    delivery_risks: List[str] = Field(default_factory=list)

class EvaluationRunStatus(str, Enum):
    INITIALIZED = "INITIALIZED"
    EXTRACTING_CRITERIA = "EXTRACTING_CRITERIA"
    EVALUATING_COMPLIANCE = "EVALUATING_COMPLIANCE"
    SCORING_PROPOSALS = "SCORING_PROPOSALS"
    AGGREGATING_SCORECARD = "AGGREGATING_SCORECARD"
    AWAITING_HUMAN_APPROVAL = "AWAITING_HUMAN_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class SharedScorecardState(BaseModel):
    """Global persistent state of an entire tender evaluation run."""
    run_id: UUID = Field(default_factory=uuid4)
    tender_id: UUID
    status: EvaluationRunStatus = Field(default=EvaluationRunStatus.INITIALIZED)
    criteria_spec: Optional[TenderCriteriaSpec] = None
    vendor_scorecards: List[VendorScorecard] = Field(default_factory=list)
    eligible_vendors_count: int = Field(default=0)
    disqualified_vendors_count: int = Field(default=0)
    execution_logs: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## 10. Award Recommendation & Human Governance Contracts

```python
class RecommendationStatus(str, Enum):
    RECOMMENDED_AWAITING_APPROVAL = "RECOMMENDED_AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    OVERRIDDEN = "OVERRIDDEN"

class AwardRecommendation(BaseModel):
    """Formal recommendation dossier generated by the Award Manager."""
    recommendation_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    tender_id: UUID
    recommended_vendor_id: Optional[UUID] = None
    recommended_vendor_name: Optional[str] = None
    winning_composite_score: Optional[float] = None
    runner_up_vendor_id: Optional[UUID] = None
    runner_up_vendor_name: Optional[str] = None
    executive_summary: str = Field(..., min_length=20)
    award_justification: str = Field(..., min_length=20)
    risk_assessment: List[str] = Field(default_factory=list)
    status: RecommendationStatus = Field(default=RecommendationStatus.RECOMMENDED_AWAITING_APPROVAL)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class HumanSignOffDecision(str, Enum):
    APPROVE_AWARD = "APPROVE_AWARD"
    REJECT_ALL = "REJECT_ALL"
    OVERRIDE_WINNER = "OVERRIDE_WINNER"
    REQUEST_RE_EVALUATION = "REQUEST_RE_EVALUATION"

class HumanSignOffRecord(BaseModel):
    """Audit record capturing the human procurement officer's final decision."""
    sign_off_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    officer_name: str = Field(..., min_length=2)
    officer_role: str = Field(..., min_length=2)
    decision: HumanSignOffDecision
    selected_vendor_id: UUID = Field(..., description="The final approved vendor ID")
    justification_comments: str = Field(..., min_length=10)
    override_reason: Optional[str] = None
    signature_timestamp: datetime = Field(default_factory=datetime.utcnow)
```

