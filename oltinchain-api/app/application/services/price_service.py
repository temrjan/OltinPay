"""Price service for OLTIN price calculations and quotes.

Integrates with Price Oracle for dynamic pricing based on Wyckoff cycles.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.config import settings
from app.application.services.price_oracle import get_price_oracle


@dataclass
class Quote:
    """Quote for buy/sell operation."""
    
    amount_usd: Decimal
    amount_oltin: Decimal
    fee_usd: Decimal
    price_per_gram: Decimal  # Effective price (with spread)
    base_price_per_gram: Decimal  # Market price (without spread)
    net_amount_usd: Decimal


class PriceService:
    """Service for OLTIN price calculations with spread and fee.
    
    Integrates with Price Oracle for dynamic pricing.
    
    Spread: Platform margin on buy/sell
    - Buy: User pays MORE (ask price)
    - Sell: User gets LESS (bid price)
    
    Fee: Additional transaction fee (1.5% or min $1)
    """

    def __init__(
        self,
        fee_percent: float | None = None,
        min_fee_usd: float | None = None,
        spread_percent: float | None = None,
    ) -> None:
        """Initialize price service.
        
        Args:
            fee_percent: Transaction fee percentage (default from settings).
            min_fee_usd: Minimum fee in USD (default $1).
            spread_percent: Bid/ask spread (default from settings).
        """
        self.fee_percent = Decimal(str(fee_percent or settings.fee_percent))
        self.min_fee = Decimal(str(min_fee_usd or 1.0))
        self.spread = Decimal(str(spread_percent or settings.spread_percent))
        self.half_spread = self.spread / 2
        self._oracle = get_price_oracle()

    def get_base_price(self) -> Decimal:
        """Get base (market) price from Price Oracle."""
        return self._oracle.get_price()

    def get_buy_price(self) -> Decimal:
        """Get buy (ask) price with spread.
        
        User pays MORE when buying.
        """
        base = self.get_base_price()
        return (base * (1 + self.half_spread)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def get_sell_price(self) -> Decimal:
        """Get sell (bid) price with spread.
        
        User gets LESS when selling.
        """
        base = self.get_base_price()
        return (base * (1 - self.half_spread)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def calculate_fee(self, amount_usd: Decimal) -> Decimal:
        """Calculate transaction fee.
        
        Fee = max(amount * fee_percent, min_fee)
        """
        if amount_usd <= 0:
            return Decimal("0")
        percent_fee = (amount_usd * self.fee_percent).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return max(percent_fee, self.min_fee)

    def get_buy_quote(self, usd_amount: Decimal) -> Quote:
        """Get quote for buying OLTIN with USD.
        
        Flow:
        1. User pays usd_amount
        2. Fee is deducted
        3. Remaining converted to OLTIN at ASK price
        
        Args:
            usd_amount: Amount user wants to spend in USD.
            
        Returns:
            Quote with calculation details.
        """
        base_price = self.get_base_price()
        fee = self.calculate_fee(usd_amount)
        net_usd = usd_amount - fee
        buy_price = (base_price * (1 + self.half_spread)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        # Convert at ask price
        oltin = (net_usd / buy_price).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
        
        return Quote(
            amount_usd=usd_amount,
            amount_oltin=oltin,
            fee_usd=fee,
            price_per_gram=buy_price,
            base_price_per_gram=base_price,
            net_amount_usd=net_usd,
        )

    def get_sell_quote(self, oltin_amount: Decimal) -> Quote:
        """Get quote for selling OLTIN for USD.
        
        Flow:
        1. User sells oltin_amount
        2. Converted to USD at BID price
        3. Fee is deducted
        
        Args:
            oltin_amount: Amount of OLTIN to sell.
            
        Returns:
            Quote with calculation details.
        """
        base_price = self.get_base_price()
        sell_price = (base_price * (1 - self.half_spread)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        # Convert at bid price
        gross_usd = (oltin_amount * sell_price).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        fee = self.calculate_fee(gross_usd)
        net_usd = gross_usd - fee
        
        return Quote(
            amount_usd=gross_usd,
            amount_oltin=oltin_amount,
            fee_usd=fee,
            price_per_gram=sell_price,
            base_price_per_gram=base_price,
            net_amount_usd=net_usd,
        )

    def get_prices(self) -> dict:
        """Get all prices for display."""
        base = self.get_base_price()
        return {
            "base_price": base,
            "buy_price": (base * (1 + self.half_spread)).quantize(Decimal("0.01")),
            "sell_price": (base * (1 - self.half_spread)).quantize(Decimal("0.01")),
            "spread_percent": float(self.spread * 100),
            "fee_percent": float(self.fee_percent * 100),
        }
