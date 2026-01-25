"""Transfer database models."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class TransferStatus(StrEnum):
    """Transfer status enumeration."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class Transfer(Base):
    """Blockchain transfer between users."""

    __tablename__ = "transfers"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    from_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )
    fee: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )
    tx_hash: Mapped[str | None] = mapped_column(
        String(66),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=TransferStatus.PENDING,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    from_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[from_user_id],
    )
    to_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[to_user_id],
    )

    def __repr__(self) -> str:
        return f"<Transfer(id={self.id}, amount={self.amount}, status={self.status})>"


from src.users.models import User  # noqa: E402, TC001
