"""Unit tests for src.infrastructure.rpc pure helpers."""

from __future__ import annotations

import pytest

from src.infrastructure.rpc import decode_uint256, is_valid_address, pad_address


class TestIsValidAddress:
    @pytest.mark.parametrize(
        "address",
        [
            "0x0000000000000000000000000000000000000000",
            "0xa0A78aA9B9619fbc3bC12b5756442BD7A7D6779e",
            "0x" + "a" * 40,
            "0x" + "F" * 40,
        ],
    )
    def test_accepts_valid(self, address: str) -> None:
        assert is_valid_address(address) is True

    @pytest.mark.parametrize(
        "address",
        [
            "",
            "0x",
            "0xshort",
            "a0A78aA9B9619fbc3bC12b5756442BD7A7D6779e",  # missing 0x
            "0x" + "g" * 40,  # invalid hex char
            "0x" + "a" * 41,  # too long
            "0x" + "a" * 39,  # too short
            "0X" + "a" * 40,  # uppercase X
        ],
    )
    def test_rejects_invalid(self, address: str) -> None:
        assert is_valid_address(address) is False


class TestPadAddress:
    def test_pads_to_32_bytes(self) -> None:
        result = pad_address("0xa0A78aA9B9619fbc3bC12b5756442BD7A7D6779e")
        assert len(result) == 64
        assert result == "000000000000000000000000a0a78aa9b9619fbc3bc12b5756442bd7a7d6779e"

    def test_lowercases_hex(self) -> None:
        upper = pad_address("0x" + "A" * 40)
        lower = pad_address("0x" + "a" * 40)
        assert upper == lower

    def test_raises_on_invalid(self) -> None:
        with pytest.raises(ValueError, match="Invalid EVM address"):
            pad_address("not-an-address")


class TestDecodeUint256:
    @pytest.mark.parametrize(
        ("hex_value", "expected"),
        [
            ("0x", 0),
            ("", 0),
            ("0x0", 0),
            ("0x00", 0),
            ("0x1", 1),
            ("0xff", 255),
            (
                "0x0000000000000000000000000000000000000000000000000de0b6b3a7640000",
                10**18,
            ),
            (
                "0x" + "f" * 64,  # max uint256
                2**256 - 1,
            ),
        ],
    )
    def test_decodes(self, hex_value: str, expected: int) -> None:
        assert decode_uint256(hex_value) == expected
