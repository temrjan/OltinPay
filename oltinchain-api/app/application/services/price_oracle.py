"""Price Oracle service for OLTIN price generation.

Generates price based on Wyckoff market cycles with Bitcoin-like behavior.
1 week = 1 Bitcoin year. Each cycle: accumulation → markup → distribution → markdown.

Key principles:
- Higher lows: each cycle ends higher than previous
- Decreasing volatility: market matures over time
- Organic movement: Geometric Brownian Motion for realistic noise
"""

import math
import random
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol

import structlog

from app.domain.models.price_cycle import (
    CycleParameters,
    CyclePhase,
    CycleState,
    PHASE_CONFIGS,
    PhaseConfig,
)

logger = structlog.get_logger()

# Genesis timestamp: when OLTIN trading started
GENESIS_TIMESTAMP = datetime(2025, 12, 29, 0, 0, 0, tzinfo=timezone.utc)
CYCLE_DURATION_DAYS = 7.0
SECONDS_PER_DAY = 86400


class PriceStorageProtocol(Protocol):
    """Protocol for price persistence."""
    
    async def get_last_price(self) -> Decimal | None:
        """Get last stored price."""
        ...
    
    async def save_price(self, price: Decimal, timestamp: datetime) -> None:
        """Save price snapshot."""
        ...


