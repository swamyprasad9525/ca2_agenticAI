from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.vendor import Vendor
from backend.app.repositories.base import BaseRepository


class VendorRepository(BaseRepository[Vendor]):
    def __init__(self, session: AsyncSession):
        super().__init__(Vendor, session)

    async def get_by_name(self, name: str) -> Optional[Vendor]:
        result = await self.session.execute(
            select(Vendor).where(Vendor.name == name)
        )
        return result.scalars().first()

    async def get_by_registration(self, registration_number: str) -> Optional[Vendor]:
        result = await self.session.execute(
            select(Vendor).where(Vendor.registration_number == registration_number)
        )
        return result.scalars().first()

