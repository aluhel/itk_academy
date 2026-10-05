from collections.abc import Sequence
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from itk_academy.models.event import Event
from itk_academy.models.place import Place
from itk_academy.models.sync_metadata import SyncMetadata
from itk_academy.models.ticket import Ticket


class EventRepository(Protocol):
    async def get(self, event_id: UUID) -> Event | None: ...

    async def list_paginated(
        self,
        *,
        date_from: date | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Event], int]: ...

    async def upsert_many(self, events: Sequence[dict]) -> int: ...


class PlaceRepository(Protocol):
    async def get(self, place_id: UUID) -> Place | None: ...

    async def upsert_many(self, places: Sequence[dict]) -> int: ...


class SyncMetadataRepository(Protocol):
    async def get(self) -> SyncMetadata | None: ...

    async def update(
        self,
        *,
        last_sync_time: datetime | None = None,
        last_changed_at: datetime | None = None,
        sync_status: str | None = None,
        last_error: str | None = None,
    ) -> SyncMetadata: ...


class TicketRepository(Protocol):
    async def get(self, ticket_id: UUID) -> Ticket | None: ...

    async def create(
        self,
        *,
        event_id: UUID,
        provider_ticket_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> Ticket: ...

    async def delete(self, ticket_id: UUID) -> None: ...
