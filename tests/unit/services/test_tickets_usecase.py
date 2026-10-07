from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from itk_academy.events_provider.dto import SeatsDTO, TicketDTO
from itk_academy.events_provider.exceptions import (
    EventsProviderBadRequestError,
    EventsProviderNotFoundError,
)
from itk_academy.models.enums import EventStatus
from itk_academy.services.tickets import (
    CancelTicketUsecase,
    CreateTicketUsecase,
    TicketEventNotFoundError,
    TicketEventNotPublishedError,
    TicketNotFoundError,
    TicketRegistrationClosedError,
    TicketSeatNotAvailableError,
)

EVENT_ID = uuid4()
TICKET_ID = uuid4()
PROVIDER_TICKET_ID = uuid4()


def _make_event(
    *,
    status: str = EventStatus.PUBLISHED,
    deadline_in_days: int = 7,
) -> MagicMock:
    event = MagicMock()
    event.id = EVENT_ID
    event.status = status
    event.registration_deadline = datetime.now(tz=UTC) + timedelta(days=deadline_in_days)
    return event


@pytest.fixture
def events_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def tickets_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def cache() -> MagicMock:
    return MagicMock()


@pytest.fixture
def uow() -> AsyncMock:
    return AsyncMock()


# ============ CreateTicketUsecase ============


async def test_create_ticket_success(
    events_repo: AsyncMock,
    tickets_repo: AsyncMock,
    client: AsyncMock,
    cache: MagicMock,
    uow: AsyncMock,
) -> None:
    events_repo.get.return_value = _make_event()
    client.seats.return_value = SeatsDTO(event_id=EVENT_ID, seats=["A1", "A2"])
    client.register.return_value = TicketDTO(ticket_id=PROVIDER_TICKET_ID)

    ticket_mock = MagicMock()
    ticket_mock.id = TICKET_ID
    tickets_repo.save_for_seat.return_value = ticket_mock

    usecase = CreateTicketUsecase(
        client=client,
        events=events_repo,
        tickets=tickets_repo,
        cache=cache,
        uow=uow,
    )
    result = await usecase.do(
        event_id=EVENT_ID,
        first_name="Ivan",
        last_name="Ivanov",
        email="ivan@example.com",
        seat="A1",
    )

    assert result.id == TICKET_ID
    client.register.assert_awaited_once()
    tickets_repo.save_for_seat.assert_awaited_once()
    uow.commit.assert_awaited_once()
    create_kwargs = tickets_repo.save_for_seat.await_args.kwargs
    assert create_kwargs["provider_ticket_id"] == PROVIDER_TICKET_ID
    assert create_kwargs["seat"] == "A1"


async def test_create_ticket_event_not_found(
    events_repo: AsyncMock,
    tickets_repo: AsyncMock,
    client: AsyncMock,
    cache: MagicMock,
    uow: AsyncMock,
) -> None:
    events_repo.get.return_value = None

    usecase = CreateTicketUsecase(
        client=client,
        events=events_repo,
        tickets=tickets_repo,
        cache=cache,
        uow=uow,
    )
    with pytest.raises(TicketEventNotFoundError):
        await usecase.do(
            event_id=EVENT_ID,
            first_name="Ivan",
            last_name="Ivanov",
            email="ivan@example.com",
            seat="A1",
        )

    client.seats.assert_not_awaited()
    client.register.assert_not_awaited()
    uow.commit.assert_not_awaited()


async def test_create_ticket_event_not_published(
    events_repo: AsyncMock,
    tickets_repo: AsyncMock,
    client: AsyncMock,
    cache: MagicMock,
    uow: AsyncMock,
) -> None:
    events_repo.get.return_value = _make_event(status="finished")

    usecase = CreateTicketUsecase(
        client=client,
        events=events_repo,
        tickets=tickets_repo,
        cache=cache,
        uow=uow,
    )
    with pytest.raises(TicketEventNotPublishedError):
        await usecase.do(
            event_id=EVENT_ID,
            first_name="Ivan",
            last_name="Ivanov",
            email="ivan@example.com",
            seat="A1",
        )

    client.seats.assert_not_awaited()


