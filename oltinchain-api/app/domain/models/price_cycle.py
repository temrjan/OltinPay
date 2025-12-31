"""Price cycle domain models.

Implements Wyckoff market cycle phases for OLTIN price generation.
Based on Bitcoin market structure with configurable cycle duration.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import NamedTuple


class CyclePhase(str, Enum):
    """Wyckoff market cycle phases."""
    
    ACCUMULATION = "accumulation"
    MARKUP = "markup"
    DISTRIBUTION = "distribution"
    MARKDOWN = "markdown"
    CAPITULATION = "capitulation"
    RE_ACCUMULATION = "re_accumulation"


class PhaseConfig(NamedTuple):
    """Configuration for a single cycle phase."""
    
    name: CyclePhase
    start_day: float  # Day within cycle (0-7)
    end_day: float
    price_mult_start: float  # Multiplier from cycle start price
    price_mult_end: float
    volatility: float  # Base volatility for this phase


# Phase configurations for 7-day cycle (1 week = 1 Bitcoin year)
PHASE_CONFIGS: list[PhaseConfig] = [
    PhaseConfig(
        name=CyclePhase.ACCUMULATION,
        start_day=0.0,
        end_day=1.5,
        price_mult_start=1.0,
        price_mult_end=1.1,
        volatility=0.02,
    ),
    PhaseConfig(
        name=CyclePhase.MARKUP,
        start_day=1.5,
        end_day=4.0,
        price_mult_start=1.1,
        price_mult_end=4.2,  # Peak multiplier for cycle 1
        volatility=0.05,
    ),
    PhaseConfig(
        name=CyclePhase.DISTRIBUTION,
        start_day=4.0,
        end_day=5.0,
        price_mult_start=4.2,
        price_mult_end=4.0,
        volatility=0.06,
    ),
    PhaseConfig(
        name=CyclePhase.MARKDOWN,
        start_day=5.0,
        end_day=6.0,
        price_mult_start=4.0,
        price_mult_end=1.5,
        volatility=0.08,
    ),
    PhaseConfig(
        name=CyclePhase.CAPITULATION,
        start_day=6.0,
        end_day=6.5,
        price_mult_start=1.5,
        price_mult_end=1.26,  # -70% from peak
        volatility=0.10,
    ),
    PhaseConfig(
        name=CyclePhase.RE_ACCUMULATION,
        start_day=6.5,
        end_day=7.0,
        price_mult_start=1.26,
        price_mult_end=1.8,  # +80% total cycle growth
        volatility=0.03,
    ),
]


@dataclass
class CycleState:
    """Current state of the price cycle."""
    
    cycle_number: int
    phase: CyclePhase
    day_in_cycle: float
    start_price: Decimal
    current_price: Decimal
    peak_price: Decimal
    bottom_price: Decimal
    target_end_price: Decimal
    
    @property
    def cycle_progress(self) -> float:
        """Progress through current cycle (0.0 to 1.0)."""
        return self.day_in_cycle / 7.0
    
    @property
    def total_growth(self) -> Decimal:
        """Total growth from cycle start."""
        if self.start_price == 0:
            return Decimal("0")
        return (self.current_price - self.start_price) / self.start_price * 100


@dataclass
class CycleParameters:
    """Parameters for a specific cycle number.
    
    Each cycle has decreasing volatility and growth multipliers,
    simulating market maturation over time.
    """
    
    cycle_number: int
    start_price: Decimal
    peak_multiplier: Decimal
    drawdown_percent: Decimal
    growth_percent: Decimal = Decimal("80")  # +80% each cycle
    
    @classmethod
    def for_cycle(cls, cycle_number: int) -> "CycleParameters":
        """Calculate parameters for given cycle number.
        
        Args:
            cycle_number: Cycle number starting from 1.
            
        Returns:
            CycleParameters with calculated values.
            
        Example:
            >>> params = CycleParameters.for_cycle(1)
            >>> params.start_price
            Decimal('100')
            >>> params.peak_multiplier
            Decimal('4.2')
        """
        # Start price grows 1.8x each cycle
        start = Decimal("100") * (Decimal("1.8") ** (cycle_number - 1))
        
        # Peak multiplier decreases each cycle (market matures)
        peak_mult = Decimal("4.5") - (Decimal("0.3") * cycle_number)
        peak_mult = max(peak_mult, Decimal("2.0"))  # Floor at 2x
        
        # Drawdown decreases each cycle
        drawdown = Decimal("70") - (Decimal("5") * (cycle_number - 1))
        drawdown = max(drawdown, Decimal("50"))  # Floor at 50%
        
        return cls(
            cycle_number=cycle_number,
            start_price=start.quantize(Decimal("0.01")),
            peak_multiplier=peak_mult.quantize(Decimal("0.01")),
            drawdown_percent=drawdown.quantize(Decimal("0.01")),
        )
    
    @property
    def peak_price(self) -> Decimal:
        """Calculate peak price for this cycle."""
        return (self.start_price * self.peak_multiplier).quantize(Decimal("0.01"))
    
    @property
    def bottom_price(self) -> Decimal:
        """Calculate bottom price after drawdown."""
        drawdown = self.drawdown_percent / 100
        return (self.peak_price * (1 - drawdown)).quantize(Decimal("0.01"))
    
    @property
    def end_price(self) -> Decimal:
        """Calculate end price (+80% from start)."""
        growth = self.growth_percent / 100
        return (self.start_price * (1 + growth)).quantize(Decimal("0.01"))
