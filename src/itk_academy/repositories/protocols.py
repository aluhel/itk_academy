from collections.abc import Sequence
from datetime import date
from typing import Protocol
from uuid import UUID

from itk_academy.models.event import Event


class EventRepository(Protocol):
    async def get(self, event_id: UUID) -> Event | None: ...

    async def list_paginated(
        self,
        *,
        date_from: date | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Event], int]: ...
