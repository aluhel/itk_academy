from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from itk_academy.core.cache import TTLCache
from itk_academy.db.session import get_session
from itk_academy.events_provider.client import EventsProviderClient
from itk_academy.repositories.events import SqlAlchemyEventRepository
from itk_academy.services.seats import SEATS_CACHE_TTL_SECONDS, GetSeatsUsecase


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
