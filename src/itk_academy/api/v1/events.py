from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status

from itk_academy.api.v1.deps import EventRepositoryDep
from itk_academy.api.v1.schemas.events import (
    EventDetail,
    EventListItem,
    PaginatedEvents,
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
    query_params = _build_query_params(date_from=date_from, page_size=page_size)

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
    "/events/{event_id}",
    response_model=EventDetail,
    summary="Event details",
)
async def get_event(
    event_id: str,
    repo: EventRepositoryDep,
) -> EventDetail:
    from uuid import UUID

    try:
        event_uuid = UUID(event_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from exc

    event = await repo.get(event_uuid)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    return EventDetail.model_validate(event)


def _build_query_params(
    *,
    date_from: date | None,
    page_size: int,
) -> str:
    if date_from is None:
        return ""
    return f"&date_from={date_from.isoformat()}"
