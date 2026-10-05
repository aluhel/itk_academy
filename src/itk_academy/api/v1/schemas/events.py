from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PlaceShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    city: str
    address: str


class PlaceDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    city: str
    address: str
    seats_pattern: str


class EventListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    place: PlaceShort
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int


class EventDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    place: PlaceDetail
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int


class PaginatedEvents(BaseModel):
    count: int
    next: str | None
    previous: str | None
    results: list[EventListItem]


class SeatsResponse(BaseModel):
    event_id: UUID
    available_seats: list[str]
