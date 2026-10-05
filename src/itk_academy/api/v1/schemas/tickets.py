from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TicketCreateRequest(BaseModel):
    event_id: UUID
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    seat: str = Field(min_length=1, max_length=20)


class TicketCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: UUID


class TicketCancelResponse(BaseModel):
    success: bool
