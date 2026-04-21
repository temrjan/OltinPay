"""High-level blockchain reads for OltinPay contracts on zkSync Sepolia.

All operations are read-only — the backend never signs user transactions
(non-custodial model). The admin may mint UZD for welcome bonuses in a
separate admin-only flow (not in this module).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.config import settings
from src.infrastructure.rpc import decode_uint256, eth_call, pad_address

if TYPE_CHECKING:
    import httpx

# Function selectors (first 4 bytes of keccak256 of the function signature)
BALANCE_OF_SELECTOR = "0x70a08231"
GET_STAKE_INFO_SELECTOR = "0xc3453153"  # getStakeInfo(address)


@dataclass(slots=True)
class StakeInfo:
    """On-chain staking position returned by OltinStaking.getStakeInfo."""

    total_principal: int
    unlocked: int
    pending: int
    lot_count: int
    next_unlock_at: int


async def _erc20_balance_of(
    contract: str, address: str, client: httpx.AsyncClient | None = None
) -> int:
    """Call ERC20.balanceOf(address) and return raw wei as int."""
    data = BALANCE_OF_SELECTOR + pad_address(address)
    raw = await eth_call(contract, data, client=client)
    return decode_uint256(raw)


async def get_oltin_balance(
    address: str, client: httpx.AsyncClient | None = None
) -> int:
    """OLTIN balance (wei) for a given address."""
    return await _erc20_balance_of(
        settings.oltin_contract_address, address, client=client
    )


async def get_uzd_balance(
    address: str, client: httpx.AsyncClient | None = None
) -> int:
    """UZD balance (wei) for a given address."""
    return await _erc20_balance_of(
        settings.uzd_contract_address, address, client=client
    )


async def get_stake_info(
    address: str, client: httpx.AsyncClient | None = None
) -> StakeInfo:
    """Fetch on-chain stake info for the user.

    Returns a StakeInfo with integer wei values. Shape matches
    `OltinStaking.getStakeInfo(address)` — 5 uint256 outputs, ABI-encoded
    as five 32-byte words concatenated.
    """
    data = GET_STAKE_INFO_SELECTOR + pad_address(address)
    raw = await eth_call(settings.staking_contract_address, data, client=client)
    body = raw[2:] if raw.startswith("0x") else raw
    if len(body) < 64 * 5:
        return StakeInfo(0, 0, 0, 0, 0)
    words = [body[i : i + 64] for i in range(0, 64 * 5, 64)]
    return StakeInfo(
        total_principal=int(words[0], 16),
        unlocked=int(words[1], 16),
        pending=int(words[2], 16),
        lot_count=int(words[3], 16),
        next_unlock_at=int(words[4], 16),
    )
