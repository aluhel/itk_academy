import contextlib
from datetime import UTC, datetime
from uuid import UUID

import structlog

from itk_academy.events_provider.exceptions import (
    EventsProviderBadRequestError,
    EventsProviderError,
    EventsProviderNotFoundError,
)
from itk_academy.models.enums import EventStatus
from itk_academy.models.ticket import Ticket
from itk_academy.repositories.protocols import (
    EventRepository,
    SeatsCache,
    TicketRepository,
)
from itk_academy.services.ports import EventsProvider

logger = structlog.get_logger(__name__)


class TicketEventNotFoundError(Exception):
    pass


class TicketEventNotPublishedError(Exception):
    pass


class TicketRegistrationClosedError(Exception):
    pass


class TicketSeatNotAvailableError(Exception):
    pass


class TicketNotFoundError(Exception):
    pass


class CreateTicketUsecase:
    def __init__(
        self,
        *,
        client: EventsProvider,
        events: EventRepository,
        tickets: TicketRepository,
        cache: SeatsCache,
    ) -> None:
        self._client = client
        self._events = events
        self._tickets = tickets
        self._cache = cache

    async def do(
        self,
        *,
        event_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> Ticket:
        event = await self._events.get(event_id)
        if event is None:
            raise TicketEventNotFoundError(f"Event {event_id} not found")

        if event.status != EventStatus.PUBLISHED:
            raise TicketEventNotPublishedError(
                f"Event {event_id} is not published (status={event.status})"
            )

        now = datetime.now(tz=UTC)
        if event.registration_deadline < now:
            raise TicketRegistrationClosedError(f"Registration for event {event_id} is closed")

        seats_dto = await self._client.seats(event_id=event_id)
        if seat not in seats_dto.seats:
            raise TicketSeatNotAvailableError(f"Seat {seat} is not available")

        try:
            ticket_dto = await self._client.register(
                event_id=event_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                seat=seat,
            )
        except EventsProviderBadRequestError as exc:
            raise TicketSeatNotAvailableError(str(exc)) from exc

        try:
            ticket = await self._tickets.create(
                event_id=event_id,
                provider_ticket_id=ticket_dto.ticket_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                seat=seat,
            )
        except Exception:
            logger.exception(
                "ticket_save_failed_compensating",
                event_id=str(event_id),
                seat=seat,
            )
            with contextlib.suppress(EventsProviderError):
                await self._client.unregister(
                    event_id=event_id,
                    ticket_id=ticket_dto.ticket_id,
                )
            raise

        self._cache.invalidate(f"seats:{event_id}")

        logger.info(
            "ticket_created",
            ticket_id=str(ticket.id),
            provider_ticket_id=str(ticket_dto.ticket_id),
            event_id=str(event_id),
            seat=seat,
        )

        return ticket


class CancelTicketUsecase:
    def __init__(
        self,
        *,
        client: EventsProvider,
        events: EventRepository,
        tickets: TicketRepository,
        cache: SeatsCache,
    ) -> None:
        self._client = client
        self._events = events
        self._tickets = tickets
        self._cache = cache

    async def do(self, *, ticket_id: UUID) -> None:
        ticket = await self._tickets.get(ticket_id)
        if ticket is None:
            raise TicketNotFoundError(f"Ticket {ticket_id} not found")

        try:
            await self._client.unregister(
                event_id=ticket.event_id,
                ticket_id=ticket.provider_ticket_id,
            )
        except EventsProviderNotFoundError:
            logger.warning(
                "ticket_already_cancelled_at_provider",
                ticket_id=str(ticket_id),
            )

        await self._tickets.delete(ticket_id)
        self._cache.invalidate(f"seats:{ticket.event_id}")

        logger.info(
            "ticket_cancelled",
            ticket_id=str(ticket_id),
            event_id=str(ticket.event_id),
        )
