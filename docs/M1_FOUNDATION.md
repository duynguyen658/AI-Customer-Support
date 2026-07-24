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
- PostgreSQL integration tests that run Alembic migrations against a dedicated test database.
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
pytest -q -m "not integration"
pytest -q -m integration
pytest --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=75
```

Fast tests override the FastAPI database dependency and use an isolated in-memory database. PostgreSQL integration tests require `TEST_DATABASE_URL`, refuse non-test database names, reset only the dedicated test schema, and create schema through Alembic migrations rather than `Base.metadata.create_all`.

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
- Automated tests for health, validation, retrieval, listing, events, rollback, database-health failure, and PostgreSQL migrations.
- Redundant non-unique `ix_tickets_ticket_code` index removal while preserving unique ticket-code enforcement.
- CI workflow for migrations, tests, PostgreSQL integration tests, and coverage.
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
- PostgreSQL integration tests require a dedicated PostgreSQL test database.
- CI workflow has been added; remote pass/fail status depends on GitHub Actions execution.

## Next Milestone Overview

The next milestone can add controlled AI classification and confidence handling after the foundation is verified in PostgreSQL. It should keep model/provider logic separate from ticket persistence and preserve auditability through ticket events.
