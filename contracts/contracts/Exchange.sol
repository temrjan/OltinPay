// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";
import "./interfaces/AggregatorV3Interface.sol";

/// @dev OLTIN surface the Exchange needs: mint (PoR-guarded) + allowance-gated burn.
interface IOltin is IERC20 {
    function mint(address to, uint256 amount) external;

    function burnFrom(address account, uint256 amount) external;
}

/**
 * @title Exchange
 * @notice Mints/redeems OLTIN against UZD at the live gold price.
 *
 * @dev The Exchange IS the UZD treasury: buys deposit UZD here, sells pay UZD
 *      from here. This is why `sell` pays with `transfer` (from this contract's
 *      own balance) rather than `transferFrom`. {treasury} / {treasuryBalance}
 *      expose that balance for tooling.
 *
 *      Safety:
 *        - {ReentrancyGuard} on both {buy} and {sell}.
 *        - Strict checks-effects-interactions: all validation (fresh prices,
 *          slippage, treasury balance) happens BEFORE any token movement.
 *        - Both price feeds are staleness-guarded (positive, not stale, not
 *          future-dated) via {_freshPrice}.
 *        - All fixed-point math via OpenZeppelin {Math-mulDiv} (512-bit
 *          intermediate, floored). Rounding always favors the protocol.
 *        - Burns are allowance-gated ({IOltin-burnFrom} of msg.sender only),
 *          preserving the non-custodial invariant.
 */
contract Exchange is ReentrancyGuard {
    using SafeERC20 for IERC20;

    IOltin public immutable oltin;
    IERC20 public immutable uzd;
    AggregatorV3Interface public immutable xauFeed; // XAU/USD, 8 decimals
    AggregatorV3Interface public immutable uzsFeed; // UZS/USD, 8 decimals
    /// @notice Max age (seconds) a price reading may have before it is stale.
    uint256 public immutable maxAgePrice;

    /// @notice Grams per troy ounce, scaled by 1e8 (31.1034768 g * 1e8).
    uint256 public constant GRAMS_PER_OZ_1E8 = 3110347680;

    event Bought(
        address indexed user,
        uint256 uzdInWei,
        uint256 oltinOutWei,
        uint256 xauAns,
        uint256 uzsAns
    );
    event Sold(
        address indexed user,
        uint256 oltinInWei,
        uint256 uzdOutWei,
        uint256 xauAns,
        uint256 uzsAns
    );

    constructor(
        address _oltin,
        address _uzd,
        address _xauFeed,
        address _uzsFeed,
        uint256 _maxAgePrice
    ) {
        require(
            _oltin != address(0) &&
                _uzd != address(0) &&
                _xauFeed != address(0) &&
                _uzsFeed != address(0),
            "Zero address"
        );
        oltin = IOltin(_oltin);
        uzd = IERC20(_uzd);
        xauFeed = AggregatorV3Interface(_xauFeed);
        uzsFeed = AggregatorV3Interface(_uzsFeed);
        maxAgePrice = _maxAgePrice;
    }

    /// @notice The UZD treasury address (this contract).
    function treasury() external view returns (address) {
        return address(this);
    }

    /// @notice UZD held by the treasury, available to pay sellers.
    function treasuryBalance() public view returns (uint256) {
        return uzd.balanceOf(address(this));
    }

    /**
     * @notice Buy OLTIN with UZD.
     * @param uzdInWei   UZD (18 decimals) to spend.
     * @param minOltinOut Minimum acceptable OLTIN out; MUST be > 0 (dust guard).
     * @return oltinOutWei OLTIN (18 decimals) minted to the caller.
     */
    function buy(uint256 uzdInWei, uint256 minOltinOut)
        external
        nonReentrant
        returns (uint256 oltinOutWei)
    {
        require(uzdInWei > 0, "Zero amount");
        uint256 xauAns = _freshPrice(xauFeed);
        uint256 uzsAns = _freshPrice(uzsFeed);

        // oltinOutWei = uzdInWei * uzsAns * GRAMS_PER_OZ_1E8 / (1e8 * xauAns)
        // Group the two SMALL factors (uzsAns * GRAMS_PER_OZ_1E8) so the large
        // product (uzdInWei * ...) flows through mulDiv's 512-bit path and can
        // never overflow uint256. Result is floored (protocol-safe: the user
        // never receives extra OLTIN).
        oltinOutWei = Math.mulDiv(
            uzdInWei,
            uzsAns * GRAMS_PER_OZ_1E8,
            1e8 * xauAns,
            Math.Rounding.Floor
        );
        require(oltinOutWei >= minOltinOut && minOltinOut > 0, "dust");

        // Effects/interactions (CEI): pull UZD into the treasury, then mint.
        uzd.safeTransferFrom(msg.sender, address(this), uzdInWei);
        oltin.mint(msg.sender, oltinOutWei);

        emit Bought(msg.sender, uzdInWei, oltinOutWei, xauAns, uzsAns);
    }

    /**
     * @notice Sell OLTIN for UZD.
     * @param oltinInWei OLTIN (18 decimals) to redeem. Caller must have approved
     *                   this Exchange for at least this amount (allowance-gated
     *                   burn — the Exchange can never burn an arbitrary holder).
     * @param minUzdOut  Minimum acceptable UZD out (slippage guard).
     * @return uzdOutWei UZD (18 decimals) paid to the caller.
     */
    function sell(uint256 oltinInWei, uint256 minUzdOut)
        external
        nonReentrant
        returns (uint256 uzdOutWei)
    {
        require(oltinInWei > 0, "Zero amount");
        uint256 xauAns = _freshPrice(xauFeed);
        uint256 uzsAns = _freshPrice(uzsFeed);

        // uzdOutWei = oltinInWei * xauAns * 1e8 / (GRAMS_PER_OZ_1E8 * uzsAns)
        // Group (xauAns * 1e8) so the large product (oltinInWei * ...) uses the
        // 512-bit path. Floored (protocol-safe: the protocol never overpays).
        uzdOutWei = Math.mulDiv(
            oltinInWei,
            xauAns * 1e8,
            GRAMS_PER_OZ_1E8 * uzsAns,
            Math.Rounding.Floor
        );
        require(uzdOutWei >= minUzdOut, "slippage");
        // Checks BEFORE any state change: the treasury must be able to pay.
        require(treasuryBalance() >= uzdOutWei, "treasury empty");

        // Interactions: burn the caller's OLTIN (allowance-gated), then pay UZD.
        oltin.burnFrom(msg.sender, oltinInWei);
        uzd.safeTransfer(msg.sender, uzdOutWei);

        emit Sold(msg.sender, oltinInWei, uzdOutWei, xauAns, uzsAns);
    }

    /// @dev Returns the positive answer or reverts if non-positive / stale /
    ///      future-dated. `upd <= block.timestamp` is checked before the
    ///      subtraction to avoid an underflow on a future-dated reading.
    function _freshPrice(AggregatorV3Interface feed)
        internal
        view
        returns (uint256)
    {
        (, int256 answer, , uint256 upd, ) = feed.latestRoundData();
        require(
            answer > 0 &&
                upd <= block.timestamp &&
                block.timestamp - upd <= maxAgePrice,
            "price stale"
        );
        return uint256(answer);
    }
}
