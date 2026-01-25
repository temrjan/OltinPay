"""Exchange service layer."""

from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.balances.models import AccountType, Currency
from src.balances.service import get_balance
from src.common.exceptions import BadRequestException, InsufficientBalanceException
from src.exchange.models import Order, OrderSide, OrderStatus, OrderType, Trade
from src.exchange.schemas import (
    OrderBookLevel,
    OrderBookResponse,
    PriceResponse,
)

# Trading fee
TRADING_FEE_RATE = Decimal("0.001")  # 0.1%

# Demo fixed price (until real orderbook)
FIXED_PRICE = Decimal("100")


async def get_orderbook(db: AsyncSession) -> OrderBookResponse:
    """Get current orderbook."""
    # Get open buy orders (bids)
    bids_result = await db.execute(
        select(Order)
        .where(
            Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
            Order.side == OrderSide.BUY,
            Order.order_type == OrderType.LIMIT,
        )
        .order_by(Order.price.desc())
        .limit(10)
    )
    bids = bids_result.scalars().all()

    # Get open sell orders (asks)
    asks_result = await db.execute(
        select(Order)
        .where(
            Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
            Order.side == OrderSide.SELL,
            Order.order_type == OrderType.LIMIT,
        )
        .order_by(Order.price.asc())
        .limit(10)
    )
    asks = asks_result.scalars().all()

    # Aggregate by price level
    bid_levels = _aggregate_orders(bids)
    ask_levels = _aggregate_orders(asks)

    # Calculate mid price
    if bid_levels and ask_levels:
        mid_price = (bid_levels[0].price + ask_levels[0].price) / 2
    elif bid_levels:
        mid_price = bid_levels[0].price
    elif ask_levels:
        mid_price = ask_levels[0].price
    else:
        mid_price = FIXED_PRICE

    return OrderBookResponse(
        bids=bid_levels,
        asks=ask_levels,
        mid_price=mid_price,
    )


def _aggregate_orders(orders: Sequence[Order]) -> list[OrderBookLevel]:
    """Aggregate orders by price level."""
    levels: dict[Decimal, Decimal] = {}
    for order in orders:
        if order.price:
            remaining = order.quantity - order.filled_quantity
            levels[order.price] = levels.get(order.price, Decimal("0")) + remaining

    return [OrderBookLevel(price=price, quantity=qty) for price, qty in levels.items()]


async def get_price(db: AsyncSession) -> PriceResponse:
    """Get current bid/ask/mid price."""
    orderbook = await get_orderbook(db)

    bid = orderbook.bids[0].price if orderbook.bids else FIXED_PRICE - 1
    ask = orderbook.asks[0].price if orderbook.asks else FIXED_PRICE + 1
    mid = orderbook.mid_price

    return PriceResponse(bid=bid, ask=ask, mid=mid)


async def create_order(
    db: AsyncSession,
    user_id: UUID,
    side: str,
    order_type: str,
    price: Decimal | None,
    quantity: Decimal,
) -> Order:
    """Create a new order.

    For buy orders: locks USD in exchange account
    For sell orders: locks OLTIN in exchange account
    """
    # Validate limit order has price
    if order_type == OrderType.LIMIT and price is None:
        raise BadRequestException("Limit orders require a price")

    # For market orders, use current price
    if order_type == OrderType.MARKET:
        price_info = await get_price(db)
        price = price_info.ask if side == OrderSide.BUY else price_info.bid

    # At this point price is guaranteed to be set
    assert price is not None

    # Check and lock balance
    if side == OrderSide.BUY:
        # Need USD to buy OLTIN
        required_usd = quantity * price
        usd_balance = await get_balance(db, user_id, AccountType.EXCHANGE, Currency.USD)
        if not usd_balance or usd_balance.amount < required_usd:
            raise InsufficientBalanceException("Insufficient USD in exchange account")
        # Lock USD (will be released/used on fill)
    else:
        # Need OLTIN to sell
        oltin_balance = await get_balance(
            db, user_id, AccountType.EXCHANGE, Currency.OLTIN
        )
        if not oltin_balance or oltin_balance.amount < quantity:
            raise InsufficientBalanceException("Insufficient OLTIN in exchange account")

    # Create order
    order = Order(
        user_id=user_id,
        side=side,
        order_type=order_type,
        price=price,
        quantity=quantity,
        status=OrderStatus.OPEN,
    )
    db.add(order)
    await db.flush()
    await db.refresh(order)

    # TODO: Match with existing orders

    return order


async def cancel_order(
    db: AsyncSession,
    order_id: UUID,
    user_id: UUID,
) -> Order:
    """Cancel an open order."""
    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.user_id == user_id,
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise BadRequestException("Order not found")

    if order.status not in [OrderStatus.OPEN, OrderStatus.PARTIAL]:
        raise BadRequestException("Order cannot be cancelled")

    order.status = OrderStatus.CANCELLED
    await db.flush()
    await db.refresh(order)

    return order


async def get_user_orders(
    db: AsyncSession,
    user_id: UUID,
    status: str | None = None,
    limit: int = 50,
) -> list[Order]:
    """Get user's orders."""
    query = select(Order).where(Order.user_id == user_id)

    if status:
        query = query.where(Order.status == status)

    query = query.order_by(Order.created_at.desc()).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_recent_trades(
    db: AsyncSession,
    limit: int = 50,
) -> list[Trade]:
    """Get recent trades."""
    result = await db.execute(
        select(Trade).order_by(Trade.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
