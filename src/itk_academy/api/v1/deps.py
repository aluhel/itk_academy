from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from itk_academy.core.cache import TTLCache
from itk_academy.db.session import get_session
from itk_academy.db.uow import SqlAlchemyUnitOfWork
from itk_academy.events_provider.client import EventsProviderClient
from itk_academy.repositories.events import SqlAlchemyEventRepository
from itk_academy.repositories.protocols import UnitOfWork
from itk_academy.repositories.tickets import SqlAlchemyTicketRepository
from itk_academy.services.seats import SEATS_CACHE_TTL_SECONDS, GetSeatsUsecase
from itk_academy.services.tickets import CancelTicketUsecase, CreateTicketUsecase


async def _session_dep() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session


def get_event_repository(
    session: Annotated[AsyncSession, Depends(_session_dep)],
) -> SqlAlchemyEventRepository:
    return SqlAlchemyEventRepository(session)


EventRepositoryDep = Annotated[
    SqlAlchemyEventRepository,
    Depends(get_event_repository),
]


def get_provider_client(request: Request) -> EventsProviderClient:
    return request.app.state.events_provider_client


ProviderClientDep = Annotated[
    EventsProviderClient,
    Depends(get_provider_client),
]


def get_uow(
    session: Annotated[AsyncSession, Depends(_session_dep)],
) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session)


UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_uow)]


@lru_cache
def get_seats_cache() -> TTLCache[list[str]]:
    return TTLCache(ttl_seconds=SEATS_CACHE_TTL_SECONDS)


def get_seats_usecase(
    repo: EventRepositoryDep,
    client: ProviderClientDep,
) -> GetSeatsUsecase:
    return GetSeatsUsecase(
        client=client,
        events=repo,
        cache=get_seats_cache(),
    )


SeatsUsecaseDep = Annotated[
    GetSeatsUsecase,
    Depends(get_seats_usecase),
]


def get_ticket_repository(
    session: Annotated[AsyncSession, Depends(_session_dep)],
) -> SqlAlchemyTicketRepository:
    return SqlAlchemyTicketRepository(session)


TicketRepositoryDep = Annotated[
    SqlAlchemyTicketRepository,
    Depends(get_ticket_repository),
]


def get_create_ticket_usecase(
    repo: EventRepositoryDep,
    tickets: TicketRepositoryDep,
    client: ProviderClientDep,
    uow: UnitOfWorkDep,
) -> CreateTicketUsecase:
    return CreateTicketUsecase(
        client=client,
        events=repo,
        tickets=tickets,
        cache=get_seats_cache(),
        uow=uow,
    )


CreateTicketUsecaseDep = Annotated[
    CreateTicketUsecase,
    Depends(get_create_ticket_usecase),
]


def get_cancel_ticket_usecase(
    repo: EventRepositoryDep,
    tickets: TicketRepositoryDep,
    client: ProviderClientDep,
    uow: UnitOfWorkDep,
) -> CancelTicketUsecase:
    return CancelTicketUsecase(
        client=client,
        events=repo,
        tickets=tickets,
        cache=get_seats_cache(),
        uow=uow,
    )


CancelTicketUsecaseDep = Annotated[
    CancelTicketUsecase,
    Depends(get_cancel_ticket_usecase),
]
