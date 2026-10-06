from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from itk_academy.api.v1.deps import EventRepositoryDep, SeatsUsecaseDep
from itk_academy.api.v1.schemas.events import (
    EventDetail,
    EventListItem,
    PaginatedEvents,
    SeatsResponse,
)
from itk_academy.events_provider.exceptions import (
    EventsProviderBadRequestError,
    EventsProviderError,
    EventsProviderNotFoundError,
    EventsProviderRateLimitError,
)
from itk_academy.services.seats import (
    EventNotFoundError,
    EventNotPublishedError,
)

router = APIRouter()


@router.get(
    "/events",
    response_model=PaginatedEvents,
    summary="List events",
)
async def list_events(
    request: Request,
    repo: EventRepositoryDep,
    date_from: Annotated[date | None, Query(description="YYYY-MM-DD")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedEvents:
    offset = (page - 1) * page_size
    events, total = await repo.list_paginated(
        date_from=date_from,
        limit=page_size,
        offset=offset,
    )

    base_url = str(request.url).split("?")[0]
    query_params = _build_query_params(date_from=date_from)

    next_url = (
        f"{base_url}?page={page + 1}&page_size={page_size}{query_params}"
        if offset + len(events) < total
        else None
    )
    previous_url = (
        f"{base_url}?page={page - 1}&page_size={page_size}{query_params}" if page > 1 else None
    )

    return PaginatedEvents(
        count=total,
        next=next_url,
        previous=previous_url,
        results=[EventListItem.model_validate(event) for event in events],
    )


@router.get(
    "/events/{event_id}/seats",
    response_model=SeatsResponse,
    summary="Available seats for an event",
)
async def get_event_seats(
    event_id: UUID,
    usecase: SeatsUsecaseDep,
) -> SeatsResponse:
    try:
        seats = await usecase.do(event_id)
    except EventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from exc
    except EventNotPublishedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event is not published for registration",
        ) from exc
    except EventsProviderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except EventsProviderBadRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except EventsProviderRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Events provider rate limit exceeded",
            headers={"Retry-After": "5"},
        ) from exc
    except EventsProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Events provider unavailable",
        ) from exc

    return SeatsResponse(event_id=event_id, available_seats=seats)


@router.get(
    "/events/{event_id}",
    response_model=EventDetail,
    summary="Event details",
)
async def get_event(
    event_id: UUID,
    repo: EventRepositoryDep,
) -> EventDetail:
    event = await repo.get(event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    return EventDetail.model_validate(event)


def _build_query_params(*, date_from: date | None) -> str:
    if date_from is None:
        return ""
    return f"&date_from={date_from.isoformat()}"
