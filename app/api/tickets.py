from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ticket import (
    TicketCreate,
    TicketEventRead,
    TicketListResponse,
    TicketRead,
)
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)) -> TicketRead:
    return TicketService(db).create_ticket(payload)


@router.get("", response_model=TicketListResponse)
def list_tickets(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> TicketListResponse:
    items, total = TicketService(db).list_tickets(limit=limit, offset=offset)
    return TicketListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: UUID, db: Session = Depends(get_db)) -> TicketRead:
    return TicketService(db).get_ticket(ticket_id)


@router.get("/{ticket_id}/events", response_model=list[TicketEventRead])
def get_ticket_events(
    ticket_id: UUID,
    db: Session = Depends(get_db),
) -> list[TicketEventRead]:
    return TicketService(db).list_events(ticket_id)

