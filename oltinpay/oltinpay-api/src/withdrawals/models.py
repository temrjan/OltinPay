"""Withdrawal database model.

A user files a withdrawal (status ``pending``); the bank later confirms (burns
the user's UZD on-chain, ``pending`` -> ``confirmed``) or rejects it
(``pending`` -> ``rejected``, no on-chain effect). State transitions are
one-way, guarded so a withdrawal is burned at most once.

Accepted limitation (spec §8): there is NO on-chain UZD lock between the user's
request and the bank's confirm — the user could move the UZD in that window. A
full on-chain escrow lock is deferred to PR-4.

SECURITY: the burn amount is capped at the user's net bank deposits (see
``withdrawals.service`` and ``bank.service.confirm_withdrawal``) so the burn can
only ever destroy UZD OltinPay minted to this user — never a third party's
tokens reached via an unverified wallet binding.
"""

from __future__ import annotations

from datetime import (
    datetime,  # noqa: TC003 — required at runtime for SQLAlchemy Mapped
)
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003 — required at runtime for SQLAlchemy Mapped

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.users.models import User


class WithdrawalStatus(StrEnum):
    """Withdrawal lifecycle state."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class Withdrawal(Base):
    """A user-initiated UZD -> fiat withdrawal request."""

    __tablename__ = "withdrawals"

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
    amount_uzd: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount_wei: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=WithdrawalStatus.PENDING.value,
        index=True,
    )
    tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<Withdrawal(id={self.id}, amount_uzd={self.amount_uzd}, "
            f"status={self.status})>"
        )
