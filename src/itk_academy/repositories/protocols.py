from collections.abc import Sequence
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from itk_academy.domain.entities import (
    EventEntity,
    PlaceEntity,
    SyncMetadataEntity,
    TicketEntity,
)


class EventRepository(Protocol):
    async def get(self, event_id: UUID) -> EventEntity | None: ...

    async def list_paginated(
        self,
        *,
        date_from: date | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[EventEntity], int]: ...

    async def upsert_many(self, events: Sequence[EventEntity]) -> int: ...


class PlaceRepository(Protocol):
    async def get(self, place_id: UUID) -> PlaceEntity | None: ...

    async def upsert_many(self, places: Sequence[PlaceEntity]) -> int: ...


class TicketRepository(Protocol):
    async def get(self, ticket_id: UUID) -> TicketEntity | None: ...

    async def create(
        self,
        *,
        event_id: UUID,
        provider_ticket_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> TicketEntity: ...

    async def delete(self, ticket_id: UUID) -> None: ...


class SyncMetadataRepository(Protocol):
    async def get(self) -> SyncMetadataEntity | None: ...

    async def get_or_create(self) -> SyncMetadataEntity: ...

    async def update(
        self,
        *,
        last_sync_time: datetime | None = None,
        last_changed_at: datetime | None = None,
        sync_status: str | None = None,
        last_error: str | None = None,
    ) -> SyncMetadataEntity: ...


class SeatsCache(Protocol):
    def invalidate(self, key: str) -> None: ...


class UnitOfWork(Protocol):
    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
