"""Balance database models."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class AccountType(StrEnum):
    """Account type enumeration."""

    WALLET = "wallet"
    EXCHANGE = "exchange"
    STAKING = "staking"


class Currency(StrEnum):
    """Currency enumeration."""

    USD = "USD"
    OLTIN = "OLTIN"


class Balance(Base):
    """User balance model."""

    __tablename__ = "balances"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        default=Decimal("0"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="balances",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "account_type",
            "currency",
            name="uq_balance_user_account_currency",
        ),
        CheckConstraint("amount >= 0", name="ck_balance_amount_positive"),
    )

    def __repr__(self) -> str:
        return f"<Balance(user_id={self.user_id}, account_type={self.account_type}, currency={self.currency}, amount={self.amount})>"


# Import here to avoid circular imports
from src.users.models import User  # noqa: E402, TC001
