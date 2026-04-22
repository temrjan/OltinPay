"""Welcome claim database model — dedup ledger for the 1000 UZD bonus."""

from __future__ import annotations

from datetime import (
    datetime,  # noqa: TC003  — required at runtime for SQLAlchemy Mapped
)
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003  — required at runtime for SQLAlchemy Mapped

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.users.models import User


class WelcomeClaim(Base):
    """Records a single welcome bonus claim per user. One row per user."""

    __tablename__ = "welcome_claims"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    wallet_address: Mapped[str] = mapped_column(String(42), nullable=False)
    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    amount_wei: Mapped[str] = mapped_column(String(80), nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<WelcomeClaim(user_id={self.user_id}, "
            f"tx_hash={self.tx_hash}, amount_wei={self.amount_wei})>"
        )
