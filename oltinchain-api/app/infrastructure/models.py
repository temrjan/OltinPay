from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """Пользователь платформы."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    wallet_address: Mapped[str | None] = mapped_column(String(42))
    encrypted_private_key: Mapped[str | None] = mapped_column(Text)  # Fernet encrypted
    kyc_level: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    kyc_data: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    balances: Mapped[list["Balance"]] = relationship(back_populates="user", lazy="selectin")
    orders: Mapped[list["Order"]] = relationship(back_populates="user", lazy="selectin")


class Balance(Base):
    """Баланс пользователя по активам."""

    __tablename__ = "balances"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    asset: Mapped[str] = mapped_column(String(10), nullable=False)
    available: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    locked: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(back_populates="balances")

    __table_args__ = (Index("ix_balances_user_asset", "user_id", "asset", unique=True),)


class Order(Base):
    """Ордер на покупку/продажу золота."""

    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)

    amount_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    amount_oltin: Mapped[Decimal] = mapped_column(Numeric(20, 18))
    price_per_gram: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    fee_uzs: Mapped[Decimal] = mapped_column(Numeric(20, 2))

    tx_hash: Mapped[str | None] = mapped_column(String(66))
    block_number: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="orders")

    __table_args__ = (
        Index("ix_orders_user_status", "user_id", "status"),
        Index("ix_orders_created", "created_at"),
        Index("ix_orders_tx_hash", "tx_hash"),
    )


class GoldBar(Base):
    """Физические слитки золота для Proof of Reserves."""

    __tablename__ = "gold_bars"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    serial_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    weight_grams: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    purity: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("999.9"))
    vault_location: Mapped[str] = mapped_column(String(100))
    acquired_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default=text("'active'")
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class Alert(Base):
    """Fraud detection алерты."""

    __tablename__ = "alerts"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    order_id: Mapped[UUID | None] = mapped_column(ForeignKey("orders.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    details: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="new", server_default=text("'new'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (
        Index("ix_alerts_user_status", "user_id", "status"),
        Index("ix_alerts_severity", "severity"),
    )


class Transaction(Base):
    """История транзакций пользователей."""

    __tablename__ = "transactions"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    order_id: Mapped[UUID | None] = mapped_column(ForeignKey("orders.id"))

    type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # deposit, withdraw, buy, sell, transfer
    asset: Mapped[str] = mapped_column(String(10), nullable=False)  # UZS, OLTIN
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)

    # For transfers
    to_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    to_address: Mapped[str | None] = mapped_column(String(42))

    tx_hash: Mapped[str | None] = mapped_column(String(66))
    block_number: Mapped[int | None] = mapped_column(Integer)

    status: Mapped[str] = mapped_column(String(20), default="completed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_transactions_user", "user_id"),
        Index("ix_transactions_created", "created_at"),
        Index("ix_transactions_tx_hash", "tx_hash"),
    )


class LimitOrder(Base):
    """Лимитный ордер в книге ордеров."""

    __tablename__ = "limit_orders"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Order details
    side: Mapped[str] = mapped_column(String(4), nullable=False)  # 'buy' or 'sell'
    price: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)  # OLTIN amount
    filled_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))

    # Status: open, partial, filled, cancelled
    status: Mapped[str] = mapped_column(String(20), default="open")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    filled_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationship
    user: Mapped["User"] = relationship()

    __table_args__ = (
        Index("ix_limit_orders_side_status_price", "side", "status", "price"),
        Index("ix_limit_orders_user_status", "user_id", "status"),
    )

    @property
    def remaining_quantity(self) -> Decimal:
        """Remaining quantity to fill."""
        return self.quantity - self.filled_quantity


class Trade(Base):
    """Исполненная сделка между двумя ордерами."""

    __tablename__ = "trades"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)

    # Orders involved
    buy_order_id: Mapped[UUID] = mapped_column(ForeignKey("limit_orders.id"), nullable=False)
    sell_order_id: Mapped[UUID] = mapped_column(ForeignKey("limit_orders.id"), nullable=False)

    # Trade details
    price: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)

    # Who initiated (taker)
    taker_side: Mapped[str] = mapped_column(String(4), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (Index("ix_trades_created", "created_at"),)
