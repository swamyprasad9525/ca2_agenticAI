import pytest
from decimal import Decimal
from pydantic import ValidationError

from backend.app.schemas.evidence import EvidenceReferenceBase
from backend.app.schemas.criteria import (
    TenderCriteriaSpec,
    MandatoryRequirementCreate,
    EvaluationCriterionCreate,
    CommercialFormulaSpec,
    CommercialFormulaType,
    MandatoryRequirementCategory,
)
from backend.app.schemas.compliance import (
    ComplianceResultCreate,
    ComplianceStatusEnum,
)
from backend.app.schemas.scorecard import (
    ScorecardCreate,
    ScoreTypeEnum,
)


def test_evidence_reference_valid():
    ev = EvidenceReferenceBase(
        document_id="doc-123",
        document_name="Proposal.pdf",
        page_number=14,
        section_reference="Section 3.2",
        verbatim_quote="We guarantee 99.99% uptime with 24/7 on-call engineers.",
        confidence_score=Decimal("0.98"),
    )
    assert ev.page_number == 14
    assert ev.confidence_score == Decimal("0.98")


def test_evidence_reference_invalid_page():
    with pytest.raises(ValidationError):
        EvidenceReferenceBase(
            document_id="doc-123",
            document_name="Proposal.pdf",
            page_number=0,  # Invalid: ge=1
            verbatim_quote="Too short",
            confidence_score=Decimal("1.0"),
        )


def test_tender_criteria_spec_weights_valid():
    spec = TenderCriteriaSpec(
        tender_id="tender-1",
        mandatory_requirements=[
            MandatoryRequirementCreate(
                requirement_code="MR-01",
                category=MandatoryRequirementCategory.CERTIFICATION,
                title="ISO 27001",
                description="Must possess valid ISO 27001 certificate",
                pass_criteria="Valid certificate provided",
            )
        ],
        technical_criteria=[
            EvaluationCriterionCreate(
                criterion_code="TC-01",
                section="Architecture",
                title="Cloud Scalability",
                description="Auto-scaling cloud infrastructure",
                max_points=Decimal("50.0"),
                weight=Decimal("0.60"),
                scoring_rubric="Rubric details here",
            ),
            EvaluationCriterionCreate(
                criterion_code="TC-02",
                section="SLA",
                title="Incident Response",
                description="SLA response commitments",
                max_points=Decimal("50.0"),
                weight=Decimal("0.40"),
                scoring_rubric="Rubric details here",
            ),
        ],
        commercial_formula=CommercialFormulaSpec(
            formula_type=CommercialFormulaType.RELATIVE_LOWEST_COST,
            formula_description="Lowest / Vendor * Weight",
        ),
        technical_weight=Decimal("0.70"),
        commercial_weight=Decimal("0.30"),
    )
    assert spec.technical_weight + spec.commercial_weight == Decimal("1.0")


def test_tender_criteria_spec_weights_invalid_total():
    with pytest.raises(ValidationError) as exc_info:
        TenderCriteriaSpec(
            tender_id="tender-1",
            mandatory_requirements=[
                MandatoryRequirementCreate(
                    requirement_code="MR-01",
                    category=MandatoryRequirementCategory.LEGAL,
                    title="Business License",
                    description="Valid business license in jurisdiction",
                    pass_criteria="License document present",
                )
            ],
            technical_criteria=[
                EvaluationCriterionCreate(
                    criterion_code="TC-01",
                    section="Architecture",
                    title="Cloud Scalability",
                    description="Auto-scaling cloud infrastructure",
                    max_points=Decimal("100.0"),
                    weight=Decimal("1.0"),
                    scoring_rubric="Rubric details here",
                )
            ],
            commercial_formula=CommercialFormulaSpec(
                formula_type=CommercialFormulaType.RELATIVE_LOWEST_COST,
                formula_description="Formula description",
            ),
            technical_weight=Decimal("0.80"),
            commercial_weight=Decimal("0.40"),  # Sums to 1.20 -> invalid!
        )
    assert "must sum to 1.0" in str(exc_info.value)


def test_compliance_result_create():
    comp = ComplianceResultCreate(
        run_id="run-1",
        vendor_id="vendor-1",
        requirement_id="req-1",
        status=ComplianceStatusEnum.FAIL,
        findings="Vendor does not possess ISO 27001 certification",
        is_disqualified=True,
    )
    assert comp.is_disqualified is True
    assert comp.status == ComplianceStatusEnum.FAIL


def test_scorecard_create_valid():
    entry = ScorecardCreate(
        run_id="run-1",
        vendor_id="vendor-1",
        criterion_id="tc-1",
        score_type=ScoreTypeEnum.TECHNICAL,
        raw_points=Decimal("45.0"),
        max_points=Decimal("50.0"),
        weight=Decimal("0.50"),
        weighted_score=Decimal("22.50"),
        normalized_score=Decimal("90.0"),
        justification="Comprehensive high-availability architecture with cross-region replication.",
    )
    assert entry.raw_points == Decimal("45.0")
    assert entry.score_type == ScoreTypeEnum.TECHNICAL

