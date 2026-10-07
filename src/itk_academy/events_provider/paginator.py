from collections.abc import AsyncIterator
from datetime import date

from itk_academy.events_provider.dto import EventDTO
from itk_academy.events_provider.ports import EventsSource


class EventsPaginator:
    def __init__(self, client: EventsSource, changed_at: date) -> None:
        self._client = client
        self._changed_at = changed_at

    async def __aiter__(self) -> AsyncIterator[EventDTO]:
        page = await self._client.events(changed_at=self._changed_at)
        while True:
            for event in page.results:
                yield event
            if page.next_url is None:
                break
            page = await self._client.events_by_url(page.next_url)
