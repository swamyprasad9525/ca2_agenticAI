import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.tender import Tender
from backend.app.db.models.vendor import Vendor
from backend.app.db.models.bid import Bid
from backend.app.repositories.tender_repo import TenderRepository
from backend.app.repositories.vendor_repo import VendorRepository
from backend.app.repositories.bid_repo import BidRepository
from backend.app.services.scorecard_service import ScorecardService
from backend.app.agents.technical_scorer import TechnicalScorer
from backend.app.agents.commercial_scorer import CommercialScorer
from backend.app.rag.chunker import DocumentChunker
from backend.app.rag.vector_store import default_vector_store
from backend.app.rag.retriever import HybridRetriever
from backend.app.schemas.criteria import (
    EvaluationPlanDTO,
    EvaluationCriterionCreate,
    CommercialFormulaSpec,
)


@pytest.mark.asyncio
async def test_technical_and_commercial_scorers(db_session: AsyncSession):
    t_repo = TenderRepository(db_session)
    v_repo = VendorRepository(db_session)
    b_repo = BidRepository(db_session)
    sc_service = ScorecardService(db_session)

    # 1. Tender & Run
    tender = await t_repo.create(
        Tender(
            title="Satellite Earth Station Modernization",
            reference_number="RFP-SAT-01",
            issuing_organization="Space Agency",
        )
    )
    run_read = await sc_service.initialize_run(tender.id)
    run_id = run_read.id

    # 2. Approved EvaluationPlan
    plan = EvaluationPlanDTO(
        plan_id="plan-sat-1",
        tender_id=tender.id,
        technical_weight=Decimal("0.70"),
        commercial_weight=Decimal("0.30"),
        technical_criteria=[
            EvaluationCriterionCreate(
                criterion_code="TC-01",
                section="Architecture",
                title="Antenna Array Architecture",
                description="High availability RF antenna array design",
                max_points=Decimal("60.0"),
                weight=Decimal("0.60"),
                scoring_rubric="0-60 points",
            ),
            EvaluationCriterionCreate(
                criterion_code="TC-02",
                section="SLA",
                title="Support Framework & 99.99% SLA",
                description="24/7 mission critical operations SLA",
                max_points=Decimal("40.0"),
                weight=Decimal("0.40"),
                scoring_rubric="0-40 points",
            ),
        ],
        commercial_formula=CommercialFormulaSpec(formula_description="Lowest cost"),
    )

    # 3. Create 2 Vendors (Vendor Alpha: Strong, Vendor Beta: Weak)
    vA = await v_repo.create(Vendor(name="SatCom Alpha"))
    vB = await v_repo.create(Vendor(name="Orbit Beta"))

    await b_repo.create(Bid(tender_id=tender.id, vendor_id=vA.id, total_quoted_price=Decimal("1200000.00")))
    await b_repo.create(Bid(tender_id=tender.id, vendor_id=vB.id, total_quoted_price=Decimal("950000.00")))

    # 4. Ingest Proposals into RAG
    chunker = DocumentChunker()

    # Vendor A: Superior architecture & 99.99% SLA
    textA = (
        "SatCom Alpha Technical Proposal:\n"
        "Our antenna array features superior high availability with automated failover and zero-downtime cross-region replication.\n"
        "We commit to enterprise-grade 99.99% mission critical SLA with dedicated on-site certified experts."
    )
    chunksA = chunker.chunk_pages(
        document_id="doc-va-tech",
        document_name="SatCom_Alpha_Tech.pdf",
        pages=[type("Page", (), {"page_number": 1, "text": textA, "headings": []})()],
        tender_id=tender.id,
        vendor_id=vA.id,
    )

    # Vendor B: Basic implementation
    textB = (
        "Orbit Beta Technical Proposal:\n"
        "We offer basic antenna design with standard sla and planned support during business hours."
    )
    chunksB = chunker.chunk_pages(
        document_id="doc-vb-tech",
        document_name="Orbit_Beta_Tech.pdf",
        pages=[type("Page", (), {"page_number": 1, "text": textB, "headings": []})()],
        tender_id=tender.id,
        vendor_id=vB.id,
    )

    await default_vector_store.add_chunks(chunksA + chunksB)

    # 5. Execute Technical Scorer
    retriever = HybridRetriever(vector_store=default_vector_store)
    tech_scorer = TechnicalScorer(scorecard_service=sc_service, retriever=retriever)

    scoresA = await tech_scorer.run(run_id=run_id, vendor_id=vA.id, evaluation_plan=plan)
    scoresB = await tech_scorer.run(run_id=run_id, vendor_id=vB.id, evaluation_plan=plan)

    total_weighted_A = sum(s.weighted_score for s in scoresA)
    total_weighted_B = sum(s.weighted_score for s in scoresB)

    # Superior technical proposal must score higher than basic proposal
    assert total_weighted_A > total_weighted_B
    assert all(s.raw_points <= s.max_points for s in scoresA + scoresB)
    assert all(len(s.evidence) > 0 for s in scoresA + scoresB)

    # 6. Execute Commercial Scorer
    comm_scorer = CommercialScorer(scorecard_service=sc_service, retriever=retriever)

    commA = await comm_scorer.run(run_id=run_id, vendor_id=vA.id, evaluation_plan=plan)
    commB = await comm_scorer.run(run_id=run_id, vendor_id=vB.id, evaluation_plan=plan)

    assert commA.raw_points == Decimal("1200000.00")
    assert commB.raw_points == Decimal("950000.00")
    assert commA.score_type == "COMMERCIAL"

