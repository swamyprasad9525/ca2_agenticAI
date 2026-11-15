import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.app.db.base import Base
from backend.app.db.models.tender import Tender
from backend.app.db.models.vendor import Vendor
from backend.app.db.models.bid import Bid
from backend.app.rag.chunker import DocumentChunk
from backend.app.rag.vector_store import HybridPersistentVectorStore
from backend.app.rag.retriever import HybridRetriever
from backend.app.services.scorecard_service import ScorecardService
from backend.app.services.report_service import ReportService
from backend.app.orchestrator.evaluation_orchestrator import EvaluationOrchestrator
from backend.app.schemas.award import (
    AwardRecommendationStatusEnum,
    HumanSignOffRequest,
    HumanSignOffDecisionEnum,
)


@pytest.fixture
async def demo_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_four_vendor_e2e_procurement_lifecycle(demo_db, tmp_path):
    """
    End-to-End Multi-Agent Procurement Demonstration:
    4 Synthetic Vendors:
    - Vendor A (Alpha Cloud Systems): Winner (Rank 1) - Superior tech, compliant, competitive price.
    - Vendor B (Beta Data Solutions): Runner-Up (Rank 2) - Good tech, compliant, higher price.
    - Vendor C (Gamma Network Innovations): Flagged for Human Review - Unclear ISO audit proof.
    - Vendor D (Delta Legacy Technologies): Disqualified - Missing mandatory security certificate.
    """
    # -------------------------------------------------------------
    # 1. Setup RAG Vector Store and Seed Tender & Bids
    # -------------------------------------------------------------
    vector_store = HybridPersistentVectorStore(persist_path=str(tmp_path / "e2e_vec.json"))
    retriever = HybridRetriever(vector_store)

    tender_id = "TND-E2E-2026-GOV"
    va_id = "v-alpha-01"
    vb_id = "v-beta-02"
    vc_id = "v-gamma-03"
    vd_id = "v-delta-04"

    # Tender Document RAG Chunks (Specification)
    await vector_store.add_chunks([
        DocumentChunk(
            chunk_id="chunk-tender-spec-01",
            document_id="doc-tender-spec",
            document_name="National_Cloud_RFP.pdf",
            page_number=2,
            section_heading="Section 3: Mandatory Eligibility Requirements",
            text=(
                "All participating bidders must submit proof of valid corporate registration "
                "and an active ISO 27001 Information Security Management Certification. "
                "Failure to provide these documents shall result in immediate disqualification."
            ),
            metadata={"tender_id": tender_id, "document_type": "TENDER"},
        ),
        DocumentChunk(
            chunk_id="chunk-tender-spec-02",
            document_id="doc-tender-spec",
            document_name="National_Cloud_RFP.pdf",
            page_number=4,
            section_heading="Section 4: Technical & Commercial Criteria",
            text=(
                "Evaluation Weights: Technical Capability: 70%, Commercial Pricing: 30%.\n"
                "Technical Criteria:\n"
                "| TC-01 | Cloud Architecture & Fault Tolerance | 40 |\n"
                "| TC-02 | Service Level Agreements & 24/7 Operations | 30 |\n"
                "| TC-03 | Enterprise Migration Track Record | 30 |\n"
                "Commercial Evaluation: Relative Lowest Price Scoring Methodology."
            ),
            metadata={"tender_id": tender_id, "document_type": "TENDER"},
        ),
    ])

    # Vendor A (Alpha Cloud Systems): High tech, compliant, $3.1M
    await vector_store.add_chunks([
        DocumentChunk(
            chunk_id="chunk-va-01",
            document_id="doc-va-01",
            document_name="Alpha_Proposal.pdf",
            page_number=1,
            section_heading="Mandatory Compliance Dossier",
            text="Alpha Cloud Systems holds valid corporate registration and certified ISO 27001 accredited compliance.",
            metadata={"tender_id": tender_id, "vendor_id": va_id, "document_type": "BID_PROPOSAL"},
        ),
        DocumentChunk(
            chunk_id="chunk-va-02",
            document_id="doc-va-01",
            document_name="Alpha_Proposal.pdf",
            page_number=5,
            section_heading="System Architecture & Scalability",
            text="Active-active multi-region Kubernetes cluster with automated failover and 99.99% uptime availability SLA.",
            metadata={"tender_id": tender_id, "vendor_id": va_id, "document_type": "BID_PROPOSAL"},
        ),
        DocumentChunk(
            chunk_id="chunk-va-03",
            document_id="doc-va-02",
            document_name="Alpha_Commercial.pdf",
            page_number=1,
            section_heading="Financial Proposal",
            text="Total turnkey contract price: USD 3,100,000 all inclusive.",
            metadata={"tender_id": tender_id, "vendor_id": va_id, "document_type": "COMMERCIAL_QUOTE"},
        ),
    ])

    # Vendor B (Beta Data Solutions): Solid tech, compliant, $3.7M
    await vector_store.add_chunks([
        DocumentChunk(
            chunk_id="chunk-vb-01",
            document_id="doc-vb-01",
            document_name="Beta_Proposal.pdf",
            page_number=1,
            section_heading="Corporate Credentials",
            text="Beta Data Solutions is registered in good standing and possesses ISO 27001 certified data operations.",
            metadata={"tender_id": tender_id, "vendor_id": vb_id, "document_type": "BID_PROPOSAL"},
        ),
        DocumentChunk(
            chunk_id="chunk-vb-02",
            document_id="doc-vb-01",
            document_name="Beta_Proposal.pdf",
            page_number=3,
            section_heading="Architecture Overview",
            text="Standard multi-zone cloud infrastructure providing 99.9% uptime SLA response commitments.",
            metadata={"tender_id": tender_id, "vendor_id": vb_id, "document_type": "BID_PROPOSAL"},
        ),
        DocumentChunk(
            chunk_id="chunk-vb-03",
            document_id="doc-vb-02",
            document_name="Beta_Commercial.pdf",
            page_number=1,
            section_heading="Commercial Summary",
            text="Total evaluated contract price: USD 3,700,000.",
            metadata={"tender_id": tender_id, "vendor_id": vb_id, "document_type": "COMMERCIAL_QUOTE"},
        ),
    ])

    # Vendor C (Gamma Network Innovations): Unclear ISO certification, $2.9M
    await vector_store.add_chunks([
        DocumentChunk(
            chunk_id="chunk-vc-01",
            document_id="doc-vc-01",
            document_name="Gamma_Proposal.pdf",
            page_number=1,
            section_heading="Corporate Registration & Audit Status",
            text="Gamma Network Innovations is a registered entity. Note: ISO 27001 certification audit is in progress with auditor.",
            metadata={"tender_id": tender_id, "vendor_id": vc_id, "document_type": "BID_PROPOSAL"},
        ),
        DocumentChunk(
            chunk_id="chunk-vc-02",
            document_id="doc-vc-01",
            document_name="Gamma_Proposal.pdf",
            page_number=4,
            section_heading="Technical Blueprint",
            text="Scalable hybrid cloud design supporting rapid container deployments and disaster recovery.",
            metadata={"tender_id": tender_id, "vendor_id": vc_id, "document_type": "BID_PROPOSAL"},
        ),
        DocumentChunk(
            chunk_id="chunk-vc-03",
            document_id="doc-vc-02",
            document_name="Gamma_Pricing.pdf",
            page_number=1,
            section_heading="Quotation Schedule",
            text="Total turnkey pricing: USD 2,900,000.",
            metadata={"tender_id": tender_id, "vendor_id": vc_id, "document_type": "COMMERCIAL_QUOTE"},
        ),
    ])

    # Vendor D (Delta Legacy Technologies): Missing ISO certificate, $2.2M (Cheapest, but Disqualified)
    await vector_store.add_chunks([
        DocumentChunk(
            chunk_id="chunk-vd-01",
            document_id="doc-vd-01",
            document_name="Delta_Proposal.pdf",
            page_number=1,
            section_heading="General Corporate Info",
            text="Delta Legacy is a registered business. Information Security Certification: not provided, currently not certified.",
            metadata={"tender_id": tender_id, "vendor_id": vd_id, "document_type": "BID_PROPOSAL"},
        ),
        DocumentChunk(
            chunk_id="chunk-vd-02",
            document_id="doc-vd-02",
            document_name="Delta_Price_Sheet.pdf",
            page_number=1,
            section_heading="Low Cost Bid",
            text="Aggressive competitive total quotation: USD 2,200,000.",
            metadata={"tender_id": tender_id, "vendor_id": vd_id, "document_type": "COMMERCIAL_QUOTE"},
        ),
    ])

    # -------------------------------------------------------------
    # 2. Database Entities Registration
    # -------------------------------------------------------------
    tender = Tender(
        id=tender_id,
        reference_number="GOV-RFP-2026-CLOUD",
        title="National Cloud Infrastructure Platform",
        issuing_organization="Government Digital Transformation Authority",
        estimated_budget=Decimal("4000000.00"),
        currency="USD",
    )
    demo_db.add(tender)
    await demo_db.commit()

    vendors = [
        Vendor(id=va_id, name="Alpha Cloud Systems Inc", registration_number="US-REG-AL-01"),
        Vendor(id=vb_id, name="Beta Data Solutions Corp", registration_number="US-REG-BT-02"),
        Vendor(id=vc_id, name="Gamma Network Innovations", registration_number="US-REG-GM-03"),
        Vendor(id=vd_id, name="Delta Legacy Technologies", registration_number="US-REG-DL-04"),
    ]
    demo_db.add_all(vendors)
    await demo_db.commit()

    bids = [
        Bid(tender_id=tender_id, vendor_id=va_id, total_quoted_price=Decimal("3100000.00"), currency="USD"),
        Bid(tender_id=tender_id, vendor_id=vb_id, total_quoted_price=Decimal("3700000.00"), currency="USD"),
        Bid(tender_id=tender_id, vendor_id=vc_id, total_quoted_price=Decimal("2900000.00"), currency="USD"),
        Bid(tender_id=tender_id, vendor_id=vd_id, total_quoted_price=Decimal("2200000.00"), currency="USD"),
    ]
    demo_db.add_all(bids)
    await demo_db.commit()

    # -------------------------------------------------------------
    # 3. Multi-Agent Orchestration Workflow
    # -------------------------------------------------------------
    scorecard_service = ScorecardService(demo_db)
    run = await scorecard_service.initialize_run(tender_id)

    orchestrator = EvaluationOrchestrator(
        scorecard_service=scorecard_service,
        retriever=retriever,
    )

    # Execute workflow across all 4 vendors
    recommendation = await orchestrator.execute_evaluation_workflow(
        run_id=run.id,
        tender_id=tender_id,
        vendor_ids=[va_id, vb_id, vc_id, vd_id],
    )

    # -------------------------------------------------------------
    # 4. Strict Procurement Business Rules Verification
    # -------------------------------------------------------------
    assert recommendation is not None
    assert recommendation.status == AwardRecommendationStatusEnum.RECOMMENDED_AWAITING_APPROVAL

    # Winner Assertion: Vendor Alpha
    assert recommendation.recommended_vendor_id == va_id
    assert recommendation.recommended_vendor_name == "Alpha Cloud Systems Inc"
    assert recommendation.winning_composite_score is not None

    # Runner-Up Assertion: Vendor Beta
    assert recommendation.runner_up_vendor_id == vb_id
    assert recommendation.runner_up_vendor_name == "Beta Data Solutions Corp"

    # Scorecard Deep Inspection
    card = await scorecard_service.get_shared_scorecard(run.id)
    assert card.total_vendors == 4
    summary_map = {s.vendor_id: s for s in card.vendor_summaries}

    # Vendor A (Winner)
    assert summary_map[va_id].rank == 1
    assert summary_map[va_id].is_disqualified is False
    assert summary_map[va_id].requires_human_review is False
    assert float(summary_map[va_id].composite_score) > float(summary_map[vb_id].composite_score)

    # Vendor B (Runner-Up)
    assert summary_map[vb_id].rank == 2
    assert summary_map[vb_id].is_disqualified is False

    # Vendor C (Flagged for Review: In-progress audit)
    assert summary_map[vc_id].requires_human_review is True
    assert "Ambiguity" in " ".join(recommendation.risk_assessment) or "Gamma" in " ".join(recommendation.risk_assessment)

    # Vendor D (Disqualified: Missing certificate)
    assert summary_map[vd_id].is_disqualified is True
    assert summary_map[vd_id].rank is None
    # Compliance gating: Technical evaluation bypassed for disqualified vendor
    assert len(summary_map[vd_id].technical_scores) == 0

    # -------------------------------------------------------------
    # 5. Human Governance Formal Sign-Off Simulation
    # -------------------------------------------------------------
    sign_off_req = HumanSignOffRequest(
        officer_name="Marcus Vance",
        officer_role="Head of Public Procurement Oversight",
        decision=HumanSignOffDecisionEnum.APPROVE_AWARD,
        selected_vendor_id=va_id,
        justification_comments="Approved based on multi-agent evaluation findings: Alpha Cloud demonstrates technical superiority and complies with all mandatory statutory security criteria.",
    )
    final_signed_recommendation = await scorecard_service.record_human_sign_off(run.id, sign_off_req)
    assert final_signed_recommendation.status == AwardRecommendationStatusEnum.APPROVED

    # Check database run status updated to AWARD_APPROVED
    updated_run = await scorecard_service.repo.get_evaluation_run(run.id)
    assert updated_run.status == "AWARD_APPROVED"

    # -------------------------------------------------------------
    # 6. Report Generation Verification (PDF, CSV, JSON)
    # -------------------------------------------------------------
    report_service = ReportService(scorecard_service)

    # PDF Generation
    pdf_bytes = await report_service.generate_pdf_report(run.id)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")

    # CSV Generation
    csv_str = await report_service.generate_csv_report(run.id)
    assert "Alpha Cloud Systems Inc" in csv_str
    assert "Beta Data Solutions Corp" in csv_str
    assert "Gamma Network Innovations" in csv_str
    assert "Delta Legacy Technologies" in csv_str
    assert "Disqualified" in csv_str

    # JSON Dump
    json_dump = await report_service.generate_json_report(run.id)
    assert json_dump["evaluation_run_id"] == run.id
    assert json_dump["award_recommendation"]["status"] == "APPROVED"
    assert len(json_dump["scorecard"]["vendor_summaries"]) == 4

