import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.app.db.base import Base
from backend.app.db.models.tender import Tender
from backend.app.db.models.vendor import Vendor
from backend.app.db.models.bid import Bid
from backend.app.db.models.criteria import EvaluationPlan, MandatoryRequirement, EvaluationCriterion
from backend.app.rag.vector_store import HybridPersistentVectorStore
from backend.app.rag.retriever import HybridRetriever
from backend.app.rag.chunker import DocumentChunk
from backend.app.services.scorecard_service import ScorecardService
from backend.app.orchestrator.evaluation_orchestrator import EvaluationOrchestrator
from backend.app.schemas.award import AwardRecommendationStatusEnum


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_evaluation_orchestrator_full_workflow(db_session, tmp_path):
    # 1. Setup Vector Store and Seed RAG Chunks
    vector_store = HybridPersistentVectorStore(persist_path=str(tmp_path / "vec_index.json"))
    retriever = HybridRetriever(vector_store)

    tender_id = "tender-orch-001"
    v_a_id = "vendor-orch-a"
    v_b_id = "vendor-orch-b"
    v_c_id = "vendor-orch-c"

    # Seed Tender Chunks (Criteria)
    await vector_store.add_chunks([
        DocumentChunk(
            chunk_id="chunk-tender-01",
            document_id="doc-tender",
            document_name="RFP_Specification.pdf",
            page_number=1,
            section_heading="Mandatory Requirements",
            text="All bidders must possess ISO 27001 Information Security certification and a valid commercial registration.",
            metadata={"tender_id": tender_id, "document_type": "TENDER"},
        ),
        DocumentChunk(
            chunk_id="chunk-tender-02",
            document_id="doc-tender",
            document_name="RFP_Specification.pdf",
            page_number=3,
            section_heading="Technical Criteria",
            text="| TC-01 | Architecture & Scalability | 50 |\n| TC-02 | Implementation & SLA | 50 |",
            metadata={"tender_id": tender_id, "document_type": "TENDER"},
        ),
    ])

    # Seed Vendor A Chunks (Compliant, strong tech, price $3,000,000)
    await vector_store.add_chunks([
        DocumentChunk(
            chunk_id="chunk-va-01",
            document_id="doc-va-01",
            document_name="VendorA_Proposal.pdf",
            page_number=1,
            section_heading="Mandatory Credentials",
            text="Vendor Alpha holds ISO 27001 Information Security certification and full commercial company registration.",
            metadata={"tender_id": tender_id, "vendor_id": v_a_id, "document_type": "BID_PROPOSAL"},
        ),
        DocumentChunk(
            chunk_id="chunk-va-02",
            document_id="doc-va-02",
            document_name="VendorA_Proposal.pdf",
            page_number=4,
            section_heading="Technical Architecture",
            text="High availability distributed cloud architecture with automated failover and 99.99% uptime guarantee.",
            metadata={"tender_id": tender_id, "vendor_id": v_a_id, "document_type": "BID_PROPOSAL"},
        ),
        DocumentChunk(
            chunk_id="chunk-va-03",
            document_id="doc-va-03",
            document_name="VendorA_Pricing.pdf",
            page_number=1,
            section_heading="Financial Schedule",
            text="Total fixed turnkey contract price: USD 3,000,000 all inclusive.",
            metadata={"tender_id": tender_id, "vendor_id": v_a_id, "document_type": "COMMERCIAL_QUOTE"},
        ),
    ])

    # Seed Vendor B Chunks (Compliant, moderate tech, price $3,500,000)
    await vector_store.add_chunks([
        DocumentChunk(
            chunk_id="chunk-vb-01",
            document_id="doc-vb-01",
            document_name="VendorB_Proposal.pdf",
            page_number=1,
            section_heading="Certifications",
            text="Vendor Beta possesses ISO 27001 security compliance and formal corporate registry.",
            metadata={"tender_id": tender_id, "vendor_id": v_b_id, "document_type": "BID_PROPOSAL"},
        ),
        DocumentChunk(
            chunk_id="chunk-vb-02",
            document_id="doc-vb-02",
            document_name="VendorB_Proposal.pdf",
            page_number=2,
            section_heading="System Specifications",
            text="Standard clustered web infrastructure with basic load balancing and 99.9% uptime SLA.",
            metadata={"tender_id": tender_id, "vendor_id": v_b_id, "document_type": "BID_PROPOSAL"},
        ),
        DocumentChunk(
            chunk_id="chunk-vb-03",
            document_id="doc-vb-03",
            document_name="VendorB_Pricing.pdf",
            page_number=1,
            section_heading="Financial Summary",
            text="Total quotation for enterprise deployment: USD 3,500,000.",
            metadata={"tender_id": tender_id, "vendor_id": v_b_id, "document_type": "COMMERCIAL_QUOTE"},
        ),
    ])

    # Seed Vendor C Chunks (Fails mandatory ISO 27001 - explicitly missing)
    await vector_store.add_chunks([
        DocumentChunk(
            chunk_id="chunk-vc-01",
            document_id="doc-vc-01",
            document_name="VendorC_Proposal.pdf",
            page_number=1,
            section_heading="Company Overview",
            text="Vendor Gamma is a software developer with general business registration. Note: ISO 27001 is currently not certified.",
            metadata={"tender_id": tender_id, "vendor_id": v_c_id, "document_type": "BID_PROPOSAL"},
        ),
        DocumentChunk(
            chunk_id="chunk-vc-02",
            document_id="doc-vc-02",
            document_name="VendorC_Pricing.pdf",
            page_number=1,
            section_heading="Price Sheet",
            text="Total bid price: USD 2,500,000.",
            metadata={"tender_id": tender_id, "vendor_id": v_c_id, "document_type": "COMMERCIAL_QUOTE"},
        ),
    ])

    # 2. Database Entities
    tender = Tender(
        id=tender_id,
        reference_number="TND-ORCH-2026",
        title="National Cloud Infrastructure Platform",
        issuing_organization="Digital Transformation Agency",
    )
    db_session.add(tender)
    await db_session.commit()

    vendor_a = Vendor(id=v_a_id, name="CloudPrime Technologies Ltd", registration_number="REG-CP-01")
    vendor_b = Vendor(id=v_b_id, name="InfraGlobal Systems Inc", registration_number="REG-IG-02")
    vendor_c = Vendor(id=v_c_id, name="Legacy Solutions Group", registration_number="REG-LS-03")
    db_session.add_all([vendor_a, vendor_b, vendor_c])
    await db_session.commit()

    # Bids
    bid_a = Bid(tender_id=tender_id, vendor_id=v_a_id, total_quoted_price=Decimal("3000000.00"), currency="USD")
    bid_b = Bid(tender_id=tender_id, vendor_id=v_b_id, total_quoted_price=Decimal("3500000.00"), currency="USD")
    bid_c = Bid(tender_id=tender_id, vendor_id=v_c_id, total_quoted_price=Decimal("2500000.00"), currency="USD")
    db_session.add_all([bid_a, bid_b, bid_c])
    await db_session.commit()

    # 3. Initialize Services and Orchestrator
    scorecard_service = ScorecardService(db_session)
    run = await scorecard_service.initialize_run(tender_id)

    orchestrator = EvaluationOrchestrator(
        scorecard_service=scorecard_service,
        retriever=retriever,
    )

    # 4. Execute Workflow
    recommendation = await orchestrator.execute_evaluation_workflow(
        run_id=run.id,
        tender_id=tender_id,
        vendor_ids=[v_a_id, v_b_id, v_c_id],
    )

    # 5. Assertions
    assert recommendation is not None
    assert recommendation.status == AwardRecommendationStatusEnum.RECOMMENDED_AWAITING_APPROVAL

    # Winner must be Vendor A (CloudPrime Technologies Ltd)
    assert recommendation.recommended_vendor_id == v_a_id
    assert recommendation.recommended_vendor_name == "CloudPrime Technologies Ltd"
    assert recommendation.winning_composite_score is not None
    assert recommendation.winning_composite_score > Decimal("0.0")

    # Runner-up must be Vendor B
    assert recommendation.runner_up_vendor_id == v_b_id
    assert recommendation.runner_up_vendor_name == "InfraGlobal Systems Inc"

    # Vendor C was non-compliant and must not be recommended
    assert recommendation.recommended_vendor_id != v_c_id

    # 6. Verify Shared Scorecard Aggregation
    final_card = await scorecard_service.get_shared_scorecard(run.id)
    assert final_card.status == "AWAITING_HUMAN_APPROVAL"
    assert final_card.total_vendors == 3

    # Check vendor summaries
    summary_map = {s.vendor_id: s for s in final_card.vendor_summaries}

    # Vendor A: Rank 1
    assert summary_map[v_a_id].rank == 1
    assert summary_map[v_a_id].is_disqualified is False
    assert len(summary_map[v_a_id].technical_scores) > 0
    assert summary_map[v_a_id].commercial_score is not None

    # Vendor B: Rank 2
    assert summary_map[v_b_id].rank == 2
    assert summary_map[v_b_id].is_disqualified is False

    # Vendor C: Disqualified, Rank None
    assert summary_map[v_c_id].is_disqualified is True
    assert summary_map[v_c_id].rank is None
    # Compliance Gating: Technical scoring bypassed for disqualified Vendor C
    assert len(summary_map[v_c_id].technical_scores) == 0

    # 7. Check Agent Execution Telemetry
    # All 5 specialized agents must have recorded telemetry
    exec_agents = {ex["agent_name"] for ex in final_card.agent_executions}
    assert "CriteriaAgent" in exec_agents
    assert "ComplianceAgent" in exec_agents
    assert "TechnicalScorer" in exec_agents
    assert "CommercialScorer" in exec_agents
    assert "AwardManager" in exec_agents
