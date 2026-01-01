"""
Bot Trading Dashboard API endpoints.
Provides orderbook, trades, cycles, and auction status with real DB data.
"""

import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import List

import asyncpg
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/bots", tags=["bots"])

# Fix DATABASE_URL format (remove +asyncpg suffix if present)
_db_url = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:SOJ0Z74xsCIbd4mjD3de4z6LAgjWsGvs@postgres:5432/oltinchain",
)
DATABASE_URL = _db_url.replace("postgresql+asyncpg://", "postgresql://")


class OrderBookEntry(BaseModel):
    price: str
    amount: str
    total: str
    bot_count: int


class OrderBook(BaseModel):
    asks: List[OrderBookEntry]
    bids: List[OrderBookEntry]
    spread: str
    spread_percent: str
    timestamp: datetime


async def get_db_stats():
    """Get real stats from database."""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Get volume stats (last 24 hours)
        stats = await conn.fetch("""
            SELECT
                type,
                COUNT(*) as count,
                COALESCE(SUM(amount_uzs), 0) as volume,
                COALESCE(SUM(amount_oltin), 0) as oltin,
                COALESCE(AVG(price_per_gram), 61) as avg_price
            FROM orders
            WHERE created_at > NOW() - INTERVAL '24 hours'
            GROUP BY type
        """)

        # Get total stats (last hour)
        totals = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_orders,
                COALESCE(AVG(price_per_gram), 61) as market_price
            FROM orders
            WHERE created_at > NOW() - INTERVAL '1 hour'
        """)

        # Get recent trades
        trades = await conn.fetch("""
            SELECT
                id, type, amount_uzs, amount_oltin, price_per_gram, created_at, user_id
            FROM orders
            ORDER BY created_at DESC
            LIMIT 50
        """)

        await conn.close()

        buy_volume = Decimal("0")
        sell_volume = Decimal("0")
        buy_count = 0
        sell_count = 0

        for row in stats:
            if row["type"] == "buy":
                buy_volume = Decimal(str(row["volume"]))
                buy_count = row["count"]
            elif row["type"] == "sell":
                sell_volume = Decimal(str(row["volume"]))
                sell_count = row["count"]

        total_volume = buy_volume + sell_volume
        imbalance = Decimal("0")
        if total_volume > 0:
            imbalance = ((buy_volume - sell_volume) / total_volume) * 100

        market_price = (
            Decimal(str(totals["market_price"]))
            if totals and totals["market_price"]
            else Decimal("61")
        )
        target_price = Decimal("61")
        deviation = (
            ((market_price - target_price) / target_price) * 100
            if target_price > 0
            else Decimal("0")
        )

        return {
            "buy_volume": float(buy_volume),
            "sell_volume": float(sell_volume),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "total_trades": (totals["total_orders"] if totals else 0) or 0,
            "imbalance": float(imbalance),
            "market_price": float(market_price),
            "target_price": float(target_price),
            "deviation": float(deviation),
            "trades": trades,
        }
    except Exception as e:
        print(f"DB Error: {e}")
        return {
            "buy_volume": 0,
            "sell_volume": 0,
            "buy_count": 0,
            "sell_count": 0,
            "total_trades": 0,
            "imbalance": 0,
            "market_price": 61,
            "target_price": 61,
            "deviation": 0,
            "trades": [],
        }


@router.get("/status")
async def get_dashboard_status():
    """Get complete dashboard status with real DB data."""
    stats = await get_db_stats()

    leader = "DRAW"
    if stats["imbalance"] > 5:
        leader = "BUYERS"
    elif stats["imbalance"] < -5:
        leader = "SELLERS"

    return {
        "match": {
            "match_id": "match_live",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "cycles_completed": stats["total_trades"] // 10,
            "current_leader": leader,
            "deviation": f"{stats['deviation']:.2f}",
            "target_price": str(stats["target_price"]),
            "market_price": str(stats["market_price"]),
        },
        "current_cycle": {
            "cycle_id": 1,
            "phase": "ACCUMULATE",
            "orders_count": stats["total_trades"],
            "buy_volume": f"{stats['buy_volume']:.2f}",
            "sell_volume": f"{stats['sell_volume']:.2f}",
            "imbalance": f"{stats['imbalance']:.1f}",
            "deviation": f"{stats['deviation']:.2f}",
        },
        "stats": {
            "total_bots": 50,
            "traders": 42,
            "whales": 2,
            "market_makers": 6,
            "active_bots": 50,
            "total_volume_usd": f"{stats['buy_volume'] + stats['sell_volume']:.2f}",
            "total_trades": stats["total_trades"],
        },
    }


@router.get("/trades")
async def get_trades(limit: int = 50):
    """Get recent trades from database."""
    stats = await get_db_stats()
    trades = []

    for row in stats["trades"][:limit]:
        user_id = str(row["user_id"])
        bot_type = "T"
        if "whale" in user_id.lower():
            bot_type = "W"
        elif "market" in user_id.lower():
            bot_type = "M"

        trades.append(
            {
                "id": str(row["id"]),
                "side": row["type"].upper(),
                "price": str(row["price_per_gram"]),
                "amount": str(row["amount_oltin"]),
                "total": str(row["amount_uzs"]),
                "bot_id": user_id[:8],
                "bot_type": bot_type,
                "timestamp": row["created_at"].isoformat(),
            }
        )

    return trades


@router.get("/orderbook")
async def get_orderbook():
    """Get order book from database."""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        asks = await conn.fetch("""
            SELECT
                ROUND(price_per_gram, 2) as price,
                SUM(amount_oltin) as amount,
                COUNT(*) as bot_count
            FROM orders
            WHERE type = 'sell' AND status = 'completed'
            GROUP BY ROUND(price_per_gram, 2)
            ORDER BY price ASC
            LIMIT 10
        """)

        bids = await conn.fetch("""
            SELECT
                ROUND(price_per_gram, 2) as price,
                SUM(amount_oltin) as amount,
                COUNT(*) as bot_count
            FROM orders
            WHERE type = 'buy' AND status = 'completed'
            GROUP BY ROUND(price_per_gram, 2)
            ORDER BY price DESC
            LIMIT 10
        """)

        await conn.close()

        ask_entries = [
            OrderBookEntry(
                price=str(row["price"]),
                amount=f"{Decimal(str(row['amount'])):.4f}",
                total=str(int(Decimal(str(row["price"])) * Decimal(str(row["amount"])))),
                bot_count=row["bot_count"],
            )
            for row in asks
        ]

        bid_entries = [
            OrderBookEntry(
                price=str(row["price"]),
                amount=f"{Decimal(str(row['amount'])):.4f}",
                total=str(int(Decimal(str(row["price"])) * Decimal(str(row["amount"])))),
                bot_count=row["bot_count"],
            )
            for row in bids
        ]

        best_ask = Decimal(str(asks[0]["price"])) if asks else Decimal("61.50")
        best_bid = Decimal(str(bids[0]["price"])) if bids else Decimal("60.50")
        spread = best_ask - best_bid
        spread_pct = (spread / best_bid) * 100 if best_bid > 0 else Decimal("0")

        return OrderBook(
            asks=ask_entries,
            bids=bid_entries,
            spread=str(spread),
            spread_percent=f"{float(spread_pct):.2f}",
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        print(f"OrderBook Error: {e}")
        return OrderBook(
            asks=[],
            bids=[],
            spread="1.00",
            spread_percent="1.64",
            timestamp=datetime.now(timezone.utc),
        )


@router.post("/update")
async def update_trading_data(data: dict):
    return {"status": "ok"}
