from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from itk_academy.api.v1.deps import (
    CancelTicketUsecaseDep,
    CreateTicketUsecaseDep,
)
from itk_academy.api.v1.schemas.tickets import (
    TicketCancelResponse,
    TicketCreateRequest,
    TicketCreateResponse,
)
from itk_academy.events_provider.exceptions import (
    EventsProviderBadRequestError,
    EventsProviderError,
    EventsProviderNotFoundError,
    EventsProviderRateLimitError,
)
from itk_academy.services.tickets import (
    TicketEventNotFoundError,
    TicketEventNotPublishedError,
    TicketNotFoundError,
    TicketRegistrationClosedError,
    TicketSeatNotAvailableError,
)

router = APIRouter()


@router.post(
    "/tickets",
    response_model=TicketCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a ticket",
)
async def create_ticket(
    payload: TicketCreateRequest,
    usecase: CreateTicketUsecaseDep,
) -> TicketCreateResponse:
    try:
        ticket = await usecase.do(
            event_id=payload.event_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            seat=payload.seat,
        )
    except TicketEventNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found") from exc
    except TicketEventNotPublishedError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Event is not published for registration"
        ) from exc
    except TicketRegistrationClosedError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Registration is closed") from exc
    except TicketSeatNotAvailableError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Seat is not available") from exc
    except EventsProviderNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except EventsProviderBadRequestError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except EventsProviderRateLimitError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Events provider rate limit exceeded",
            headers={"Retry-After": "5"},
        ) from exc
    except EventsProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Events provider unavailable") from exc

    return TicketCreateResponse(ticket_id=ticket.id)


@router.delete(
    "/tickets/{ticket_id}",
    response_model=TicketCancelResponse,
    summary="Cancel a ticket",
)
async def cancel_ticket(
    ticket_id: UUID,
    usecase: CancelTicketUsecaseDep,
) -> TicketCancelResponse:
    try:
        await usecase.do(ticket_id=ticket_id)
    except TicketNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found") from exc
    except EventsProviderNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except EventsProviderBadRequestError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except EventsProviderRateLimitError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Events provider rate limit exceeded",
            headers={"Retry-After": "5"},
        ) from exc
    except EventsProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Events provider unavailable") from exc

    return TicketCancelResponse(success=True)
