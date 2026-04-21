"""Balance service — reads live from zkSync Era contracts.

The backend does not store balances anymore. All reads go through RPC.
A single httpx.AsyncClient is reused across the three concurrent calls
(OLTIN, UZD, staking) so one request to `/balances` is one connection.
"""

from __future__ import annotations

import asyncio

import httpx

from src.balances.schemas import BalancesResponse, StakingBalances, WalletBalances
from src.common.exceptions import BadRequestException
from src.infrastructure.blockchain import (
    get_oltin_balance,
    get_stake_info,
    get_uzd_balance,
)


async def get_user_balances(wallet_address: str | None) -> BalancesResponse:
    """Read on-chain balances for the user's wallet.

    Raises BadRequestException if the user hasn't completed onboarding
    yet (no wallet_address bound). The three RPC calls run concurrently.
    """
    if not wallet_address:
        raise BadRequestException("Wallet address not registered. Complete onboarding.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        oltin_wei, uzd_wei, stake = await asyncio.gather(
            get_oltin_balance(wallet_address, client=client),
            get_uzd_balance(wallet_address, client=client),
            get_stake_info(wallet_address, client=client),
        )

    return BalancesResponse(
        wallet_address=wallet_address,
        wallet=WalletBalances(
            oltin_wei=str(oltin_wei),
            uzd_wei=str(uzd_wei),
        ),
        staking=StakingBalances(
            total_principal_wei=str(stake.total_principal),
            unlocked_wei=str(stake.unlocked),
            pending_reward_wei=str(stake.pending),
            lot_count=stake.lot_count,
            next_unlock_at=stake.next_unlock_at,
        ),
    )
