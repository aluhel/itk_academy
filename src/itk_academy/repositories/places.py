from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from itk_academy.models.place import Place


class SqlAlchemyPlaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, place_id: UUID) -> Place | None:
        stmt = select(Place).where(Place.id == place_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
