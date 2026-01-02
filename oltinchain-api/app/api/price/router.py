"""Price API endpoints.

Provides current price, cycle state, and price history for OLTIN.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Query

from app.api.price.schemas import (
    CycleStateResponse,
    PriceHistoryItem,
    PriceHistoryResponse,
    PriceResponse,
)
from app.application.services.price_oracle import get_price_oracle

router = APIRouter(prefix="/price", tags=["price"])


@router.get("/current", response_model=PriceResponse)
async def get_current_price() -> PriceResponse:
    """Get current OLTIN price with bid/ask spread.

    Returns:
        Current price, bid, ask, and spread information.
    """
    oracle = get_price_oracle()
    now = datetime.now(timezone.utc)

    spread = Decimal("1.0")  # 1% spread
    mid, bid, ask = oracle.get_price_with_spread(now, spread)

    return PriceResponse(
        price=mid,
        bid=bid,
        ask=ask,
        spread_percent=spread,
        timestamp=now,
    )


@router.get("/gold", response_model=PriceResponse)
async def get_gold_price() -> PriceResponse:
    """Get current gold/OLTIN price (alias for /current)."""
    return await get_current_price()


@router.get("/cycle", response_model=CycleStateResponse)
async def get_cycle_state() -> CycleStateResponse:
    """Get current market cycle state.

    Returns information about:
    - Current cycle number and phase
    - Price targets (peak, bottom, end)
    - Progress through the cycle

    Returns:
        Current cycle state with all price targets.
    """
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
    interval: str = Query(
        default="1h",
        regex="^(1m|5m|15m|1h|4h|1d)$",
        description="Candle interval",
    ),
    limit: int = Query(default=100, ge=1, le=1000, description="Number of candles"),
) -> PriceHistoryResponse:
    """Get historical OHLCV price data.

    Generates simulated historical data based on cycle model.
    For production, this should query stored price data.

    Args:
        interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d).
        limit: Number of candles to return.

    Returns:
        OHLCV data for the requested period.
    """
    oracle = get_price_oracle()
    now = datetime.now(timezone.utc)

    # Calculate interval in seconds
    interval_seconds = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
    }[interval]

    candles: list[PriceHistoryItem] = []

    for i in range(limit - 1, -1, -1):
        # Calculate timestamp for this candle
        candle_time = datetime.fromtimestamp(
            now.timestamp() - (i * interval_seconds),
            tz=timezone.utc,
        )

        # Generate price for this time
        state = oracle.get_current_cycle_state(candle_time)
        base_price = state.current_price

        # Simulate OHLC from base price
        volatility = Decimal("0.005")  # 0.5% intracandle volatility

        open_price = base_price * (
            1 + Decimal(str((hash(str(candle_time) + "o") % 100 - 50) / 10000))
        )
        close_price = base_price * (
            1 + Decimal(str((hash(str(candle_time) + "c") % 100 - 50) / 10000))
        )

        high_price = max(open_price, close_price) * (1 + volatility)
        low_price = min(open_price, close_price) * (1 - volatility)

        candles.append(
            PriceHistoryItem(
                timestamp=candle_time,
                open=open_price.quantize(Decimal("0.01")),
                high=high_price.quantize(Decimal("0.01")),
                low=low_price.quantize(Decimal("0.01")),
                close=close_price.quantize(Decimal("0.01")),
                volume=Decimal(str(1000 + (hash(str(candle_time)) % 5000))),
            )
        )

    return PriceHistoryResponse(
        interval=interval,
        data=candles,
    )


@router.get("/xau-usd")
async def get_xau_usd_price():
    """Get XAU/USD price in format expected by frontend."""
    oracle = get_price_oracle()
    now = datetime.now(timezone.utc)

    spread = Decimal("1.0")
    mid, bid, ask = oracle.get_price_with_spread(now, spread)

    return {
        "price_usd": float(mid),
        "price_change_pct": 0.0,
        "data_index": 0,
        "data_date": now.strftime("%Y-%m-%d"),
        "timestamp": now.isoformat(),
    }


@router.get("/xau-usd/history")
async def get_xau_usd_history(limit: int = 500):
    """Get XAU/USD price history."""
    oracle = get_price_oracle()
    now = datetime.now(timezone.utc)

    history = []
    for i in range(limit):
        t = now - timedelta(minutes=i * 5)
        spread = Decimal("1.0")
        mid, _, _ = oracle.get_price_with_spread(t, spread)
        history.append(
            {
                "timestamp": t.isoformat(),
                "price_usd": float(mid),
                "change_pct": 0.0,
            }
        )

    return {"history": list(reversed(history))}
