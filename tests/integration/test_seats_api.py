from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from itk_academy.events_provider.dto import SeatsDTO
from itk_academy.models.enums import EventStatus
from itk_academy.models.event import Event
from itk_academy.models.place import Place


async def _seed_published_event(db_session: AsyncSession) -> Event:
    place = Place(
        id=uuid4(),
        name="Hall",
        city="Moscow",
        address="Lenina 1",
        seats_pattern="A1-100",
        changed_at=datetime.now(tz=UTC),
        created_at=datetime.now(tz=UTC),
    )
    db_session.add(place)
    await db_session.flush()

    event = Event(
        id=uuid4(),
        place_id=place.id,
        name="Conference",
        event_time=datetime(2030, 1, 1, 17, 0, tzinfo=UTC),
        registration_deadline=datetime(2029, 12, 31, 17, 0, tzinfo=UTC),
        status=EventStatus.PUBLISHED,
        number_of_visitors=0,
        changed_at=datetime.now(tz=UTC),
        created_at=datetime.now(tz=UTC),
        status_changed_at=datetime.now(tz=UTC),
    )
    db_session.add(event)
    await db_session.commit()
    return event


async def _seed_finished_event(db_session: AsyncSession) -> Event:
    place = Place(
        id=uuid4(),
        name="Hall",
        city="Moscow",
        address="Lenina 1",
        seats_pattern="A1-100",
        changed_at=datetime.now(tz=UTC),
        created_at=datetime.now(tz=UTC),
    )
    db_session.add(place)
    await db_session.flush()

    event = Event(
        id=uuid4(),
        place_id=place.id,
        name="Finished conference",
        event_time=datetime(2020, 1, 1, 17, 0, tzinfo=UTC),
        registration_deadline=datetime(2019, 12, 31, 17, 0, tzinfo=UTC),
        status="finished",
        number_of_visitors=0,
        changed_at=datetime.now(tz=UTC),
        created_at=datetime.now(tz=UTC),
        status_changed_at=datetime.now(tz=UTC),
    )
    db_session.add(event)
    await db_session.commit()
    return event


async def test_get_seats_returns_200(
    api_client,
    db_session: AsyncSession,
    fake_provider_client: AsyncMock,
) -> None:
    event = await _seed_published_event(db_session)
    fake_provider_client.seats.return_value = SeatsDTO(event_id=event.id, seats=["A1", "A2", "A3"])

    response = await api_client.get(f"/api/events/{event.id}/seats")

    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == str(event.id)
    assert data["available_seats"] == ["A1", "A2", "A3"]


async def test_get_seats_returns_400_when_not_published(
    api_client,
    db_session: AsyncSession,
    fake_provider_client: AsyncMock,
) -> None:
    event = await _seed_finished_event(db_session)

    response = await api_client.get(f"/api/events/{event.id}/seats")

    assert response.status_code == 400
    fake_provider_client.seats.assert_not_awaited()


async def test_get_seats_returns_404_for_unknown(
    api_client,
    fake_provider_client: AsyncMock,
) -> None:
    response = await api_client.get(f"/api/events/{uuid4()}/seats")

    assert response.status_code == 404
