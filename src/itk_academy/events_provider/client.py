from datetime import date
from types import TracebackType
from typing import Any
from uuid import UUID

import httpx

from itk_academy.events_provider.dto import EventsPage, SeatsDTO, TicketDTO
from itk_academy.events_provider.exceptions import (
    EventsProviderAuthError,
    EventsProviderBadRequestError,
    EventsProviderNotFoundError,
    EventsProviderRateLimitError,
    EventsProviderServerError,
    EventsProviderUnexpectedError,
)


class EventsProviderClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={
                "x-api-key": api_key,
                "Accept": "application/json",
            },
            follow_redirects=True,
        )

    async def __aenter__(self) -> "EventsProviderClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def events(
        self,
        changed_at: date,
        cursor: str | None = None,
    ) -> EventsPage:
        params: dict[str, str] = {"changed_at": changed_at.isoformat()}
        if cursor is not None:
            params["cursor"] = cursor

        data = await self._get_json("/api/events/", params=params)
        return EventsPage.from_raw(data)

    async def events_by_url(self, url: str) -> EventsPage:
        data = await self._get_json(url)
        return EventsPage.from_raw(data)

    async def seats(self, event_id: UUID) -> SeatsDTO:
        data = await self._get_json(f"/api/events/{event_id}/seats/")
        return SeatsDTO(event_id=event_id, seats=data["seats"])

    async def register(
        self,
        event_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> TicketDTO:
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "seat": seat,
        }
        data = await self._post_json(f"/api/events/{event_id}/register/", json=payload)
        return TicketDTO.from_raw(data)

    async def unregister(self, event_id: UUID, ticket_id: UUID) -> None:
        await self._delete_json(
            f"/api/events/{event_id}/unregister/",
            json={"ticket_id": str(ticket_id)},
        )

    async def _post_json(self, url: str, json: dict[str, Any]) -> Any:
        response = await self._http.post(url, json=json)
        self._raise_for_status(response)
        return response.json()

    async def _delete_json(self, url: str, json: dict[str, Any]) -> Any:
        response = await self._http.request("DELETE", url, json=json)
        self._raise_for_status(response)
        if response.content:
            return response.json()
        return None

    async def _get_json(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        response = await self._http.get(url, params=params)
        self._raise_for_status(response)
        return response.json()

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        status = response.status_code
        if status < 400:
            return

        detail = _safe_detail(response)
        if status == 400:
            raise EventsProviderBadRequestError(detail)
        if status == 401:
            raise EventsProviderAuthError(detail)
        if status == 404:
            raise EventsProviderNotFoundError(detail)
        if status == 429:
            raise EventsProviderRateLimitError(detail)
        if 500 <= status < 600:
            raise EventsProviderServerError(detail)
        raise EventsProviderUnexpectedError(f"{status}: {detail}")


def _safe_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text[:500]
    if isinstance(data, dict):
        return str(data.get("detail") or data)
    return str(data)
