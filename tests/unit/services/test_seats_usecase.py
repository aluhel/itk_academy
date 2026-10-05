from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from itk_academy.core.cache import TTLCache
from itk_academy.events_provider.dto import SeatsDTO
from itk_academy.models.enums import EventStatus
from itk_academy.services.seats import (
    EventNotFoundError,
    EventNotPublishedError,
    GetSeatsUsecase,
)

EVENT_ID = uuid4()


def _make_event(status: str = EventStatus.PUBLISHED) -> MagicMock:
    event = MagicMock()
    event.id = EVENT_ID
    event.status = status
    return event


@pytest.fixture
def events_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def cache() -> TTLCache[list[str]]:
    return TTLCache(ttl_seconds=30)


async def test_returns_seats_on_cache_miss(
    events_repo: AsyncMock,
    client: AsyncMock,
    cache: TTLCache[list[str]],
) -> None:
    events_repo.get.return_value = _make_event()
    client.seats.return_value = SeatsDTO(event_id=EVENT_ID, seats=["A1", "A2"])

    usecase = GetSeatsUsecase(client=client, events=events_repo, cache=cache)
    result = await usecase.do(EVENT_ID)

    assert result == ["A1", "A2"]
    client.seats.assert_awaited_once_with(event_id=EVENT_ID)


async def test_second_call_uses_cache(
    events_repo: AsyncMock,
    client: AsyncMock,
    cache: TTLCache[list[str]],
) -> None:
    events_repo.get.return_value = _make_event()
    client.seats.return_value = SeatsDTO(event_id=EVENT_ID, seats=["A1"])

    usecase = GetSeatsUsecase(client=client, events=events_repo, cache=cache)
    await usecase.do(EVENT_ID)
    await usecase.do(EVENT_ID)

    assert client.seats.await_count == 1


async def test_raises_when_event_not_found(
    events_repo: AsyncMock,
    client: AsyncMock,
    cache: TTLCache[list[str]],
) -> None:
    events_repo.get.return_value = None

    usecase = GetSeatsUsecase(client=client, events=events_repo, cache=cache)
    with pytest.raises(EventNotFoundError):
        await usecase.do(EVENT_ID)

    client.seats.assert_not_awaited()


async def test_raises_when_event_not_published(
    events_repo: AsyncMock,
    client: AsyncMock,
    cache: TTLCache[list[str]],
) -> None:
    events_repo.get.return_value = _make_event(status="finished")

    usecase = GetSeatsUsecase(client=client, events=events_repo, cache=cache)
    with pytest.raises(EventNotPublishedError):
        await usecase.do(EVENT_ID)

    client.seats.assert_not_awaited()
