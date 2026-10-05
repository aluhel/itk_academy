import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest

from itk_academy.events_provider.client import EventsProviderClient
from itk_academy.events_provider.exceptions import (
    EventsProviderBadRequestError,
    EventsProviderNotFoundError,
)

EVENT_ID = uuid4()
TICKET_ID = uuid4()


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


async def test_register_sends_payload_and_returns_ticket(
    client: EventsProviderClient, mock_http: AsyncMock
) -> None:
    mock_http.post.return_value = _make_response(201, {"ticket_id": str(TICKET_ID)})

    result = await client.register(
        event_id=EVENT_ID,
        first_name="Ivan",
        last_name="Ivanov",
        email="ivan@example.com",
        seat="A15",
    )

    assert result.ticket_id == TICKET_ID
    call_args = mock_http.post.call_args
    assert call_args.args[0] == f"/api/events/{EVENT_ID}/register/"
    assert call_args.kwargs["json"] == {
        "first_name": "Ivan",
        "last_name": "Ivanov",
        "email": "ivan@example.com",
        "seat": "A15",
    }


async def test_register_raises_bad_request_for_taken_seat(
    client: EventsProviderClient, mock_http: AsyncMock
) -> None:
    mock_http.post.return_value = _make_response(
        400, text='["This ticket is not available (already sold)."]'
    )

    with pytest.raises(EventsProviderBadRequestError):
        await client.register(
            event_id=EVENT_ID,
            first_name="Ivan",
            last_name="Ivanov",
            email="ivan@example.com",
            seat="A15",
        )


async def test_register_raises_not_found(
    client: EventsProviderClient, mock_http: AsyncMock
) -> None:
    mock_http.post.return_value = _make_response(404, {"detail": "Event not found."})

    with pytest.raises(EventsProviderNotFoundError):
        await client.register(
            event_id=EVENT_ID,
            first_name="Ivan",
            last_name="Ivanov",
            email="ivan@example.com",
            seat="A15",
        )


async def test_unregister_sends_ticket_id(
    client: EventsProviderClient, mock_http: AsyncMock
) -> None:
    mock_http.request.return_value = _make_response(200, {"success": True})

    await client.unregister(event_id=EVENT_ID, ticket_id=TICKET_ID)

    call_args = mock_http.request.call_args
    assert call_args.args[0] == "DELETE"
    assert call_args.args[1] == f"/api/events/{EVENT_ID}/unregister/"
    assert call_args.kwargs["json"] == {"ticket_id": str(TICKET_ID)}


async def test_unregister_handles_empty_response(
    client: EventsProviderClient, mock_http: AsyncMock
) -> None:
    mock_http.request.return_value = _make_response(200, text="")

    await client.unregister(event_id=EVENT_ID, ticket_id=TICKET_ID)

    mock_http.request.assert_awaited_once()
