from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from itk_academy.events_provider.dto import SeatsDTO, TicketDTO
from itk_academy.models.enums import EventStatus
from itk_academy.models.event import Event
from itk_academy.models.place import Place
from itk_academy.models.ticket import Ticket


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
        event_time=datetime.now(tz=UTC) + timedelta(days=30),
        registration_deadline=datetime.now(tz=UTC) + timedelta(days=29),
        status=EventStatus.PUBLISHED,
        number_of_visitors=0,
        changed_at=datetime.now(tz=UTC),
        created_at=datetime.now(tz=UTC),
        status_changed_at=datetime.now(tz=UTC),
    )
    db_session.add(event)
    await db_session.commit()
    return event


async def test_post_ticket_returns_201(
    api_client,
    db_session: AsyncSession,
    fake_provider_client,
) -> None:
    event = await _seed_published_event(db_session)
    provider_ticket_id = uuid4()
    fake_provider_client.seats.return_value = SeatsDTO(event_id=event.id, seats=["A1"])
    fake_provider_client.register.return_value = TicketDTO(ticket_id=provider_ticket_id)

    response = await api_client.post(
        "/api/tickets",
        json={
            "event_id": str(event.id),
            "first_name": "Ivan",
            "last_name": "Ivanov",
            "email": "ivan@example.com",
            "seat": "A1",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "ticket_id" in data


async def test_post_ticket_returns_404_for_unknown_event(
    api_client,
    fake_provider_client,
) -> None:
    response = await api_client.post(
        "/api/tickets",
        json={
            "event_id": str(uuid4()),
            "first_name": "Ivan",
            "last_name": "Ivanov",
            "email": "ivan@example.com",
            "seat": "A1",
        },
    )

    assert response.status_code == 404


async def test_post_ticket_returns_422_for_invalid_email(
    api_client,
    fake_provider_client,
) -> None:
    response = await api_client.post(
        "/api/tickets",
        json={
            "event_id": str(uuid4()),
            "first_name": "Ivan",
            "last_name": "Ivanov",
            "email": "not-an-email",
            "seat": "A1",
        },
    )

    assert response.status_code == 422


async def test_delete_ticket_returns_success(
    api_client,
    db_session: AsyncSession,
    fake_provider_client,
) -> None:
    event = await _seed_published_event(db_session)

    ticket = Ticket(
        id=uuid4(),
        provider_ticket_id=uuid4(),
        event_id=event.id,
        first_name="Ivan",
        last_name="Ivanov",
        email="ivan@example.com",
        seat="A1",
        created_at=datetime.now(tz=UTC),
    )
    db_session.add(ticket)
    await db_session.commit()

    response = await api_client.delete(f"/api/tickets/{ticket.id}")

    assert response.status_code == 200
    assert response.json() == {"success": True}
    fake_provider_client.unregister.assert_awaited_once()


async def test_delete_ticket_returns_404_for_unknown(
    api_client,
    fake_provider_client,
) -> None:
    response = await api_client.delete(f"/api/tickets/{uuid4()}")

    assert response.status_code == 404


async def test_post_ticket_returns_502_on_provider_error(
    api_client,
    db_session: AsyncSession,
    fake_provider_client: AsyncMock,
) -> None:
    from itk_academy.events_provider.exceptions import EventsProviderUnavailableError

    event = await _seed_published_event(db_session)
    fake_provider_client.seats.side_effect = EventsProviderUnavailableError("timeout")

    response = await api_client.post(
        "/api/tickets",
        json={
            "event_id": str(event.id),
            "first_name": "Ivan",
            "last_name": "Ivanov",
            "email": "ivan@example.com",
            "seat": "A1",
        },
    )

    assert response.status_code == 502


async def test_post_ticket_overwrites_stale_local_record(
    api_client,
    db_session: AsyncSession,
    fake_provider_client,
) -> None:
    """If a stale local record exists on a seat (cancelled outside our API),
    the new registration should overwrite it instead of failing with 500."""
    event = await _seed_published_event(db_session)

    stale_ticket = Ticket(
        id=uuid4(),
        provider_ticket_id=uuid4(),
        event_id=event.id,
        first_name="Old",
        last_name="Owner",
        email="old@example.com",
        seat="A1",
        created_at=datetime.now(tz=UTC),
    )
    db_session.add(stale_ticket)
    await db_session.commit()
    stale_id = stale_ticket.id

    new_provider_ticket_id = uuid4()
    fake_provider_client.seats.return_value = SeatsDTO(event_id=event.id, seats=["A1"])
    fake_provider_client.register.return_value = TicketDTO(ticket_id=new_provider_ticket_id)

    response = await api_client.post(
        "/api/tickets",
        json={
            "event_id": str(event.id),
            "first_name": "New",
            "last_name": "Owner",
            "email": "new@example.com",
            "seat": "A1",
        },
    )

    assert response.status_code == 201

    # Exactly one row must remain for (event_id, A1) — with the new data.
    from sqlalchemy import select as sa_select

    result = await db_session.execute(
        sa_select(Ticket).where(Ticket.event_id == event.id, Ticket.seat == "A1")
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].email == "new@example.com"
    assert rows[0].first_name == "New"
    # id обновлён, старый владелец не сможет отменить новый билет
    assert rows[0].id != stale_id
    assert rows[0].provider_ticket_id == new_provider_ticket_id
