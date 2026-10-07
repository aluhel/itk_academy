from datetime import UTC, date, datetime
from uuid import UUID

import structlog

from itk_academy.config import get_settings
from itk_academy.domain.entities import EventEntity, PlaceEntity
from itk_academy.events_provider.dto import EventDTO, PlaceDTO
from itk_academy.events_provider.paginator import EventsPaginator
from itk_academy.events_provider.ports import EventsSource
from itk_academy.models.enums import SyncStatus
from itk_academy.repositories.protocols import (
    EventRepository,
    PlaceRepository,
    SyncMetadataRepository,
    UnitOfWork,
)

logger = structlog.get_logger(__name__)


FIRST_SYNC_DATE = date(2000, 1, 1)
BATCH_SIZE = 100


def _place_dto_to_entity(place: PlaceDTO) -> PlaceEntity:
    return PlaceEntity(
        id=place.id,
        name=place.name,
        city=place.city,
        address=place.address,
        seats_pattern=place.seats_pattern,
        changed_at=place.changed_at,
        created_at=place.created_at,
    )


def _event_dto_to_entity(event: EventDTO) -> EventEntity:
    return EventEntity(
        id=event.id,
        place_id=event.place.id,
        name=event.name,
        place=_place_dto_to_entity(event.place),
        event_time=event.event_time,
        registration_deadline=event.registration_deadline,
        status=event.status,
        number_of_visitors=event.number_of_visitors,
        changed_at=event.changed_at,
        created_at=event.created_at,
        status_changed_at=event.status_changed_at,
    )


class SyncEventsUsecase:
    def __init__(
        self,
        *,
        client: EventsSource,
        events: EventRepository,
        places: PlaceRepository,
        sync_metadata: SyncMetadataRepository,
        uow: UnitOfWork,
    ) -> None:
        self._client = client
        self._events = events
        self._places = places
        self._sync_metadata = sync_metadata
        self._uow = uow

    async def do(self) -> dict:
        settings = get_settings()
        metadata = await self._sync_metadata.get_or_create()

        if metadata.sync_status == SyncStatus.RUNNING:
            logger.warning(
                "sync_already_running",
                last_sync_time=str(metadata.last_sync_time),
            )

        # Фиксируем статус RUNNING отдельным коммитом, чтобы при падении
        # в БД остался след, что процесс стартовал.
        await self._sync_metadata.update(
            sync_status=SyncStatus.RUNNING,
            last_sync_time=datetime.now(tz=UTC),
            last_error="",
        )
        await self._uow.commit()

        changed_at: date = (
            metadata.last_changed_at.date() if metadata.last_changed_at else FIRST_SYNC_DATE
        )

        logger.info(
            "sync_started",
            changed_at=changed_at.isoformat(),
            provider_url=settings.events_provider_url,
        )

        events_count = 0
        max_changed_at: datetime | None = metadata.last_changed_at

        try:
            paginator = EventsPaginator(self._client, changed_at=changed_at)
            events_batch: list[EventEntity] = []
            places_batch: dict[UUID, PlaceEntity] = {}

            async for event_dto in paginator:
                entity = _event_dto_to_entity(event_dto)
                events_batch.append(entity)
                places_batch[entity.place_id] = entity.place
                events_count += 1
                if max_changed_at is None or entity.changed_at > max_changed_at:
                    max_changed_at = entity.changed_at

                if len(events_batch) >= BATCH_SIZE:
                    await self._places.upsert_many(list(places_batch.values()))
                    await self._events.upsert_many(events_batch)
                    await self._uow.commit()
                    events_batch.clear()
                    places_batch.clear()

            if events_batch:
                await self._places.upsert_many(list(places_batch.values()))
                await self._events.upsert_many(events_batch)
                await self._uow.commit()

            await self._sync_metadata.update(
                sync_status=SyncStatus.SUCCESS,
                last_changed_at=max_changed_at,
                last_error="",
            )
            await self._uow.commit()

            logger.info(
                "sync_finished",
                events_count=events_count,
                last_changed_at=max_changed_at.isoformat() if max_changed_at else None,
            )

            return {
                "status": "success",
                "events_count": events_count,
                "last_changed_at": max_changed_at.isoformat() if max_changed_at else None,
            }

        except Exception as exc:
            logger.exception("sync_failed", error=str(exc))
            await self._uow.rollback()
            await self._sync_metadata.update(
                sync_status=SyncStatus.FAILED,
                last_error=str(exc)[:1000],
            )
            await self._uow.commit()
            raise
