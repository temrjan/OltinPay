"""Staking service — reads live from the OltinStaking contract.

All state-changing actions (stake, unstake, claim, compound) are
performed by the user client-side via viem — the backend is read-only.
"""

from __future__ import annotations

from src.common.exceptions import BadRequestException
from src.infrastructure.blockchain import get_stake_info
from src.staking.schemas import StakingInfoResponse


async def get_staking_info(wallet_address: str | None) -> StakingInfoResponse:
    """Fetch on-chain stake info for the user's wallet."""
    if not wallet_address:
        raise BadRequestException(
            "Wallet address not registered. Complete onboarding first."
        )

    wallet = wallet_address.lower()
    stake = await get_stake_info(wallet)
    return StakingInfoResponse(
        wallet_address=wallet,
        total_principal_wei=str(stake.total_principal),
        unlocked_wei=str(stake.unlocked),
        pending_reward_wei=str(stake.pending),
        lot_count=stake.lot_count,
        next_unlock_at=stake.next_unlock_at,
    )
