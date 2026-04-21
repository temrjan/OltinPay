# mypy: ignore-errors
"""Add wallet_address to users.

Revision ID: 002
Revises: 001
Create Date: 2026-04-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("wallet_address", sa.String(length=42), nullable=True),
    )
    op.create_index(
        "ix_users_wallet_address",
        "users",
        ["wallet_address"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_users_wallet_address", table_name="users")
    op.drop_column("users", "wallet_address")
