from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Form, status
from backend.app.api.deps import get_vendor_service
from backend.app.services.vendor_service import VendorService
from backend.app.schemas.vendor import VendorCreate, VendorRead
from backend.app.schemas.bid import BidCreate, BidRead

router = APIRouter(tags=["Vendors & Bids"])


@router.post("/vendors", response_model=VendorRead, status_code=status.HTTP_201_CREATED)
async def register_vendor(
    payload: VendorCreate,
    service: VendorService = Depends(get_vendor_service),
) -> VendorRead:
    """Register a new competing commercial vendor."""
    return await service.create_vendor(payload)


@router.get("/vendors", response_model=List[VendorRead])
async def list_vendors(
    skip: int = 0,
    limit: int = 100,
    service: VendorService = Depends(get_vendor_service),
) -> List[VendorRead]:
    """Retrieve all registered vendors."""
    return await service.list_vendors(skip=skip, limit=limit)


@router.get("/vendors/{vendor_id}", response_model=VendorRead)
async def get_vendor(
    vendor_id: str,
    service: VendorService = Depends(get_vendor_service),
) -> VendorRead:
    """Retrieve a vendor by ID."""
    return await service.get_vendor(vendor_id)


@router.post("/vendors/{vendor_id}/bids", response_model=BidRead, status_code=status.HTTP_201_CREATED)
async def submit_bid(
    vendor_id: str,
    payload: BidCreate,
    service: VendorService = Depends(get_vendor_service),
) -> BidRead:
    """Register a vendor's bid submission against a tender."""
    # Ensure payload vendor_id matches URL parameter
    payload.vendor_id = vendor_id
    return await service.submit_bid(payload)


@router.get("/tenders/{tender_id}/bids", response_model=List[BidRead])
async def list_bids_for_tender(
    tender_id: str,
    service: VendorService = Depends(get_vendor_service),
) -> List[BidRead]:
    """List all bids submitted for a specific tender."""
    return await service.list_bids_for_tender(tender_id)


@router.post("/bids/{bid_id}/documents", response_model=BidRead, status_code=status.HTTP_201_CREATED)
async def upload_bid_document(
    bid_id: str,
    file: UploadFile = File(...),
    document_type: str = Form(default="TECHNICAL_BID"),
    service: VendorService = Depends(get_vendor_service),
) -> BidRead:
    """Upload a technical or commercial proposal document for a bid."""
    content = await file.read()
    return await service.add_bid_document(
        bid_id=bid_id,
        filename=file.filename or "uploaded_bid_doc.pdf",
        content=content,
        document_type=document_type,
    )

