"""Unit tests for PriceService."""

from decimal import Decimal

import pytest

from app.application.services.price_service import PriceService, Quote


class TestPriceService:
    """Tests for PriceService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = PriceService(
            gold_price_uzs_per_gram=650_000,
            fee_percent=0.015,
            min_fee_uzs=3_800,
        )

    # get_gold_price tests
    def test_get_gold_price_returns_configured_price(self):
        # Arrange - done in setup
        # Act
        price = self.service.get_gold_price()
        # Assert
        assert price == Decimal("650000")

    def test_get_gold_price_custom_value(self):
        # Arrange
        service = PriceService(gold_price_uzs_per_gram=700_000)
        # Act
        price = service.get_gold_price()
        # Assert
        assert price == Decimal("700000")

    # calculate_oltin_amount tests
    def test_calculate_oltin_amount_basic(self):
        # Arrange
        uzs = Decimal("650000")
        # Act
        oltin = self.service.calculate_oltin_amount(uzs)
        # Assert
        assert oltin == Decimal("1.000000")

    def test_calculate_oltin_amount_fractional(self):
        # Arrange
        uzs = Decimal("325000")
        # Act
        oltin = self.service.calculate_oltin_amount(uzs)
        # Assert
        assert oltin == Decimal("0.500000")

    def test_calculate_oltin_amount_zero(self):
        # Arrange
        uzs = Decimal("0")
        # Act
        oltin = self.service.calculate_oltin_amount(uzs)
        # Assert
        assert oltin == Decimal("0")

    def test_calculate_oltin_amount_negative(self):
        # Arrange
        uzs = Decimal("-100000")
        # Act
        oltin = self.service.calculate_oltin_amount(uzs)
        # Assert
        assert oltin == Decimal("0")

    # calculate_uzs_amount tests
    def test_calculate_uzs_amount_one_gram(self):
        # Arrange
        oltin = Decimal("1")
        # Act
        uzs = self.service.calculate_uzs_amount(oltin)
        # Assert
        assert uzs == Decimal("650000.00")

    def test_calculate_uzs_amount_fractional(self):
        # Arrange
        oltin = Decimal("0.5")
        # Act
        uzs = self.service.calculate_uzs_amount(oltin)
        # Assert
        assert uzs == Decimal("325000.00")

    def test_calculate_uzs_amount_zero(self):
        # Arrange
        oltin = Decimal("0")
        # Act
        uzs = self.service.calculate_uzs_amount(oltin)
        # Assert
        assert uzs == Decimal("0")

    def test_calculate_uzs_amount_negative(self):
        # Arrange
        oltin = Decimal("-1")
        # Act
        uzs = self.service.calculate_uzs_amount(oltin)
        # Assert
        assert uzs == Decimal("0")

    # calculate_fee tests
    def test_calculate_fee_uses_percent_when_above_minimum(self):
        # Arrange - 1M UZS, 1.5% = 15,000 > 3,800 min
        amount = Decimal("1000000")
        # Act
        fee = self.service.calculate_fee(amount)
        # Assert
        assert fee == Decimal("15000.00")

    def test_calculate_fee_uses_minimum_when_below_threshold(self):
        # Arrange - 100K UZS, 1.5% = 1,500 < 3,800 min
        amount = Decimal("100000")
        # Act
        fee = self.service.calculate_fee(amount)
        # Assert
        assert fee == Decimal("3800")

    def test_calculate_fee_at_threshold(self):
        # Arrange - at threshold: 3800 / 0.015 = 253,333.33 UZS
        # At exactly this amount, percent_fee == min_fee
        amount = Decimal("253333.33")
        # Act
        fee = self.service.calculate_fee(amount)
        # Assert
        assert fee >= Decimal("3800")

    def test_calculate_fee_zero_amount(self):
        # Arrange
        amount = Decimal("0")
        # Act
        fee = self.service.calculate_fee(amount)
        # Assert
        assert fee == Decimal("0")

    def test_calculate_fee_negative_amount(self):
        # Arrange
        amount = Decimal("-100000")
        # Act
        fee = self.service.calculate_fee(amount)
        # Assert
        assert fee == Decimal("0")

    # get_buy_quote tests
    def test_get_buy_quote_returns_quote_object(self):
        # Arrange
        uzs = Decimal("1000000")
        # Act
        quote = self.service.get_buy_quote(uzs)
        # Assert
        assert isinstance(quote, Quote)

    def test_get_buy_quote_correct_calculation(self):
        # Arrange - 1M UZS, fee = 15000, net = 985000
        uzs = Decimal("1000000")
        # Act
        quote = self.service.get_buy_quote(uzs)
        # Assert
        assert quote.amount_uzs == Decimal("1000000")
        assert quote.fee_uzs == Decimal("15000.00")
        assert quote.net_amount_uzs == Decimal("985000.00")
        assert quote.gold_price_per_gram == Decimal("650000")
        # 985000 / 650000 = 1.515384...
        expected_oltin = Decimal("985000") / Decimal("650000")
        assert quote.amount_oltin == expected_oltin.quantize(Decimal("0.000001"))

    def test_get_buy_quote_small_amount_uses_min_fee(self):
        # Arrange - 200K UZS, 1.5% = 3000 < 3800, so fee = 3800
        uzs = Decimal("200000")
        # Act
        quote = self.service.get_buy_quote(uzs)
        # Assert
        assert quote.fee_uzs == Decimal("3800")
        assert quote.net_amount_uzs == Decimal("196200")

    # get_sell_quote tests
    def test_get_sell_quote_returns_quote_object(self):
        # Arrange
        oltin = Decimal("1")
        # Act
        quote = self.service.get_sell_quote(oltin)
        # Assert
        assert isinstance(quote, Quote)

    def test_get_sell_quote_correct_calculation(self):
        # Arrange - 1 gram = 650000 UZS, fee = 9750, net = 640250
        oltin = Decimal("1")
        # Act
        quote = self.service.get_sell_quote(oltin)
        # Assert
        assert quote.amount_oltin == Decimal("1")
        assert quote.amount_uzs == Decimal("650000.00")
        assert quote.fee_uzs == Decimal("9750.00")  # 1.5% of 650000
        assert quote.net_amount_uzs == Decimal("640250.00")

    def test_get_sell_quote_small_amount_uses_min_fee(self):
        # Arrange - 0.1 gram = 65000 UZS, 1.5% = 975 < 3800
        oltin = Decimal("0.1")
        # Act
        quote = self.service.get_sell_quote(oltin)
        # Assert
        assert quote.amount_uzs == Decimal("65000.00")
        assert quote.fee_uzs == Decimal("3800")
        assert quote.net_amount_uzs == Decimal("61200.00")


class TestPriceServiceEdgeCases:
    """Edge case tests for PriceService."""

    def test_large_amounts(self):
        # Arrange - 100 million UZS
        service = PriceService()
        amount = Decimal("100000000")
        # Act
        quote = service.get_buy_quote(amount)
        # Assert
        assert quote.fee_uzs == Decimal("1500000.00")  # 1.5%
        assert quote.net_amount_uzs == Decimal("98500000.00")

    def test_precision_is_maintained(self):
        # Arrange
        service = PriceService()
        # Act
        oltin = service.calculate_oltin_amount(Decimal("123456.789"))
        # Assert - should have 6 decimal precision
        assert "0." in str(oltin)
        assert len(str(oltin).split(".")[1]) == 6

    def test_roundtrip_conversion(self):
        # Arrange
        service = PriceService()
        original_uzs = Decimal("650000")
        # Act
        oltin = service.calculate_oltin_amount(original_uzs)
        back_to_uzs = service.calculate_uzs_amount(oltin)
        # Assert
        assert back_to_uzs == original_uzs