async def test_create_ticket_deadline_passed(
    events_repo: AsyncMock,
    tickets_repo: AsyncMock,
    client: AsyncMock,
    cache: MagicMock,
    uow: AsyncMock,
) -> None:
    events_repo.get.return_value = _make_event(deadline_in_days=-1)

    usecase = CreateTicketUsecase(
        client=client,
        events=events_repo,
        tickets=tickets_repo,
        cache=cache,
        uow=uow,
    )
    with pytest.raises(TicketRegistrationClosedError):
        await usecase.do(
            event_id=EVENT_ID,
            first_name="Ivan",
            last_name="Ivanov",
            email="ivan@example.com",
            seat="A1",
        )

    client.seats.assert_not_awaited()


async def test_create_ticket_seat_not_available(
    events_repo: AsyncMock,
    tickets_repo: AsyncMock,
    client: AsyncMock,
    cache: MagicMock,
    uow: AsyncMock,
) -> None:
    events_repo.get.return_value = _make_event()
    client.seats.return_value = SeatsDTO(event_id=EVENT_ID, seats=["A1", "A2"])

    usecase = CreateTicketUsecase(
        client=client,
        events=events_repo,
        tickets=tickets_repo,
        cache=cache,
        uow=uow,
    )
    with pytest.raises(TicketSeatNotAvailableError):
        await usecase.do(
            event_id=EVENT_ID,
            first_name="Ivan",
            last_name="Ivanov",
            email="ivan@example.com",
            seat="Z99",
        )

    client.register.assert_not_awaited()


async def test_create_ticket_provider_race_returns_seat_unavailable(
    events_repo: AsyncMock,
    tickets_repo: AsyncMock,
    client: AsyncMock,
    cache: MagicMock,
    uow: AsyncMock,
) -> None:
    """Если провайдер вернул 400 (место занято) — маппим в TicketSeatNotAvailableError."""
    events_repo.get.return_value = _make_event()
    client.seats.return_value = SeatsDTO(event_id=EVENT_ID, seats=["A1"])
    client.register.side_effect = EventsProviderBadRequestError("already sold")

    usecase = CreateTicketUsecase(
        client=client,
        events=events_repo,
        tickets=tickets_repo,
        cache=cache,
        uow=uow,
    )
    with pytest.raises(TicketSeatNotAvailableError):
        await usecase.do(
            event_id=EVENT_ID,
            first_name="Ivan",
            last_name="Ivanov",
            email="ivan@example.com",
            seat="A1",
        )

    tickets_repo.save_for_seat.assert_not_awaited()


async def test_create_ticket_invalidates_cache_on_success(
    events_repo: AsyncMock,
    tickets_repo: AsyncMock,
    client: AsyncMock,
    cache: MagicMock,
    uow: AsyncMock,
) -> None:
    events_repo.get.return_value = _make_event()
    client.seats.return_value = SeatsDTO(event_id=EVENT_ID, seats=["A1"])
    client.register.return_value = TicketDTO(ticket_id=PROVIDER_TICKET_ID)

    ticket_mock = MagicMock()
    ticket_mock.id = TICKET_ID
    tickets_repo.save_for_seat.return_value = ticket_mock

    usecase = CreateTicketUsecase(
        client=client,
        events=events_repo,
        tickets=tickets_repo,
        cache=cache,
        uow=uow,
    )
    await usecase.do(
        event_id=EVENT_ID,
        first_name="Ivan",
        last_name="Ivanov",
        email="ivan@example.com",
        seat="A1",
    )

    cache.invalidate.assert_called_once_with(f"seats:{EVENT_ID}")


