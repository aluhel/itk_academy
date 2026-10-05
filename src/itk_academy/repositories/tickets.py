from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from itk_academy.models.ticket import Ticket


class SqlAlchemyTicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, ticket_id: UUID) -> Ticket | None:
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        event_id: UUID,
        provider_ticket_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> Ticket:
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
        await self._session.commit()
        await self._session.refresh(ticket)
        return ticket

    async def delete(self, ticket_id: UUID) -> None:
        ticket = await self.get(ticket_id)
        if ticket is None:
            return
        await self._session.delete(ticket)
        await self._session.commit()
