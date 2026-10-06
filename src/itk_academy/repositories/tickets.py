from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from itk_academy.domain.entities import TicketEntity
from itk_academy.models.ticket import Ticket


def _to_ticket_entity(ticket: Ticket) -> TicketEntity:
    return TicketEntity(
        id=ticket.id,
        provider_ticket_id=ticket.provider_ticket_id,
        event_id=ticket.event_id,
        first_name=ticket.first_name,
        last_name=ticket.last_name,
        email=ticket.email,
        seat=ticket.seat,
        created_at=ticket.created_at,
    )


class SqlAlchemyTicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, ticket_id: UUID) -> TicketEntity | None:
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await self._session.execute(stmt)
        ticket = result.scalar_one_or_none()
        return _to_ticket_entity(ticket) if ticket else None

    async def create(
        self,
        *,
        event_id: UUID,
        provider_ticket_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> TicketEntity:
        ticket = Ticket(
            id=uuid4(),
            provider_ticket_id=provider_ticket_id,
            event_id=event_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
            created_at=datetime.now(tz=UTC),
        )
        self._session.add(ticket)
        await self._session.flush()
        await self._session.refresh(ticket)
        return _to_ticket_entity(ticket)

    async def delete(self, ticket_id: UUID) -> None:
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await self._session.execute(stmt)
        ticket = result.scalar_one_or_none()
        if ticket is None:
            return
        await self._session.delete(ticket)
        await self._session.flush()
