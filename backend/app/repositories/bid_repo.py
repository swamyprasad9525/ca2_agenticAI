from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.bid import Bid, BidDocument
from backend.app.repositories.base import BaseRepository


class BidRepository(BaseRepository[Bid]):
    def __init__(self, session: AsyncSession):
        super().__init__(Bid, session)

    async def get_by_tender_and_vendor(self, tender_id: str, vendor_id: str) -> Optional[Bid]:
        stmt = (
            select(Bid)
            .where(Bid.tender_id == tender_id, Bid.vendor_id == vendor_id)
            .options(
                selectinload(Bid.documents),
                selectinload(Bid.vendor),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_bids_for_tender(self, tender_id: str) -> List[Bid]:
        stmt = (
            select(Bid)
            .where(Bid.tender_id == tender_id)
            .options(
                selectinload(Bid.documents),
                selectinload(Bid.vendor),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_document(self, document: BidDocument) -> BidDocument:
        self.session.add(document)
        await self.session.flush()
        await self.session.refresh(document)
        return document

