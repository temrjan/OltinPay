"""Balance Pydantic schemas.

On-chain model: balances are read live from zkSync Era contracts via
RPC. Values are raw wei (uint256) — serialized as strings because JSON
numbers don't safely hold >2^53.
"""

from pydantic import BaseModel, ConfigDict


class WalletBalances(BaseModel):
    """ERC20 balances held by the user's EOA."""

    oltin_wei: str
    uzd_wei: str


class StakingBalances(BaseModel):
    """On-chain staking position (OltinStaking.getStakeInfo)."""

    total_principal_wei: str
    unlocked_wei: str
    pending_reward_wei: str
    lot_count: int
    next_unlock_at: int  # unix seconds; 0 = nothing locked


class BalancesResponse(BaseModel):
    """Snapshot of all user balances, all on-chain."""

    model_config = ConfigDict(extra="forbid")

    wallet_address: str
    wallet: WalletBalances
    staking: StakingBalances
