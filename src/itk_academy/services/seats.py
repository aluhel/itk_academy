from uuid import UUID

import structlog

from itk_academy.core.cache import TTLCache, get_or_set
from itk_academy.models.enums import EventStatus
from itk_academy.repositories.protocols import EventRepository
from itk_academy.services.ports import EventsProvider

logger = structlog.get_logger(__name__)


SEATS_CACHE_TTL_SECONDS = 30


class EventNotFoundError(Exception):
    pass


class EventNotPublishedError(Exception):
    pass


class GetSeatsUsecase:
    def __init__(
        self,
        *,
        client: EventsProvider,
        events: EventRepository,
        cache: TTLCache[list[str]],
    ) -> None:
        self._client = client
        self._events = events
        self._cache = cache

    async def do(self, event_id: UUID) -> list[str]:
        event = await self._events.get(event_id)
        if event is None:
            raise EventNotFoundError(f"Event {event_id} not found")

        if event.status != EventStatus.PUBLISHED:
            logger.info(
                "seats_skipped_not_published",
                event_id=str(event_id),
                status=event.status,
            )
            raise EventNotPublishedError(
                f"Event {event_id} is not published (status={event.status})"
            )

        cache_key = f"seats:{event_id}"

        async def fetch() -> list[str]:
            logger.info("seats_fetch_from_provider", event_id=str(event_id))
            dto = await self._client.seats(event_id=event_id)
            return dto.seats

        return await get_or_set(self._cache, cache_key, fetch)
