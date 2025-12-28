"""Metrics service for dashboard."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import Order, User


class MetricsService:
    """Service for calculating platform metrics."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_live_metrics(self) -> dict:
        """Get live metrics for dashboard."""
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(hours=24)

        # Transaction count in 24h
        tx_count_result = await self.session.execute(
            select(func.count(Order.id)).where(
                and_(
                    Order.status == "completed",
                    Order.created_at >= day_ago
                )
            )
        )
        transaction_count_24h = tx_count_result.scalar() or 0

        # Volume in 24h (OLTIN)
        volume_result = await self.session.execute(
            select(func.sum(Order.amount_oltin)).where(
                and_(
                    Order.status == "completed",
                    Order.created_at >= day_ago
                )
            )
        )
        volume_24h = volume_result.scalar() or Decimal("0")

        # Active users in 24h (unique users with orders)
        active_result = await self.session.execute(
            select(func.count(func.distinct(Order.user_id))).where(
                and_(
                    Order.status == "completed",
                    Order.created_at >= day_ago
                )
            )
        )
        active_users_24h = active_result.scalar() or 0

        return {
            "transaction_count_24h": transaction_count_24h,
            "volume_24h": str(volume_24h),
            "active_users_24h": active_users_24h,
        }