class PriceOracle:
    """Price oracle that generates OLTIN price based on market cycles.
    
    The oracle uses deterministic cycle calculation combined with
    stochastic noise to generate realistic price movements.
    
    Attributes:
        genesis: Starting timestamp for cycle calculation.
        cycle_days: Duration of one full cycle in days.
    """
    
    def __init__(
        self,
        genesis: datetime | None = None,
        cycle_days: float = CYCLE_DURATION_DAYS,
    ) -> None:
        """Initialize price oracle.
        
        Args:
            genesis: Start time for cycles. Defaults to GENESIS_TIMESTAMP.
            cycle_days: Days per cycle. Defaults to 7 (1 week).
        """
        self.genesis = genesis or GENESIS_TIMESTAMP
        self.cycle_days = cycle_days
        self._last_price: Decimal | None = None
        self._last_update: datetime | None = None
    
    def get_current_cycle_state(self, now: datetime | None = None) -> CycleState:
        """Calculate current cycle state based on time.
        
        Args:
            now: Current timestamp. Defaults to UTC now.
            
        Returns:
            CycleState with all current cycle information.
        """
        now = now or datetime.now(timezone.utc)
        
        # Calculate days since genesis
        delta = now - self.genesis
        total_days = delta.total_seconds() / SECONDS_PER_DAY
        
        # Calculate cycle number and position
        cycle_number = int(total_days / self.cycle_days) + 1
        day_in_cycle = total_days % self.cycle_days
        
        # Get cycle parameters
        params = CycleParameters.for_cycle(cycle_number)
        
        # Determine current phase
        phase = self._get_phase_for_day(day_in_cycle)
        
        # Calculate current target price
        target_price = self._calculate_target_price(
            day_in_cycle=day_in_cycle,
            params=params,
        )
        
        return CycleState(
            cycle_number=cycle_number,
            phase=phase,
            day_in_cycle=round(day_in_cycle, 4),
            start_price=params.start_price,
            current_price=target_price,
            peak_price=params.peak_price,
            bottom_price=params.bottom_price,
            target_end_price=params.end_price,
        )
    
    def get_price(self, now: datetime | None = None) -> Decimal:
        """Get current OLTIN price with noise.
        
        Combines deterministic cycle position with stochastic noise
        for realistic price movement.
        
        Args:
            now: Current timestamp. Defaults to UTC now.
            
        Returns:
            Current price in USD.
        """
        now = now or datetime.now(timezone.utc)
        state = self.get_current_cycle_state(now)
        
        # Add noise based on current phase volatility
        noise = self._generate_noise(state.phase)
        noisy_price = state.current_price * (1 + noise)
        
        # Ensure price stays positive
        final_price = max(noisy_price, Decimal("0.01"))
        final_price = final_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        logger.debug(
            "price_generated",
            cycle=state.cycle_number,
            phase=state.phase.value,
            day=state.day_in_cycle,
            target_price=str(state.current_price),
            final_price=str(final_price),
            noise=f"{noise:.4f}",
        )
        
        self._last_price = final_price
        self._last_update = now
        
        return final_price
    
    def get_price_with_spread(
        self,
        now: datetime | None = None,
        spread_percent: Decimal = Decimal("1.0"),
    ) -> tuple[Decimal, Decimal, Decimal]:
        """Get price with bid/ask spread.
        
        Args:
            now: Current timestamp.
            spread_percent: Total spread percentage (default 1%).
            
        Returns:
            Tuple of (mid_price, bid_price, ask_price).
        """
        mid = self.get_price(now)
        half_spread = spread_percent / 200  # Half spread as decimal
        
        bid = (mid * (1 - half_spread)).quantize(Decimal("0.01"))
        ask = (mid * (1 + half_spread)).quantize(Decimal("0.01"))
        
        return mid, bid, ask
    
    def _get_phase_for_day(self, day_in_cycle: float) -> CyclePhase:
        """Determine which phase based on day position."""
        for config in PHASE_CONFIGS:
            if config.start_day <= day_in_cycle < config.end_day:
                return config.name
        return CyclePhase.RE_ACCUMULATION
    
    def _get_phase_config(self, day_in_cycle: float) -> PhaseConfig:
        """Get phase configuration for given day."""
        for config in PHASE_CONFIGS:
            if config.start_day <= day_in_cycle < config.end_day:
                return config
        return PHASE_CONFIGS[-1]
    
    def _calculate_target_price(
        self,
        day_in_cycle: float,
        params: CycleParameters,
    ) -> Decimal:
        """Calculate target price for given day in cycle.
        
        Uses linear interpolation within each phase.
        """
        config = self._get_phase_config(day_in_cycle)
        
        # Calculate progress within phase
        phase_duration = config.end_day - config.start_day
        phase_progress = (day_in_cycle - config.start_day) / phase_duration
        phase_progress = min(max(phase_progress, 0.0), 1.0)
        
        # Interpolate price multiplier
        mult_range = config.price_mult_end - config.price_mult_start
        current_mult = config.price_mult_start + (mult_range * phase_progress)
        
        # Adjust multipliers based on cycle number
        cycle_adjustment = self._get_cycle_adjustment(
            params.cycle_number,
            config.name,
        )
        adjusted_mult = current_mult * cycle_adjustment
        
        target = params.start_price * Decimal(str(adjusted_mult))
        return target.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    def _get_cycle_adjustment(
        self,
        cycle_number: int,
        phase: CyclePhase,
    ) -> float:
        """Adjust multipliers based on cycle maturity.
        
        Later cycles have lower peaks and smaller drawdowns.
        """
        if cycle_number == 1:
            return 1.0
        
        # Reduce peak multipliers for later cycles
        if phase in (CyclePhase.MARKUP, CyclePhase.DISTRIBUTION):
            return 1.0 - (0.05 * (cycle_number - 1))
        
        # Reduce drawdown depth for later cycles
        if phase in (CyclePhase.MARKDOWN, CyclePhase.CAPITULATION):
            return 1.0 + (0.03 * (cycle_number - 1))
        
        return 1.0
    
    def _generate_noise(self, phase: CyclePhase) -> Decimal:
        """Generate price noise based on phase volatility.
        
        Uses Geometric Brownian Motion for realistic noise.
        """
        config = next(c for c in PHASE_CONFIGS if c.name == phase)
        volatility = config.volatility
        
        # GBM noise component
        z = random.gauss(0, 1)
        noise = volatility * z
        
        # Clamp noise to prevent extreme moves
        max_move = volatility * 3
        noise = max(min(noise, max_move), -max_move)
        
        return Decimal(str(noise))


# Singleton instance
_oracle: PriceOracle | None = None


def get_price_oracle() -> PriceOracle:
    """Get or create singleton price oracle instance."""
    global _oracle
    if _oracle is None:
        _oracle = PriceOracle()
    return _oracle
