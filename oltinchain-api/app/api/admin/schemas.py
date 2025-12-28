"""Admin API schemas."""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


# Users
class AdminUserResponse(BaseModel):
    """User info for admin."""
    id: str
    phone: str
    wallet_address: str | None
    kyc_level: int
    is_active: bool
    balance_uzs: Decimal
    balance_oltin: Decimal
    orders_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserListResponse(BaseModel):
    """List of users."""
    users: list[AdminUserResponse]
    total: int
    limit: int
    offset: int


class AdminUserUpdateRequest(BaseModel):
    """Update user request."""
    is_active: bool | None = None
    kyc_level: int | None = None


# Transactions
class AdminTransactionResponse(BaseModel):
    """Transaction for admin view."""
    id: str
    user_id: str
    user_phone: str
    type: str
    amount_uzs: Decimal
    amount_oltin: Decimal
    price_per_gram: Decimal
    fee_uzs: Decimal
    status: str
    tx_hash: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AdminTransactionListResponse(BaseModel):
    """List of transactions."""
    transactions: list[AdminTransactionResponse]
    total: int
    limit: int
    offset: int


# Alerts
class AdminAlertResponse(BaseModel):
    """Alert for admin view."""
    id: str
    user_id: str
    user_phone: str
    order_id: str | None
    alert_type: str
    severity: str
    details: dict | None
    status: str
    created_at: datetime
    resolved_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AdminAlertListResponse(BaseModel):
    """List of alerts."""
    alerts: list[AdminAlertResponse]
    total: int
    limit: int
    offset: int


class AdminAlertUpdateRequest(BaseModel):
    """Update alert status."""
    status: str  # new, reviewing, resolved, dismissed


# Analytics
class AdminAnalyticsResponse(BaseModel):
    """Platform analytics."""
    total_users: int
    active_users_24h: int
    total_orders: int
    orders_24h: int
    total_volume_uzs: Decimal
    volume_24h_uzs: Decimal
    total_oltin_minted: Decimal
    pending_alerts: int
    high_severity_alerts: int
