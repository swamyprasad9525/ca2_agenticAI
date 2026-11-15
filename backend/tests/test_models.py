import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.db.models.tender import Tender, TenderDocument
from backend.app.db.models.vendor import Vendor
from backend.app.db.models.bid import Bid, BidDocument
from backend.app.db.models.criteria import MandatoryRequirement, EvaluationCriterion
from backend.app.db.models.execution import EvaluationRun, AgentExecution
from backend.app.db.models.compliance import ComplianceResult
from backend.app.db.models.scorecard import Scorecard
from backend.app.db.models.evidence import EvidenceReference


@pytest.mark.asyncio
async def test_create_tender_and_relations(db_session: AsyncSession):
    tender = Tender(
        title="Smart City IoT RFP",
        reference_number="RFP-2026-IOT-01",
        issuing_organization="City of Innovation",
        estimated_budget=Decimal("1250000.50"),
        currency="USD",
    )
    db_session.add(tender)
    await db_session.flush()

    # Add document
    doc = TenderDocument(
        tender_id=tender.id,
        filename="RFP_Specification.pdf",
        file_path="/uploads/test.pdf",
        document_type="TENDER_RFP",
        page_count=35,
        file_size_bytes=450000,
        sha256_checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )
    db_session.add(doc)

    # Add criteria
    tc = EvaluationCriterion(
        tender_id=tender.id,
        criterion_code="TC-01",
        criterion_type="TECHNICAL",
        section="Architecture",
        title="Sensor Mesh Scalability",
        description="Scalable IoT gateway mesh",
        max_points=Decimal("100.00"),
        weight=Decimal("1.0000"),
        scoring_rubric="Full points for dynamic routing",
    )
    db_session.add(tc)

    mr = MandatoryRequirement(
        tender_id=tender.id,
        requirement_code="MR-01",
        category="LEGAL",
        title="Telecom License",
        description="Must hold telecommunications operating license",
        pass_criteria="Valid official license document",
    )
    db_session.add(mr)

    await db_session.commit()

    # Verify retrieval
    res = await db_session.execute(select(Tender).where(Tender.id == tender.id))
    retrieved = res.scalars().first()
    assert retrieved is not None
    assert retrieved.estimated_budget == Decimal("1250000.50")
    assert retrieved.reference_number == "RFP-2026-IOT-01"


@pytest.mark.asyncio
async def test_vendor_bid_and_scorecard_lifecycle(db_session: AsyncSession):
    # 1. Tender
    tender = Tender(
        title="Network Upgrade RFP",
        reference_number="RFP-NET-01",
        issuing_organization="Telecom Corp",
    )
    db_session.add(tender)

    # 2. Vendor
    vendor = Vendor(
        name="Cisco Partner Inc",
        registration_number="REG-778899",
        contact_email="bids@ciscopartner.com",
    )
    db_session.add(vendor)
    await db_session.flush()

    # 3. Bid
    bid = Bid(
        tender_id=tender.id,
        vendor_id=vendor.id,
        total_quoted_price=Decimal("890000.00"),
        currency="USD",
    )
    db_session.add(bid)

    # 4. Evaluation Run
    run = EvaluationRun(tender_id=tender.id, status="RUNNING")
    db_session.add(run)
    await db_session.flush()

    # 5. Agent Execution
    agent_exec = AgentExecution(
        run_id=run.id,
        agent_name="CriteriaAgent",
        status="COMPLETED",
        idempotency_key="key-criteria-1",
    )
    db_session.add(agent_exec)

    # 6. Scorecard entry with evidence
    scorecard = Scorecard(
        run_id=run.id,
        vendor_id=vendor.id,
        score_type="TECHNICAL",
        raw_points=Decimal("92.50"),
        max_points=Decimal("100.00"),
        weight=Decimal("0.7000"),
        weighted_score=Decimal("64.7500"),
        normalized_score=Decimal("92.5000"),
        version=1,
    )
    db_session.add(scorecard)
    await db_session.flush()

    ev = EvidenceReference(
        document_id="doc-bid-1",
        document_name="Technical_Proposal.pdf",
        page_number=18,
        section_reference="Section 4.1 Topology",
        verbatim_quote="Dual redundant 10Gbps uplinks with automated failover under 50ms.",
        confidence_score=Decimal("0.9900"),
        scorecard_id=scorecard.id,
    )
    db_session.add(ev)

    await db_session.commit()

    # Verify
    stmt = select(Scorecard).where(Scorecard.id == scorecard.id)
    retrieved = (await db_session.execute(stmt)).scalars().first()
    assert retrieved is not None
    assert retrieved.weighted_score == Decimal("64.7500")

