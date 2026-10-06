from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PlaceEntity:
    id: UUID
    name: str
    city: str
    address: str
    seats_pattern: str
    changed_at: datetime
    created_at: datetime


@dataclass(frozen=True, slots=True)
class EventEntity:
    id: UUID
    place_id: UUID
    name: str
    place: PlaceEntity | None
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int
    changed_at: datetime
    created_at: datetime
    status_changed_at: datetime


@dataclass(frozen=True, slots=True)
class TicketEntity:
    id: UUID
    provider_ticket_id: UUID
    event_id: UUID
    first_name: str
    last_name: str
    email: str
    seat: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SyncMetadataEntity:
    id: int
    last_sync_time: datetime | None
    last_changed_at: datetime | None
    sync_status: str
    last_error: str | None
    updated_at: datetime
