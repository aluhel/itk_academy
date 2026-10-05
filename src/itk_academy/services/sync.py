from datetime import UTC, date, datetime

import structlog

from itk_academy.config import get_settings
from itk_academy.events_provider.client import EventsProviderClient
from itk_academy.events_provider.dto import EventDTO
from itk_academy.events_provider.paginator import EventsPaginator
from itk_academy.models.enums import SyncStatus
from itk_academy.repositories.protocols import (
    EventRepository,
    PlaceRepository,
    SyncMetadataRepository,
)

logger = structlog.get_logger(__name__)


FIRST_SYNC_DATE = date(2000, 1, 1)


class SyncEventsUsecase:
    def __init__(
        self,
        *,
        client: EventsProviderClient,
        events: EventRepository,
        places: PlaceRepository,
        sync_metadata: SyncMetadataRepository,
    ) -> None:
        self._client = client
        self._events = events
        self._places = places
        self._sync_metadata = sync_metadata

    async def do(self) -> dict:
        settings = get_settings()
        metadata = await self._sync_metadata.get_or_create()

        # Начинаем синхронизацию
        await self._sync_metadata.update(
            sync_status=SyncStatus.RUNNING,
            last_sync_time=datetime.now(tz=UTC),
            last_error="",
        )

        changed_at: date = (
            metadata.last_changed_at.date() if metadata.last_changed_at else FIRST_SYNC_DATE
        )

        logger.info(
            "sync_started",
            changed_at=changed_at.isoformat(),
            provider_url=settings.events_provider_url,
        )

        events_count = 0
        places_count = 0
        max_changed_at: datetime | None = metadata.last_changed_at

        try:
            paginator = EventsPaginator(self._client, changed_at=changed_at)
            async for event in paginator:
                await self._upsert_event(event)
                events_count += 1
                if max_changed_at is None or event.changed_at > max_changed_at:
                    max_changed_at = event.changed_at

            await self._sync_metadata.update(
                sync_status=SyncStatus.SUCCESS,
                last_changed_at=max_changed_at,
                last_error="",
            )

            logger.info(
                "sync_finished",
                events_count=events_count,
                places_count=places_count,
                last_changed_at=max_changed_at.isoformat() if max_changed_at else None,
            )

            return {
                "status": "success",
                "events_count": events_count,
                "last_changed_at": max_changed_at.isoformat() if max_changed_at else None,
            }

        except Exception as exc:
            logger.exception("sync_failed", error=str(exc))
            await self._sync_metadata.update(
                sync_status=SyncStatus.FAILED,
                last_error=str(exc)[:1000],
            )
            raise

    async def _upsert_event(self, event: EventDTO) -> None:
        await self._places.upsert_many(
            [
                {
                    "id": event.place.id,
                    "name": event.place.name,
                    "city": event.place.city,
                    "address": event.place.address,
                    "seats_pattern": event.place.seats_pattern,
                    "changed_at": event.place.changed_at,
                    "created_at": event.place.created_at,
                }
            ]
        )
        await self._events.upsert_many(
            [
                {
                    "id": event.id,
                    "place_id": event.place.id,
                    "name": event.name,
                    "event_time": event.event_time,
                    "registration_deadline": event.registration_deadline,
                    "status": event.status,
                    "number_of_visitors": event.number_of_visitors,
                    "changed_at": event.changed_at,
                    "created_at": event.created_at,
                    "status_changed_at": event.status_changed_at,
                }
            ]
        )
