from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.ticket import Ticket, TicketStatus, utc_now
from app.models.ticket_event import TicketEvent
from app.repositories.ticket_repository import TicketRepository
from app.schemas.ticket import TicketCreate
from app.services.ticket_service import TicketService


pytestmark = pytest.mark.integration


def _create_ticket(session: Session, payload: dict[str, str]) -> Ticket:
    ticket = TicketService(session).create_ticket(TicketCreate.model_validate(payload))
    session.refresh(ticket)
    return ticket


def test_postgres_service_persists_ticket_and_created_event(
    postgres_session: Session,
    integration_ticket_payload: dict[str, str],
) -> None:
    ticket = _create_ticket(postgres_session, integration_ticket_payload)

    assert isinstance(ticket.id, UUID)
    assert ticket.status == TicketStatus.RECEIVED
    assert ticket.category is None
    assert ticket.priority is None
    assert ticket.confidence is None
    assert ticket.created_at.tzinfo is not None
    assert ticket.updated_at.tzinfo is not None

    events = TicketRepository(postgres_session).list_events(ticket.id)
    assert len(events) == 1
    assert events[0].event_type == "TICKET_CREATED"
    assert events[0].to_status == "RECEIVED"


def test_postgres_api_ticket_flow(
    postgres_client,
    integration_ticket_payload: dict[str, str],
) -> None:
    created = postgres_client.post("/api/v1/tickets", json=integration_ticket_payload)
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "RECEIVED"
    assert body["category"] is None
    assert body["priority"] is None
    assert body["confidence"] is None

    assert postgres_client.get("/api/v1/tickets").status_code == 200
    assert postgres_client.get(f"/api/v1/tickets/{body['id']}").status_code == 200
    events = postgres_client.get(f"/api/v1/tickets/{body['id']}/events")
    assert events.status_code == 200
    assert len(events.json()) == 1


def test_postgres_delete_ticket_cascades_events(
    postgres_session: Session,
    integration_ticket_payload: dict[str, str],
) -> None:
    ticket = _create_ticket(postgres_session, integration_ticket_payload)

    postgres_session.delete(ticket)
    postgres_session.commit()

    assert postgres_session.scalar(select(func.count()).select_from(Ticket)) == 0
    assert postgres_session.scalar(select(func.count()).select_from(TicketEvent)) == 0


def test_postgres_parent_ticket_delete_sets_child_parent_to_null(
    postgres_session: Session,
    integration_ticket_payload: dict[str, str],
) -> None:
    parent = _create_ticket(postgres_session, integration_ticket_payload)
    child = _create_ticket(
        postgres_session,
        {**integration_ticket_payload, "customer_email": "child@example.com"},
    )
    child.parent_ticket_id = parent.id
    postgres_session.commit()

    postgres_session.execute(text("DELETE FROM tickets WHERE id = :id"), {"id": parent.id})
    postgres_session.commit()
    postgres_session.expire(child)

    assert postgres_session.get(Ticket, child.id).parent_ticket_id is None


def test_postgres_ticket_code_uniqueness(
    postgres_session: Session,
    integration_ticket_payload: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(TicketService, "_generate_ticket_code", staticmethod(lambda: "TKT-PG-SAME"))
    _create_ticket(postgres_session, integration_ticket_payload)

    with pytest.raises(IntegrityError):
        duplicate = Ticket(
            ticket_code="TKT-PG-SAME",
            channel="web",
            customer_name="Duplicate",
            customer_email="duplicate@example.com",
            subject="Duplicate ticket",
            content="This duplicate ticket code should violate uniqueness.",
            status=TicketStatus.RECEIVED,
        )
        postgres_session.add(duplicate)
        postgres_session.commit()

    postgres_session.rollback()


def test_postgres_listing_order_and_pagination(postgres_session: Session) -> None:
    base = utc_now()
    tickets = [
        Ticket(
            ticket_code=f"TKT-PG-{index}",
            channel="web",
            customer_name="Tester",
            customer_email=f"tester{index}@example.com",
            subject=f"Ticket {index}",
            content="PostgreSQL pagination test content.",
            status=TicketStatus.RECEIVED,
            created_at=base + timedelta(seconds=index),
            updated_at=base + timedelta(seconds=index),
        )
        for index in range(3)
    ]
    postgres_session.add_all(tickets)
    postgres_session.commit()

    items = TicketRepository(postgres_session).list_tickets(limit=2, offset=1)

    assert [item.ticket_code for item in items] == ["TKT-PG-1", "TKT-PG-0"]
    assert TicketRepository(postgres_session).count_tickets() == 3


def test_postgres_transaction_rollback_on_persistence_failure(
    postgres_client,
    postgres_session: Session,
    integration_ticket_payload: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_add_event(self: TicketRepository, event: TicketEvent) -> TicketEvent:
        raise SQLAlchemyError("simulated integration persistence failure")

    monkeypatch.setattr(TicketRepository, "add_event", fail_add_event)

    response = postgres_client.post("/api/v1/tickets", json=integration_ticket_payload)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "TICKET_PERSISTENCE_FAILED"
    assert postgres_session.scalar(select(func.count()).select_from(Ticket)) == 0
    assert postgres_session.scalar(select(func.count()).select_from(TicketEvent)) == 0

