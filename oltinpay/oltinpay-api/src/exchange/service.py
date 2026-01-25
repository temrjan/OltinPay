"""Exchange service layer."""

from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.balances.models import AccountType, Balance, Currency
from src.balances.service import get_balance
from src.common.exceptions import BadRequestException, InsufficientBalanceException
from src.exchange.gold_price import get_price_with_spread
from src.exchange.models import Order, OrderSide, OrderStatus, OrderType, Trade
from src.exchange.schemas import (
    OrderBookLevel,
    OrderBookResponse,
    PriceResponse,
    SwapQuoteResponse,
    SwapResponse,
)

# Trading fee for swap
SWAP_FEE_PERCENT = Decimal("0.001")  # 0.1%


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

    # Get real gold price
    bid_price, ask_price, mid_price = await get_price_with_spread()

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


async def get_price(_db: AsyncSession) -> PriceResponse:
    """Get current bid/ask/mid price from real gold market."""
    bid, ask, mid = await get_price_with_spread()
    return PriceResponse(bid=bid, ask=ask, mid=mid)


async def get_swap_quote(
    side: str,
    amount: Decimal,
    amount_type: str = "from",
) -> SwapQuoteResponse:
    """Get swap quote without executing.

    Args:
        side: 'buy' (USD->OLTIN) or 'sell' (OLTIN->USD)
        amount: Amount to swap
        amount_type: 'from' = amount you give, 'to' = amount you receive
    """
    bid, ask, mid = await get_price_with_spread()

    if side == "buy":
        # Buying OLTIN with USD
        price = ask  # Pay higher price when buying

        if amount_type == "from":
            # User specifies USD amount
            usd_amount = amount
            gross_oltin = usd_amount / price
            fee = gross_oltin * SWAP_FEE_PERCENT
            oltin_amount = gross_oltin - fee
        else:
            # User specifies OLTIN amount they want
            oltin_amount = amount
            gross_oltin = oltin_amount / (1 - SWAP_FEE_PERCENT)
            fee = gross_oltin - oltin_amount
            usd_amount = gross_oltin * price

        return SwapQuoteResponse(
            side=side,
            from_currency="USD",
            from_amount=usd_amount.quantize(Decimal("0.01")),
            to_currency="OLTIN",
            to_amount=oltin_amount.quantize(Decimal("0.0001")),
            price=price,
            fee=fee.quantize(Decimal("0.0001")),
            fee_percent=SWAP_FEE_PERCENT * 100,
        )
    else:
        # Selling OLTIN for USD
        price = bid  # Get lower price when selling

        if amount_type == "from":
            # User specifies OLTIN amount
            oltin_amount = amount
            gross_usd = oltin_amount * price
            fee = gross_usd * SWAP_FEE_PERCENT
            usd_amount = gross_usd - fee
        else:
            # User specifies USD amount they want
            usd_amount = amount
            gross_usd = usd_amount / (1 - SWAP_FEE_PERCENT)
            fee = gross_usd - usd_amount
            oltin_amount = gross_usd / price

        return SwapQuoteResponse(
            side=side,
            from_currency="OLTIN",
            from_amount=oltin_amount.quantize(Decimal("0.0001")),
            to_currency="USD",
            to_amount=usd_amount.quantize(Decimal("0.01")),
            price=price,
            fee=fee.quantize(Decimal("0.01")),
            fee_percent=SWAP_FEE_PERCENT * 100,
        )


async def execute_swap(
    db: AsyncSession,
    user_id: UUID,
    side: str,
    amount: Decimal,
    amount_type: str = "from",
) -> SwapResponse:
    """Execute instant swap.

    Swaps happen on the EXCHANGE account.
    """
    # Get quote
    quote = await get_swap_quote(side, amount, amount_type)

    if side == "buy":
        # Check USD balance on exchange account
        usd_balance = await get_balance(db, user_id, AccountType.EXCHANGE, Currency.USD)
        if not usd_balance or usd_balance.amount < quote.from_amount:
            raise InsufficientBalanceException(
                f"Insufficient USD. Need {quote.from_amount}, have {usd_balance.amount if usd_balance else 0}"
            )

        # Get or create OLTIN balance
        oltin_balance = await get_balance(
            db, user_id, AccountType.EXCHANGE, Currency.OLTIN
        )
        if not oltin_balance:
            oltin_balance = Balance(
                user_id=user_id,
                account_type=AccountType.EXCHANGE,
                currency=Currency.OLTIN,
                amount=Decimal("0"),
            )
            db.add(oltin_balance)

        # Execute swap
        usd_balance.amount -= quote.from_amount
        oltin_balance.amount += quote.to_amount

    else:
        # Check OLTIN balance on exchange account
        oltin_balance = await get_balance(
            db, user_id, AccountType.EXCHANGE, Currency.OLTIN
        )
        if not oltin_balance or oltin_balance.amount < quote.from_amount:
            raise InsufficientBalanceException(
                f"Insufficient OLTIN. Need {quote.from_amount}, have {oltin_balance.amount if oltin_balance else 0}"
            )

        # Get USD balance
        usd_balance = await get_balance(db, user_id, AccountType.EXCHANGE, Currency.USD)
        if not usd_balance:
            usd_balance = Balance(
                user_id=user_id,
                account_type=AccountType.EXCHANGE,
                currency=Currency.USD,
                amount=Decimal("0"),
            )
            db.add(usd_balance)

        # Execute swap
        oltin_balance.amount -= quote.from_amount
        usd_balance.amount += quote.to_amount

    await db.flush()

    return SwapResponse(
        side=quote.side,
        from_currency=quote.from_currency,
        from_amount=quote.from_amount,
        to_currency=quote.to_currency,
        to_amount=quote.to_amount,
        price=quote.price,
        fee=quote.fee,
    )


# ===== LEGACY ORDER FUNCTIONS (kept for compatibility) =====


async def create_order(
    db: AsyncSession,
    user_id: UUID,
    side: str,
    order_type: str,
    price: Decimal | None,
    quantity: Decimal,
) -> Order:
    """Create a new order (legacy - prefer swap for instant execution)."""
    bid, ask, mid = await get_price_with_spread()

    # For market orders, use current price
    if order_type == OrderType.MARKET:
        price = ask if side == OrderSide.BUY else bid

    if price is None:
        raise BadRequestException("Price required for limit orders")

    # Check balance
    if side == OrderSide.BUY:
        required_usd = quantity * price
        usd_balance = await get_balance(db, user_id, AccountType.EXCHANGE, Currency.USD)
        if not usd_balance or usd_balance.amount < required_usd:
            raise InsufficientBalanceException("Insufficient USD in exchange account")
    else:
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
