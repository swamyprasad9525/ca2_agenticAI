from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.tender import Tender, TenderDocument
from backend.app.repositories.base import BaseRepository


class TenderRepository(BaseRepository[Tender]):
    def __init__(self, session: AsyncSession):
        super().__init__(Tender, session)

    async def get_by_reference(self, reference_number: str) -> Optional[Tender]:
        result = await self.session.execute(
            select(Tender).where(Tender.reference_number == reference_number)
        )
        return result.scalars().first()

    async def get_with_relations(self, tender_id: str) -> Optional[Tender]:
        stmt = (
            select(Tender)
            .where(Tender.id == tender_id)
            .options(
                selectinload(Tender.documents),
                selectinload(Tender.criteria),
                selectinload(Tender.mandatory_requirements),
                selectinload(Tender.bids),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def add_document(self, document: TenderDocument) -> TenderDocument:
        self.session.add(document)
        await self.session.flush()
        await self.session.refresh(document)
        return document

