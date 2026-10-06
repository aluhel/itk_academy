from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PlaceDTO:
    id: UUID
    name: str
    city: str
    address: str
    seats_pattern: str
    changed_at: datetime
    created_at: datetime


@dataclass(frozen=True, slots=True)
class EventDTO:
    id: UUID
    name: str
    place: PlaceDTO
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int
    changed_at: datetime
    created_at: datetime
    status_changed_at: datetime


@dataclass(frozen=True, slots=True)
class EventsPage:
    results: list[EventDTO]
    next_url: str | None
    previous_url: str | None


@dataclass(frozen=True, slots=True)
class SeatsDTO:
    event_id: UUID
    seats: list[str]


@dataclass(frozen=True, slots=True)
class TicketDTO:
    ticket_id: UUID


def parse_place(data: dict[str, Any]) -> PlaceDTO:
    return PlaceDTO(
        id=UUID(data["id"]),
        name=data["name"],
        city=data["city"],
        address=data["address"],
        seats_pattern=data["seats_pattern"],
        changed_at=datetime.fromisoformat(data["changed_at"]),
        created_at=datetime.fromisoformat(data["created_at"]),
    )


def parse_event(data: dict[str, Any]) -> EventDTO:
    return EventDTO(
        id=UUID(data["id"]),
        name=data["name"],
        place=parse_place(data["place"]),
        event_time=datetime.fromisoformat(data["event_time"]),
        registration_deadline=datetime.fromisoformat(data["registration_deadline"]),
        status=data["status"],
        number_of_visitors=data["number_of_visitors"],
        changed_at=datetime.fromisoformat(data["changed_at"]),
        created_at=datetime.fromisoformat(data["created_at"]),
        status_changed_at=datetime.fromisoformat(data["status_changed_at"]),
    )


def parse_events_page(data: dict[str, Any]) -> EventsPage:
    return EventsPage(
        results=[parse_event(item) for item in data["results"]],
        next_url=data.get("next"),
        previous_url=data.get("previous"),
    )


def parse_ticket(data: dict[str, Any]) -> TicketDTO:
    return TicketDTO(ticket_id=UUID(data["ticket_id"]))
