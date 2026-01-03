"""Price API endpoints.

Provides current price from orderbook and cycle state.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.price.schemas import (
    CycleStateResponse,
    PriceHistoryItem,
    PriceHistoryResponse,
    PriceResponse,
)
from app.application.services.price_oracle import get_price_oracle
from app.infrastructure.models import LimitOrder, Trade

router = APIRouter(prefix="/price", tags=["price"])


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
        mid = (best_bid + best_ask) / 2
        return mid.quantize(Decimal("0.01")), best_bid, best_ask
    elif best_bid:
        return best_bid, best_bid, best_bid
    elif best_ask:
        return best_ask, best_ask, best_ask
    else:
        oracle = get_price_oracle()
        now = datetime.now(timezone.utc)
        return oracle.get_price_with_spread(now, Decimal("1.0"))


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


@router.get("/cycle", response_model=CycleStateResponse)
async def get_cycle_state() -> CycleStateResponse:
    """Get current market cycle state."""
    oracle = get_price_oracle()
    state = oracle.get_current_cycle_state()
    return CycleStateResponse(
        cycle_number=state.cycle_number,
        phase=state.phase.value,
        day_in_cycle=state.day_in_cycle,
        cycle_progress=state.cycle_progress,
        start_price=state.start_price,
        current_price=state.current_price,
        peak_price=state.peak_price,
        bottom_price=state.bottom_price,
        end_price=state.target_end_price,
        total_growth_percent=state.total_growth,
    )


@router.get("/history", response_model=PriceHistoryResponse)
async def get_price_history(
    interval: str = Query(default="1h", pattern="^(1m|5m|15m|1h|4h|1d)$"),
    limit: int = Query(default=100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
) -> PriceHistoryResponse:
    """Get historical OHLCV price data from real trades."""
    now = datetime.utcnow()  # timezone-naive for DB
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
    last_price = Decimal("500")

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
    now = datetime.utcnow()  # timezone-naive for DB
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
            price = 500.0

        history.append(
            {
                "timestamp": t.replace(tzinfo=timezone.utc).isoformat(),
                "price_usd": price,
                "change_pct": 0.0,
            }
        )

    return {"history": history}
