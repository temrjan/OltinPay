// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title AggregatorV3Interface
 * @notice Local, minimal copy of the canonical Chainlink price-feed interface.
 * @dev We intentionally do NOT add the @chainlink npm dependency. The tuple
 *      order and types below MUST match Chainlink exactly so that swapping our
 *      {Attestor} for a native Chainlink feed on mainnet is a drop-in change
 *      for every consumer ({OltinTokenV3}, {Exchange}).
 *
 *      Chainlink `latestRoundData` returns:
 *        (uint80 roundId, int256 answer, uint256 startedAt,
 *         uint256 updatedAt, uint80 answeredInRound)
 */
interface AggregatorV3Interface {
    /// @notice Number of decimals in the answer (e.g. 8 for USD-quoted feeds).
    function decimals() external view returns (uint8);

    /// @notice Data of the latest round.
    function latestRoundData()
        external
        view
        returns (
            uint80 roundId,
            int256 answer,
            uint256 startedAt,
            uint256 updatedAt,
            uint80 answeredInRound
        );
}
