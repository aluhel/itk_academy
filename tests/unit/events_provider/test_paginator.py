from datetime import date
from unittest.mock import AsyncMock
from uuid import uuid4

from itk_academy.events_provider.dto import EventDTO, EventsPage, PlaceDTO
from itk_academy.events_provider.paginator import EventsPaginator


def _make_event(name: str) -> EventDTO:
    from datetime import datetime

    now = datetime.now().astimezone()
    return EventDTO(
        id=uuid4(),
        name=name,
        place=PlaceDTO(
            id=uuid4(),
            name="Hall",
            city="Moscow",
            address="Lenina 1",
            seats_pattern="A1-100",
            changed_at=now,
            created_at=now,
        ),
        event_time=now,
        registration_deadline=now,
        status="published",
        number_of_visitors=0,
        changed_at=now,
        created_at=now,
        status_changed_at=now,
    )


async def test_paginator_yields_all_events_from_single_page() -> None:
    client = AsyncMock()
    events = [_make_event("A"), _make_event("B"), _make_event("C")]
    client.events.return_value = EventsPage(results=events, next_url=None, previous_url=None)

    paginator = EventsPaginator(client, changed_at=date(2000, 1, 1))
    collected = [event async for event in paginator]

    assert [e.name for e in collected] == ["A", "B", "C"]
    client.events.assert_awaited_once_with(changed_at=date(2000, 1, 1))
    client.events_by_url.assert_not_awaited()


async def test_paginator_follows_next_url_across_pages() -> None:
    client = AsyncMock()
    page1_events = [_make_event("A"), _make_event("B")]
    page2_events = [_make_event("C")]

    client.events.return_value = EventsPage(
        results=page1_events,
        next_url="http://test.local/api/events/?cursor=xyz",
        previous_url=None,
    )
    client.events_by_url.return_value = EventsPage(
        results=page2_events,
        next_url=None,
        previous_url="http://test.local/api/events/",
    )

    paginator = EventsPaginator(client, changed_at=date(2000, 1, 1))
    collected = [event async for event in paginator]

    assert [e.name for e in collected] == ["A", "B", "C"]
    client.events.assert_awaited_once_with(changed_at=date(2000, 1, 1))
    client.events_by_url.assert_awaited_once_with("http://test.local/api/events/?cursor=xyz")


async def test_paginator_stops_on_empty_first_page() -> None:
    client = AsyncMock()
    client.events.return_value = EventsPage(results=[], next_url=None, previous_url=None)

    paginator = EventsPaginator(client, changed_at=date(2000, 1, 1))
    collected = [event async for event in paginator]

    assert collected == []
    client.events.assert_awaited_once()
    client.events_by_url.assert_not_awaited()


async def test_paginator_handles_multiple_pages() -> None:
    client = AsyncMock()
    client.events.return_value = EventsPage(
        results=[_make_event("A")],
        next_url="http://test.local/api/events/?cursor=1",
        previous_url=None,
    )
    client.events_by_url.side_effect = [
        EventsPage(
            results=[_make_event("B")],
            next_url="http://test.local/api/events/?cursor=2",
            previous_url=None,
        ),
        EventsPage(results=[_make_event("C")], next_url=None, previous_url=None),
    ]

    paginator = EventsPaginator(client, changed_at=date(2000, 1, 1))
    collected = [event async for event in paginator]

    assert [e.name for e in collected] == ["A", "B", "C"]
    assert client.events_by_url.await_count == 2
