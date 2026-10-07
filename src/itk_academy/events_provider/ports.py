from datetime import date
from typing import Protocol

from itk_academy.events_provider.dto import EventsPage


class EventsSource(Protocol):
    """Protocol for iterating events from the provider.

    Implemented by `EventsProviderClient`, used by `EventsPaginator`
    and `SyncEventsUsecase`.
    """

    async def events(
        self,
        changed_at: date,
        cursor: str | None = None,
    ) -> EventsPage: ...

    async def events_by_url(self, url: str) -> EventsPage: ...
