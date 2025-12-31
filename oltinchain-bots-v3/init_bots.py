"""Initialize bot users and balances directly in database."""

import asyncio
import os
import uuid
from decimal import Decimal
from datetime import datetime

import asyncpg

# Bot configuration
BOTS = [
    # Market Makers (20 bots)
    *[{"phone": f"+998900{i:06d}", "type": "mm", "usd": 5000, "oltin": 10} for i in range(20)],
    # Arbitrageurs (15 bots)
    *[{"phone": f"+998901{i:06d}", "type": "arb", "usd": 3000, "oltin": 8} for i in range(15)],
    # Momentum (10 bots)
    *[{"phone": f"+998902{i:06d}", "type": "mom", "usd": 2000, "oltin": 5} for i in range(10)],
    # Whales (5 bots)
    *[{"phone": f"+998903{i:06d}", "type": "whale", "usd": 10000, "oltin": 25} for i in range(5)],
]

# Password hash for "BotPass123" (bcrypt)
BOT_PASSWORD_HASH = "$2b$12$Y2SYik8fspDlyHjxoRoUbe/0nII6Llh9QWtAvZJTLSlqnBmo3Rv1G"


async def init_bots():
    """Create bot users and balances."""
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@postgres:5432/oltinchain"
    )

    # Parse asyncpg format
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    print(f"Connecting to database...")
    conn = await asyncpg.connect(db_url)

    try:
        print(f"Creating {len(BOTS)} bots...")

        for bot in BOTS:
            user_id = uuid.uuid4()
            phone = bot["phone"]

            # Check if user exists
            existing = await conn.fetchrow(
                "SELECT id FROM users WHERE phone = $1", phone
            )

            if existing:
                user_id = existing["id"]
                print(f"Bot {phone} already exists")
            else:
                # Create user
                await conn.execute(
                    """
                    INSERT INTO users (id, phone, password_hash, kyc_level, is_active, created_at, updated_at)
                    VALUES ($1, $2, $3, 0, true, $4, $4)
                    """,
                    user_id, phone, BOT_PASSWORD_HASH, datetime.utcnow()
                )
                print(f"Created bot {phone}")

            # Create/update USD balance
            existing_usd = await conn.fetchrow(
                "SELECT id FROM balances WHERE user_id = $1 AND asset = 'USD'", user_id
            )
            if existing_usd:
                await conn.execute(
                    "UPDATE balances SET available = $1 WHERE id = $2",
                    Decimal(str(bot["usd"])), existing_usd["id"]
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO balances (id, user_id, asset, available, locked, updated_at)
                    VALUES ($1, $2, 'USD', $3, 0, $4)
                    """,
                    uuid.uuid4(), user_id, Decimal(str(bot["usd"])), datetime.utcnow()
                )

            # Create/update OLTIN balance
            existing_oltin = await conn.fetchrow(
                "SELECT id FROM balances WHERE user_id = $1 AND asset = 'OLTIN'", user_id
            )
            if existing_oltin:
                await conn.execute(
                    "UPDATE balances SET available = $1 WHERE id = $2",
                    Decimal(str(bot["oltin"])), existing_oltin["id"]
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO balances (id, user_id, asset, available, locked, updated_at)
                    VALUES ($1, $2, 'OLTIN', $3, 0, $4)
                    """,
                    uuid.uuid4(), user_id, Decimal(str(bot["oltin"])), datetime.utcnow()
                )

        print("Done!")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(init_bots())
