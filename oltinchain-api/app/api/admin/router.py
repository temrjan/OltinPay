"""Admin API endpoints."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.schemas import (
    AdminAlertListResponse,
    AdminAlertResponse,
    AdminAlertUpdateRequest,
    AdminAnalyticsResponse,
    AdminTransactionListResponse,
    AdminTransactionResponse,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdateRequest,
)
from app.api.deps import get_session
from app.infrastructure.models import Alert, Balance, Order, User

router = APIRouter(prefix="/admin", tags=["admin"])


# NOTE: В продакшене нужно добавить проверку роли администратора
# Сейчас endpoints открыты для demo целей


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = None,
    is_active: bool | None = None,
    session: AsyncSession = Depends(get_session),
):
    """List all users with their balances and order counts."""
    # Base query
    query = select(User).order_by(desc(User.created_at))

    # Filters
    if search:
        query = query.where(User.phone.contains(search))
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # Count total
    count_query = select(func.count()).select_from(User)
    if search:
        count_query = count_query.where(User.phone.contains(search))
    if is_active is not None:
        count_query = count_query.where(User.is_active == is_active)
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    users = result.scalars().all()

    # Build response with balances and order counts
    user_responses = []
    for user in users:
        # Get balances
        balance_uzs = Decimal("0")
        balance_oltin = Decimal("0")
        for b in user.balances:
            if b.asset == "UZS":
                balance_uzs = b.available + b.locked
            elif b.asset == "OLTIN":
                balance_oltin = b.available + b.locked

        # Get order count
        orders_count = len(user.orders)

        user_responses.append(
            AdminUserResponse(
                id=str(user.id),
                phone=user.phone,
                wallet_address=user.wallet_address,
                kyc_level=user.kyc_level,
                is_active=user.is_active,
                balance_uzs=balance_uzs,
                balance_oltin=balance_oltin,
                orders_count=orders_count,
                created_at=user.created_at,
            )
        )

    return AdminUserListResponse(
        users=user_responses,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get single user details."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    balance_uzs = Decimal("0")
    balance_oltin = Decimal("0")
    for b in user.balances:
        if b.asset == "UZS":
            balance_uzs = b.available + b.locked
        elif b.asset == "OLTIN":
            balance_oltin = b.available + b.locked

    return AdminUserResponse(
        id=str(user.id),
        phone=user.phone,
        wallet_address=user.wallet_address,
        kyc_level=user.kyc_level,
        is_active=user.is_active,
        balance_uzs=balance_uzs,
        balance_oltin=balance_oltin,
        orders_count=len(user.orders),
        created_at=user.created_at,
    )


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: UUID,
    request: AdminUserUpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Update user status or KYC level."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.is_active is not None:
        user.is_active = request.is_active
    if request.kyc_level is not None:
        user.kyc_level = request.kyc_level

    await session.commit()
    await session.refresh(user)

    balance_uzs = Decimal("0")
    balance_oltin = Decimal("0")
    for b in user.balances:
        if b.asset == "UZS":
            balance_uzs = b.available + b.locked
        elif b.asset == "OLTIN":
            balance_oltin = b.available + b.locked

    return AdminUserResponse(
        id=str(user.id),
        phone=user.phone,
        wallet_address=user.wallet_address,
        kyc_level=user.kyc_level,
        is_active=user.is_active,
        balance_uzs=balance_uzs,
        balance_oltin=balance_oltin,
        orders_count=len(user.orders),
        created_at=user.created_at,
    )


@router.get("/transactions", response_model=AdminTransactionListResponse)
async def list_transactions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = None,
    order_type: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """List all orders/transactions."""
    # Join with User to get phone
    query = (
        select(Order, User.phone)
        .join(User, Order.user_id == User.id)
        .order_by(desc(Order.created_at))
    )

    # Filters
    if status:
        query = query.where(Order.status == status)
    if order_type:
        query = query.where(Order.type == order_type)

    # Count total
    count_query = select(func.count()).select_from(Order)
    if status:
        count_query = count_query.where(Order.status == status)
    if order_type:
        count_query = count_query.where(Order.type == order_type)
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    rows = result.all()

    transactions = [
        AdminTransactionResponse(
            id=str(order.id),
            user_id=str(order.user_id),
            user_phone=phone,
            type=order.type,
            amount_uzs=order.amount_uzs,
            amount_oltin=order.amount_oltin,
            price_per_gram=order.price_per_gram,
            fee_uzs=order.fee_uzs,
            status=order.status,
            tx_hash=order.tx_hash,
            created_at=order.created_at,
            completed_at=order.completed_at,
        )
        for order, phone in rows
    ]

    return AdminTransactionListResponse(
        transactions=transactions,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/alerts", response_model=AdminAlertListResponse)
async def list_alerts(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = None,
    severity: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """List all fraud alerts."""
    # Join with User to get phone
    query = (
        select(Alert, User.phone)
        .join(User, Alert.user_id == User.id)
        .order_by(desc(Alert.created_at))
    )

    # Filters
    if status:
        query = query.where(Alert.status == status)
    if severity:
        query = query.where(Alert.severity == severity)

    # Count total
    count_query = select(func.count()).select_from(Alert)
    if status:
        count_query = count_query.where(Alert.status == status)
    if severity:
        count_query = count_query.where(Alert.severity == severity)
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    rows = result.all()

    alerts = [
        AdminAlertResponse(
            id=str(alert.id),
            user_id=str(alert.user_id),
            user_phone=phone,
            order_id=str(alert.order_id) if alert.order_id else None,
            alert_type=alert.alert_type,
            severity=alert.severity,
            details=alert.details,
            status=alert.status,
            created_at=alert.created_at,
            resolved_at=alert.resolved_at,
        )
        for alert, phone in rows
    ]

    return AdminAlertListResponse(
        alerts=alerts,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/alerts/{alert_id}", response_model=AdminAlertResponse)
async def update_alert(
    alert_id: UUID,
    request: AdminAlertUpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Update alert status."""
    result = await session.execute(
        select(Alert, User.phone).join(User, Alert.user_id == User.id).where(Alert.id == alert_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert, phone = row

    alert.status = request.status
    if request.status in ("resolved", "dismissed"):
        alert.resolved_at = datetime.utcnow()

    await session.commit()
    await session.refresh(alert)

    return AdminAlertResponse(
        id=str(alert.id),
        user_id=str(alert.user_id),
        user_phone=phone,
        order_id=str(alert.order_id) if alert.order_id else None,
        alert_type=alert.alert_type,
        severity=alert.severity,
        details=alert.details,
        status=alert.status,
        created_at=alert.created_at,
        resolved_at=alert.resolved_at,
    )


@router.get("/analytics", response_model=AdminAnalyticsResponse)
async def get_analytics(
    session: AsyncSession = Depends(get_session),
):
    """Get platform analytics."""
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)

    # Total users
    total_users_result = await session.execute(select(func.count()).select_from(User))
    total_users = total_users_result.scalar() or 0

    # Active users (had orders in last 24h)
    active_users_result = await session.execute(
        select(func.count(func.distinct(Order.user_id))).where(Order.created_at >= day_ago)
    )
    active_users_24h = active_users_result.scalar() or 0

    # Total orders
    total_orders_result = await session.execute(
        select(func.count()).select_from(Order).where(Order.status == "completed")
    )
    total_orders = total_orders_result.scalar() or 0

    # Orders in 24h
    orders_24h_result = await session.execute(
        select(func.count())
        .select_from(Order)
        .where(Order.status == "completed")
        .where(Order.created_at >= day_ago)
    )
    orders_24h = orders_24h_result.scalar() or 0

    # Total volume UZS
    total_volume_result = await session.execute(
        select(func.coalesce(func.sum(Order.amount_uzs), 0)).where(Order.status == "completed")
    )
    total_volume_uzs = total_volume_result.scalar() or Decimal("0")

    # Volume 24h
    volume_24h_result = await session.execute(
        select(func.coalesce(func.sum(Order.amount_uzs), 0))
        .where(Order.status == "completed")
        .where(Order.created_at >= day_ago)
    )
    volume_24h_uzs = volume_24h_result.scalar() or Decimal("0")

    # Total OLTIN minted (sum of buy orders)
    oltin_result = await session.execute(
        select(func.coalesce(func.sum(Order.amount_oltin), 0))
        .where(Order.status == "completed")
        .where(Order.type == "buy")
    )
    total_oltin_minted = oltin_result.scalar() or Decimal("0")

    # Pending alerts
    pending_alerts_result = await session.execute(
        select(func.count()).select_from(Alert).where(Alert.status.in_(["new", "reviewing"]))
    )
    pending_alerts = pending_alerts_result.scalar() or 0

    # High severity alerts
    high_alerts_result = await session.execute(
        select(func.count())
        .select_from(Alert)
        .where(Alert.severity == "high")
        .where(Alert.status.in_(["new", "reviewing"]))
    )
    high_severity_alerts = high_alerts_result.scalar() or 0

    return AdminAnalyticsResponse(
        total_users=total_users,
        active_users_24h=active_users_24h,
        total_orders=total_orders,
        orders_24h=orders_24h,
        total_volume_uzs=total_volume_uzs,
        volume_24h_uzs=volume_24h_uzs,
        total_oltin_minted=total_oltin_minted,
        pending_alerts=pending_alerts,
        high_severity_alerts=high_severity_alerts,
    )


# === Internal Endpoints for Bots ===

from pydantic import BaseModel


class AddBalanceRequest(BaseModel):
    phone: str
    asset: str  # USD or OLTIN
    amount: Decimal


class AddBalanceResponse(BaseModel):
    user_id: str
    phone: str
    asset: str
    new_balance: Decimal


@router.post("/internal/add-balance", response_model=AddBalanceResponse)
async def add_balance(
    request: AddBalanceRequest,
    session: AsyncSession = Depends(get_session),
):
    """Add balance to a user by phone. Internal use for bots."""
    from uuid import uuid4

    # Find user
    result = await session.execute(select(User).where(User.phone == request.phone))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"User with phone {request.phone} not found")

    # Find or create balance
    balance_result = await session.execute(
        select(Balance).where(Balance.user_id == user.id, Balance.asset == request.asset)
    )
    balance = balance_result.scalar_one_or_none()

    if balance:
        balance.available += request.amount
    else:
        balance = Balance(
            id=uuid4(),
            user_id=user.id,
            asset=request.asset,
            available=request.amount,
            locked=Decimal("0"),
        )
        session.add(balance)

    await session.commit()
    await session.refresh(balance)

    return AddBalanceResponse(
        user_id=str(user.id),
        phone=user.phone,
        asset=request.asset,
        new_balance=balance.available,
    )
