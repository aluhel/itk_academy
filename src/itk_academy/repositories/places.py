from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from itk_academy.models.place import Place


class SqlAlchemyPlaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, place_id: UUID) -> Place | None:
        stmt = select(Place).where(Place.id == place_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_many(self, places: Sequence[dict]) -> int:
        if not places:
            return 0

        stmt = insert(Place).values(list(places))
        stmt = stmt.on_conflict_do_update(
            index_elements=[Place.id],
            set_={
                "name": stmt.excluded.name,
                "city": stmt.excluded.city,
                "address": stmt.excluded.address,
                "seats_pattern": stmt.excluded.seats_pattern,
                "changed_at": stmt.excluded.changed_at,
                "created_at": stmt.excluded.created_at,
            },
        )
        await self._session.execute(stmt)
        await self._session.commit()
        return len(places)
