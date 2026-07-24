# AI Customer Support Automation System

Python backend for an AI Applied Specialist technical assessment. The current scope is Milestone 1: Foundation and Ticket Management.

## M1 Scope

Implemented:

- FastAPI service with Swagger at `http://localhost:8000/docs`
- PostgreSQL persistence with SQLAlchemy 2
- Alembic migrations
- Ticket creation, listing, detail, and event history
- Atomic Ticket and TicketEvent creation
- Structured 404 and infrastructure errors
- Health checks
- Structured JSON logging
- Docker Compose setup
- Fast SQLite tests and PostgreSQL integration tests
- GitHub Actions CI workflow

Deferred to later milestones: LLM classification, prompt engineering, RAG, knowledge base, spam detection, duplicate detection, missing-information detection, human review, dashboard, n8n, external channels, authentication, Redis, and Celery.

## Technology Stack

Python 3.11, FastAPI, Uvicorn, Pydantic v2, pydantic-settings, SQLAlchemy 2, PostgreSQL 16, psycopg 3, Alembic, structlog, Pytest, HTTPX, Docker, and Docker Compose.

## Prerequisites

- Python 3.11
- Docker Desktop or Docker Engine with Compose
- Git

## Windows PowerShell Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
pip install -r requirements.txt
```

## Linux / WSL Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
cp .env.example .env
pip install -r requirements.txt
```

## Docker Startup

Stable demo startup:

```bash
docker compose down -v
docker compose up --build -d
docker compose ps
docker compose logs api --tail=200
```

The API container waits for PostgreSQL to become healthy, runs `alembic upgrade head`, then starts Uvicorn on port `8000`.

Stop and reset Docker data:

```bash
docker compose down -v
```

## Health Checks

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/db
```

`/health` does not require database access. `/health/db` runs a lightweight `SELECT 1`.

## Migrations

Alembic reads `DATABASE_URL`.

```bash
alembic upgrade head
alembic current
alembic history
```

The application does not call `Base.metadata.create_all` during startup.

## Tests

Fast tests using isolated SQLite fixtures:

```bash
pytest -q -m "not integration"
```

PostgreSQL integration tests:

```bash
docker compose -f docker-compose.test.yml up -d
$env:TEST_DATABASE_URL = "postgresql+psycopg://support_test:support_test@localhost:5433/support_test"
pytest -q -m integration
```

Linux / WSL:

```bash
docker compose -f docker-compose.test.yml up -d
export TEST_DATABASE_URL="postgresql+psycopg://support_test:support_test@localhost:5433/support_test"
pytest -q -m integration
```

Complete suite and coverage:

```bash
pytest -q
pytest --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=75
```

Integration tests refuse to run destructive setup unless the target database name contains `test`.

## Example Requests

Bash:

```bash
curl -X POST http://localhost:8000/api/v1/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "web",
    "customer_name": "Minh Duy",
    "customer_email": "minhduy@example.com",
    "subject": "Payment has not been updated",
    "content": "I completed the payment but the transaction is not visible."
  }'
```

PowerShell:

```powershell
$body = @{
  channel = "web"
  customer_name = "Minh Duy"
  customer_email = "minhduy@example.com"
  subject = "Payment has not been updated"
  content = "I completed the payment but the transaction is not visible."
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/tickets" -ContentType "application/json" -Body $body
```

List tickets:

```bash
curl "http://localhost:8000/api/v1/tickets?limit=20&offset=0"
```

## Known Limitations

- No authentication or authorization yet.
- No background workers.
- PostgreSQL integration tests require a dedicated `TEST_DATABASE_URL`.
- GitHub Actions workflow is configured, but remote CI status depends on the workflow running on GitHub.
