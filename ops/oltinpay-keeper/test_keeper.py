"""Unit tests for the feed keeper's pure helpers (encoding + post decision).

Import-safe: keeper.py imports eth_account lazily, so these run without the
signing dependency. On-chain behaviour is covered by the staging run on 7demo.

Run:  python -m pytest test_keeper.py -q
"""

import keeper


class TestEncodeInt256:
    def test_zero(self):
        assert keeper.encode_int256(0) == "0" * 64

    def test_one(self):
        assert keeper.encode_int256(1) == "0" * 63 + "1"

    def test_minus_one_is_twos_complement(self):
        assert keeper.encode_int256(-1) == "f" * 64

    def test_xau_style_value(self):
        # 4050.545 * 1e8 (8 decimals) — a realistic frozen XAU answer.
        value = 405054500000
        assert keeper.encode_int256(value) == "%064x" % value

    def test_round_trip_signed(self):
        for value in (0, 1, -1, 42, -42, 405054500000, -(2 ** 200), 2 ** 200):
            assert keeper.decode_int256(keeper.encode_int256(value)) == value

    def test_out_of_range_raises(self):
        for value in (2 ** 255, -(2 ** 255) - 1):
            try:
                keeper.encode_int256(value)
            except ValueError:
                pass
            else:
                raise AssertionError(f"expected ValueError for {value}")


class TestDecodeInt256:
    def test_all_f_is_minus_one(self):
        assert keeper.decode_int256("f" * 64) == -1

    def test_zero(self):
        assert keeper.decode_int256("0" * 64) == 0

    def test_positive_word(self):
        assert keeper.decode_int256("%064x" % 12345) == 12345


class TestEncodePostAnswer:
    def test_selector_prefix_and_length(self):
        calldata = keeper.encode_post_answer(405054500000)
        assert calldata.startswith("0xd7fc7b18")
        # 0x + 8 selector hex + 64 arg hex
        assert len(calldata) == 2 + 8 + 64

    def test_encodes_negative_answer(self):
        assert keeper.encode_post_answer(-1) == "0xd7fc7b18" + "f" * 64


class TestDecide:
    def test_post_when_older_than_heartbeat(self):
        assert keeper.decide(age=2000, heartbeat=1500) == "POST"

    def test_skip_when_fresher_than_heartbeat(self):
        assert keeper.decide(age=1000, heartbeat=1500) == "SKIP"

    def test_boundary_posts(self):
        # exactly at heartbeat -> POST (never let it drift past)
        assert keeper.decide(age=1500, heartbeat=1500) == "POST"
