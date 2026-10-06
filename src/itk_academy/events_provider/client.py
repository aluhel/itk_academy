from datetime import date
from types import TracebackType
from typing import Any
from uuid import UUID

import httpx

from itk_academy.events_provider.dto import (
    EventsPage,
    SeatsDTO,
    TicketDTO,
    parse_events_page,
    parse_ticket,
)
from itk_academy.events_provider.exceptions import (
    EventsProviderAuthError,
    EventsProviderBadRequestError,
    EventsProviderNotFoundError,
    EventsProviderRateLimitError,
    EventsProviderServerError,
    EventsProviderUnavailableError,
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
        transport = httpx.AsyncHTTPTransport(retries=3)
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={
                "x-api-key": api_key,
                "Accept": "application/json",
            },
            follow_redirects=True,
            transport=transport,
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

        data = await self._request_json("GET", "/api/events/", params=params)
        return parse_events_page(data)

    async def events_by_url(self, url: str) -> EventsPage:
        data = await self._request_json("GET", url)
        return parse_events_page(data)

    async def seats(self, event_id: UUID) -> SeatsDTO:
        data = await self._request_json("GET", f"/api/events/{event_id}/seats/")
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
        data = await self._request_json(
            "POST",
            f"/api/events/{event_id}/register/",
            json=payload,
        )
        return parse_ticket(data)

    async def unregister(self, event_id: UUID, ticket_id: UUID) -> None:
        await self._request_json(
            "DELETE",
            f"/api/events/{event_id}/unregister/",
            json={"ticket_id": str(ticket_id)},
            allow_empty_response=True,
        )

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        allow_empty_response: bool = False,
    ) -> Any:
        try:
            response = await self._http.request(method, url, params=params, json=json)
        except httpx.TimeoutException as exc:
            raise EventsProviderUnavailableError(f"timeout: {exc}") from exc
        except httpx.TransportError as exc:
            raise EventsProviderUnavailableError(str(exc)) from exc

        _raise_for_status(response)

        if allow_empty_response and not response.content:
            return None
        return response.json()


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
