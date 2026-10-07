from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
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

    async def save_for_seat(
        self,
        *,
        event_id: UUID,
        provider_ticket_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> TicketEntity:
        """Upsert по (event_id, seat): провайдер уже подтвердил, что место свободно,
        значит любая старая локальная запись на это место устарела.
        Обновляем в том числе id, чтобы прежний владелец не мог отменить новый билет."""
        stmt = insert(Ticket).values(
            id=uuid4(),
            provider_ticket_id=provider_ticket_id,
            event_id=event_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
            created_at=datetime.now(tz=UTC),
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_tickets_event_id_seat",
            set_={
                "id": stmt.excluded.id,
                "provider_ticket_id": stmt.excluded.provider_ticket_id,
                "first_name": stmt.excluded.first_name,
                "last_name": stmt.excluded.last_name,
                "email": stmt.excluded.email,
                "created_at": stmt.excluded.created_at,
            },
        ).returning(Ticket)
        result = await self._session.execute(stmt)
        ticket = result.scalar_one()
        await self._session.flush()
        return _to_ticket_entity(ticket)

    async def delete(self, ticket_id: UUID) -> None:
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await self._session.execute(stmt)
        ticket = result.scalar_one_or_none()
        if ticket is None:
            return
        await self._session.delete(ticket)
        await self._session.flush()