async def test_create_ticket_compensates_on_save_failure(
    events_repo: AsyncMock,
    tickets_repo: AsyncMock,
    client: AsyncMock,
    cache: MagicMock,
    uow: AsyncMock,
) -> None:
    events_repo.get.return_value = _make_event()
    client.seats.return_value = SeatsDTO(event_id=EVENT_ID, seats=["A1"])
    client.register.return_value = TicketDTO(ticket_id=PROVIDER_TICKET_ID)
    tickets_repo.save_for_seat.side_effect = RuntimeError("db down")

    usecase = CreateTicketUsecase(
        client=client,
        events=events_repo,
        tickets=tickets_repo,
        cache=cache,
        uow=uow,
    )
    with pytest.raises(RuntimeError):
        await usecase.do(
            event_id=EVENT_ID,
            first_name="Ivan",
            last_name="Ivanov",
            email="ivan@example.com",
            seat="A1",
        )

    client.unregister.assert_awaited_once_with(
        event_id=EVENT_ID,
        ticket_id=PROVIDER_TICKET_ID,
    )
    uow.commit.assert_not_awaited()
    cache.invalidate.assert_not_called()


# ============ CancelTicketUsecase ============


async def test_cancel_ticket_success(
    events_repo: AsyncMock,
    tickets_repo: AsyncMock,
    client: AsyncMock,
    cache: MagicMock,
    uow: AsyncMock,
) -> None:
    ticket_mock = MagicMock()
    ticket_mock.id = TICKET_ID
    ticket_mock.event_id = EVENT_ID
    ticket_mock.provider_ticket_id = PROVIDER_TICKET_ID
    tickets_repo.get.return_value = ticket_mock

    usecase = CancelTicketUsecase(
        client=client,
        events=events_repo,
        tickets=tickets_repo,
        cache=cache,
        uow=uow,
    )
    await usecase.do(ticket_id=TICKET_ID)

    client.unregister.assert_awaited_once_with(
        event_id=EVENT_ID,
        ticket_id=PROVIDER_TICKET_ID,
    )
    tickets_repo.delete.assert_awaited_once_with(TICKET_ID)
    uow.commit.assert_awaited_once()


async def test_cancel_ticket_not_found(
    events_repo: AsyncMock,
    tickets_repo: AsyncMock,
    client: AsyncMock,
    cache: MagicMock,
    uow: AsyncMock,
) -> None:
    tickets_repo.get.return_value = None

    usecase = CancelTicketUsecase(
        client=client,
        events=events_repo,
        tickets=tickets_repo,
        cache=cache,
        uow=uow,
    )
    with pytest.raises(TicketNotFoundError):
        await usecase.do(ticket_id=TICKET_ID)

    client.unregister.assert_not_awaited()
    tickets_repo.delete.assert_not_awaited()
    uow.commit.assert_not_awaited()


async def test_cancel_ticket_idempotent_when_provider_returns_404(
    events_repo: AsyncMock,
    tickets_repo: AsyncMock,
    client: AsyncMock,
    cache: MagicMock,
    uow: AsyncMock,
) -> None:
    ticket_mock = MagicMock()
    ticket_mock.id = TICKET_ID
    ticket_mock.event_id = EVENT_ID
    ticket_mock.provider_ticket_id = PROVIDER_TICKET_ID
    tickets_repo.get.return_value = ticket_mock
    client.unregister.side_effect = EventsProviderNotFoundError("not found")

    usecase = CancelTicketUsecase(
        client=client,
        events=events_repo,
        tickets=tickets_repo,
        cache=cache,
        uow=uow,
    )
    await usecase.do(ticket_id=TICKET_ID)

    tickets_repo.delete.assert_awaited_once_with(TICKET_ID)
    uow.commit.assert_awaited_once()


async def test_cancel_ticket_invalidates_cache(
    events_repo: AsyncMock,
    tickets_repo: AsyncMock,
    client: AsyncMock,
    cache: MagicMock,
    uow: AsyncMock,
) -> None:
    ticket_mock = MagicMock()
    ticket_mock.id = TICKET_ID
    ticket_mock.event_id = EVENT_ID
    ticket_mock.provider_ticket_id = PROVIDER_TICKET_ID
    tickets_repo.get.return_value = ticket_mock

    usecase = CancelTicketUsecase(
        client=client,
        events=events_repo,
        tickets=tickets_repo,
        cache=cache,
        uow=uow,
    )
    await usecase.do(ticket_id=TICKET_ID)

    cache.invalidate.assert_called_once_with(f"seats:{EVENT_ID}")
