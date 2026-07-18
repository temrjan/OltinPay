// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "./interfaces/AggregatorV3Interface.sol";

/**
 * @title OltinToken V3 (Proof-of-Reserve, non-custodial)
 * @notice Gold-backed ERC20. 1 OLTIN == 1 gram of attested gold reserve.
 *
 * @dev Redesign vs V2 — the custodial anti-patterns are REMOVED:
 *        - NO BURNER_ROLE and NO admin/arbitrary-holder burn. Burning is only
 *          via the public, allowance-gated {ERC20Burnable-burnFrom} / {burn}.
 *        - NO adminTransfer (users' balances can never be moved by an admin).
 *        - MINTER_ROLE is granted to the {Exchange} ONLY (in the deploy script),
 *          never to the deployer, so every mint passes the reserve guard.
 *
 *      Secure-Mint (Proof-of-Reserve): {mint} reads a Chainlink-compatible
 *      reserve feed and refuses to mint beyond the attested reserve, refuses a
 *      non-positive reserve, and refuses a stale (or future-dated) reading.
 *
 *      `transferFeeBps` is stored and settable but DORMANT in this release:
 *      {_update} does NOT siphon a fee. It exists for a future fee activation.
 */
contract OltinTokenV3 is ERC20, ERC20Burnable, AccessControl, Pausable {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    /// @notice Reserve proof feed (attested grams of gold, see {reserveDecimals}).
    AggregatorV3Interface public immutable reserveFeed;
    /// @notice Cached decimals of {reserveFeed}, validated <= 18 at construction.
    uint8 public immutable reserveDecimals;
    /// @notice Max age (seconds) a reserve reading may have before it is stale.
    uint256 public immutable maxAgeReserve;

    /// @notice DORMANT in this release — stored/settable but not applied.
    uint256 public transferFeeBps = 50;
    /// @notice DORMANT fee sink (unused while {transferFeeBps} is dormant).
    address public feeCollector;

    event Minted(address indexed to, uint256 amount, uint256 timestamp);
    event FeeConfigUpdated(uint256 feeBps, address collector);

    /**
     * @param _reserveFeed   Address of the reserve proof feed (an {Attestor}).
     * @param _maxAgeReserve Max staleness (seconds) accepted for a reserve read.
     * @param _feeCollector  Dormant fee collector (may be zero for now).
     */
    constructor(
        address _reserveFeed,
        uint256 _maxAgeReserve,
        address _feeCollector
    ) ERC20("Oltin Gold Token", "OLTIN") {
        require(_reserveFeed != address(0), "Zero address");
        uint8 d = AggregatorV3Interface(_reserveFeed).decimals();
        require(d <= 18, "reserve decimals>18");

        reserveFeed = AggregatorV3Interface(_reserveFeed);
        reserveDecimals = d;
        maxAgeReserve = _maxAgeReserve;
        feeCollector = _feeCollector;

        // NOTE: MINTER_ROLE is intentionally NOT granted here. The deploy
        // script grants it to the Exchange, the sole minter.
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(PAUSER_ROLE, msg.sender);
    }

    /**
     * @notice Mint `amount` OLTIN to `to`, subject to the Proof-of-Reserve guard.
     * @dev Callable only by MINTER_ROLE (the Exchange). Reverts unless the
     *      reserve reading is positive, fresh, and covers total supply + amount.
     */
    function mint(address to, uint256 amount)
        external
        onlyRole(MINTER_ROLE)
        whenNotPaused
    {
        require(to != address(0), "Zero address");
        require(amount > 0, "Zero amount");

        (, int256 r, , uint256 upd, ) = reserveFeed.latestRoundData();
        require(r > 0, "reserve<=0");
        // `upd <= block.timestamp` is checked FIRST so a future-dated reading
        // reverts with the named error instead of underflowing the subtraction.
        require(
            upd <= block.timestamp && block.timestamp - upd <= maxAgeReserve,
            "reserve stale"
        );
        // Scale the reserve up to 18 decimals (1 OLTIN wei == 1e-18 gram).
        require(
            totalSupply() + amount <= uint256(r) * 10 ** (18 - reserveDecimals),
            "exceeds reserve"
        );

        _mint(to, amount);
        emit Minted(to, amount, block.timestamp);
    }

    /**
     * @notice Update the (dormant) fee configuration.
     * @dev No effect on transfers while the fee is dormant; kept for a future
     *      activation and to mirror the V2 admin surface.
     */
    function setFeeConfig(uint256 _feeBps, address _collector)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        require(_feeBps <= 500, "Fee max 5%");
        transferFeeBps = _feeBps;
        feeCollector = _collector;
        emit FeeConfigUpdated(_feeBps, _collector);
    }

    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    /**
     * @dev Pausable transfer hook. The DORMANT `transferFeeBps` is deliberately
     *      NOT applied here — transfers move the full amount in this release.
     */
    function _update(address from, address to, uint256 value)
        internal
        override
        whenNotPaused
    {
        super._update(from, to, value);
    }

    function decimals() public pure override returns (uint8) {
        return 18;
    }
}
