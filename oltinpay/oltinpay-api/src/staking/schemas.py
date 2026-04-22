"""Staking schemas — on-chain view of OltinStaking contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StakingInfoResponse(BaseModel):
    """On-chain stake position for the current user.

    All amounts are uint256 wei serialized as strings (JS-safe).
    """

    model_config = ConfigDict(extra="forbid")

    wallet_address: str
    total_principal_wei: str
    unlocked_wei: str
    pending_reward_wei: str
    lot_count: int
    next_unlock_at: int
    apy_bps: int = 700  # mirrors OltinStaking.APY_BPS for UI convenience
    lock_period_days: int = 7
