from decimal import Decimal
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import VendorNotFoundError, TenderNotFoundError
from backend.app.core.logging import logger
from backend.app.db.models.vendor import Vendor
from backend.app.db.models.bid import Bid, BidDocument
from backend.app.repositories.vendor_repo import VendorRepository
from backend.app.repositories.bid_repo import BidRepository
from backend.app.repositories.tender_repo import TenderRepository
from backend.app.services.document_service import DocumentService
from backend.app.schemas.vendor import VendorCreate, VendorRead
from backend.app.schemas.bid import BidCreate, BidRead


class VendorService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.vendor_repo = VendorRepository(session)
        self.bid_repo = BidRepository(session)
        self.tender_repo = TenderRepository(session)
        self.doc_service = DocumentService()

    async def create_vendor(self, data: VendorCreate) -> VendorRead:
        existing = await self.vendor_repo.get_by_name(data.name)
        if existing:
            raise ValueError(f"Vendor '{data.name}' already registered")

        vendor = Vendor(
            name=data.name,
            registration_number=data.registration_number,
            contact_email=data.contact_email,
            country=data.country,
        )
        created = await self.vendor_repo.create(vendor)
        await self.session.commit()
        logger.info(f"Registered Vendor {created.id} ({created.name})")
        return VendorRead.model_validate(created)

    async def get_vendor(self, vendor_id: str) -> VendorRead:
        vendor = await self.vendor_repo.get_by_id(vendor_id)
        if not vendor:
            raise VendorNotFoundError(f"Vendor '{vendor_id}' not found")
        return VendorRead.model_validate(vendor)

    async def list_vendors(self, skip: int = 0, limit: int = 100) -> List[VendorRead]:
        vendors = await self.vendor_repo.get_all(skip=skip, limit=limit)
        return [VendorRead.model_validate(v) for v in vendors]

    async def submit_bid(self, data: BidCreate) -> BidRead:
        tender = await self.tender_repo.get_by_id(data.tender_id)
        if not tender:
            raise TenderNotFoundError(f"Tender '{data.tender_id}' not found")

        vendor = await self.vendor_repo.get_by_id(data.vendor_id)
        if not vendor:
            raise VendorNotFoundError(f"Vendor '{data.vendor_id}' not found")

        existing_bid = await self.bid_repo.get_by_tender_and_vendor(data.tender_id, data.vendor_id)
        if existing_bid:
            return BidRead.model_validate(existing_bid)

        bid = Bid(
            tender_id=data.tender_id,
            vendor_id=data.vendor_id,
            total_quoted_price=data.total_quoted_price,
            currency=data.currency,
            status="SUBMITTED",
        )
        created = await self.bid_repo.create(bid)
        await self.session.commit()
        logger.info(f"Created Bid {created.id} for Vendor {data.vendor_id} on Tender {data.tender_id}")
        full = await self.bid_repo.get_by_tender_and_vendor(data.tender_id, data.vendor_id)
        return BidRead.model_validate(full)

    async def add_bid_document(
        self,
        bid_id: str,
        filename: str,
        content: bytes,
        document_type: str = "TECHNICAL_BID",
    ) -> BidRead:
        import uuid
        bid = await self.bid_repo.get_by_id(bid_id)
        if not bid:
            raise ValueError(f"Bid '{bid_id}' not found")

        doc_id = str(uuid.uuid4())
        file_path, sha256, file_size, page_count = await self.doc_service.save_uploaded_file(
            filename=filename,
            content=content,
            document_id=doc_id,
            tender_id=bid.tender_id,
            vendor_id=bid.vendor_id,
            document_type=document_type,
        )

        doc = BidDocument(
            id=doc_id,
            bid_id=bid_id,
            filename=filename,
            file_path=file_path,
            document_type=document_type,
            page_count=page_count,
            file_size_bytes=file_size,
            sha256_checksum=sha256,
        )
        await self.bid_repo.add_document(doc)
        await self.session.commit()
        logger.info(f"Attached and indexed document {filename} for Bid {bid_id}")
        full = await self.bid_repo.get_by_tender_and_vendor(bid.tender_id, bid.vendor_id)
        return BidRead.model_validate(full)

    async def list_bids_for_tender(self, tender_id: str) -> List[BidRead]:
        bids = await self.bid_repo.get_bids_for_tender(tender_id)
        return [BidRead.model_validate(b) for b in bids]

