from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from itk_academy.models.enums import EventStatus
from itk_academy.models.event import Event
from itk_academy.models.place import Place
from itk_academy.repositories.events import SqlAlchemyEventRepository


async def _seed_place_and_events(db_session: AsyncSession) -> None:
    place = Place(
        id=uuid4(),
        name="Test Hall",
        city="Moscow",
        address="Lenina 1",
        seats_pattern="A1-100",
        changed_at=datetime.now(tz=UTC),
        created_at=datetime.now(tz=UTC),
    )
    db_session.add(place)
    await db_session.flush()

    for i in range(3):
        event = Event(
            id=uuid4(),
            place_id=place.id,
            name=f"Event {i}",
            event_time=datetime(2026, 1, 10 + i, 17, 0, tzinfo=UTC),
            registration_deadline=datetime(2026, 1, 9 + i, 17, 0, tzinfo=UTC),
            status=EventStatus.PUBLISHED,
            number_of_visitors=0,
            changed_at=datetime.now(tz=UTC),
            created_at=datetime.now(tz=UTC),
            status_changed_at=datetime.now(tz=UTC),
        )
        db_session.add(event)

    await db_session.commit()


async def test_get_returns_event(db_session: AsyncSession) -> None:
    await _seed_place_and_events(db_session)
    repo = SqlAlchemyEventRepository(db_session)

    events, total = await repo.list_paginated(date_from=None, limit=10, offset=0)

    assert total == 3
    assert len(events) == 3

    first = events[0]
    found = await repo.get(first.id)
    assert found is not None
    assert found.id == first.id


async def test_get_returns_none_for_unknown(db_session: AsyncSession) -> None:
    repo = SqlAlchemyEventRepository(db_session)
    result = await repo.get(uuid4())
    assert result is None


async def test_list_filter_by_date(db_session: AsyncSession) -> None:
    await _seed_place_and_events(db_session)
    repo = SqlAlchemyEventRepository(db_session)

    from datetime import date

    events, total = await repo.list_paginated(
        date_from=date(2026, 1, 11),
        limit=10,
        offset=0,
    )

    assert total == 2
    assert all(e.event_time >= datetime(2026, 1, 11, tzinfo=UTC) for e in events)


async def test_list_pagination(db_session: AsyncSession) -> None:
    await _seed_place_and_events(db_session)
    repo = SqlAlchemyEventRepository(db_session)

    page1, total = await repo.list_paginated(date_from=None, limit=2, offset=0)
    page2, _ = await repo.list_paginated(date_from=None, limit=2, offset=2)

    assert total == 3
    assert len(page1) == 2
    assert len(page2) == 1
    assert {e.id for e in page1}.isdisjoint({e.id for e in page2})
