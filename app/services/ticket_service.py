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


class TicketService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TicketRepository(db)

    def create_ticket(self, payload: TicketCreate) -> Ticket:
        for attempt in range(5):
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
            except IntegrityError:
                self.db.rollback()
                if attempt < 4:
                    continue
                logger.error("ticket_code_collision_exhausted")
                raise InfrastructureError(
                    message="Could not create a unique ticket code.",
                    code="TICKET_CODE_GENERATION_FAILED",
                )
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

