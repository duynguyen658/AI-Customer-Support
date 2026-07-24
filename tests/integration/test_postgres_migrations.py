import pytest
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


pytestmark = pytest.mark.integration


def test_postgres_migration_creates_expected_tables(postgres_engine: Engine) -> None:
    inspector = inspect(postgres_engine)

    assert {"tickets", "ticket_events", "alembic_version"}.issubset(
        set(inspector.get_table_names())
    )


def test_postgres_migration_revision_is_head(postgres_engine: Engine) -> None:
    with postgres_engine.connect() as conn:
        revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    assert revision == "202607250001"


def test_redundant_ticket_code_index_is_removed(postgres_engine: Engine) -> None:
    inspector = inspect(postgres_engine)
    indexes = {index["name"] for index in inspector.get_indexes("tickets")}

    assert "ix_tickets_ticket_code" not in indexes
    assert {"ix_tickets_customer_email", "ix_tickets_status", "ix_tickets_created_at"}.issubset(indexes)


def test_ticket_code_unique_constraint_remains(postgres_engine: Engine) -> None:
    inspector = inspect(postgres_engine)
    constraints = inspector.get_unique_constraints("tickets")

    assert any(
        constraint["column_names"] == ["ticket_code"]
        for constraint in constraints
    )


def test_ticket_foreign_key_actions(postgres_engine: Engine) -> None:
    inspector = inspect(postgres_engine)
    ticket_fks = inspector.get_foreign_keys("tickets")
    event_fks = inspector.get_foreign_keys("ticket_events")

    assert any(
        fk["referred_table"] == "tickets"
        and fk["constrained_columns"] == ["parent_ticket_id"]
        and fk["options"].get("ondelete") == "SET NULL"
        for fk in ticket_fks
    )
    assert any(
        fk["referred_table"] == "tickets"
        and fk["constrained_columns"] == ["ticket_id"]
        and fk["options"].get("ondelete") == "CASCADE"
        for fk in event_fks
    )

