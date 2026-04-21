"""Balances router — on-chain read-only."""

from fastapi import APIRouter

from src.auth.dependencies import CurrentUser
from src.balances import service
from src.balances.schemas import BalancesResponse

router = APIRouter()


@router.get("", response_model=BalancesResponse)
async def get_balances(current_user: CurrentUser) -> BalancesResponse:
    """Read the current user's balances from zkSync Era.

    The result contains raw uint256 wei values (as strings) for OLTIN
    and UZD held by the user's EOA, plus their staking position
    (principal, unlocked portion, pending reward, lot count, next unlock
    timestamp).
    """
    return await service.get_user_balances(current_user.wallet_address)
