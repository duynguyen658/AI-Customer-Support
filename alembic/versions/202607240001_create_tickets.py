"""create tickets and ticket events

Revision ID: 202607240001
Revises:
Create Date: 2026-07-24 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202607240001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_code", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("customer_email", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "information",
                "complaint",
                "technical",
                "payment",
                "emergency",
                "spam",
                "unknown",
                name="ticketcategory",
                native_enum=False,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column(
            "priority",
            sa.Enum(
                "low",
                "medium",
                "high",
                "critical",
                name="ticketpriority",
                native_enum=False,
                length=16,
            ),
            nullable=True,
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "RECEIVED",
                "PROCESSING",
                "CLASSIFIED",
                "NEED_MORE_INFO",
                "RETRIEVING",
                "AUTO_ANSWERED",
                "ESCALATED",
                "HUMAN_REVIEW",
                "RESOLVED",
                "SPAM",
                "DUPLICATE",
                "PROCESSING_FAILED",
                name="ticketstatus",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("assigned_team", sa.String(length=128), nullable=True),
        sa.Column("parent_ticket_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent_ticket_id"],
            ["tickets.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_code"),
    )
    op.create_index("ix_tickets_created_at", "tickets", ["created_at"], unique=False)
    op.create_index(
        "ix_tickets_customer_email",
        "tickets",
        ["customer_email"],
        unique=False,
    )
    op.create_index("ix_tickets_status", "tickets", ["status"], unique=False)
    op.create_index("ix_tickets_ticket_code", "tickets", ["ticket_code"], unique=False)

    op.create_table(
        "ticket_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_events_ticket_id", "ticket_events", ["ticket_id"])


def downgrade() -> None:
    op.drop_index("ix_ticket_events_ticket_id", table_name="ticket_events")
    op.drop_table("ticket_events")
    op.drop_index("ix_tickets_ticket_code", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_index("ix_tickets_customer_email", table_name="tickets")
    op.drop_index("ix_tickets_created_at", table_name="tickets")
    op.drop_table("tickets")

