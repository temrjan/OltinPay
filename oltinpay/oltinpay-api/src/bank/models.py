"""Bank connector database models — idempotency ledgers for A2.

Each bank write reserves a row with a UNIQUE idempotency key BEFORE broadcasting
on-chain (reserve-then-broadcast, mirroring welcome/models.py). A duplicate
``auditRef`` / ``bankTxId`` collides on the unique index and never reaches a
second broadcast.
"""

from __future__ import annotations

from datetime import (
    datetime,  # noqa: TC003 — required at runtime for SQLAlchemy Mapped
)
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003 — required at runtime for SQLAlchemy Mapped

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.users.models import User


class ReserveAttestation(Base):
    """A gold-reserve attestation posted to the ReserveAttestor feed."""

    __tablename__ = "reserve_attestations"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    grams: Mapped[int] = mapped_column(BigInteger, nullable=False)
    audit_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("audit_ref", name="uq_reserve_attestation_audit_ref"),
    )

    def __repr__(self) -> str:
        return (
            f"<ReserveAttestation(audit_ref={self.audit_ref}, "
            f"grams={self.grams}, tx_hash={self.tx_hash})>"
        )


class BankDeposit(Base):
    """A confirmed fiat deposit that minted UZD to the user's wallet."""

    __tablename__ = "bank_deposits"

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
    bank_tx_id: Mapped[str] = mapped_column(String(128), nullable=False)
    amount_uzs: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount_wei: Mapped[str] = mapped_column(String(80), nullable=False)
    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship("User")

    __table_args__ = (UniqueConstraint("bank_tx_id", name="uq_bank_deposit_bank_tx_id"),)

    def __repr__(self) -> str:
        return (
            f"<BankDeposit(bank_tx_id={self.bank_tx_id}, "
            f"amount_uzs={self.amount_uzs}, tx_hash={self.tx_hash})>"
        )
