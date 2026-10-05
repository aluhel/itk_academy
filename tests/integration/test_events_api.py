from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from itk_academy.models.enums import EventStatus
from itk_academy.models.event import Event
from itk_academy.models.place import Place


async def _seed_events(db_session: AsyncSession) -> list[Event]:
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

    events = []
    for i in range(5):
        event = Event(
            id=uuid4(),
            place_id=place.id,
            name=f"Event {i}",
            event_time=datetime(2026, 1, 10 + i, 17, 0, tzinfo=UTC),
            registration_deadline=datetime(2026, 1, 9 + i, 17, 0, tzinfo=UTC),
            status=EventStatus.PUBLISHED,
            number_of_visitors=i,
            changed_at=datetime.now(tz=UTC),
            created_at=datetime.now(tz=UTC),
            status_changed_at=datetime.now(tz=UTC),
        )
        db_session.add(event)
        events.append(event)

    await db_session.commit()
    return events


async def test_list_events_returns_paginated_format(
    api_client,
    db_session: AsyncSession,
) -> None:
    await _seed_events(db_session)

    response = await api_client.get("/api/events?page=1&page_size=2")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 5
    assert data["previous"] is None
    assert data["next"] is not None
    assert "page=2" in data["next"]
    assert len(data["results"]) == 2

    # Проверяем, что в списке place без seats_pattern
    first = data["results"][0]
    assert "seats_pattern" not in first["place"]
    assert set(first["place"].keys()) == {"id", "name", "city", "address"}


async def test_list_events_previous_on_second_page(
    api_client,
    db_session: AsyncSession,
) -> None:
    await _seed_events(db_session)

    response = await api_client.get("/api/events?page=2&page_size=2")

    assert response.status_code == 200
    data = response.json()
    assert data["previous"] is not None
    assert "page=1" in data["previous"]


async def test_list_events_date_filter(
    api_client,
    db_session: AsyncSession,
) -> None:
    await _seed_events(db_session)

    response = await api_client.get("/api/events?date_from=2026-01-12")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3  # 12, 13, 14 января
    for item in data["results"]:
        assert item["event_time"] >= "2026-01-12"


async def test_get_event_detail_returns_seats_pattern(
    api_client,
    db_session: AsyncSession,
) -> None:
    events = await _seed_events(db_session)
    event_id = events[0].id

    response = await api_client.get(f"/api/events/{event_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(event_id)
    assert data["place"]["seats_pattern"] == "A1-100"


async def test_get_event_returns_404_for_unknown_uuid(
    api_client,
    db_session: AsyncSession,
) -> None:
    response = await api_client.get(f"/api/events/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"


async def test_get_event_returns_404_for_invalid_uuid(
    api_client,
) -> None:
    response = await api_client.get("/api/events/not-a-uuid")

    assert response.status_code == 404
