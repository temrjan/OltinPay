// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "./interfaces/AggregatorV3Interface.sol";

/**
 * @title Attestor
 * @notice Minimal, Chainlink-compatible push oracle. One code, three instances:
 *         ReserveAttestor (decimals 0), XauUsdFeed (decimals 8),
 *         UzsUsdFeed (decimals 8).
 *
 * @dev Implements {AggregatorV3Interface} so on-chain consumers can be pointed
 *      at either this Attestor (testnet / bootstrap) or a native Chainlink feed
 *      (mainnet) without code changes.
 *
 *      SECURITY — self-stamped timestamps: {postAnswer} takes ONLY the answer.
 *      It stamps `updatedAt = block.timestamp` itself; the POSTER can never
 *      backdate or forward-date a reading. This is what makes the consumers'
 *      `block.timestamp - updatedAt <= maxAge` staleness guards trustworthy.
 */
contract Attestor is AccessControl, AggregatorV3Interface {
    bytes32 public constant POSTER_ROLE = keccak256("POSTER_ROLE");

    /// @dev Immutable feed precision, set once at construction.
    uint8 private immutable _decimals;

    int256 private _answer;
    uint256 private _updatedAt;
    uint80 private _roundId;

    event AnswerPosted(uint80 indexed roundId, int256 answer, uint256 updatedAt);

    /**
     * @param decimals_ Number of decimals this feed reports (0 for a raw
     *                  gram-count reserve feed, 8 for USD-quoted price feeds).
     */
    constructor(uint8 decimals_) {
        _decimals = decimals_;
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(POSTER_ROLE, msg.sender);
    }

    /**
     * @notice Publish a new reading. Only a POSTER may call.
     * @dev Self-stamps `updatedAt = block.timestamp` and bumps a monotonic
     *      round id. The poster does NOT (and cannot) pass a timestamp.
     */
    function postAnswer(int256 answer_) external onlyRole(POSTER_ROLE) {
        _roundId += 1;
        _answer = answer_;
        _updatedAt = block.timestamp;
        emit AnswerPosted(_roundId, answer_, block.timestamp);
    }

    /// @inheritdoc AggregatorV3Interface
    function decimals() external view override returns (uint8) {
        return _decimals;
    }

    /// @inheritdoc AggregatorV3Interface
    function latestRoundData()
        external
        view
        override
        returns (
            uint80 roundId,
            int256 answer,
            uint256 startedAt,
            uint256 updatedAt,
            uint80 answeredInRound
        )
    {
        return (_roundId, _answer, _updatedAt, _updatedAt, _roundId);
    }
}
