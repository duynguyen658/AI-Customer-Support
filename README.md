# AI Customer Support Automation System

Python backend for an AI Applied Specialist technical assessment. The system is being built incrementally to receive and manage customer-support requests before later AI automation milestones.

## Current Milestone

Milestone 1: Foundation and Ticket Management.

Implemented now:

- FastAPI service
- PostgreSQL persistence model
- Alembic migrations
- Ticket creation, listing, detail, and event history
- Structured 404 and infrastructure errors
- Health checks
- Structured logging
- Docker Compose setup
- Automated tests

AI features are not implemented in this milestone.

## Technology Stack

- Python 3.11
- FastAPI
- Uvicorn
- Pydantic v2
- pydantic-settings
- SQLAlchemy 2
- PostgreSQL 16
- psycopg 3
- Alembic
- structlog
- Pytest
- HTTPX
- Docker and Docker Compose

## Environment Setup

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create local environment settings:

```bash
copy .env.example .env
```

For local Docker, `.env.example` already contains safe development defaults.

## Docker Startup

```bash
docker compose up --build
```

The API listens on `http://localhost:8000`.

Swagger UI:

```text
http://localhost:8000/docs
```

## Migrations

With PostgreSQL reachable and `DATABASE_URL` configured:

```bash
alembic upgrade head
alembic current
alembic history
```

The application does not create tables on startup. Schema creation is handled by Alembic.

## Tests

```bash
pytest -q
pytest --cov=app --cov-report=term-missing
```

Tests override the database dependency and do not modify production databases.

## Example Ticket Request

```bash
curl -X POST http://localhost:8000/api/v1/tickets ^
  -H "Content-Type: application/json" ^
  -d "{\"channel\":\"web\",\"customer_name\":\"Minh Nguyen\",\"customer_email\":\"minh@example.com\",\"subject\":\"Cannot access account\",\"content\":\"I cannot access my account after resetting the password.\"}"
```

## Project Status

Milestone 1 is implemented. Later milestones may add AI classification, retrieval, spam or duplicate detection, missing-information checks, human review, dashboards, and integrations.

