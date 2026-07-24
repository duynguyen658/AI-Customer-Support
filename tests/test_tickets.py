from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.ticket import TicketStatus, utc_now
from app.models.ticket_event import TicketEvent
from app.repositories.ticket_repository import TicketRepository


def create_ticket(client: TestClient, payload: dict[str, str]) -> dict:
    response = client.post("/api/v1/tickets", json=payload)
    assert response.status_code == 201
    return response.json()


def test_valid_ticket_creation_sets_initial_state_and_event(
    client: TestClient,
    valid_ticket_payload: dict[str, str],
) -> None:
    ticket = create_ticket(client, valid_ticket_payload)

    assert ticket["status"] == "RECEIVED"
    assert ticket["category"] is None
    assert ticket["priority"] is None
    assert ticket["confidence"] is None
    assert ticket["channel"] == "web"
    assert ticket["customer_email"] == "minh@example.com"
    assert ticket["customer_name"] == "Minh Nguyen"
    assert ticket["subject"] == "Cannot access account"

    events_response = client.get(f"/api/v1/tickets/{ticket['id']}/events")
    assert events_response.status_code == 200
    events = events_response.json()
    assert len(events) == 1
    assert events[0]["event_type"] == "TICKET_CREATED"
    assert events[0]["from_status"] is None
    assert events[0]["to_status"] == "RECEIVED"
    assert events[0]["extra_data"]["channel"] == "web"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("customer_email", "not-an-email"),
        ("subject", "No"),
        ("content", "bad"),
        ("content", "x" * 20_001),
    ],
)
def test_ticket_validation_errors(
    client: TestClient,
    valid_ticket_payload: dict[str, str],
    field: str,
    value: str,
) -> None:
    payload = {**valid_ticket_payload, field: value}

    response = client.post("/api/v1/tickets", json=payload)

    assert response.status_code == 422


def test_existing_ticket_detail_returns_ticket(
    client: TestClient,
    valid_ticket_payload: dict[str, str],
) -> None:
    ticket = create_ticket(client, valid_ticket_payload)

    response = client.get(f"/api/v1/tickets/{ticket['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == ticket["id"]


def test_missing_ticket_returns_structured_404(client: TestClient) -> None:
    missing_id = uuid4()

    response = client.get(f"/api/v1/tickets/{missing_id}")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "TICKET_NOT_FOUND",
            "message": f"Ticket '{missing_id}' was not found.",
        }
    }


def test_invalid_ticket_uuid_returns_422(client: TestClient) -> None:
    response = client.get("/api/v1/tickets/not-a-uuid")

    assert response.status_code == 422


def test_ticket_list_supports_pagination_total_and_ordering(
    client: TestClient,
    valid_ticket_payload: dict[str, str],
) -> None:
    first = create_ticket(client, {**valid_ticket_payload, "subject": "First ticket"})
    second = create_ticket(client, {**valid_ticket_payload, "subject": "Second ticket"})
    third = create_ticket(client, {**valid_ticket_payload, "subject": "Third ticket"})

    response = client.get("/api/v1/tickets?limit=2&offset=1")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert [item["id"] for item in body["items"]] == [second["id"], first["id"]]
    assert third["id"] not in [item["id"] for item in body["items"]]


def test_ticket_events_are_chronological(
    client: TestClient,
    db_session: Session,
    valid_ticket_payload: dict[str, str],
) -> None:
    ticket = create_ticket(client, valid_ticket_payload)
    ticket_id = UUID(ticket["id"])
    base_time = utc_now()
    later_event = TicketEvent(
        ticket_id=ticket_id,
        event_type="SECOND_EVENT",
        from_status=TicketStatus.RECEIVED.value,
        to_status=TicketStatus.PROCESSING.value,
        reason="Manual test transition.",
        extra_data={"source": "test"},
        created_at=base_time + timedelta(seconds=5),
    )
    db_session.add(later_event)
    db_session.commit()

    response = client.get(f"/api/v1/tickets/{ticket_id}/events")

    assert response.status_code == 200
    assert [event["event_type"] for event in response.json()] == [
        "TICKET_CREATED",
        "SECOND_EVENT",
    ]


def test_missing_ticket_event_history_returns_404(client: TestClient) -> None:
    missing_id = uuid4()

    response = client.get(f"/api/v1/tickets/{missing_id}/events")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TICKET_NOT_FOUND"


def test_ticket_creation_rolls_back_when_event_persistence_fails(
    client: TestClient,
    db_session: Session,
    valid_ticket_payload: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_add_event(self: TicketRepository, event: TicketEvent) -> TicketEvent:
        raise SQLAlchemyError("simulated persistence failure")

    monkeypatch.setattr(TicketRepository, "add_event", fail_add_event)

    response = client.post("/api/v1/tickets", json=valid_ticket_payload)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "TICKET_PERSISTENCE_FAILED"
    assert TicketRepository(db_session).count_tickets() == 0
