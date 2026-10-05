import json
from datetime import date
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest

from itk_academy.events_provider.client import EventsProviderClient
from itk_academy.events_provider.exceptions import (
    EventsProviderAuthError,
    EventsProviderNotFoundError,
    EventsProviderServerError,
)

PLACE_ID = uuid4()
EVENT_ID = uuid4()


def _make_event_payload() -> dict:
    return {
        "id": str(EVENT_ID),
        "name": "Conference",
        "place": {
            "id": str(PLACE_ID),
            "name": "Hall",
            "city": "Moscow",
            "address": "Lenina 1",
            "seats_pattern": "A1-100",
            "changed_at": "2025-01-01T03:00:00+03:00",
            "created_at": "2025-01-01T03:00:00+03:00",
        },
        "event_time": "2026-01-11T17:00:00+03:00",
        "registration_deadline": "2026-01-10T17:00:00+03:00",
        "status": "published",
        "number_of_visitors": 5,
        "changed_at": "2026-01-04T22:28:35+03:00",
        "created_at": "2026-01-04T22:28:35+03:00",
        "status_changed_at": "2026-01-04T22:28:35+03:00",
    }


def _make_response(status_code: int, payload: dict | None = None, text: str = "") -> httpx.Response:
    if payload is not None:
        return httpx.Response(
            status_code=status_code,
            content=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
    return httpx.Response(
        status_code=status_code,
        content=text.encode("utf-8"),
    )


@pytest.fixture
def mock_http() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(mock_http: AsyncMock) -> EventsProviderClient:
    with patch(
        "itk_academy.events_provider.client.httpx.AsyncClient",
        return_value=mock_http,
    ):
        yield EventsProviderClient(base_url="http://test.local", api_key="test-key")


async def test_events_sends_changed_at_and_api_key(
    client: EventsProviderClient, mock_http: AsyncMock
) -> None:
    mock_http.get.return_value = _make_response(
        200,
        {"next": None, "previous": None, "results": []},
    )

    await client.events(changed_at=date(2000, 1, 1))

    mock_http.get.assert_awaited_once()
    call_args = mock_http.get.call_args
    assert call_args.args[0] == "/api/events/"
    assert call_args.kwargs["params"] == {"changed_at": "2000-01-01"}


async def test_events_passes_cursor(client: EventsProviderClient, mock_http: AsyncMock) -> None:
    mock_http.get.return_value = _make_response(
        200,
        {"next": None, "previous": None, "results": []},
    )

    await client.events(changed_at=date(2026, 1, 1), cursor="abc")

    params = mock_http.get.call_args.kwargs["params"]
    assert params == {"changed_at": "2026-01-01", "cursor": "abc"}


async def test_events_parses_response(client: EventsProviderClient, mock_http: AsyncMock) -> None:
    mock_http.get.return_value = _make_response(
        200,
        {
            "next": "http://test.local/api/events/?cursor=xyz",
            "previous": None,
            "results": [_make_event_payload()],
        },
    )

    page = await client.events(changed_at=date(2000, 1, 1))

    assert page.next_url == "http://test.local/api/events/?cursor=xyz"
    assert page.previous_url is None
    assert len(page.results) == 1
    event = page.results[0]
    assert event.id == EVENT_ID
    assert event.name == "Conference"
    assert event.place.id == PLACE_ID
    assert event.place.city == "Moscow"
    assert event.status == "published"
    assert event.event_time.year == 2026
    assert event.event_time.month == 1
    assert event.event_time.day == 11
    assert event.event_time.hour == 17


async def test_events_raises_auth_error(client: EventsProviderClient, mock_http: AsyncMock) -> None:
    mock_http.get.return_value = _make_response(401, {"detail": "Invalid API key"})

    with pytest.raises(EventsProviderAuthError):
        await client.events(changed_at=date(2000, 1, 1))


async def test_events_raises_not_found(client: EventsProviderClient, mock_http: AsyncMock) -> None:
    mock_http.get.return_value = _make_response(404, {"detail": "Event not found"})

    with pytest.raises(EventsProviderNotFoundError):
        await client.events(changed_at=date(2000, 1, 1))


async def test_events_raises_server_error(
    client: EventsProviderClient, mock_http: AsyncMock
) -> None:
    mock_http.get.return_value = _make_response(500, text="Internal Server Error")

    with pytest.raises(EventsProviderServerError):
        await client.events(changed_at=date(2000, 1, 1))
