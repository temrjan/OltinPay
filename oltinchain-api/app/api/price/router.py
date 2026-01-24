"""Price API endpoints.

Provides current price from orderbook.
"""

from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.price.schemas import (
    BuyQuoteRequest,
    PriceHistoryItem,
    PriceHistoryResponse,
    PriceResponse,
    QuoteResponse,
    SellQuoteRequest,
)
from app.config import settings
from app.infrastructure.models import LimitOrder, Trade

router = APIRouter(prefix="/price", tags=["price"])

# Default price if orderbook is empty
DEFAULT_PRICE = Decimal("500.00")


async def get_orderbook_price(session: AsyncSession) -> tuple[Decimal, Decimal, Decimal]:
    """Get mid, bid, ask from orderbook."""
    bid_result = await session.execute(
        select(LimitOrder.price)
        .where(and_(LimitOrder.side == "buy", LimitOrder.status.in_(["open", "partial"])))
        .order_by(desc(LimitOrder.price))
        .limit(1)
    )
    best_bid = bid_result.scalar_one_or_none()

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
        return DEFAULT_PRICE, DEFAULT_PRICE, DEFAULT_PRICE


@router.get("/current", response_model=PriceResponse)
async def get_current_price(session: AsyncSession = Depends(get_session)) -> PriceResponse:
    """Get current OLTIN price from orderbook."""
    now = datetime.now(timezone.utc)
    mid, bid, ask = await get_orderbook_price(session)
    spread = Decimal("0")
    if bid > 0:
        spread = ((ask - bid) / bid * 100).quantize(Decimal("0.01"))
    return PriceResponse(price=mid, bid=bid, ask=ask, spread_percent=spread, timestamp=now)


@router.get("/gold", response_model=PriceResponse)
async def get_gold_price(session: AsyncSession = Depends(get_session)) -> PriceResponse:
    """Alias for /current."""
    return await get_current_price(session)


@router.get("/history", response_model=PriceHistoryResponse)
async def get_price_history(
    interval: str = Query(default="1h", pattern="^(1m|5m|15m|1h|4h|1d)$"),
    limit: int = Query(default=100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
) -> PriceHistoryResponse:
    """Get historical OHLCV price data from real trades."""
    now = datetime.utcnow()
    interval_seconds = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}[
        interval
    ]
    start_time = now - timedelta(seconds=interval_seconds * limit)

    result = await session.execute(
        select(Trade.price, Trade.quantity, Trade.created_at)
        .where(Trade.created_at >= start_time)
        .order_by(Trade.created_at)
    )
    trades = result.fetchall()

    candles: list[PriceHistoryItem] = []
    last_price = DEFAULT_PRICE

    for i in range(limit):
        candle_start = now - timedelta(seconds=interval_seconds * (limit - i))
        candle_end = candle_start + timedelta(seconds=interval_seconds)

        candle_trades = [t for t in trades if candle_start <= t.created_at < candle_end]

        if candle_trades:
            prices = [t.price for t in candle_trades]
            volumes = [t.quantity for t in candle_trades]
            last_price = prices[-1]
            candles.append(
                PriceHistoryItem(
                    timestamp=candle_start.replace(tzinfo=timezone.utc),
                    open=prices[0].quantize(Decimal("0.01")),
                    high=max(prices).quantize(Decimal("0.01")),
                    low=min(prices).quantize(Decimal("0.01")),
                    close=prices[-1].quantize(Decimal("0.01")),
                    volume=sum(volumes).quantize(Decimal("0.0001")),
                )
            )
        else:
            candles.append(
                PriceHistoryItem(
                    timestamp=candle_start.replace(tzinfo=timezone.utc),
                    open=last_price.quantize(Decimal("0.01")),
                    high=last_price.quantize(Decimal("0.01")),
                    low=last_price.quantize(Decimal("0.01")),
                    close=last_price.quantize(Decimal("0.01")),
                    volume=Decimal("0"),
                )
            )

    return PriceHistoryResponse(interval=interval, data=candles)


@router.get("/xau-usd")
async def get_xau_usd_price(session: AsyncSession = Depends(get_session)):
    """Get XAU/USD price from orderbook."""
    now = datetime.now(timezone.utc)
    mid, bid, ask = await get_orderbook_price(session)
    return {"price_usd": float(mid), "price_change_pct": 0.0, "timestamp": now.isoformat()}


@router.get("/xau-usd/history")
async def get_xau_usd_history(
    limit: int = 500,
    session: AsyncSession = Depends(get_session),
):
    """Get XAU/USD price history from trades."""
    now = datetime.utcnow()
    start_time = now - timedelta(minutes=limit * 5)

    result = await session.execute(
        select(Trade.price, Trade.created_at)
        .where(Trade.created_at >= start_time)
        .order_by(Trade.created_at)
    )
    trades = result.fetchall()

    history: list[dict[str, float | str]] = []
    for i in range(limit):
        t = now - timedelta(minutes=(limit - i - 1) * 5)
        t_end = t + timedelta(minutes=5)

        matching = [tr for tr in trades if t <= tr.created_at < t_end]
        if matching:
            price = float(matching[-1].price)
        elif history:
            price = float(history[-1]["price_usd"])
        else:
            price = float(DEFAULT_PRICE)

        history.append(
            {
                "timestamp": t.replace(tzinfo=timezone.utc).isoformat(),
                "price_usd": price,
                "change_pct": 0.0,
            }
        )

    return {"history": history}


def calculate_fee(amount_usd: Decimal) -> Decimal:
    """Calculate transaction fee."""
    fee_percent = Decimal(str(settings.fee_percent))
    min_fee = Decimal("1.0")
    if amount_usd <= 0:
        return Decimal("0")
    percent_fee = (amount_usd * fee_percent).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return max(percent_fee, min_fee)


@router.post("/quote/buy", response_model=QuoteResponse)
async def get_buy_quote(
    data: BuyQuoteRequest,
    session: AsyncSession = Depends(get_session),
) -> QuoteResponse:
    """Get quote for buying OLTIN with USD.

    Uses orderbook ask price for accurate quotes.
    """
    mid, bid, ask = await get_orderbook_price(session)

    fee = calculate_fee(data.amount_usd)
    net_usd = data.amount_usd - fee

    oltin = (net_usd / ask).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    return QuoteResponse(
        amount_usd=data.amount_usd,
        amount_oltin=oltin,
        fee_usd=fee,
        price_per_gram=ask,
    )


@router.post("/quote/sell", response_model=QuoteResponse)
async def get_sell_quote(
    data: SellQuoteRequest,
    session: AsyncSession = Depends(get_session),
) -> QuoteResponse:
    """Get quote for selling OLTIN for USD.

    Uses orderbook bid price for accurate quotes.
    """
    mid, bid, ask = await get_orderbook_price(session)

    gross_usd = (data.amount_oltin * bid).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    fee = calculate_fee(gross_usd)
    net_usd = gross_usd - fee

    return QuoteResponse(
        amount_usd=net_usd,
        amount_oltin=data.amount_oltin,
        fee_usd=fee,
        price_per_gram=bid,
    )
