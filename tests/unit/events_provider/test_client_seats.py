import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest

from itk_academy.events_provider.client import EventsProviderClient
from itk_academy.events_provider.exceptions import (
    EventsProviderNotFoundError,
    EventsProviderServerError,
)

EVENT_ID = uuid4()


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


async def test_seats_returns_seats(client: EventsProviderClient, mock_http: AsyncMock) -> None:
    mock_http.request.return_value = _make_response(200, {"seats": ["A1", "A2", "B5"]})

    result = await client.seats(event_id=EVENT_ID)

    assert result.event_id == EVENT_ID
    assert result.seats == ["A1", "A2", "B5"]
    call_args = mock_http.request.call_args
    assert call_args.args[0] == "GET"
    assert call_args.args[1] == f"/api/events/{EVENT_ID}/seats/"


async def test_seats_raises_not_found(client: EventsProviderClient, mock_http: AsyncMock) -> None:
    mock_http.request.return_value = _make_response(404, {"detail": "Event not found"})

    with pytest.raises(EventsProviderNotFoundError):
        await client.seats(event_id=EVENT_ID)


async def test_seats_raises_server_error(
    client: EventsProviderClient, mock_http: AsyncMock
) -> None:
    mock_http.request.return_value = _make_response(
        500, text="UnexpectedEventStatus: Event is not published for registration."
    )

    with pytest.raises(EventsProviderServerError):
        await client.seats(event_id=EVENT_ID)
