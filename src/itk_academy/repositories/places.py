from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from itk_academy.domain.entities import PlaceEntity
from itk_academy.models.place import Place


def _to_place_entity(place: Place) -> PlaceEntity:
    return PlaceEntity(
        id=place.id,
        name=place.name,
        city=place.city,
        address=place.address,
        seats_pattern=place.seats_pattern,
        changed_at=place.changed_at,
        created_at=place.created_at,
    )


class SqlAlchemyPlaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, place_id: UUID) -> PlaceEntity | None:
        stmt = select(Place).where(Place.id == place_id)
        result = await self._session.execute(stmt)
        place = result.scalar_one_or_none()
        return _to_place_entity(place) if place else None

    async def upsert_many(self, places: Sequence[PlaceEntity]) -> int:
        if not places:
            return 0

        values = [
            {
                "id": p.id,
                "name": p.name,
                "city": p.city,
                "address": p.address,
                "seats_pattern": p.seats_pattern,
                "changed_at": p.changed_at,
                "created_at": p.created_at,
            }
            for p in places
        ]

        stmt = insert(Place).values(values)
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
        await self._session.flush()
        return len(places)
