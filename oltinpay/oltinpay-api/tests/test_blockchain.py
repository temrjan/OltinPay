"""Tests for src.infrastructure.blockchain.

Uses respx to intercept the single HTTP POST that eth_call makes.
Verifies both happy path and the ABI decoding of the 5-tuple returned
by getStakeInfo.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from src.config import settings
from src.infrastructure.blockchain import (
    get_oltin_balance,
    get_stake_info,
    get_uzd_balance,
)

ADDRESS = "0xa0A78aA9B9619fbc3bC12b5756442BD7A7D6779e"


def _uint256(n: int) -> str:
    """Return a zero-padded 32-byte hex word (no 0x prefix)."""
    return f"{n:064x}"


def _rpc_result(hex_body: str) -> dict[str, object]:
    return {"jsonrpc": "2.0", "id": 1, "result": "0x" + hex_body}


@pytest.mark.asyncio
async def test_get_oltin_balance_returns_wei() -> None:
    expected_wei = 7 * 10**18
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url=settings.zksync_rpc_url) as mock:
            mock.post("").mock(
                return_value=httpx.Response(200, json=_rpc_result(_uint256(expected_wei)))
            )
            result = await get_oltin_balance(ADDRESS, client=client)
    assert result == expected_wei


@pytest.mark.asyncio
async def test_get_uzd_balance_returns_wei() -> None:
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url=settings.zksync_rpc_url) as mock:
            mock.post("").mock(
                return_value=httpx.Response(200, json=_rpc_result(_uint256(1000 * 10**18)))
            )
            result = await get_uzd_balance(ADDRESS, client=client)
    assert result == 1000 * 10**18


@pytest.mark.asyncio
async def test_get_stake_info_decodes_five_uint256_words() -> None:
    principal = 100 * 10**18
    unlocked = 40 * 10**18
    pending = 5 * 10**17  # 0.5 OLTIN
    lot_count = 3
    next_unlock = 1_761_000_000
    body = (
        _uint256(principal)
        + _uint256(unlocked)
        + _uint256(pending)
        + _uint256(lot_count)
        + _uint256(next_unlock)
    )

    async with httpx.AsyncClient() as client:
        with respx.mock(base_url=settings.zksync_rpc_url) as mock:
            mock.post("").mock(return_value=httpx.Response(200, json=_rpc_result(body)))
            stake = await get_stake_info(ADDRESS, client=client)

    assert stake.total_principal == principal
    assert stake.unlocked == unlocked
    assert stake.pending == pending
    assert stake.lot_count == lot_count
    assert stake.next_unlock_at == next_unlock


@pytest.mark.asyncio
async def test_get_stake_info_handles_empty_response() -> None:
    """Fresh address with no stake returns '0x' — decoder must yield zeros."""
    async with httpx.AsyncClient() as client:
        with respx.mock(base_url=settings.zksync_rpc_url) as mock:
            mock.post("").mock(return_value=httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": "0x"}))
            stake = await get_stake_info(ADDRESS, client=client)

    assert stake.total_principal == 0
    assert stake.unlocked == 0
    assert stake.pending == 0
    assert stake.lot_count == 0
    assert stake.next_unlock_at == 0


@pytest.mark.asyncio
async def test_balance_fails_on_invalid_address() -> None:
    with pytest.raises(ValueError, match="Invalid EVM address"):
        await get_oltin_balance("not-a-valid-address")
