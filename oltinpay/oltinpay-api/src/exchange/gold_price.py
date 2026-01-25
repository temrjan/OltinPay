"""Gold price service - fetches real gold price from API."""

import logging
from decimal import Decimal

import httpx

from src.redis_client import get_redis

logger = logging.getLogger(__name__)

# Cache settings
GOLD_PRICE_KEY = "gold:price:usd"
GOLD_PRICE_TTL = 300  # 5 minutes

# Spread for buy/sell (0.5% each side = 1% total spread)
SPREAD_PERCENT = Decimal("0.005")

# Fallback price if API fails
FALLBACK_PRICE = Decimal("2650.00")

# API URLs (try in order)
PRICE_APIS = [
    "https://api.metals.live/v1/spot/gold",
    "https://api.gold-api.com/price/XAU",
]


async def fetch_gold_price_from_api() -> Decimal | None:
    """Fetch gold price from external API."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Try metals.live first
        try:
            response = await client.get("https://api.metals.live/v1/spot/gold")
            if response.status_code == 200:
                data = response.json()
                # metals.live returns list: [{"gold": 2650.50, ...}]
                if isinstance(data, list) and len(data) > 0:
                    price = data[0].get("gold")
                    if price:
                        logger.info(f"Got gold price from metals.live: ${price}")
                        return Decimal(str(price))
        except Exception as e:
            logger.warning(f"metals.live API failed: {e}")

        # Fallback: try goldprice.org API
        try:
            response = await client.get(
                "https://data-asg.goldprice.org/dbXRates/USD",
                headers={"Accept": "application/json"},
            )
            if response.status_code == 200:
                data = response.json()
                # Returns: {"items": [{"xauPrice": 2650.50, ...}]}
                items = data.get("items", [])
                if items:
                    price = items[0].get("xauPrice")
                    if price:
                        logger.info(f"Got gold price from goldprice.org: ${price}")
                        return Decimal(str(price))
        except Exception as e:
            logger.warning(f"goldprice.org API failed: {e}")

    return None


async def get_gold_price() -> Decimal:
    """Get current gold price (cached).

    Returns price per troy ounce in USD.
    """
    redis = await get_redis()

    # Try to get from cache
    cached_price = await redis.get(GOLD_PRICE_KEY)
    if cached_price:
        return Decimal(cached_price)

    # Fetch from API
    price = await fetch_gold_price_from_api()

    if price:
        # Cache the price
        await redis.setex(GOLD_PRICE_KEY, GOLD_PRICE_TTL, str(price))
        return price

    # Fallback: try to get last known price or use default
    last_price = await redis.get(f"{GOLD_PRICE_KEY}:last")
    if last_price:
        logger.warning(f"Using last known gold price: ${last_price}")
        return Decimal(last_price)

    logger.warning(f"Using fallback gold price: ${FALLBACK_PRICE}")
    return FALLBACK_PRICE


async def get_price_with_spread() -> tuple[Decimal, Decimal, Decimal]:
    """Get bid, ask, and mid prices.

    Returns (bid, ask, mid) where:
    - bid = price user gets when selling OLTIN (lower)
    - ask = price user pays when buying OLTIN (higher)
    - mid = market mid price
    """
    mid = await get_gold_price()

    # 1 OLTIN = 1 gram of gold
    # 1 troy ounce = 31.1035 grams
    GRAMS_PER_OUNCE = Decimal("31.1035")

    # Convert to price per gram
    price_per_gram = mid / GRAMS_PER_OUNCE

    # Apply spread
    bid = price_per_gram * (1 - SPREAD_PERCENT)
    ask = price_per_gram * (1 + SPREAD_PERCENT)

    return (
        bid.quantize(Decimal("0.01")),
        ask.quantize(Decimal("0.01")),
        price_per_gram.quantize(Decimal("0.01")),
    )


async def refresh_gold_price() -> Decimal | None:
    """Force refresh gold price from API."""
    price = await fetch_gold_price_from_api()
    if price:
        redis = await get_redis()
        await redis.setex(GOLD_PRICE_KEY, GOLD_PRICE_TTL, str(price))
        await redis.set(f"{GOLD_PRICE_KEY}:last", str(price))
        return price
    return None
