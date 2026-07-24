# Milestone 1: Foundation and Ticket Management

## Objective

Milestone 1 establishes a stable Python backend for the AI Customer Support Automation System. It implements ticket persistence, event history, API validation, migrations, Docker configuration, tests, and documentation.

No AI functionality is implemented in this milestone.

## Architecture Implemented

- FastAPI application with versioned ticket routes.
- Pydantic v2 request and response schemas.
- SQLAlchemy 2 ORM models and repositories.
- Service layer for ticket business rules and transactions.
- Alembic migrations for schema creation.
- Structlog JSON logging.
- Pytest API tests with dependency-overridden isolated database sessions.
- Docker Compose for PostgreSQL 16 and the API service.

## Folder Structure

```text
app/
  api/
  core/
  db/
  models/
  repositories/
  schemas/
  services/
alembic/
tests/
docs/
```

## Database Entities

### Ticket

Stores customer support requests with UUID primary keys, unique ticket codes, customer contact fields, subject/content, workflow status, future nullable AI-related fields, timestamps, and optional parent ticket references.

### TicketEvent

Stores chronological history for each ticket. Ticket deletion cascades to related events.

## API Endpoints

- `GET /health`
- `GET /health/db`
- `POST /api/v1/tickets`
- `GET /api/v1/tickets`
- `GET /api/v1/tickets/{ticket_id}`
- `GET /api/v1/tickets/{ticket_id}/events`

Swagger UI is available at `http://localhost:8000/docs`.

## Ticket Initial-State Rules

New tickets:

- Receive a generated `TKT-YYYYMMDDHHMMSS-XXXXXX` ticket code.
- Start with status `RECEIVED`.
- Keep `category`, `priority`, and `confidence` as `null`.
- Normalize channel and email to lowercase.
- Trim customer name, subject, and content.
- Create exactly one `TICKET_CREATED` event.

## Transactions

Ticket creation adds the ticket and its first event in one SQLAlchemy session transaction. The service commits only after both records are flushed successfully. Any SQLAlchemy persistence error rolls back the whole transaction and returns a client-safe infrastructure error.

## Migrations

Alembic reads `DATABASE_URL` from the environment.

```bash
alembic upgrade head
alembic current
alembic history
```

FastAPI startup does not create tables automatically.

## Tests

```bash
pytest -q
pytest --cov=app --cov-report=term-missing
```

The test suite overrides the FastAPI database dependency and uses an isolated in-memory database. This prevents tests from modifying a production or local PostgreSQL database.

## Completed

- FastAPI app and health checks.
- PostgreSQL-oriented SQLAlchemy models.
- Alembic initial migration.
- Ticket create/list/detail APIs.
- Ticket event-history API.
- Validation for ticket input.
- Structured 404 and infrastructure error responses.
- Atomic ticket creation with rollback.
- Dockerfile and Docker Compose.
- Automated tests for health, validation, retrieval, listing, events, and rollback.
- README and milestone documentation.

## Not Implemented Yet

- LLM classification
- prompt engineering
- RAG
- knowledge base
- spam detection
- duplicate detection
- missing-information detection
- human review
- dashboard
- n8n

## Known Limitations

- Authentication and authorization are intentionally out of scope.
- Background workers are intentionally out of scope.
- Tests use an isolated override database; run Alembic against PostgreSQL locally to validate the production migration path.

## Next Milestone Overview

The next milestone can add controlled AI classification and confidence handling after the foundation is verified in PostgreSQL. It should keep model/provider logic separate from ticket persistence and preserve auditability through ticket events.

