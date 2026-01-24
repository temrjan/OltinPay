"""Orderbook price service.

Gets real prices from orderbook (limit orders from bots).
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import and_, asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.models import LimitOrder

# Default price if orderbook is empty
DEFAULT_PRICE = Decimal("500.00")


@dataclass
class Quote:
    """Quote for buy/sell operation."""

    amount_usd: Decimal
    amount_oltin: Decimal
    fee_usd: Decimal
    price_per_gram: Decimal
    net_amount_usd: Decimal


async def get_orderbook_prices(session: AsyncSession) -> tuple[Decimal, Decimal, Decimal]:
    """Get mid, bid, ask prices from orderbook.

    Returns:
        Tuple of (mid_price, bid_price, ask_price)
    """
    # Get best bid (highest buy order)
    bid_result = await session.execute(
        select(LimitOrder.price)
        .where(and_(LimitOrder.side == "buy", LimitOrder.status.in_(["open", "partial"])))
        .order_by(desc(LimitOrder.price))
        .limit(1)
    )
    best_bid = bid_result.scalar_one_or_none()

    # Get best ask (lowest sell order)
    ask_result = await session.execute(
        select(LimitOrder.price)
        .where(and_(LimitOrder.side == "sell", LimitOrder.status.in_(["open", "partial"])))
        .order_by(asc(LimitOrder.price))
        .limit(1)
    )
    best_ask = ask_result.scalar_one_or_none()

    if best_bid and best_ask:
        mid = ((best_bid + best_ask) / 2).quantize(Decimal("0.01"))
        return mid, best_bid, best_ask
    elif best_bid:
        return best_bid, best_bid, best_bid
    elif best_ask:
        return best_ask, best_ask, best_ask
    else:
        # Fallback to default price if orderbook is empty
        return DEFAULT_PRICE, DEFAULT_PRICE, DEFAULT_PRICE


def calculate_fee(amount_usd: Decimal) -> Decimal:
    """Calculate transaction fee.

    Fee = max(amount * fee_percent, min_fee)
    """
    fee_percent = Decimal(str(settings.fee_percent))
    min_fee = Decimal("1.0")

    if amount_usd <= 0:
        return Decimal("0")

    percent_fee = (amount_usd * fee_percent).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return max(percent_fee, min_fee)


async def get_buy_quote(session: AsyncSession, amount_usd: Decimal) -> Quote:
    """Get quote for buying OLTIN with USD.

    Uses ask price from orderbook.
    """
    mid, bid, ask = await get_orderbook_prices(session)

    fee = calculate_fee(amount_usd)
    net_usd = amount_usd - fee

    # Buy at ask price
    oltin = (net_usd / ask).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    return Quote(
        amount_usd=amount_usd,
        amount_oltin=oltin,
        fee_usd=fee,
        price_per_gram=ask,
        net_amount_usd=net_usd,
    )


async def get_sell_quote(session: AsyncSession, amount_oltin: Decimal) -> Quote:
    """Get quote for selling OLTIN for USD.

    Uses bid price from orderbook.
    """
    mid, bid, ask = await get_orderbook_prices(session)

    # Sell at bid price
    gross_usd = (amount_oltin * bid).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    fee = calculate_fee(gross_usd)
    net_usd = gross_usd - fee

    return Quote(
        amount_usd=gross_usd,
        amount_oltin=amount_oltin,
        fee_usd=fee,
        price_per_gram=bid,
        net_amount_usd=net_usd,
    )
