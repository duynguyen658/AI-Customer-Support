"""drop redundant ticket code index

Revision ID: 202607250001
Revises: 202607240001
Create Date: 2026-07-25 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "202607250001"
down_revision: Union[str, None] = "202607240001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_tickets_ticket_code", table_name="tickets")


def downgrade() -> None:
    op.create_index(
        "ix_tickets_ticket_code",
        "tickets",
        ["ticket_code"],
        unique=False,
    )
