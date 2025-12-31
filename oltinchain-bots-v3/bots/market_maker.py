"""Market Maker bot - provides liquidity on both sides."""

import random
from decimal import Decimal

from bots.base import BaseBot, Order
from clients.api_client import APIClient
from clients.oracle_client import CycleState


class MarketMakerBot(BaseBot):
    """
    Market Maker - always maintains bid AND ask orders.

    Provides liquidity for other traders.
    Earns from the spread between bid and ask.
    """

    bot_type = "market_maker"

    def __init__(
        self,
        bot_id: str,
        api_client: APIClient,
        initial_usd: Decimal,
        initial_oltin: Decimal,
    ):
        super().__init__(bot_id, api_client, initial_usd, initial_oltin)

        # Random spread for each MM (0.3% - 1.0%)
        self.spread = Decimal(str(random.uniform(0.003, 0.010)))

        # Random order size (1% - 5% of balance)
        self.order_size_pct = Decimal(str(random.uniform(0.01, 0.05)))

        self.logger.info(
            f"Initialized with spread={self.spread:.4f}, "
            f"order_size={self.order_size_pct:.2%}"
        )

    async def generate_orders(
        self,
        oracle_price: Decimal,
        market_price: Decimal | None,
        cycle_state: CycleState,
    ) -> list[Order]:
        """Generate bid + ask orders around oracle price."""
        orders = []

        # Use oracle price as reference
        reference_price = market_price if market_price else oracle_price
        half_spread = self.spread / 2

        # Skip if we already have 2+ active orders
        if len(self.state.active_orders) >= 2:
            return orders

        # BID (buy) - below reference price
        bid_price = reference_price * (1 - half_spread)
        min_usd = Decimal("10")

        if self.balance_usd > min_usd:
            bid_amount_usd = self.balance_usd * self.order_size_pct
            bid_qty = (bid_amount_usd / bid_price).quantize(Decimal("0.0001"))

            if bid_qty >= Decimal("0.001"):
                orders.append(Order(
                    side="buy",
                    price=bid_price.quantize(Decimal("0.01")),
                    quantity=bid_qty,
                ))

        # ASK (sell) - above reference price
        ask_price = reference_price * (1 + half_spread)
        min_oltin = Decimal("0.01")

        if self.balance_oltin > min_oltin:
            ask_qty = (self.balance_oltin * self.order_size_pct).quantize(
                Decimal("0.0001")
            )

            if ask_qty >= Decimal("0.001"):
                orders.append(Order(
                    side="sell",
                    price=ask_price.quantize(Decimal("0.01")),
                    quantity=ask_qty,
                ))

        return orders
