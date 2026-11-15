import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.tender import Tender, TenderDocument
from backend.app.db.models.vendor import Vendor
from backend.app.db.models.bid import Bid
from backend.app.repositories.tender_repo import TenderRepository
from backend.app.repositories.vendor_repo import VendorRepository
from backend.app.repositories.bid_repo import BidRepository
from backend.app.repositories.scorecard_repo import ScorecardRepository


@pytest.mark.asyncio
async def test_tender_repository_crud(db_session: AsyncSession):
    repo = TenderRepository(db_session)

    tender = Tender(
        title="High Performance Computing Cluster",
        reference_number="RFP-HPC-2026",
        issuing_organization="National Science Foundation",
        estimated_budget=Decimal("5000000.00"),
    )
    created = await repo.create(tender)
    assert created.id is not None

    by_ref = await repo.get_by_reference("RFP-HPC-2026")
    assert by_ref is not None
    assert by_ref.title == "High Performance Computing Cluster"

    # Add document
    doc = TenderDocument(
        tender_id=created.id,
        filename="Spec.pdf",
        file_path="/tmp/spec.pdf",
        document_type="TENDER_RFP",
        page_count=20,
        file_size_bytes=102400,
        sha256_checksum="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    )
    await repo.add_document(doc)

    with_rel = await repo.get_with_relations(created.id)
    assert len(with_rel.documents) == 1
    assert with_rel.documents[0].filename == "Spec.pdf"


@pytest.mark.asyncio
async def test_vendor_and_bid_repository(db_session: AsyncSession):
    v_repo = VendorRepository(db_session)
    b_repo = BidRepository(db_session)
    t_repo = TenderRepository(db_session)

    tender = await t_repo.create(
        Tender(
            title="Database Migration RFP",
            reference_number="RFP-DB-01",
            issuing_organization="Finance Bureau",
        )
    )

    vendor = await v_repo.create(
        Vendor(
            name="DataCorp Global",
            registration_number="DC-8899",
            contact_email="sales@datacorp.com",
            country="Germany",
        )
    )

    bid = await b_repo.create(
        Bid(
            tender_id=tender.id,
            vendor_id=vendor.id,
            total_quoted_price=Decimal("450000.00"),
            currency="EUR",
        )
    )

    found_bid = await b_repo.get_by_tender_and_vendor(tender.id, vendor.id)
    assert found_bid is not None
    assert found_bid.total_quoted_price == Decimal("450000.00")
    assert found_bid.vendor.name == "DataCorp Global"


@pytest.mark.asyncio
async def test_scorecard_repository_lifecycle(db_session: AsyncSession):
    sc_repo = ScorecardRepository(db_session)
    t_repo = TenderRepository(db_session)
    v_repo = VendorRepository(db_session)

    tender = await t_repo.create(
        Tender(
            title="Hospital Telehealth Platform",
            reference_number="RFP-MED-01",
            issuing_organization="Health Authority",
        )
    )

    run = await sc_repo.create_evaluation_run(tender.id)
    assert run.status == "INITIALIZED"

    # Update status
    updated = await sc_repo.update_evaluation_status(
        run_id=run.id,
        status="RUNNING",
        current_step="Screening Compliance",
        eligible_count=2,
        disqualified_count=1,
    )
    assert updated.status == "RUNNING"
    assert updated.eligible_vendors_count == 2
    assert updated.disqualified_vendors_count == 1

