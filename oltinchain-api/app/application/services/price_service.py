"""Price service for gold price calculations and quotes."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.config import settings


@dataclass
class Quote:
    """Quote for buy/sell operation."""
    amount_uzs: Decimal
    amount_oltin: Decimal
    fee_uzs: Decimal
    gold_price_per_gram: Decimal  # Effective price (with spread)
    base_price_per_gram: Decimal  # Market price (without spread)
    net_amount_uzs: Decimal


class PriceService:
    """Service for gold price calculations with spread and fee.
    
    Spread: Platform margin on buy/sell
    - Buy: User pays MORE (ask price = base * 1.005)
    - Sell: User gets LESS (bid price = base * 0.995)
    
    Fee: Additional transaction fee (1.5% or min 3800 UZS)
    """

    def __init__(
        self,
        gold_price_uzs_per_gram: int | None = None,
        fee_percent: float | None = None,
        min_fee_uzs: int | None = None,
        spread_percent: float | None = None,
    ):
        self.base_price = Decimal(gold_price_uzs_per_gram or settings.gold_price_uzs_per_gram)
        self.fee_percent = Decimal(str(fee_percent or settings.fee_percent))
        self.min_fee = Decimal(min_fee_uzs or settings.min_fee_uzs)
        self.spread = Decimal(str(spread_percent or settings.spread_percent))
        
        # Half spread each way
        self.half_spread = self.spread / 2

    def get_base_price(self) -> Decimal:
        """Get base (market) gold price in UZS per gram."""
        return self.base_price

    def get_buy_price(self) -> Decimal:
        """Get buy (ask) price with spread.
        
        User pays MORE when buying.
        """
        return (self.base_price * (1 + self.half_spread)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

    def get_sell_price(self) -> Decimal:
        """Get sell (bid) price with spread.
        
        User gets LESS when selling.
        """
        return (self.base_price * (1 - self.half_spread)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

    def calculate_fee(self, amount_uzs: Decimal) -> Decimal:
        """Calculate transaction fee.
        
        Fee = max(amount * 1.5%, 3800 UZS)
        """
        if amount_uzs <= 0:
            return Decimal(0)
        percent_fee = (amount_uzs * self.fee_percent).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        return max(percent_fee, self.min_fee)

    def get_buy_quote(self, uzs_amount: Decimal) -> Quote:
        """Get quote for buying OLTIN with UZS.
        
        Flow:
        1. User pays uzs_amount
        2. Fee is deducted
        3. Remaining converted to OLTIN at ASK price (higher)
        
        Args:
            uzs_amount: Amount user wants to spend in UZS
            
        Returns:
            Quote with all calculation details
        """
        fee = self.calculate_fee(uzs_amount)
        net_uzs = uzs_amount - fee
        buy_price = self.get_buy_price()
        
        # Convert at higher (ask) price
        oltin = (net_uzs / buy_price).quantize(
            Decimal('0.000001'), rounding=ROUND_HALF_UP
        )
        
        return Quote(
            amount_uzs=uzs_amount,
            amount_oltin=oltin,
            fee_uzs=fee,
            gold_price_per_gram=buy_price,
            base_price_per_gram=self.base_price,
            net_amount_uzs=net_uzs,
        )

    def get_sell_quote(self, oltin_amount: Decimal) -> Quote:
        """Get quote for selling OLTIN for UZS.
        
        Flow:
        1. User sells oltin_amount
        2. Converted to UZS at BID price (lower)
        3. Fee is deducted
        
        Args:
            oltin_amount: Amount of OLTIN to sell (grams)
            
        Returns:
            Quote with all calculation details
        """
        sell_price = self.get_sell_price()
        
        # Convert at lower (bid) price
        gross_uzs = (oltin_amount * sell_price).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        fee = self.calculate_fee(gross_uzs)
        net_uzs = gross_uzs - fee
        
        return Quote(
            amount_uzs=gross_uzs,
            amount_oltin=oltin_amount,
            fee_uzs=fee,
            gold_price_per_gram=sell_price,
            base_price_per_gram=self.base_price,
            net_amount_uzs=net_uzs,
        )

    def get_prices(self) -> dict:
        """Get all prices for display."""
        return {
            "base_price": self.base_price,
            "buy_price": self.get_buy_price(),  # Ask (user pays)
            "sell_price": self.get_sell_price(),  # Bid (user receives)
            "spread_percent": float(self.spread * 100),
            "fee_percent": float(self.fee_percent * 100),
        }
