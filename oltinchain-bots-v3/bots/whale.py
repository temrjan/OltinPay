"""Whale bot - large corrections when market deviates significantly."""

from decimal import Decimal

from bots.base import BaseBot, Order
from clients.api_client import APIClient
from clients.oracle_client import CycleState


class WhaleBot(BaseBot):
    """
    Whale - large orders when market deviates significantly from oracle.

    Activates only when deviation > 3%.
    Uses up to 30% of balance per order.
    """

    bot_type = "whale"

    # Activation threshold
    ACTIVATION_THRESHOLD = Decimal("0.03")  # 3%

    # Maximum order size
    MAX_ORDER_PCT = Decimal("0.30")  # 30% of balance

    def __init__(
        self,
        bot_id: str,
        api_client: APIClient,
        initial_usd: Decimal,
        initial_oltin: Decimal,
    ):
        super().__init__(bot_id, api_client, initial_usd, initial_oltin)
        self.logger.info("Initialized whale bot")

    async def generate_orders(
        self,
        oracle_price: Decimal,
        market_price: Decimal | None,
        cycle_state: CycleState,
    ) -> list[Order]:
        """Generate large corrective order if deviation is significant."""
        orders = []

        # Need market price
        if market_price is None:
            return orders

        # Skip if we already have active orders
        if len(self.state.active_orders) >= 1:
            return orders

        # Calculate deviation
        deviation = (market_price - oracle_price) / oracle_price

        # Only activate on significant deviation
        if abs(deviation) < self.ACTIVATION_THRESHOLD:
            return orders

        # Calculate intensity (3% -> 10%, 6% -> 20%, 10%+ -> 30%)
        intensity = min(abs(deviation) * 3, self.MAX_ORDER_PCT)

        # Market is above oracle - sell to correct
        if deviation > 0:
            min_oltin = Decimal("0.5")
            if self.balance_oltin < min_oltin:
                return orders

            amount = (self.balance_oltin * intensity).quantize(Decimal("0.0001"))
            price = market_price * Decimal("0.995")  # Aggressive price

            if amount >= Decimal("0.01"):
                orders.append(Order(
                    side="sell",
                    price=price.quantize(Decimal("0.01")),
                    quantity=amount,
                ))
                self.logger.info(
                    f"WHALE SELL: deviation={deviation:.2%}, "
                    f"amount={amount} OLTIN"
                )

        # Market is below oracle - buy to correct
        else:
            min_usd = Decimal("100")
            if self.balance_usd < min_usd:
                return orders

            amount_usd = self.balance_usd * intensity
            price = market_price * Decimal("1.005")  # Aggressive price

            qty = (amount_usd / price).quantize(Decimal("0.0001"))

            if qty >= Decimal("0.01"):
                orders.append(Order(
                    side="buy",
                    price=price.quantize(Decimal("0.01")),
                    quantity=qty,
                ))
                self.logger.info(
                    f"WHALE BUY: deviation={deviation:.2%}, "
                    f"amount={qty} OLTIN"
                )

        return orders
