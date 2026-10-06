from typing import Protocol
from uuid import UUID

from itk_academy.events_provider.dto import SeatsDTO, TicketDTO


class EventsProvider(Protocol):
    async def seats(self, event_id: UUID) -> SeatsDTO: ...

    async def register(
        self,
        event_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> TicketDTO: ...

    async def unregister(self, event_id: UUID, ticket_id: UUID) -> None: ...
