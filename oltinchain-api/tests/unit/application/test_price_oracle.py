"""Tests for Price Oracle service."""

from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from app.application.services.price_oracle import PriceOracle, GENESIS_TIMESTAMP
from app.domain.models.price_cycle import CyclePhase


class TestPriceOracle:
    """Tests for PriceOracle class."""
    
    @pytest.fixture
    def oracle(self) -> PriceOracle:
        """Create oracle with fixed genesis for testing."""
        genesis = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        return PriceOracle(genesis=genesis)
    
    def test_genesis_cycle_is_1(self, oracle: PriceOracle):
        """At genesis, cycle should be 1."""
        # Given
        genesis = oracle.genesis
        
        # When
        state = oracle.get_current_cycle_state(genesis)
        
        # Then
        assert state.cycle_number == 1
        assert state.day_in_cycle == 0.0
    
    def test_day_3_5_is_markup_phase(self, oracle: PriceOracle):
        """Day 3.5 should be in markup phase."""
        # Given
        time = oracle.genesis + timedelta(days=3.5)
        
        # When
        state = oracle.get_current_cycle_state(time)
        
        # Then
        assert state.phase == CyclePhase.MARKUP
    
    def test_day_4_5_is_distribution_phase(self, oracle: PriceOracle):
        """Day 4.5 should be in distribution phase."""
        # Given
        time = oracle.genesis + timedelta(days=4.5)
        
        # When
        state = oracle.get_current_cycle_state(time)
        
        # Then
        assert state.phase == CyclePhase.DISTRIBUTION
    
    def test_day_5_5_is_markdown_phase(self, oracle: PriceOracle):
        """Day 5.5 should be in markdown phase."""
        # Given
        time = oracle.genesis + timedelta(days=5.5)
        
        # When
        state = oracle.get_current_cycle_state(time)
        
        # Then
        assert state.phase == CyclePhase.MARKDOWN
    
    def test_day_7_starts_cycle_2(self, oracle: PriceOracle):
        """Day 7 should start cycle 2."""
        # Given
        time = oracle.genesis + timedelta(days=7)
        
        # When
        state = oracle.get_current_cycle_state(time)
        
        # Then
        assert state.cycle_number == 2
        assert state.day_in_cycle == pytest.approx(0.0, abs=0.01)
    
    def test_price_is_positive(self, oracle: PriceOracle):
        """Price should always be positive."""
        # Given
        times = [
            oracle.genesis + timedelta(days=d)
            for d in [0, 1, 2, 3, 4, 5, 6, 6.5, 7, 14, 21]
        ]
        
        # When/Then
        for time in times:
            price = oracle.get_price(time)
            assert price > Decimal("0"), f"Price at {time} should be positive"
    
    def test_price_increases_during_markup(self, oracle: PriceOracle):
        """Price should generally increase during markup phase."""
        # Given
        start_time = oracle.genesis + timedelta(days=1.5)  # Start of markup
        end_time = oracle.genesis + timedelta(days=3.5)    # Mid markup
        
        # When
        start_state = oracle.get_current_cycle_state(start_time)
        end_state = oracle.get_current_cycle_state(end_time)
        
        # Then
        assert end_state.current_price > start_state.current_price
    
    def test_price_decreases_during_markdown(self, oracle: PriceOracle):
        """Price should generally decrease during markdown phase."""
        # Given
        start_time = oracle.genesis + timedelta(days=5.0)   # Start of markdown
        end_time = oracle.genesis + timedelta(days=6.0)     # End of markdown
        
        # When
        start_state = oracle.get_current_cycle_state(start_time)
        end_state = oracle.get_current_cycle_state(end_time)
        
        # Then
        assert end_state.current_price < start_state.current_price
    
    def test_spread_calculation(self, oracle: PriceOracle):
        """Bid should be lower than ask."""
        # Given
        time = oracle.genesis + timedelta(days=2)
        spread = Decimal("1.0")  # 1%
        
        # When
        mid, bid, ask = oracle.get_price_with_spread(time, spread)
        
        # Then
        assert bid < mid < ask
        assert ask - bid == pytest.approx(mid * Decimal("0.01"), rel=Decimal("0.01"))
    
    def test_cycle_2_starts_at_180(self, oracle: PriceOracle):
        """Cycle 2 should start at $180 (cycle 1 end)."""
        # Given
        time = oracle.genesis + timedelta(days=7)  # Start of cycle 2
        
        # When
        state = oracle.get_current_cycle_state(time)
        
        # Then
        assert state.start_price == Decimal("180.00")
    
    def test_cycle_progress_at_midpoint(self, oracle: PriceOracle):
        """At day 3.5, progress should be 0.5."""
        # Given
        time = oracle.genesis + timedelta(days=3.5)
        
        # When
        state = oracle.get_current_cycle_state(time)
        
        # Then
        assert state.cycle_progress == 0.5


class TestPriceOracleEdgeCases:
    """Edge case tests for Price Oracle."""
    
    def test_far_future_cycle(self):
        """Oracle should work for future cycles."""
        # Given
        oracle = PriceOracle()
        future = datetime(2030, 1, 1, tzinfo=timezone.utc)
        
        # When
        state = oracle.get_current_cycle_state(future)
        price = oracle.get_price(future)
        
        # Then
        assert state.cycle_number > 1
        assert price > Decimal("0")
    
    def test_multiple_calls_give_similar_prices(self):
        """Multiple rapid calls should give similar prices."""
        # Given
        oracle = PriceOracle()
        now = datetime.now(timezone.utc)
        
        # When
        prices = [oracle.get_price(now) for _ in range(10)]
        
        # Then - all prices should be within 30% of each other (due to noise)
        min_price = min(prices)
        max_price = max(prices)
        variance = (max_price - min_price) / min_price
        assert variance < Decimal("0.30")
