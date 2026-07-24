from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.models.ticket_event import TicketEvent


class TicketRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_ticket(self, ticket: Ticket) -> Ticket:
        self.db.add(ticket)
        return ticket

    def add_event(self, event: TicketEvent) -> TicketEvent:
        self.db.add(event)
        return event

    def get_by_id(self, ticket_id: UUID) -> Ticket | None:
        return self.db.get(Ticket, ticket_id)

    def list_tickets(self, limit: int, offset: int) -> list[Ticket]:
        statement = (
            select(Ticket)
            .order_by(Ticket.created_at.desc(), Ticket.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def count_tickets(self) -> int:
        statement = select(func.count()).select_from(Ticket)
        return int(self.db.scalar(statement) or 0)

    def list_events(self, ticket_id: UUID) -> list[TicketEvent]:
        statement = (
            select(TicketEvent)
            .where(TicketEvent.ticket_id == ticket_id)
            .order_by(TicketEvent.created_at.asc(), TicketEvent.id.asc())
        )
        return list(self.db.scalars(statement).all())

