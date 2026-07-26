"""Guard: the contract-address defaults must stay pinned to the canonical V3.1
deployment (docs/DEPLOYMENTS.md).

A default silently pointing at a retired contract shipped once already —
STAKING_CONTRACT_ADDRESS defaulted to the V2-bound 0x63e537A3 and was caught
only in review, not by CI. This test turns that class of drift into a red run.
"""

from __future__ import annotations

from pydantic import SecretStr

from src.config import Settings

# Canonical addresses — docs/DEPLOYMENTS.md (V3.1 money edge + V3-bound staking).
CANONICAL_DEFAULTS = {
    "oltin_contract_address": "0x906bcf6c92ed1b30aA453c69eB40aeDbb3d5B3A5",
    "uzd_contract_address": "0x51232fd0065bD2ca50551761Acef476E3CDf02aA",
    "staking_contract_address": "0xD3b6ffd1dE409e1C37BA5B867d6eC3897A721fAa",
    "exchange_address": "0x99D733E64eb60c3B3D5f3DeDe4CC4adC92BCd1c9",
    "reserve_attestor_address": "0x9413F60295dcf7D81fcb69eE256029900B107d1B",
    "xau_feed_address": "0xe0AFc7eD0c6028b8172C2b108624168d235e8BFD",
    "uzs_feed_address": "0x637347fd661cFFAE9B562aFA394A392214fa24aD",
}

# The address the staking default regressed to — immutably bound to the V2 token
# (docs/DEPLOYMENTS.md). Must never be the default again.
RETIRED_STAKING_V2 = "0x63e537A3a150d06035151E29904C1640181C8314"


def test_contract_address_defaults_are_canonical() -> None:
    settings = Settings(
        _env_file=None,
        secret_key=SecretStr("test"),
        database_url="postgresql+asyncpg://t:t@localhost/t",
    )
    for field, expected in CANONICAL_DEFAULTS.items():
        assert getattr(settings, field) == expected, (
            f"{field} default drifted from docs/DEPLOYMENTS.md"
        )
    assert settings.staking_contract_address != RETIRED_STAKING_V2
