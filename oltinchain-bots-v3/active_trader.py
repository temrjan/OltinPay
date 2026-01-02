"""
Active Trader Bot - Crosses the spread to generate trades.

Unlike Market Makers who place limit orders within the spread,
Active Traders place orders that cross the spread to execute immediately.
"""

import logging
from decimal import Decimal
from uuid import UUID
from datetime import datetime, timezone

from database import Database

logger = logging.getLogger(__name__)


class ActiveTrader:
    """
    Active Trader that crosses the spread to generate trades.

    - RED (Seller): Places SELL orders at best_bid * 0.999 (crosses spread)
    - GREEN (Buyer): Places BUY orders at best_ask * 1.001 (crosses spread)
    - Trades 1-3% of balance per turn
    - Waits for queue rotation before next trade
    - Switches role when balance depleted (<10%)
    """

    def __init__(
        self,
        user_id: UUID,
        phone: str,
        db: Database,
        api_client,  # Global APIClient instance
        side: str,  # 'red' or 'green'
        position: int,  # Queue position (1-10)
    ):
        self.user_id = user_id
        self.phone = phone
        self.api = api_client
        self.db = db
        self.side = side
        self.position = position
        self.is_active = True
        self.last_trade_at: datetime | None = None
        self._logged_in = False

        # Trade parameters
        self.min_trade_pct = Decimal("0.01")  # 1% of balance
        self.max_trade_pct = Decimal("0.03")  # 3% of balance
        self.role_switch_threshold = Decimal("0.10")  # Switch when <10% remains

    async def ensure_logged_in(self) -> bool:
        """Ensure bot is logged in."""
        if not self._logged_in:
            success = await self.api.login(self.phone)
            if success:
                self._logged_in = True
            return success
        return True

    async def get_balances(self) -> tuple[Decimal, Decimal]:
        """Get (USD, OLTIN) balances from database."""
        return await self.db.get_bot_balances(self.user_id)

    async def should_switch_role(self) -> bool:
        """Check if bot should switch from RED to GREEN or vice versa."""
        usd_balance, oltin_balance = await self.get_balances()

        # Get current oracle price to calculate total value
        oracle_price = await self.db.get_last_oracle_price() or Decimal("500")

        # Calculate total value in USD
        oltin_value_usd = oltin_balance * oracle_price
        total_value = usd_balance + oltin_value_usd

        if total_value <= 0:
            return False

        if self.side == "red":
            # RED sells OLTIN, check if OLTIN is depleted
            oltin_ratio = oltin_value_usd / total_value
            return oltin_ratio < self.role_switch_threshold
        else:
            # GREEN buys OLTIN with USD, check if USD is depleted
            usd_ratio = usd_balance / total_value
            return usd_ratio < self.role_switch_threshold

    async def switch_role(self) -> None:
        """Switch between RED and GREEN role."""
        old_side = self.side
        self.side = "green" if self.side == "red" else "red"

        # Update in database
        await self.db.execute(
            """
            UPDATE active_bot_queue
            SET side = $1, updated_at = NOW()
            WHERE bot_id = $2
            """,
            self.side,
            self.user_id,
        )

        logger.info(f"ActiveTrader {self.phone} role switch: {old_side} -> {self.side}")

    async def calculate_trade_amount(self, oracle_price: Decimal) -> Decimal:
        """Calculate trade amount (1-3% of relevant balance)."""
        import random

        trade_pct = Decimal(
            str(random.uniform(float(self.min_trade_pct), float(self.max_trade_pct)))
        )

        usd_balance, oltin_balance = await self.get_balances()

        if self.side == "red":
            # Selling OLTIN
            return (oltin_balance * trade_pct).quantize(Decimal("0.0001"))
        else:
            # Buying OLTIN with USD
            # Convert USD to OLTIN amount
            oltin_amount = usd_balance * trade_pct / oracle_price
            return oltin_amount.quantize(Decimal("0.0001"))

    async def execute_trade(
        self,
        best_bid: Decimal,
        best_ask: Decimal,
        oracle_price: Decimal,
    ) -> dict | None:
        """
        Execute a trade that crosses the spread.

        Returns order dict if successful, None otherwise.
        """
        # Ensure logged in
        if not await self.ensure_logged_in():
            logger.warning(f"ActiveTrader {self.phone} failed to login")
            return None

        # Check if should switch role first
        if await self.should_switch_role():
            await self.switch_role()

        amount = await self.calculate_trade_amount(oracle_price)

        if amount < Decimal("0.001"):
            logger.warning(f"ActiveTrader {self.phone} insufficient balance for trade")
            return None

        if self.side == "red":
            # SELL at slightly below best bid to ensure execution
            price = (best_bid * Decimal("0.999")).quantize(Decimal("0.01"))
            side = "sell"
        else:
            # BUY at slightly above best ask to ensure execution
            price = (best_ask * Decimal("1.001")).quantize(Decimal("0.01"))
            side = "buy"

        try:
            order_id = await self.api.place_order(
                phone=self.phone,
                side=side,
                price=price,
                quantity=amount,
            )

            if order_id:
                self.last_trade_at = datetime.now(timezone.utc)

                # Update stats in database
                await self.db.execute(
                    """
                    UPDATE active_bot_queue
                    SET
                        last_trade_at = NOW(),
                        trades_count = trades_count + 1,
                        total_volume = total_volume + $1,
                        updated_at = NOW()
                    WHERE bot_id = $2
                    """,
                    float(amount * price),
                    self.user_id,
                )

                logger.info(
                    f"ActiveTrader {self.phone} executed: {side} {amount} @ ${price} (order={order_id})"
                )

                return {
                    "id": str(order_id),
                    "side": side,
                    "price": str(price),
                    "quantity": str(amount),
                }

        except Exception as e:
            logger.error(f"ActiveTrader {self.phone} error: {e}")

        return None

    def __repr__(self) -> str:
        return (
            f"ActiveTrader(phone={self.phone}, side={self.side}, pos={self.position})"
        )
