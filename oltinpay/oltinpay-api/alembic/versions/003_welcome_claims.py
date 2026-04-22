# mypy: ignore-errors
"""Add welcome_claims table.

Revision ID: 003
Revises: 002
Create Date: 2026-04-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "welcome_claims",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("wallet_address", sa.String(42), nullable=False),
        sa.Column("tx_hash", sa.String(66), nullable=False),
        sa.Column("amount_wei", sa.String(80), nullable=False),
        sa.Column(
            "claimed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", name="uq_welcome_claim_user"),
    )
    op.create_index(
        "ix_welcome_claims_user_id", "welcome_claims", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_welcome_claims_user_id", table_name="welcome_claims")
    op.drop_table("welcome_claims")
