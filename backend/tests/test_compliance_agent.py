import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.tender import Tender
from backend.app.db.models.vendor import Vendor
from backend.app.repositories.tender_repo import TenderRepository
from backend.app.repositories.vendor_repo import VendorRepository
from backend.app.services.scorecard_service import ScorecardService
from backend.app.agents.compliance_agent import ComplianceAgent
from backend.app.rag.chunker import DocumentChunker
from backend.app.rag.vector_store import default_vector_store
from backend.app.rag.retriever import HybridRetriever
from backend.app.schemas.criteria import (
    EvaluationPlanDTO,
    MandatoryRequirementCreate,
    MandatoryRequirementCategory,
    CommercialFormulaSpec,
)
from backend.app.schemas.compliance import ComplianceStatusEnum


@pytest.mark.asyncio
async def test_compliance_agent_three_vendors(db_session: AsyncSession):
    t_repo = TenderRepository(db_session)
    v_repo = VendorRepository(db_session)
    sc_service = ScorecardService(db_session)

    # 1. Tender & Run
    tender = await t_repo.create(
        Tender(
            title="Healthcare IT Infrastructure",
            reference_number="RFP-HEALTH-01",
            issuing_organization="National Health Service",
        )
    )
    run_read = await sc_service.initialize_run(tender.id)
    run_id = run_read.id

    # 2. Approved EvaluationPlan with 2 mandatory requirements
    plan = EvaluationPlanDTO(
        plan_id="plan-test-1",
        tender_id=tender.id,
        mandatory_requirements=[
            MandatoryRequirementCreate(
                requirement_code="MR-01",
                category=MandatoryRequirementCategory.CERTIFICATION,
                title="ISO 27001 Certification",
                description="Must possess valid ISO 27001 security certificate",
                pass_criteria="Certificate verification",
            ),
            MandatoryRequirementCreate(
                requirement_code="MR-02",
                category=MandatoryRequirementCategory.LEGAL,
                title="Business License",
                description="Valid commercial operating license",
                pass_criteria="Official registration",
            ),
        ],
        commercial_formula=CommercialFormulaSpec(formula_description="Lowest cost"),
    )

    # 3. Register 3 Vendors
    vA = await v_repo.create(Vendor(name="Vendor Alpha (Fully Compliant)"))
    vB = await v_repo.create(Vendor(name="Vendor Beta (Disqualified)"))
    vC = await v_repo.create(Vendor(name="Vendor Gamma (Ambiguous / Inconclusive)"))

    # 4. Ingest Documents into RAG
    chunker = DocumentChunker()

    # Vendor A: All valid certificates
    docA_text = (
        "Vendor Alpha Submission:\n"
        "Attached is our valid ISO 27001 certified security accreditation by BSI.\n"
        "We are an incorporated and registered commercial entity holding official business license."
    )
    chunksA = chunker.chunk_pages(
        document_id="doc-va",
        document_name="VendorA_Compliance.pdf",
        pages=[type("Page", (), {"page_number": 1, "text": docA_text, "headings": []})()],
        tender_id=tender.id,
        vendor_id=vA.id,
    )

    # Vendor B: Explicit non-compliance (missing ISO)
    docB_text = (
        "Vendor Beta Submission:\n"
        "We have registered commercial license. However, our ISO 27001 certificate is currently expired and not provided."
    )
    chunksB = chunker.chunk_pages(
        document_id="doc-vb",
        document_name="VendorB_Compliance.pdf",
        pages=[type("Page", (), {"page_number": 1, "text": docB_text, "headings": []})()],
        tender_id=tender.id,
        vendor_id=vB.id,
    )

    # Vendor C: Inconclusive / In-progress proof
    docC_text = (
        "Vendor Gamma Submission:\n"
        "Registered entity in good standing. Regarding ISO 27001, audit discussions occurred in Q3."
    )
    chunksC = chunker.chunk_pages(
        document_id="doc-vc",
        document_name="VendorC_Compliance.pdf",
        pages=[type("Page", (), {"page_number": 1, "text": docC_text, "headings": []})()],
        tender_id=tender.id,
        vendor_id=vC.id,
    )

    await default_vector_store.add_chunks(chunksA + chunksB + chunksC)

    # 5. Execute Compliance Agent for all three vendors
    retriever = HybridRetriever(vector_store=default_vector_store)
    agent = ComplianceAgent(scorecard_service=sc_service, retriever=retriever)

    # Vendor A Evaluation
    resultsA = await agent.run(run_id=run_id, vendor_id=vA.id, evaluation_plan=plan)
    assert all(r.status == ComplianceStatusEnum.PASS for r in resultsA)
    assert not any(r.is_disqualified for r in resultsA)

    # Vendor B Evaluation (Disqualification)
    resultsB = await agent.run(run_id=run_id, vendor_id=vB.id, evaluation_plan=plan)
    assert any(r.status == ComplianceStatusEnum.FAIL for r in resultsB)
    assert any(r.is_disqualified for r in resultsB)

    # Vendor C Evaluation (Ambiguous -> UNCLEAR, Human Review Required)
    resultsC = await agent.run(run_id=run_id, vendor_id=vC.id, evaluation_plan=plan)
    assert any(r.status == ComplianceStatusEnum.UNCLEAR for r in resultsC)
    assert any(r.requires_human_review for r in resultsC)
    # Crucial: Unclear cases must NOT be automatically disqualified!
    unclear_item = next(r for r in resultsC if r.status == ComplianceStatusEnum.UNCLEAR)
    assert unclear_item.is_disqualified is False

