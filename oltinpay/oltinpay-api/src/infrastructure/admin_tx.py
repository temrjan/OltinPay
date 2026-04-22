"""Admin-signed EIP-1559 transactions on zkSync Era Sepolia.

Used exclusively by privileged server-side operations (welcome bonus
mint). The admin private key is loaded from `settings.admin_private_key`
and never persisted to disk or logs. eth-account is the only dep —
no full web3.py.

zkSync Era accepts plain EIP-1559 transactions from EOAs — no custom
EIP-712 serialization needed for externally-owned accounts. The native
account-abstraction features (paymasters, custom nonces) are only
required for smart-account senders.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx
from eth_account import Account

from src.config import settings
from src.infrastructure.rpc import eth_call, is_valid_address, pad_address

if TYPE_CHECKING:
    from eth_account.signers.local import LocalAccount

logger = logging.getLogger(__name__)

# ERC20 mint(address,uint256) selector
MINT_SELECTOR = "0x40c10f19"


class AdminUnconfigured(RuntimeError):
    """Raised when ADMIN_PRIVATE_KEY is not set."""


class AdminTxError(RuntimeError):
    """Raised when the signed transaction could not be broadcast."""


def _load_admin_account() -> LocalAccount:
    if settings.admin_private_key is None:
        raise AdminUnconfigured(
            "ADMIN_PRIVATE_KEY is not configured on the server."
        )
    account: LocalAccount = Account.from_key(
        settings.admin_private_key.get_secret_value()
    )
    return account


def _encode_uint256(value: int) -> str:
    if value < 0 or value >= 2**256:
        raise ValueError(f"Value out of uint256 range: {value}")
    return f"{value:064x}"


def encode_mint_calldata(to: str, amount_wei: int) -> str:
    """Build ERC20.mint(address, uint256) calldata for zkSync transactions."""
    if not is_valid_address(to):
        raise ValueError(f"Invalid recipient address: {to}")
    return "0x" + MINT_SELECTOR[2:] + pad_address(to) + _encode_uint256(amount_wei)


async def _rpc(method: str, params: list[object], client: httpx.AsyncClient) -> object:
    response = await client.post(
        settings.zksync_rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    )
    response.raise_for_status()
    body = response.json()
    if "error" in body:
        raise AdminTxError(f"{method}: {body['error']}")
    return body.get("result")


async def send_admin_mint(
    contract: str, recipient: str, amount_wei: int
) -> str:
    """Admin-sign and broadcast UZD.mint(recipient, amount_wei).

    Returns the transaction hash. Raises AdminUnconfigured if the admin
    key is missing, AdminTxError on RPC failures.
    """
    account = _load_admin_account()
    data = encode_mint_calldata(recipient, amount_wei)

    async with httpx.AsyncClient(timeout=15.0) as client:
        nonce_hex = await _rpc("eth_getTransactionCount", [account.address, "pending"], client)
        gas_price_hex = await _rpc("eth_gasPrice", [], client)
        if not isinstance(nonce_hex, str) or not isinstance(gas_price_hex, str):
            raise AdminTxError("Unexpected RPC response for nonce/gasPrice")
        base_fee = int(gas_price_hex, 16)

        est_hex = await _rpc(
            "eth_estimateGas",
            [{"from": account.address, "to": contract, "data": data}],
            client,
        )
        if not isinstance(est_hex, str):
            raise AdminTxError("Unexpected RPC response for estimateGas")
        # 20% headroom — EraVM estimation is usually tight but can spike
        # if the contract takes a different branch at execution time.
        gas_limit = int(est_hex, 16) * 12 // 10

        priority_hex = await _rpc("eth_maxPriorityFeePerGas", [], client)
        max_priority = (
            int(priority_hex, 16) if isinstance(priority_hex, str) else 0
        )
        # Standard Ethereum formula: ensures inclusion even if base_fee doubles.
        max_fee = base_fee * 2 + max_priority

        tx = {
            "chainId": settings.zksync_chain_id,
            "nonce": int(nonce_hex, 16),
            "to": contract,
            "value": 0,
            "data": data,
            "gas": gas_limit,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority,
            "type": 2,
        }
        signed = account.sign_transaction(tx)  # type: ignore[arg-type]
        raw_hex = "0x" + signed.raw_transaction.hex()

        tx_hash = await _rpc("eth_sendRawTransaction", [raw_hex], client)
        if not isinstance(tx_hash, str):
            raise AdminTxError(f"Unexpected sendRawTransaction result: {tx_hash!r}")

    logger.info("admin_mint_sent contract=%s to=%s amount=%s tx=%s",
                contract, recipient, amount_wei, tx_hash)
    return tx_hash


# eth_call is re-exported for convenience, keeping one import surface for
# welcome/service.py to check existing UZD balances if ever needed.
__all__ = [
    "AdminTxError",
    "AdminUnconfigured",
    "encode_mint_calldata",
    "eth_call",
    "send_admin_mint",
]
