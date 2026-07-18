// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../interfaces/AggregatorV3Interface.sol";

/**
 * @title MockAttestor
 * @notice TEST-ONLY oracle whose decimals, answer and updatedAt are fully
 *         settable — including pathological values the real {Attestor} can
 *         never produce (e.g. a future-dated `updatedAt`, or decimals > 18).
 *         Used to exercise the consumers' guards.
 */
contract MockAttestor is AggregatorV3Interface {
    uint8 private _decimals;
    int256 private _answer;
    uint256 private _updatedAt;
    uint80 private _roundId;

    constructor(uint8 decimals_, int256 answer_, uint256 updatedAt_) {
        _decimals = decimals_;
        _answer = answer_;
        _updatedAt = updatedAt_;
        _roundId = 1;
    }

    function setAnswer(int256 answer_) external {
        _answer = answer_;
        _roundId += 1;
    }

    function setUpdatedAt(uint256 updatedAt_) external {
        _updatedAt = updatedAt_;
    }

    function set(int256 answer_, uint256 updatedAt_) external {
        _answer = answer_;
        _updatedAt = updatedAt_;
        _roundId += 1;
    }

    function decimals() external view override returns (uint8) {
        return _decimals;
    }

    function latestRoundData()
        external
        view
        override
        returns (uint80, int256, uint256, uint256, uint80)
    {
        return (_roundId, _answer, _updatedAt, _updatedAt, _roundId);
    }
}
