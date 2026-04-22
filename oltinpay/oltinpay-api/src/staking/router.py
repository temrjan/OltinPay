"""Staking router — on-chain read-only.

State-changing actions (stake, unstake, claim, compound) are signed by
the user directly via viem in the web app — they hit the OltinStaking
contract on zkSync Sepolia without touching this backend.
"""

from fastapi import APIRouter

from src.auth.dependencies import CurrentUser
from src.staking import service
from src.staking.schemas import StakingInfoResponse

router = APIRouter()


@router.get("", response_model=StakingInfoResponse)
async def get_staking_info(current_user: CurrentUser) -> StakingInfoResponse:
    """Fetch the user's on-chain stake position."""
    return await service.get_staking_info(current_user.wallet_address)
