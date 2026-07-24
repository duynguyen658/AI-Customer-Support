from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.ticket import TicketCategory, TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    channel: str = Field(default="web", min_length=2, max_length=32)
    customer_name: str = Field(min_length=2, max_length=255)
    customer_email: EmailStr
    subject: str = Field(min_length=3, max_length=255)
    content: str = Field(min_length=5, max_length=20_000)

    @field_validator("channel", mode="before")
    @classmethod
    def normalize_channel(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("customer_name", "subject", "content", mode="before")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("customer_email", mode="after")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class TicketRead(BaseModel):
    id: UUID
    ticket_code: str
    channel: str
    customer_name: str
    customer_email: str
    subject: str
    content: str
    category: TicketCategory | None
    priority: TicketPriority | None
    confidence: float | None
    status: TicketStatus
    assigned_team: str | None
    parent_ticket_id: UUID | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TicketListResponse(BaseModel):
    items: list[TicketRead]
    total: int
    limit: int
    offset: int


class TicketEventRead(BaseModel):
    id: UUID
    ticket_id: UUID
    event_type: str
    from_status: str | None
    to_status: str | None
    reason: str | None
    extra_data: dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

