"""OrderBook service for limit orders management.

Implements a price-time priority matching engine for limit orders.
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

import structlog
from sqlalchemy import and_, asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.orderbook_broadcast import orderbook_broadcast
from app.database import async_session_maker
from app.infrastructure.models import Balance, LimitOrder, Trade

logger = structlog.get_logger()


async def _broadcast_orderbook_with_new_session():
    """Broadcast orderbook update using a new database session."""
    try:
        async with async_session_maker() as session:
            await orderbook_broadcast.broadcast_orderbook_update(session)
    except Exception as e:
        logger.error("broadcast_orderbook_error", error=str(e))


async def _broadcast_trades(trades: list[Trade]):
    """Broadcast trades."""
    try:
        for trade in trades:
            await orderbook_broadcast.broadcast_trade(trade)
    except Exception as e:
        logger.error("broadcast_trades_error", error=str(e))


class OrderBookService:
    """Service for managing limit orders and order book."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def place_order(
        self,
        user_id: UUID,
        side: str,
        price: Decimal,
        quantity: Decimal,
    ) -> tuple[LimitOrder, list[Trade]]:
        """Place a new limit order.

        Args:
            user_id: User placing the order.
            side: 'buy' or 'sell'.
            price: Limit price in USD.
            quantity: Amount of OLTIN.

        Returns:
            Tuple of (created order, list of trades if matched).
        """
        # Lock funds first
        await self._lock_funds(user_id, side, price, quantity)

        # Create order
        order = LimitOrder(
            id=uuid4(),
            user_id=user_id,
            side=side,
            price=price,
            quantity=quantity,
            filled_quantity=Decimal("0"),
            status="open",
        )
        self.session.add(order)

        logger.info(
            "limit_order_placed",
            order_id=str(order.id),
            user_id=str(user_id),
            side=side,
            price=str(price),
            quantity=str(quantity),
        )

        # Try to match
        trades = await self._match_order(order)

        await self.session.commit()

        # Broadcast updates (non-blocking, uses NEW session)
        asyncio.create_task(_broadcast_orderbook_with_new_session())
        if trades:
            asyncio.create_task(_broadcast_trades(trades))

        return order, trades

    async def cancel_order(self, order_id: UUID, user_id: UUID) -> LimitOrder:
        """Cancel an open limit order.

        Args:
            order_id: Order to cancel.
            user_id: Must be the order owner.

        Returns:
            Cancelled order.
        """
        result = await self.session.execute(
            select(LimitOrder).where(
                and_(
                    LimitOrder.id == order_id,
                    LimitOrder.user_id == user_id,
                    LimitOrder.status.in_(["open", "partial"]),
                )
            )
        )
        order = result.scalar_one_or_none()

        if not order:
            raise ValueError("Order not found or already filled/cancelled")

        # Unlock remaining funds
        remaining = order.remaining_quantity
        if order.side == "buy":
            asset = "USD"
            amount = remaining * order.price
        else:
            asset = "OLTIN"
            amount = remaining

        await self._unlock_funds(order.user_id, asset, amount)

        order.status = "cancelled"
        order.updated_at = datetime.utcnow()

        await self.session.commit()

        # Broadcast orderbook update (non-blocking, uses NEW session)
        asyncio.create_task(_broadcast_orderbook_with_new_session())

        logger.info(
            "limit_order_cancelled",
            order_id=str(order_id),
        )

        return order

    async def get_orderbook(self, depth: int = 20) -> dict:
        """Get current order book state.

        Args:
            depth: Number of price levels per side.

        Returns:
            Dict with 'bids' and 'asks' lists.
        """
        # Get best bids (highest price first)
        bids_result = await self.session.execute(
            select(
                LimitOrder.price,
                LimitOrder.quantity,
                LimitOrder.filled_quantity,
            )
            .where(
                and_(
                    LimitOrder.side == "buy",
                    LimitOrder.status.in_(["open", "partial"]),
                )
            )
            .order_by(desc(LimitOrder.price), asc(LimitOrder.created_at))
            .limit(depth * 10)  # Get more to aggregate
        )

        # Get best asks (lowest price first)
        asks_result = await self.session.execute(
            select(
                LimitOrder.price,
                LimitOrder.quantity,
                LimitOrder.filled_quantity,
            )
            .where(
                and_(
                    LimitOrder.side == "sell",
                    LimitOrder.status.in_(["open", "partial"]),
                )
            )
            .order_by(asc(LimitOrder.price), asc(LimitOrder.created_at))
            .limit(depth * 10)
        )

        # Aggregate by price level
        bids = self._aggregate_levels(bids_result.fetchall(), depth)
        asks = self._aggregate_levels(asks_result.fetchall(), depth)

        return {
            "bids": bids,
            "asks": asks,
        }

    async def get_user_orders(
        self,
        user_id: UUID,
        status: str | None = None,
        limit: int = 50,
    ) -> list[LimitOrder]:
        """Get user's limit orders."""
        query = select(LimitOrder).where(LimitOrder.user_id == user_id)

        if status:
            query = query.where(LimitOrder.status == status)

        query = query.order_by(desc(LimitOrder.created_at)).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_recent_trades(self, limit: int = 50) -> list[Trade]:
        """Get recent trades."""
        result = await self.session.execute(
            select(Trade).order_by(desc(Trade.created_at)).limit(limit)
        )
        return list(result.scalars().all())

    async def _match_order(self, order: LimitOrder) -> list[Trade]:
        """Match order against order book.

        Uses price-time priority matching.
        """
        trades: list[Trade] = []

        if order.side == "buy":
            # Match against asks (sellers) at or below our price
            opposite_side = "sell"
            price_condition = LimitOrder.price <= order.price
            order_by = [asc(LimitOrder.price), asc(LimitOrder.created_at)]
        else:
            # Match against bids (buyers) at or above our price
            opposite_side = "buy"
            price_condition = LimitOrder.price >= order.price
            order_by = [desc(LimitOrder.price), asc(LimitOrder.created_at)]

        # Get matching orders
        result = await self.session.execute(
            select(LimitOrder)
            .where(
                and_(
                    LimitOrder.side == opposite_side,
                    LimitOrder.status.in_(["open", "partial"]),
                    price_condition,
                )
            )
            .order_by(*order_by)
            .with_for_update()  # Lock for matching
        )

        matching_orders = list(result.scalars().all())

        for match in matching_orders:
            if order.remaining_quantity <= 0:
                break

            # Calculate trade quantity
            trade_qty = min(order.remaining_quantity, match.remaining_quantity)
            trade_price = match.price  # Maker price

            # Create trade
            trade = Trade(
                id=uuid4(),
                buy_order_id=order.id if order.side == "buy" else match.id,
                sell_order_id=match.id if order.side == "buy" else order.id,
                price=trade_price,
                quantity=trade_qty,
                taker_side=order.side,
            )
            self.session.add(trade)
            trades.append(trade)

            # Update filled quantities
            order.filled_quantity += trade_qty
            match.filled_quantity += trade_qty

            # Update statuses
            order.status = "filled" if order.remaining_quantity == 0 else "partial"
            match.status = "filled" if match.remaining_quantity == 0 else "partial"

            if match.status == "filled":
                match.filled_at = datetime.utcnow()

            # Settle balances
            await self._settle_trade(trade, order, match)

            logger.info(
                "trade_executed",
                trade_id=str(trade.id),
                price=str(trade_price),
                quantity=str(trade_qty),
                taker_side=order.side,
            )

        if order.remaining_quantity == 0:
            order.status = "filled"
            order.filled_at = datetime.utcnow()

        return trades

    async def _lock_funds(
        self,
        user_id: UUID,
        side: str,
        price: Decimal,
        quantity: Decimal,
    ) -> None:
        """Lock funds for order."""
        if side == "buy":
            asset = "USD"
            amount = price * quantity
        else:
            asset = "OLTIN"
            amount = quantity

        result = await self.session.execute(
            select(Balance)
            .where(
                and_(
                    Balance.user_id == user_id,
                    Balance.asset == asset,
                )
            )
            .with_for_update()
        )
        balance = result.scalar_one_or_none()

        if not balance or balance.available < amount:
            raise ValueError(f"Insufficient {asset} balance")

        balance.available -= amount
        balance.locked += amount

    async def _unlock_funds(
        self,
        user_id: UUID,
        asset: str,
        amount: Decimal,
    ) -> None:
        """Unlock funds when order cancelled."""
        result = await self.session.execute(
            select(Balance)
            .where(
                and_(
                    Balance.user_id == user_id,
                    Balance.asset == asset,
                )
            )
            .with_for_update()
        )
        balance = result.scalar_one_or_none()

        if balance:
            balance.locked -= amount
            balance.available += amount

    async def _settle_trade(
        self,
        trade: Trade,
        taker_order: LimitOrder,
        maker_order: LimitOrder,
    ) -> None:
        """Settle balances after trade execution."""
        usd_amount = trade.price * trade.quantity
        oltin_amount = trade.quantity

        if taker_order.side == "buy":
            buyer_id = taker_order.user_id
            seller_id = maker_order.user_id
        else:
            buyer_id = maker_order.user_id
            seller_id = taker_order.user_id

        # Buyer: locked USD -> spent, receive OLTIN
        buyer_usd = await self._get_balance(buyer_id, "USD")
        buyer_usd.locked -= usd_amount

        buyer_oltin = await self._get_or_create_balance(buyer_id, "OLTIN")
        buyer_oltin.available += oltin_amount

        # Seller: locked OLTIN -> spent, receive USD
        seller_oltin = await self._get_balance(seller_id, "OLTIN")
        seller_oltin.locked -= oltin_amount

        seller_usd = await self._get_or_create_balance(seller_id, "USD")
        seller_usd.available += usd_amount

    async def _get_balance(self, user_id: UUID, asset: str) -> Balance:
        """Get balance, must exist."""
        result = await self.session.execute(
            select(Balance)
            .where(
                and_(
                    Balance.user_id == user_id,
                    Balance.asset == asset,
                )
            )
            .with_for_update()
        )
        return result.scalar_one()

    async def _get_or_create_balance(self, user_id: UUID, asset: str) -> Balance:
        """Get or create balance."""
        result = await self.session.execute(
            select(Balance)
            .where(
                and_(
                    Balance.user_id == user_id,
                    Balance.asset == asset,
                )
            )
            .with_for_update()
        )
        balance = result.scalar_one_or_none()

        if not balance:
            balance = Balance(
                id=uuid4(),
                user_id=user_id,
                asset=asset,
                available=Decimal("0"),
                locked=Decimal("0"),
            )
            self.session.add(balance)

        return balance

    def _aggregate_levels(
        self,
        rows: list,
        depth: int,
    ) -> list[dict]:
        """Aggregate orders into price levels."""
        levels: dict[Decimal, Decimal] = {}

        for price, quantity, filled_quantity in rows:
            remaining = quantity - filled_quantity
            if remaining > 0:
                if price not in levels:
                    levels[price] = Decimal("0")
                levels[price] += remaining

        # Sort and limit
        sorted_levels = sorted(levels.items(), key=lambda x: x[0], reverse=True)[:depth]

        return [{"price": str(price), "quantity": str(qty)} for price, qty in sorted_levels]
