from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class TicketCategory(str, Enum):
    INFORMATION = "information"
    COMPLAINT = "complaint"
    TECHNICAL = "technical"
    PAYMENT = "payment"
    EMERGENCY = "emergency"
    SPAM = "spam"
    UNKNOWN = "unknown"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketStatus(str, Enum):
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    CLASSIFIED = "CLASSIFIED"
    NEED_MORE_INFO = "NEED_MORE_INFO"
    RETRIEVING = "RETRIEVING"
    AUTO_ANSWERED = "AUTO_ANSWERED"
    ESCALATED = "ESCALATED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    RESOLVED = "RESOLVED"
    SPAM = "SPAM"
    DUPLICATE = "DUPLICATE"
    PROCESSING_FAILED = "PROCESSING_FAILED"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def enum_values(enum_type: type[Enum]) -> list[str]:
    return [item.value for item in enum_type]


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ticket_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="web")
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[TicketCategory | None] = mapped_column(
        SqlEnum(
            TicketCategory,
            values_callable=enum_values,
            native_enum=False,
            validate_strings=True,
            length=32,
        ),
        nullable=True,
    )
    priority: Mapped[TicketPriority | None] = mapped_column(
        SqlEnum(
            TicketPriority,
            values_callable=enum_values,
            native_enum=False,
            validate_strings=True,
            length=16,
        ),
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[TicketStatus] = mapped_column(
        SqlEnum(
            TicketStatus,
            values_callable=enum_values,
            native_enum=False,
            validate_strings=True,
            length=32,
        ),
        nullable=False,
        default=TicketStatus.RECEIVED,
    )
    assigned_team: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parent_ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tickets.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    parent_ticket: Mapped[Ticket | None] = relationship(
        "Ticket",
        remote_side=[id],
        back_populates="child_tickets",
    )
    child_tickets: Mapped[list[Ticket]] = relationship(
        "Ticket",
        back_populates="parent_ticket",
    )
    events: Mapped[list["TicketEvent"]] = relationship(
        "TicketEvent",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketEvent.created_at",
        passive_deletes=True,
    )


Index("ix_tickets_ticket_code", Ticket.ticket_code)
Index("ix_tickets_customer_email", Ticket.customer_email)
Index("ix_tickets_status", Ticket.status)
Index("ix_tickets_created_at", Ticket.created_at)

