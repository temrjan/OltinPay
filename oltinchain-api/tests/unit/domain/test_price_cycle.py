"""Tests for price cycle domain models."""

from decimal import Decimal

import pytest

from app.domain.models.price_cycle import (
    CycleParameters,
    CyclePhase,
    CycleState,
    PHASE_CONFIGS,
)


class TestCycleParameters:
    """Tests for CycleParameters."""
    
    def test_cycle_1_parameters(self):
        """First cycle should start at $100 with 4.2x peak multiplier."""
        # Given
        cycle_number = 1
        
        # When
        params = CycleParameters.for_cycle(cycle_number)
        
        # Then
        assert params.cycle_number == 1
        assert params.start_price == Decimal("100.00")
        assert params.peak_multiplier == Decimal("4.20")
        assert params.drawdown_percent == Decimal("70.00")
    
    def test_cycle_2_parameters(self):
        """Second cycle should start at $180 with lower multiplier."""
        # Given
        cycle_number = 2
        
        # When
        params = CycleParameters.for_cycle(cycle_number)
        
        # Then
        assert params.start_price == Decimal("180.00")
        assert params.peak_multiplier == Decimal("3.90")
        assert params.drawdown_percent == Decimal("65.00")
    
    def test_cycle_3_parameters(self):
        """Third cycle continues growth pattern."""
        # Given
        cycle_number = 3
        
        # When
        params = CycleParameters.for_cycle(cycle_number)
        
        # Then
        assert params.start_price == Decimal("324.00")
        assert params.peak_multiplier == Decimal("3.60")
        assert params.drawdown_percent == Decimal("60.00")
    
    def test_peak_price_calculation(self):
        """Peak price = start * multiplier."""
        # Given
        params = CycleParameters.for_cycle(1)
        
        # When
        peak = params.peak_price
        
        # Then
        expected = Decimal("100.00") * Decimal("4.20")
        assert peak == expected.quantize(Decimal("0.01"))
    
    def test_bottom_price_calculation(self):
        """Bottom price = peak * (1 - drawdown)."""
        # Given
        params = CycleParameters.for_cycle(1)
        
        # When
        bottom = params.bottom_price
        
        # Then
        # Peak 420, drawdown 70% -> bottom = 420 * 0.3 = 126
        assert bottom == Decimal("126.00")
    
    def test_end_price_calculation(self):
        """End price = start * 1.8 (+80%)."""
        # Given
        params = CycleParameters.for_cycle(1)
        
        # When
        end = params.end_price
        
        # Then
        assert end == Decimal("180.00")
    
    def test_higher_lows_principle(self):
        """Each cycle ends higher than previous cycle started."""
        # Given
        cycles = [CycleParameters.for_cycle(i) for i in range(1, 6)]
        
        # Then
        for i in range(1, len(cycles)):
            prev_end = cycles[i - 1].end_price
            current_start = cycles[i].start_price
            assert current_start == prev_end, (
                f"Cycle {i + 1} should start at previous cycle end"
            )


class TestPhaseConfigs:
    """Tests for phase configurations."""
    
    def test_phases_cover_full_cycle(self):
        """All phases should cover days 0-7."""
        # Then
        assert PHASE_CONFIGS[0].start_day == 0.0
        assert PHASE_CONFIGS[-1].end_day == 7.0
    
    def test_phases_are_continuous(self):
        """Phases should be continuous with no gaps."""
        # Then
        for i in range(1, len(PHASE_CONFIGS)):
            prev_end = PHASE_CONFIGS[i - 1].end_day
            current_start = PHASE_CONFIGS[i].start_day
            assert prev_end == current_start, (
                f"Gap between phase {i - 1} and {i}"
            )
    
    def test_accumulation_is_first(self):
        """Cycle should start with accumulation phase."""
        # Then
        assert PHASE_CONFIGS[0].name == CyclePhase.ACCUMULATION
    
    def test_re_accumulation_is_last(self):
        """Cycle should end with re-accumulation."""
        # Then
        assert PHASE_CONFIGS[-1].name == CyclePhase.RE_ACCUMULATION


class TestCycleState:
    """Tests for CycleState dataclass."""
    
    def test_cycle_progress(self):
        """Progress should be day/7."""
        # Given
        state = CycleState(
            cycle_number=1,
            phase=CyclePhase.MARKUP,
            day_in_cycle=3.5,
            start_price=Decimal("100"),
            current_price=Decimal("250"),
            peak_price=Decimal("420"),
            bottom_price=Decimal("126"),
            target_end_price=Decimal("180"),
        )
        
        # Then
        assert state.cycle_progress == 0.5
    
    def test_total_growth(self):
        """Growth should be (current - start) / start * 100."""
        # Given
        state = CycleState(
            cycle_number=1,
            phase=CyclePhase.MARKUP,
            day_in_cycle=3.5,
            start_price=Decimal("100"),
            current_price=Decimal("150"),
            peak_price=Decimal("420"),
            bottom_price=Decimal("126"),
            target_end_price=Decimal("180"),
        )
        
        # Then
        assert state.total_growth == Decimal("50")
