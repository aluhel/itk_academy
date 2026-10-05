from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from itk_academy.events_provider.dto import EventDTO, PlaceDTO
from itk_academy.events_provider.exceptions import EventsProviderServerError
from itk_academy.models.enums import SyncStatus
from itk_academy.services.sync import FIRST_SYNC_DATE, SyncEventsUsecase


def _make_event(name: str, changed_at: datetime) -> EventDTO:
    place_id = uuid4()
    return EventDTO(
        id=uuid4(),
        name=name,
        place=PlaceDTO(
            id=place_id,
            name="Hall",
            city="Moscow",
            address="Lenina 1",
            seats_pattern="A1-100",
            changed_at=changed_at,
            created_at=changed_at,
        ),
        event_time=changed_at,
        registration_deadline=changed_at,
        status="published",
        number_of_visitors=0,
        changed_at=changed_at,
        created_at=changed_at,
        status_changed_at=changed_at,
    )


@pytest.fixture
def sync_metadata() -> AsyncMock:
    mock = AsyncMock()
    mock.get_or_create.return_value = MagicMock(last_changed_at=None)
    return mock


@pytest.fixture
def events_repo() -> AsyncMock:
    mock = AsyncMock()
    mock.upsert_many.return_value = 1
    return mock


@pytest.fixture
def places_repo() -> AsyncMock:
    mock = AsyncMock()
    mock.upsert_many.return_value = 1
    return mock


@pytest.fixture
def client() -> AsyncMock:
    return AsyncMock()


async def test_sync_uses_first_date_when_no_metadata(
    sync_metadata: AsyncMock,
    events_repo: AsyncMock,
    places_repo: AsyncMock,
    client: AsyncMock,
) -> None:
    client.events.return_value = MagicMock(next_url=None, results=[])
    usecase = SyncEventsUsecase(
        client=client,
        events=events_repo,
        places=places_repo,
        sync_metadata=sync_metadata,
    )

    await usecase.do()

    client.events.assert_awaited_once_with(changed_at=FIRST_SYNC_DATE)


async def test_sync_uses_last_changed_at_when_present(
    events_repo: AsyncMock,
    places_repo: AsyncMock,
    client: AsyncMock,
) -> None:
    sync_metadata = AsyncMock()
    sync_metadata.get_or_create.return_value = MagicMock(
        last_changed_at=datetime(2026, 5, 4, 12, 0, tzinfo=UTC)
    )
    client.events.return_value = MagicMock(next_url=None, results=[])
    usecase = SyncEventsUsecase(
        client=client,
        events=events_repo,
        places=places_repo,
        sync_metadata=sync_metadata,
    )

    await usecase.do()

    from datetime import date

    client.events.assert_awaited_once_with(changed_at=date(2026, 5, 4))


async def test_sync_success_updates_metadata_and_upserts_events(
    sync_metadata: AsyncMock,
    events_repo: AsyncMock,
    places_repo: AsyncMock,
    client: AsyncMock,
) -> None:
    changed_at_1 = datetime(2026, 5, 4, 12, 0, tzinfo=UTC)
    changed_at_2 = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
    event_1 = _make_event("A", changed_at_1)
    event_2 = _make_event("B", changed_at_2)

    client.events.return_value = MagicMock(next_url=None, results=[event_1, event_2])

    usecase = SyncEventsUsecase(
        client=client,
        events=events_repo,
        places=places_repo,
        sync_metadata=sync_metadata,
    )

    result = await usecase.do()

    assert result["status"] == "success"
    assert result["events_count"] == 2

    assert events_repo.upsert_many.await_count == 2
    assert places_repo.upsert_many.await_count == 2

    final_update = sync_metadata.update.await_args_list[-1]
    assert final_update.kwargs["sync_status"] == SyncStatus.SUCCESS
    assert final_update.kwargs["last_changed_at"] == changed_at_2


async def test_sync_marks_failed_on_client_error(
    sync_metadata: AsyncMock,
    events_repo: AsyncMock,
    places_repo: AsyncMock,
    client: AsyncMock,
) -> None:
    client.events.side_effect = EventsProviderServerError("boom")

    usecase = SyncEventsUsecase(
        client=client,
        events=events_repo,
        places=places_repo,
        sync_metadata=sync_metadata,
    )

    with pytest.raises(EventsProviderServerError):
        await usecase.do()

    final_update = sync_metadata.update.await_args_list[-1]
    assert final_update.kwargs["sync_status"] == SyncStatus.FAILED
    assert "boom" in final_update.kwargs["last_error"]


async def test_sync_iterates_over_pages(
    sync_metadata: AsyncMock,
    events_repo: AsyncMock,
    places_repo: AsyncMock,
    client: AsyncMock,
) -> None:
    """Проверяем, что пагинация обходит все страницы и события суммируются."""
    from itk_academy.events_provider.dto import EventsPage

    changed_at = datetime(2026, 5, 4, 12, 0, tzinfo=UTC)
    event_1 = _make_event("A", changed_at)
    event_2 = _make_event("B", changed_at)

    client.events.return_value = EventsPage(
        results=[event_1],
        next_url="http://test.local/api/events/?cursor=xyz",
        previous_url=None,
    )
    client.events_by_url.return_value = EventsPage(
        results=[event_2],
        next_url=None,
        previous_url=None,
    )

    usecase = SyncEventsUsecase(
        client=client,
        events=events_repo,
        places=places_repo,
        sync_metadata=sync_metadata,
    )

    result = await usecase.do()

    assert result["events_count"] == 2
    client.events_by_url.assert_awaited_once_with("http://test.local/api/events/?cursor=xyz")
