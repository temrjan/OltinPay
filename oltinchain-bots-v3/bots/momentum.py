"""Momentum bot - follows Wyckoff cycle trend."""

import random
from decimal import Decimal

from bots.base import BaseBot, Order
from clients.api_client import APIClient
from clients.oracle_client import CycleState


class MomentumBot(BaseBot):
    """
    Momentum - follows the Wyckoff cycle direction.

    In bullish phases: more likely to buy
    In bearish phases: more likely to sell
    """

    bot_type = "momentum"

    # Probabilities by phase
    PHASE_PROBABILITIES = {
        "accumulation":    {"buy": 0.65, "sell": 0.20, "hold": 0.15},
        "markup":          {"buy": 0.70, "sell": 0.15, "hold": 0.15},
        "distribution":    {"buy": 0.20, "sell": 0.60, "hold": 0.20},
        "markdown":        {"buy": 0.15, "sell": 0.70, "hold": 0.15},
        "capitulation":    {"buy": 0.25, "sell": 0.55, "hold": 0.20},
        "re_accumulation": {"buy": 0.60, "sell": 0.25, "hold": 0.15},
    }

    def __init__(
        self,
        bot_id: str,
        api_client: APIClient,
        initial_usd: Decimal,
        initial_oltin: Decimal,
    ):
        super().__init__(bot_id, api_client, initial_usd, initial_oltin)
        self.logger.info("Initialized momentum bot")

    async def generate_orders(
        self,
        oracle_price: Decimal,
        market_price: Decimal | None,
        cycle_state: CycleState,
    ) -> list[Order]:
        """Generate order based on Wyckoff phase."""
        orders = []

        # Skip if we already have active orders
        if len(self.state.active_orders) >= 1:
            return orders

        # Get probabilities for current phase
        phase = cycle_state.phase.lower()
        probs = self.PHASE_PROBABILITIES.get(
            phase,
            {"buy": 0.40, "sell": 0.40, "hold": 0.20}
        )

        # Random decision
        roll = random.random()

        reference_price = market_price if market_price else oracle_price

        # Buy decision
        if roll < probs["buy"]:
            min_usd = Decimal("20")
            if self.balance_usd < min_usd:
                return orders

            # Random order size (2% - 8% of balance)
            pct = Decimal(str(random.uniform(0.02, 0.08)))
            amount_usd = self.balance_usd * pct

            # Price near oracle with small random offset
            price_offset = Decimal(str(random.uniform(-0.005, 0.005)))
            price = reference_price * (1 + price_offset)

            qty = (amount_usd / price).quantize(Decimal("0.0001"))

            if qty >= Decimal("0.001"):
                orders.append(Order(
                    side="buy",
                    price=price.quantize(Decimal("0.01")),
                    quantity=qty,
                ))

        # Sell decision
        elif roll < probs["buy"] + probs["sell"]:
            min_oltin = Decimal("0.02")
            if self.balance_oltin < min_oltin:
                return orders

            pct = Decimal(str(random.uniform(0.02, 0.08)))
            amount_oltin = (self.balance_oltin * pct).quantize(Decimal("0.0001"))

            price_offset = Decimal(str(random.uniform(-0.005, 0.005)))
            price = reference_price * (1 + price_offset)

            if amount_oltin >= Decimal("0.001"):
                orders.append(Order(
                    side="sell",
                    price=price.quantize(Decimal("0.01")),
                    quantity=amount_oltin,
                ))

        # Hold - do nothing
        return orders
