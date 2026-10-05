from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from itk_academy.db.session import get_session
from itk_academy.repositories.events import SqlAlchemyEventRepository


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
