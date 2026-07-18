"""Read-only contract views for PoR, rates, quotes and the chain indexer.

Greenfield helpers built on ``rpc.py`` (eth_call / decode_uint256 / pad_address
/ rpc_request). Covers the Chainlink-style AggregatorV3 ``latestRoundData`` and
``decimals``, ERC20 ``totalSupply``, plus ``eth_getLogs`` / ``eth_blockNumber``
for the indexer. httpx-based, read-only, no web3.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.infrastructure.rpc import RpcError, decode_uint256, eth_call, rpc_request

if TYPE_CHECKING:
    import httpx

# Function selectors (first 4 bytes of keccak256 of the signature).
LATEST_ROUND_DATA_SELECTOR = "0xfeaf968c"  # latestRoundData()
DECIMALS_SELECTOR = "0x313ce567"  # decimals()
TOTAL_SUPPLY_SELECTOR = "0x18160ddd"  # totalSupply()


@dataclass(slots=True)
class RoundData:
    """A Chainlink-style AggregatorV3 ``latestRoundData`` tuple."""

    round_id: int
    answer: int  # signed int256
    started_at: int
    updated_at: int
    answered_in_round: int


def _decode_int256_word(word: str) -> int:
    """Decode a 32-byte hex word as a two's-complement signed int256."""
    value = int(word, 16)
    return value - 2**256 if value >= 2**255 else value


async def latest_round_data(
    feed: str, *, client: httpx.AsyncClient | None = None
) -> RoundData:
    """Read ``feed.latestRoundData()`` and decode the 5-word tuple."""
    raw = await eth_call(feed, LATEST_ROUND_DATA_SELECTOR, client=client)
    body = raw[2:] if raw.startswith("0x") else raw
    if len(body) < 64 * 5:
        return RoundData(0, 0, 0, 0, 0)
    words = [body[i : i + 64] for i in range(0, 64 * 5, 64)]
    return RoundData(
        round_id=int(words[0], 16),
        answer=_decode_int256_word(words[1]),
        started_at=int(words[2], 16),
        updated_at=int(words[3], 16),
        answered_in_round=int(words[4], 16),
    )


async def feed_decimals(feed: str, *, client: httpx.AsyncClient | None = None) -> int:
    """Read ``feed.decimals()``."""
    raw = await eth_call(feed, DECIMALS_SELECTOR, client=client)
    return decode_uint256(raw)


async def total_supply(token: str, *, client: httpx.AsyncClient | None = None) -> int:
    """Read ERC20 ``token.totalSupply()`` (wei)."""
    raw = await eth_call(token, TOTAL_SUPPLY_SELECTOR, client=client)
    return decode_uint256(raw)


async def block_number(*, client: httpx.AsyncClient | None = None) -> int:
    """Current chain head block number."""
    raw = await rpc_request("eth_blockNumber", [], client=client)
    if not isinstance(raw, str):
        raise RpcError(f"Unexpected eth_blockNumber response: {raw!r}")
    return int(raw, 16)


async def get_logs(
    *,
    from_block: int,
    to_block: int,
    address: str | list[str],
    topics: list[Any],
    client: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    """Fetch logs via ``eth_getLogs``.

    ``topics`` follows the JSON-RPC shape: a positional list where each slot is
    a single topic hash, a list of alternatives (OR), or ``None`` (wildcard).
    """
    params = [
        {
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
            "address": address,
            "topics": topics,
        }
    ]
    result = await rpc_request("eth_getLogs", params, client=client)
    if not isinstance(result, list):
        return []
    return [log for log in result if isinstance(log, dict)]
