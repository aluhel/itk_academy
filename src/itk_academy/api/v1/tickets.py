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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from exc
    except TicketEventNotPublishedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event is not published for registration",
        ) from exc
    except TicketRegistrationClosedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration is closed",
        ) from exc
    except TicketSeatNotAvailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seat is not available",
        ) from exc

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        ) from exc

    return TicketCancelResponse(success=True)
