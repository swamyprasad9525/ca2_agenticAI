"""
Seed Demo Script for Tender & Procurement Evaluation System.

Populates the database and vector store with realistic procurement data:
- 1 National Infrastructure Tender
- 4 Competing Vendors (Alpha, Beta, Gamma, Delta)
- Evidence-anchored proposal and pricing chunks
- Executes the 5-Agent Multi-Agent Evaluation Workflow
- Stores the final ranked scorecard and award recommendation
"""

import asyncio
from decimal import Decimal

from backend.app.core.logging import logger
from backend.app.db.session import init_db, AsyncSessionLocal
from backend.app.db.models.tender import Tender
from backend.app.db.models.vendor import Vendor
from backend.app.db.models.bid import Bid
from backend.app.rag.vector_store import default_vector_store
from backend.app.rag.chunker import DocumentChunk
from backend.app.rag.retriever import HybridRetriever
from backend.app.services.scorecard_service import ScorecardService
from backend.app.orchestrator.evaluation_orchestrator import EvaluationOrchestrator


async def seed():
    logger.info("Initializing database schema...")
    await init_db()

    tender_id = "TND-E2E-2026-GOV"
    va_id = "v-alpha-01"
    vb_id = "v-beta-02"
    vc_id = "v-gamma-03"
    vd_id = "v-delta-04"

    logger.info("Seeding vector store chunks for RAG...")
    # 1. Tender Specification Chunks
    await default_vector_store.add_chunks([
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

    # 2. Vendor A (Alpha Cloud Systems): Winner
    await default_vector_store.add_chunks([
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

    # 3. Vendor B (Beta Data Solutions): Runner-Up
    await default_vector_store.add_chunks([
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

    # 4. Vendor C (Gamma Network Innovations): Ambiguous Certification
    await default_vector_store.add_chunks([
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

    # 5. Vendor D (Delta Legacy Technologies): Disqualified
    await default_vector_store.add_chunks([
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

    async with AsyncSessionLocal() as session:
        # Check if tender already exists
        existing_tender = await session.get(Tender, tender_id)
        if not existing_tender:
            logger.info("Inserting Tender record...")
            tender = Tender(
                id=tender_id,
                reference_number="GOV-RFP-2026-CLOUD",
                title="National Cloud Infrastructure Platform",
                issuing_organization="Government Digital Transformation Authority",
                estimated_budget=Decimal("4000000.00"),
                currency="USD",
            )
            session.add(tender)
            await session.commit()

        # Vendors
        for v_id, name, reg in [
            (va_id, "Alpha Cloud Systems Inc", "US-REG-AL-01"),
            (vb_id, "Beta Data Solutions Corp", "US-REG-BT-02"),
            (vc_id, "Gamma Network Innovations", "US-REG-GM-03"),
            (vd_id, "Delta Legacy Technologies", "US-REG-DL-04"),
        ]:
            if not await session.get(Vendor, v_id):
                session.add(Vendor(id=v_id, name=name, registration_number=reg))
        await session.commit()

        # Bids
        for v_id, price in [
            (va_id, Decimal("3100000.00")),
            (vb_id, Decimal("3700000.00")),
            (vc_id, Decimal("2900000.00")),
            (vd_id, Decimal("2200000.00")),
        ]:
            from sqlalchemy import select
            b_stmt = select(Bid).where(Bid.tender_id == tender_id, Bid.vendor_id == v_id)
            res = await session.execute(b_stmt)
            if not res.scalar_one_or_none():
                session.add(Bid(tender_id=tender_id, vendor_id=v_id, total_quoted_price=price, currency="USD"))
        await session.commit()

        logger.info("Executing initial multi-agent evaluation workflow...")
        scorecard_service = ScorecardService(session)
        run = await scorecard_service.initialize_run(tender_id)

        retriever = HybridRetriever(default_vector_store)
        orchestrator = EvaluationOrchestrator(
            scorecard_service=scorecard_service,
            retriever=retriever,
        )

        rec = await orchestrator.execute_evaluation_workflow(
            run_id=run.id,
            tender_id=tender_id,
            vendor_ids=[va_id, vb_id, vc_id, vd_id],
        )

        logger.info("=" * 60)
        logger.info("DEMO SEEDING COMPLETED SUCCESSFULLY!")
        logger.info(f"Tender ID: {tender_id}")
        logger.info(f"Evaluation Run ID: {run.id}")
        logger.info(f"Recommended Winner: {rec.recommended_vendor_name} (Composite Score: {rec.winning_composite_score})")
        logger.info(f"Runner Up: {rec.runner_up_vendor_name}")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed())
