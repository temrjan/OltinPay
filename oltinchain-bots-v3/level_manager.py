"""Level pricing management."""

from decimal import Decimal
from typing import List

from config import config
from models import LevelPrice, OrderSide


class LevelManager:
    """Manages price levels for bots."""

    def calculate_level_price(
        self,
        oracle_price: Decimal,
        level: int,
        side: OrderSide,
    ) -> LevelPrice:
        """
        Calculate price for a specific level.

        Level 1 is closest to mid-price, Level 10 is furthest.
        """
        # Calculate spread for this level
        spread_pct = config.base_spread_pct + (config.level_step_pct * (level - 1))

        if side == OrderSide.SELL:
            price = oracle_price * (1 + spread_pct)
        else:
            price = oracle_price * (1 - spread_pct)

        return LevelPrice(
            level=level,
            side=side,
            price=price.quantize(Decimal("0.01")),
            spread_pct=spread_pct,
        )

    def get_all_level_prices(self, oracle_price: Decimal) -> List[LevelPrice]:
        """Get prices for all levels on both sides."""
        prices = []

        for level in range(1, config.levels + 1):
            prices.append(
                self.calculate_level_price(oracle_price, level, OrderSide.SELL)
            )
            prices.append(
                self.calculate_level_price(oracle_price, level, OrderSide.BUY)
            )

        return prices

    def get_order_size(self, level: int) -> Decimal:
        """Get order size in USD for a level."""
        return config.order_sizes.get(level, Decimal("100"))

    def get_order_quantity(
        self,
        level: int,
        side: OrderSide,
        oracle_price: Decimal,
        available_usd: Decimal,
        available_oltin: Decimal,
    ) -> Decimal:
        """
        Calculate order quantity for a level.

        Returns quantity in OLTIN.
        """
        target_value = self.get_order_size(level)

        if side == OrderSide.SELL:
            # Selling OLTIN - limited by OLTIN balance
            max_oltin = available_oltin
            target_oltin = target_value / oracle_price
            quantity = min(target_oltin, max_oltin)
        else:
            # Buying OLTIN - limited by USD balance
            max_usd = available_usd
            actual_value = min(target_value, max_usd)
            quantity = actual_value / oracle_price

        # Round to 4 decimal places
        return quantity.quantize(Decimal("0.0001"))


# Global instance
level_manager = LevelManager()
