from collections.abc import Sequence
from datetime import date, datetime, time
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from itk_academy.config import get_settings
from itk_academy.domain.entities import EventEntity, PlaceEntity
from itk_academy.models.event import Event
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


def _to_event_entity(event: Event) -> EventEntity:
    return EventEntity(
        id=event.id,
        place_id=event.place_id,
        name=event.name,
        place=_to_place_entity(event.place) if event.place else None,
        event_time=event.event_time,
        registration_deadline=event.registration_deadline,
        status=event.status,
        number_of_visitors=event.number_of_visitors,
        changed_at=event.changed_at,
        created_at=event.created_at,
        status_changed_at=event.status_changed_at,
    )


class SqlAlchemyEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tz = ZoneInfo(get_settings().timezone)

    async def get(self, event_id: UUID) -> EventEntity | None:
        stmt = select(Event).where(Event.id == event_id).options(selectinload(Event.place))
        result = await self._session.execute(stmt)
        event = result.scalar_one_or_none()
        return _to_event_entity(event) if event else None

    async def list_paginated(
        self,
        *,
        date_from: date | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[EventEntity], int]:
        stmt = select(Event).options(selectinload(Event.place))
        count_stmt = select(func.count()).select_from(Event)

        if date_from is not None:
            start_dt = datetime.combine(date_from, time.min, tzinfo=self._tz)
            stmt = stmt.where(Event.event_time >= start_dt)
            count_stmt = count_stmt.where(Event.event_time >= start_dt)

        stmt = stmt.order_by(Event.event_time.asc(), Event.id.asc()).limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        events = result.scalars().all()

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        return [_to_event_entity(e) for e in events], total

    async def upsert_many(self, events: Sequence[EventEntity]) -> int:
        if not events:
            return 0

        values = [
            {
                "id": e.id,
                "place_id": e.place_id,
                "name": e.name,
                "event_time": e.event_time,
                "registration_deadline": e.registration_deadline,
                "status": e.status,
                "number_of_visitors": e.number_of_visitors,
                "changed_at": e.changed_at,
                "created_at": e.created_at,
                "status_changed_at": e.status_changed_at,
            }
            for e in events
        ]

        stmt = insert(Event).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Event.id],
            set_={
                "place_id": stmt.excluded.place_id,
                "name": stmt.excluded.name,
                "event_time": stmt.excluded.event_time,
                "registration_deadline": stmt.excluded.registration_deadline,
                "status": stmt.excluded.status,
                "number_of_visitors": stmt.excluded.number_of_visitors,
                "changed_at": stmt.excluded.changed_at,
                "created_at": stmt.excluded.created_at,
                "status_changed_at": stmt.excluded.status_changed_at,
            },
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return len(events)
