from __future__ import annotations

import secrets
from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import InfrastructureError, TicketNotFoundError
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_event import TicketEvent
from app.repositories.ticket_repository import TicketRepository
from app.schemas.ticket import TicketCreate

logger = structlog.get_logger(__name__)

POSTGRES_UNIQUE_VIOLATION = "23505"
TICKET_CODE_CONSTRAINT_NAMES = {
    "tickets_ticket_code_key",
    "uq_tickets_ticket_code",
}
MAX_TICKET_CODE_ATTEMPTS = 5


def is_ticket_code_unique_violation(exc: IntegrityError) -> bool:
    """Return True only for unique violations on the ticket_code constraint."""

    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    diag = getattr(orig, "diag", None)
    constraint_name = getattr(diag, "constraint_name", None)

    if sqlstate == POSTGRES_UNIQUE_VIOLATION:
        return constraint_name in TICKET_CODE_CONSTRAINT_NAMES

    message = str(orig).lower() if orig is not None else str(exc).lower()
    return (
        "unique constraint failed" in message
        and "tickets.ticket_code" in message
    )


class TicketService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TicketRepository(db)

    def create_ticket(self, payload: TicketCreate) -> Ticket:
        for attempt in range(MAX_TICKET_CODE_ATTEMPTS):
            ticket = Ticket(
                ticket_code=self._generate_ticket_code(),
                channel=payload.channel.strip().lower(),
                customer_name=payload.customer_name.strip(),
                customer_email=str(payload.customer_email).lower(),
                subject=payload.subject.strip(),
                content=payload.content.strip(),
                status=TicketStatus.RECEIVED,
                category=None,
                priority=None,
                confidence=None,
            )
            event = TicketEvent(
                ticket=ticket,
                event_type="TICKET_CREATED",
                from_status=None,
                to_status=TicketStatus.RECEIVED.value,
                reason="Ticket received and recorded without AI classification.",
                extra_data={"channel": ticket.channel},
            )

            try:
                self.repository.add_ticket(ticket)
                self.repository.add_event(event)
                self.db.flush()
                self.db.commit()
                self.db.refresh(ticket)
            except IntegrityError as exc:
                self.db.rollback()
                if is_ticket_code_unique_violation(exc) and attempt < MAX_TICKET_CODE_ATTEMPTS - 1:
                    logger.warning(
                        "ticket_code_collision_retry",
                        attempt=attempt + 1,
                        max_attempts=MAX_TICKET_CODE_ATTEMPTS,
                    )
                    continue
                if is_ticket_code_unique_violation(exc):
                    logger.error("ticket_code_collision_exhausted")
                    raise InfrastructureError(
                        message="Could not create a unique ticket code.",
                        code="TICKET_CODE_GENERATION_FAILED",
                    ) from exc
                logger.error(
                    "ticket_creation_integrity_failure",
                    error_type=type(exc).__name__,
                )
                raise InfrastructureError(
                    message="Could not persist the ticket.",
                    code="TICKET_PERSISTENCE_FAILED",
                ) from exc
            except SQLAlchemyError as exc:
                self.db.rollback()
                logger.error(
                    "ticket_creation_database_failure",
                    error_type=type(exc).__name__,
                )
                raise InfrastructureError(
                    message="Could not persist the ticket.",
                    code="TICKET_PERSISTENCE_FAILED",
                ) from exc

            logger.info(
                "ticket_created",
                ticket_id=str(ticket.id),
                ticket_code=ticket.ticket_code,
            )
            return ticket

        raise InfrastructureError(
            message="Could not create a unique ticket code.",
            code="TICKET_CODE_GENERATION_FAILED",
        )

    def list_tickets(self, limit: int, offset: int) -> tuple[list[Ticket], int]:
        return self.repository.list_tickets(limit, offset), self.repository.count_tickets()

    def get_ticket(self, ticket_id: UUID) -> Ticket:
        ticket = self.repository.get_by_id(ticket_id)
        if ticket is None:
            raise TicketNotFoundError(str(ticket_id))
        return ticket

    def list_events(self, ticket_id: UUID) -> list[TicketEvent]:
        if self.repository.get_by_id(ticket_id) is None:
            raise TicketNotFoundError(str(ticket_id))
        return self.repository.list_events(ticket_id)

    @staticmethod
    def _generate_ticket_code() -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        suffix = secrets.token_hex(3).upper()
        return f"TKT-{timestamp}-{suffix}"
