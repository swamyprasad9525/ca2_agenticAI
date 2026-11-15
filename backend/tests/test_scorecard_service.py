import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.tender import Tender
from backend.app.db.models.vendor import Vendor
from backend.app.db.models.criteria import MandatoryRequirement
from backend.app.repositories.tender_repo import TenderRepository
from backend.app.repositories.vendor_repo import VendorRepository
from backend.app.services.scorecard_service import ScorecardService
from backend.app.schemas.compliance import ComplianceResultCreate, ComplianceStatusEnum
from backend.app.schemas.scorecard import ScorecardCreate, ScoreTypeEnum
from backend.app.schemas.evidence import EvidenceReferenceCreate


@pytest.mark.asyncio
async def test_scorecard_service_end_to_end(db_session: AsyncSession):
    service = ScorecardService(db_session)
    t_repo = TenderRepository(db_session)
    v_repo = VendorRepository(db_session)

    # 1. Setup Tender and Mandatory Requirement
    tender = await t_repo.create(
        Tender(
            title="Enterprise Cybersecurity RFP",
            reference_number="RFP-SEC-99",
            issuing_organization="Cyber Command",
        )
    )
    req = MandatoryRequirement(
        tender_id=tender.id,
        requirement_code="MR-01",
        category="SECURITY_CLEARANCE",
        title="SOC2 Type II",
        description="Vendor must hold active SOC2 Type II certification",
        pass_criteria="Certificate verification",
    )
    db_session.add(req)
    await db_session.flush()

    # 2. Setup 2 Vendors
    v1 = await v_repo.create(Vendor(name="SecureCorp", registration_number="SC-001"))
    v2 = await v_repo.create(Vendor(name="InsecureLLC", registration_number="IL-002"))

    # 3. Initialize Evaluation Run
    run_read = await service.initialize_run(tender.id)
    assert run_read.status == "INITIALIZED"
    run_id = run_read.id

    # 4. Record Agent Execution Telemetry
    ag_exec = await service.start_agent_execution(
        run_id=run_id,
        agent_name="ComplianceAgent",
        vendor_id=v1.id,
        idempotency_key="comp-v1",
    )
    assert ag_exec.status == "RUNNING"

    await service.complete_agent_execution(
        execution_id=ag_exec.id,
        status="COMPLETED",
        execution_log="Verified SOC2 certification from official audit report page 4.",
    )

    # 5. Record Compliance Results
    # Vendor 1: PASS
    await service.record_compliance_result(
        ComplianceResultCreate(
            run_id=run_id,
            vendor_id=v1.id,
            requirement_id=req.id,
            status=ComplianceStatusEnum.PASS,
            findings="Valid SOC2 Type II certificate verified through KPMG report.",
            is_disqualified=False,
            idempotency_key=f"comp-{v1.id}-{req.id}",
            evidence=[
                EvidenceReferenceCreate(
                    document_id="doc-v1",
                    document_name="Audit_Report.pdf",
                    page_number=4,
                    section_reference="Section 1.3 Scope",
                    verbatim_quote="KPMG has audited and verified SOC2 Type II controls.",
                    confidence_score=Decimal("1.0000"),
                )
            ],
        )
    )

    # Vendor 2: FAIL (Disqualified)
    await service.record_compliance_result(
        ComplianceResultCreate(
            run_id=run_id,
            vendor_id=v2.id,
            requirement_id=req.id,
            status=ComplianceStatusEnum.FAIL,
            findings="Vendor did not provide any SOC2 Type II certificate.",
            is_disqualified=True,
            idempotency_key=f"comp-{v2.id}-{req.id}",
            evidence=[
                EvidenceReferenceCreate(
                    document_id="doc-v2",
                    document_name="Proposal.pdf",
                    page_number=2,
                    section_reference="Executive Summary",
                    verbatim_quote="We are currently in progress towards SOC2 compliance.",
                    confidence_score=Decimal("0.9500"),
                )
            ],
        )
    )

    # 6. Record Scorecard Entries for Compliant Vendor 1
    await service.record_scorecard_entry(
        ScorecardCreate(
            run_id=run_id,
            vendor_id=v1.id,
            score_type=ScoreTypeEnum.TECHNICAL,
            raw_points=Decimal("88.00"),
            max_points=Decimal("100.00"),
            weight=Decimal("0.7000"),
            weighted_score=Decimal("61.6000"),
            normalized_score=Decimal("88.0000"),
            justification="Excellent zero-trust architecture.",
            idempotency_key=f"score-tech-{v1.id}",
        )
    )

    await service.record_scorecard_entry(
        ScorecardCreate(
            run_id=run_id,
            vendor_id=v1.id,
            score_type=ScoreTypeEnum.COMMERCIAL,
            raw_points=Decimal("95.00"),
            max_points=Decimal("100.00"),
            weight=Decimal("0.3000"),
            weighted_score=Decimal("28.5000"),
            normalized_score=Decimal("95.0000"),
            justification="Lowest pricing submitted.",
            idempotency_key=f"score-comm-{v1.id}",
        )
    )

    await service.record_scorecard_entry(
        ScorecardCreate(
            run_id=run_id,
            vendor_id=v1.id,
            score_type=ScoreTypeEnum.COMPOSITE,
            raw_points=Decimal("90.10"),
            max_points=Decimal("100.00"),
            normalized_score=Decimal("90.1000"),
            rank=1,
            justification="Composite score: 61.60 + 28.50 = 90.10",
            idempotency_key=f"score-comp-{v1.id}",
        )
    )

    # 7. Retrieve Global Shared Scorecard
    scorecard = await service.get_shared_scorecard(run_id)
    assert scorecard.total_vendors == 2
    assert scorecard.eligible_vendors_count == 1
    assert scorecard.disqualified_vendors_count == 1

    # Verify Vendor 1 summary
    v1_summary = next(s for s in scorecard.vendor_summaries if s.vendor_id == v1.id)
    assert v1_summary.compliance_status == "PASSED"
    assert v1_summary.is_disqualified is False
    assert v1_summary.composite_score == Decimal("90.1000")
    assert v1_summary.rank == 1

    # Verify Vendor 2 summary
    v2_summary = next(s for s in scorecard.vendor_summaries if s.vendor_id == v2.id)
    assert v2_summary.compliance_status == "DISQUALIFIED"
    assert v2_summary.is_disqualified is True

