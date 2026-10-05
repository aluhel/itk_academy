from collections.abc import Sequence
from datetime import UTC, date, datetime, time
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from itk_academy.models.event import Event


class SqlAlchemyEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, event_id: UUID) -> Event | None:
        stmt = select(Event).where(Event.id == event_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        *,
        date_from: date | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Event], int]:
        stmt = select(Event)
        count_stmt = select(func.count()).select_from(Event)

        if date_from is not None:
            start_dt = datetime.combine(date_from, time.min, tzinfo=UTC)
            stmt = stmt.where(Event.event_time >= start_dt)
            count_stmt = count_stmt.where(Event.event_time >= start_dt)

        stmt = stmt.order_by(Event.event_time.asc()).limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        events = result.scalars().all()

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        return events, total

    async def upsert_many(self, events: Sequence[dict]) -> int:
        if not events:
            return 0

        stmt = insert(Event).values(list(events))
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
        await self._session.commit()
        return len(events)
