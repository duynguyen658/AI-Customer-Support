from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.main import app


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_database_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_health_does_not_require_database(client: TestClient) -> None:
    def broken_db():
        raise AssertionError("database dependency should not be used")
        yield

    app.dependency_overrides[get_db] = broken_db

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_database_health_failure_returns_structured_503(client: TestClient) -> None:
    class BrokenSession:
        def execute(self, statement):
            raise SQLAlchemyError("simulated database outage with sensitive details")

    def broken_db():
        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_db

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "DATABASE_UNAVAILABLE",
            "message": "Database is unavailable.",
        }
    }
    assert "simulated" not in response.text
    assert "sensitive" not in response.text
