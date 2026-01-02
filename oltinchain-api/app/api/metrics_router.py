"""Dashboard metrics API endpoints."""

from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, union
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.infrastructure.models import LimitOrder, Trade

router = APIRouter(prefix="/metrics", tags=["metrics"])


class DashboardMetrics(BaseModel):
    """Dashboard metrics response."""

    total_supply: str
    transaction_count_24h: int
    active_users_24h: int
    volume_24h: str


@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    session: AsyncSession = Depends(get_session),
) -> DashboardMetrics:
    """Get dashboard metrics for the last 24 hours."""
    now = datetime.utcnow()
    day_ago = now - timedelta(hours=24)

    # Get trade count in last 24h
    count_query = select(func.count(Trade.id)).where(Trade.created_at >= day_ago)
    count_result = await session.execute(count_query)
    trade_count = count_result.scalar() or 0

    # Get volume in last 24h
    volume_query = select(func.sum(Trade.quantity)).where(Trade.created_at >= day_ago)
    volume_result = await session.execute(volume_query)
    volume = volume_result.scalar() or Decimal("0")

    # Get unique active users (actual user_ids from orders involved in trades)
    # Join trades with orders to get user_ids
    buy_users = (
        select(LimitOrder.user_id)
        .join(Trade, Trade.buy_order_id == LimitOrder.id)
        .where(Trade.created_at >= day_ago)
    )
    sell_users = (
        select(LimitOrder.user_id)
        .join(Trade, Trade.sell_order_id == LimitOrder.id)
        .where(Trade.created_at >= day_ago)
    )

    # Union and count distinct
    all_users = union(buy_users, sell_users).subquery()
    active_query = select(func.count(func.distinct(all_users.c.user_id)))
    active_result = await session.execute(active_query)
    active_users = active_result.scalar() or 0

    total_supply = "10000.0000"

    return DashboardMetrics(
        total_supply=total_supply,
        transaction_count_24h=trade_count,
        active_users_24h=active_users,
        volume_24h=str(volume),
    )
