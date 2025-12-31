"""OrderBook broadcast service for real-time updates."""

import asyncio
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ws.manager import manager
from app.infrastructure.models import LimitOrder, Trade

logger = structlog.get_logger()


class OrderBookBroadcast:
    """Service for broadcasting orderbook updates via WebSocket."""

    @staticmethod
    async def broadcast_orderbook_update(session: AsyncSession, depth: int = 20):
        """Broadcast current orderbook state to all subscribers."""
        try:
            # Get bids (buy orders) - highest price first
            bids_query = (
                select(LimitOrder.price, LimitOrder.quantity, LimitOrder.filled_quantity)
                .where(and_(
                    LimitOrder.side == "buy",
                    LimitOrder.status.in_(["open", "partial"])
                ))
                .order_by(LimitOrder.price.desc())
            )
            bids_result = await session.execute(bids_query)
            
            # Aggregate by price
            bids_aggregated: dict[Decimal, Decimal] = {}
            for row in bids_result:
                price = row.price
                remaining = row.quantity - row.filled_quantity
                if price in bids_aggregated:
                    bids_aggregated[price] += remaining
                else:
                    bids_aggregated[price] = remaining

            # Get asks (sell orders) - lowest price first
            asks_query = (
                select(LimitOrder.price, LimitOrder.quantity, LimitOrder.filled_quantity)
                .where(and_(
                    LimitOrder.side == "sell",
                    LimitOrder.status.in_(["open", "partial"])
                ))
                .order_by(LimitOrder.price.asc())
            )
            asks_result = await session.execute(asks_query)
            
            # Aggregate by price
            asks_aggregated: dict[Decimal, Decimal] = {}
            for row in asks_result:
                price = row.price
                remaining = row.quantity - row.filled_quantity
                if price in asks_aggregated:
                    asks_aggregated[price] += remaining
                else:
                    asks_aggregated[price] = remaining

            # Format response
            bids = [
                {"price": str(price), "quantity": str(qty)}
                for price, qty in sorted(bids_aggregated.items(), reverse=True)[:depth]
            ]
            asks = [
                {"price": str(price), "quantity": str(qty)}
                for price, qty in sorted(asks_aggregated.items())[:depth]
            ]

            message = {
                "type": "orderbook",
                "data": {
                    "bids": bids,
                    "asks": asks,
                }
            }

            await manager.broadcast_to_channel("orderbook", message)
            logger.debug("orderbook_broadcast", bids=len(bids), asks=len(asks))

        except Exception as e:
            logger.error("orderbook_broadcast_error", error=str(e))

    @staticmethod
    async def broadcast_trade(trade: Trade):
        """Broadcast a new trade to all subscribers."""
        try:
            message = {
                "type": "trade",
                "data": {
                    "id": str(trade.id),
                    "price": str(trade.price),
                    "quantity": str(trade.quantity),
                    "taker_side": trade.taker_side,
                    "created_at": trade.created_at.isoformat(),
                }
            }

            await manager.broadcast_to_channel("trades", message)
            logger.debug("trade_broadcast", trade_id=str(trade.id))

        except Exception as e:
            logger.error("trade_broadcast_error", error=str(e))

    @staticmethod
    async def broadcast_order_update(order: LimitOrder, action: str):
        """Broadcast order update (placed, cancelled, filled)."""
        try:
            message = {
                "type": "order_update",
                "action": action,
                "data": {
                    "id": str(order.id),
                    "side": order.side,
                    "price": str(order.price),
                    "quantity": str(order.quantity),
                    "filled_quantity": str(order.filled_quantity),
                    "status": order.status,
                }
            }

            await manager.broadcast_to_channel("orderbook", message)

        except Exception as e:
            logger.error("order_update_broadcast_error", error=str(e))


# Global instance
orderbook_broadcast = OrderBookBroadcast()
