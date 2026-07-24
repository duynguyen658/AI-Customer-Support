import os
from collections.abc import Generator
from urllib.parse import urlparse

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app


def _require_safe_test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not set; skipping PostgreSQL integration tests")

    database_name = urlparse(database_url).path.lstrip("/")
    if "test" not in database_name.lower():
        pytest.fail("Refusing to run integration tests against a non-test database")
    return database_url


@pytest.fixture(scope="session")
def postgres_url() -> str:
    return _require_safe_test_database_url()


@pytest.fixture(scope="session")
def postgres_engine(postgres_url: str) -> Generator[Engine, None, None]:
    engine = create_engine(postgres_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def migrated_postgres(postgres_url: str, postgres_engine: Engine) -> None:
    with postgres_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    os.environ["DATABASE_URL"] = postgres_url
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture()
def postgres_session(postgres_engine: Engine) -> Generator[Session, None, None]:
    session_factory = sessionmaker(
        bind=postgres_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        with postgres_engine.begin() as conn:
            conn.execute(text("DELETE FROM tickets"))


@pytest.fixture()
def postgres_client(postgres_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield postgres_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def integration_ticket_payload() -> dict[str, str]:
    return {
        "channel": "web",
        "customer_name": "Minh Duy",
        "customer_email": "minhduy@example.com",
        "subject": "Payment has not been updated",
        "content": "I completed the payment but the transaction is not visible.",
    }

