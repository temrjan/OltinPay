"""Price API router."""

import json
from typing import Optional

from fastapi import APIRouter, Depends
import redis.asyncio as aioredis

from app.api.price.schemas import (
    BuyQuoteRequest,
    GoldPriceResponse,
    QuoteResponse,
    SellQuoteRequest,
    XauUsdPriceResponse,
    XauUsdHistoryResponse,
)
from app.application.services.price_service import PriceService
from app.config import settings

router = APIRouter(prefix="/price", tags=["price"])


def get_price_service() -> PriceService:
    """Get price service dependency."""
    return PriceService()


async def get_redis():
    """Get Redis connection."""
    redis = aioredis.from_url(settings.redis_url)
    try:
        yield redis
    finally:
        await redis.close()


@router.get("/gold", response_model=GoldPriceResponse)
async def get_gold_price():
    """Get current gold prices (base, buy, sell) in UZS per gram."""
    service = get_price_service()
    prices = service.get_prices()
    return GoldPriceResponse(
        base_price=prices["base_price"],
        buy_price=prices["buy_price"],
        sell_price=prices["sell_price"],
        spread_percent=prices["spread_percent"],
    )


@router.get("/xau-usd", response_model=XauUsdPriceResponse)
async def get_xau_usd_price(redis: aioredis.Redis = Depends(get_redis)):
    """Get current XAU/USD price from replay strategy."""
    try:
        data = await redis.get("current_xau_usd")
        if data:
            parsed = json.loads(data)
            return XauUsdPriceResponse(
                price_usd=parsed.get("price_usd", 0),
                price_change_pct=parsed.get("price_change_pct", 0),
                data_index=parsed.get("data_index", 0),
                data_date=parsed.get("data_date", ""),
                timestamp=parsed.get("timestamp", ""),
            )
    except Exception:
        pass
    
    return XauUsdPriceResponse(
        price_usd=0,
        price_change_pct=0,
        data_index=0,
        data_date="",
        timestamp="",
    )


@router.get("/xau-usd/history", response_model=XauUsdHistoryResponse)
async def get_xau_usd_history(
    limit: int = 100,
    redis: aioredis.Redis = Depends(get_redis),
):
    """Get XAU/USD price history for charting."""
    try:
        data = await redis.lrange("xau_usd_history", 0, limit - 1)
        history = []
        for item in data:
            parsed = json.loads(item)
            history.append({
                "timestamp": parsed.get("t", ""),
                "price_usd": parsed.get("p", 0),
                "change_pct": parsed.get("c", 0),
            })
        return XauUsdHistoryResponse(prices=history, count=len(history))
    except Exception:
        pass
    
    return XauUsdHistoryResponse(prices=[], count=0)


@router.post("/quote/buy", response_model=QuoteResponse)
async def get_buy_quote(data: BuyQuoteRequest):
    """Get quote for buying OLTIN with UZS.
    
    Uses ASK price (higher) - user pays more when buying.
    """
    service = get_price_service()
    quote = service.get_buy_quote(data.amount_uzs)
    return QuoteResponse(
        amount_uzs=quote.amount_uzs,
        amount_oltin=quote.amount_oltin,
        fee_uzs=quote.fee_uzs,
        gold_price_per_gram=quote.gold_price_per_gram,
        base_price_per_gram=quote.base_price_per_gram,
        net_amount_uzs=quote.net_amount_uzs,
    )


@router.post("/quote/sell", response_model=QuoteResponse)
async def get_sell_quote(data: SellQuoteRequest):
    """Get quote for selling OLTIN for UZS.
    
    Uses BID price (lower) - user gets less when selling.
    """
    service = get_price_service()
    quote = service.get_sell_quote(data.amount_oltin)
    return QuoteResponse(
        amount_uzs=quote.amount_uzs,
        amount_oltin=quote.amount_oltin,
        fee_uzs=quote.fee_uzs,
        gold_price_per_gram=quote.gold_price_per_gram,
        base_price_per_gram=quote.base_price_per_gram,
        net_amount_uzs=quote.net_amount_uzs,
    )
