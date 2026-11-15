import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.tender import Tender
from backend.app.repositories.tender_repo import TenderRepository
from backend.app.services.scorecard_service import ScorecardService
from backend.app.agents.criteria_agent import CriteriaAgent
from backend.app.rag.chunker import DocumentChunker, DocumentChunk
from backend.app.rag.vector_store import default_vector_store
from backend.app.rag.retriever import HybridRetriever


@pytest.mark.asyncio
async def test_criteria_agent_extraction_and_weights(db_session: AsyncSession):
    t_repo = TenderRepository(db_session)
    sc_service = ScorecardService(db_session)

    # 1. Create Tender
    tender = await t_repo.create(
        Tender(
            title="Enterprise Cloud ERP Modernization",
            reference_number="RFP-ERP-2026",
            issuing_organization="Global Logistics Agency",
        )
    )

    # 2. Pre-populate RAG with tender RFP chunks
    chunker = DocumentChunker()
    rfp_text = (
        "Section 2: Mandatory Eligibility Requirements\n"
        "1. All bidders must submit a valid ISO 27001 cybersecurity certification.\n"
        "2. Bidders must hold statutory business registration and tax clearance certificate.\n\n"
        "Section 3: Technical Evaluation Criteria\n"
        "| Criterion Code | Section | Max Points |\n"
        "|---|---|---|\n"
        "| TC-01 | Microservices Cloud Architecture | 40 |\n"
        "| TC-02 | DevOps Deployment Pipeline & 24/7 SLA | 30 |\n"
        "| TC-03 | Past Performance on 5+ Similar Projects | 30 |\n\n"
        "Section 4: Commercial Pricing Formula\n"
        "Commercial evaluation will be based on relative lowest cost formula: (Lowest Bid / Vendor Bid) * 30 points.\n"
        "Technical weight is 70% and commercial weight is 30%."
    )
    chunks = chunker.chunk_pages(
        document_id="doc-rfp-1",
        document_name="ERP_RFP_Official.pdf",
        pages=[type("Page", (), {"page_number": 1, "text": rfp_text, "headings": ["Section 2: Mandatory Eligibility"]})()],
        tender_id=tender.id,
    )
    await default_vector_store.add_chunks(chunks)

    # 3. Execute Criteria Agent
    retriever = HybridRetriever(vector_store=default_vector_store)
    agent = CriteriaAgent(scorecard_service=sc_service, retriever=retriever)

    plan = await agent.run(tender_id=tender.id)

    # 4. Verify structured EvaluationPlan
    assert plan.tender_id == tender.id
    assert len(plan.mandatory_requirements) >= 2
    assert len(plan.technical_criteria) >= 3
    assert plan.technical_weight + plan.commercial_weight == Decimal("1.0")

    # Verify individual technical criteria weights sum to 1.0
    tech_sum = sum(tc.weight for tc in plan.technical_criteria)
    assert abs(tech_sum - Decimal("1.0")) <= Decimal("0.001")
    assert plan.is_approved_by_human is False
    assert len(plan.evidence_citations) > 0

