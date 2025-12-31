"""Arbitrageur bot - keeps market price close to oracle."""

import random
from decimal import Decimal

from bots.base import BaseBot, Order
from clients.api_client import APIClient
from clients.oracle_client import CycleState


class ArbitrageurBot(BaseBot):
    """
    Arbitrageur - buys when market is below oracle, sells when above.

    Keeps market price anchored to the oracle price.
    """

    bot_type = "arbitrageur"

    def __init__(
        self,
        bot_id: str,
        api_client: APIClient,
        initial_usd: Decimal,
        initial_oltin: Decimal,
    ):
        super().__init__(bot_id, api_client, initial_usd, initial_oltin)

        # Minimum deviation to act (0.5% - 2.0%)
        self.min_deviation = Decimal(str(random.uniform(0.005, 0.020)))

        # Aggressiveness multiplier (0.5 - 1.5)
        self.aggressiveness = Decimal(str(random.uniform(0.5, 1.5)))

        self.logger.info(
            f"Initialized with min_deviation={self.min_deviation:.4f}, "
            f"aggressiveness={self.aggressiveness:.2f}"
        )

    async def generate_orders(
        self,
        oracle_price: Decimal,
        market_price: Decimal | None,
        cycle_state: CycleState,
    ) -> list[Order]:
        """Generate order if arbitrage opportunity exists."""
        orders = []

        # Need market price to arbitrage
        if market_price is None:
            return orders

        # Skip if we already have active orders
        if len(self.state.active_orders) >= 1:
            return orders

        # Calculate deviation
        deviation = (market_price - oracle_price) / oracle_price

        # Market is below oracle - buy opportunity
        if deviation < -self.min_deviation:
            min_usd = Decimal("50")
            if self.balance_usd < min_usd:
                return orders

            # Order size proportional to deviation
            intensity = min(abs(deviation) * 10, Decimal("1"))
            base_amount = self.balance_usd * Decimal("0.10")  # 10% of balance
            amount_usd = base_amount * intensity * self.aggressiveness

            # Price slightly above market for quick execution
            price = market_price * Decimal("1.002")
            qty = (amount_usd / price).quantize(Decimal("0.0001"))

            if qty >= Decimal("0.001"):
                orders.append(Order(
                    side="buy",
                    price=price.quantize(Decimal("0.01")),
                    quantity=qty,
                ))

        # Market is above oracle - sell opportunity
        elif deviation > self.min_deviation:
            min_oltin = Decimal("0.05")
            if self.balance_oltin < min_oltin:
                return orders

            intensity = min(abs(deviation) * 10, Decimal("1"))
            base_amount = self.balance_oltin * Decimal("0.10")
            amount_oltin = (base_amount * intensity * self.aggressiveness).quantize(
                Decimal("0.0001")
            )

            # Price slightly below market for quick execution
            price = market_price * Decimal("0.998")

            if amount_oltin >= Decimal("0.001"):
                orders.append(Order(
                    side="sell",
                    price=price.quantize(Decimal("0.01")),
                    quantity=amount_oltin,
                ))

        return orders
