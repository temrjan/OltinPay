// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IPaymaster, ExecutionResult, PAYMASTER_VALIDATION_SUCCESS_MAGIC} from "@matterlabs/zksync-contracts/contracts/system-contracts/interfaces/IPaymaster.sol";
import {IPaymasterFlow} from "@matterlabs/zksync-contracts/contracts/system-contracts/interfaces/IPaymasterFlow.sol";
import {Transaction} from "@matterlabs/zksync-contracts/contracts/system-contracts/libraries/TransactionHelper.sol";
import {BOOTLOADER_FORMAL_ADDRESS} from "@matterlabs/zksync-contracts/contracts/system-contracts/Constants.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable2Step.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";

/**
 * @title OltinPaymaster
 * @notice Sponsors gas for OltinPay users: the paymaster pays the ETH, the user
 *         pays a fee in OLTIN (zkSync `approvalBased` flow).
 *
 * @dev SECURITY — why the fee is computed here and not taken from the user.
 *      The previous version derived the fee from `minAllowance`, a value the
 *      USER puts in `paymasterInput`, while paying the bootloader
 *      `gasLimit * maxFeePerGas`, a value the user also controls. Nothing tied
 *      the two together, so `minAllowance = 0` plus a gas-heavy target drained
 *      the ETH balance for dust. Now the paymaster computes the ETH it is about
 *      to spend and charges the OLTIN equivalent of THAT ({quoteFee}); the
 *      user's `minAllowance` is nothing more than the allowance request it has
 *      always been, and it is verified, not trusted.
 *
 *      Defence in depth, because a fee peg alone bounds cost per transaction
 *      but not in aggregate:
 *        - {sponsoredTarget} allowlist — we sponsor calls to OUR contracts only;
 *        - {maxSponsoredEthWei} — per-transaction ceiling;
 *        - {dailyEthCapSender} / {dailyEthCapGlobal} — per-day ceilings. The
 *          per-sender one is NOT an anti-attacker control (addresses are free);
 *          it stops a looping client. The GLOBAL one is what bounds the loss.
 *        - {Pausable} — kill switch, matching UZD / OltinTokenV3 / OltinStaking.
 *
 *      PRICING — the rate is an owner-set configuration, not an oracle: there is
 *      no ETH/USD feed on zkSync Sepolia, and a demo does not need economic
 *      precision (the loss ceiling comes from the caps, not from rate accuracy).
 *      It is guarded like one, though: bounded by immutable {minRate}/{maxRate}
 *      (a fat finger, or `rate = 0` turning this into a free relay, cannot be
 *      configured), self-stamped {rateUpdatedAt} (the owner cannot backdate),
 *      and refused once older than {maxRateAge}.
 *
 *      FEE BASIS (deliberate): the fee is charged on `gasLimit * maxFeePerGas` —
 *      the amount prefunded to the bootloader — not on gas actually burned. The
 *      unused part is refunded BY the bootloader TO this contract (measured in
 *      the VM suite: ~25% of the prefund came back on a plain ERC20 transfer).
 *      So the user pays for the limit they requested and the refund accrues to
 *      the paymaster. The daily buckets likewise count the gross prefund. Both
 *      choices are conservative on purpose.
 *
 *      Ownership transfer is TWO-STEP ({Ownable2Step}): a typo in a one-step
 *      transfer would lock the ETH reserve and the collected fees forever, with
 *      no recovery path on a non-upgradeable contract.
 *
 *      SINGLE-OWNER, unlike its siblings. UZD / OltinTokenV3 / OltinStaking use
 *      AccessControl with a separate PAUSER_ROLE so ops can hold the kill switch
 *      without holding the funds. Here the whole admin surface is one key on
 *      purpose: this contract has exactly one operator (the deployer), the demo
 *      has no separate ops team to delegate to, and a second role would add a
 *      key to protect without removing one. If a monitoring key is ever wanted,
 *      that is the moment to move to AccessControl — not before.
 *
 *      NOT UPGRADEABLE, on purpose. Everything operational is configurable
 *      (rate, surcharge, floor, caps, allowlist, pause, withdrawals), so only a
 *      change of validation LOGIC needs a redeploy. A proxy on the contract that
 *      holds ETH and signs off on sponsorship is exactly what a bank security
 *      review asks about ("who can swap the implementation?"), and swapping the
 *      address costs one line of client config.
 */
contract OltinPaymaster is IPaymaster, Ownable2Step, Pausable {
    using SafeERC20 for IERC20;

    /// @notice Fee token (OLTIN). Immutable — a paymaster bound to one token.
    IERC20 public immutable oltinToken;

    /// @notice Inclusive bounds for {oltinPerEth}. Immutable: a misconfigured
    ///         rate is the one setting that silently breaks the fee peg.
    uint256 public immutable minRate;
    uint256 public immutable maxRate;

    /// @notice How old a rate reading may be before sponsorship is refused.
    uint256 public immutable maxRateAge;

    /// @notice Hard ceiling on the surcharge an owner can configure (5%).
    uint256 public constant MAX_SURCHARGE_BPS = 500;

    /// @notice Hard ceiling on the fee floor an owner can configure (0.01 OLTIN
    ///         ~ $1 at demo prices) — an owner cannot price gasless out of use.
    uint256 public constant MAX_MIN_FEE_OLTIN = 0.01 ether;

    /// @notice OLTIN (18 dec) charged per 1 ETH (1e18 wei) of sponsored gas.
    uint256 public oltinPerEth;

    /// @notice Self-stamped timestamp of the last {setRate}.
    uint256 public rateUpdatedAt;

    /// @notice Surcharge on top of the pegged fee, in basis points.
    uint256 public surchargeBps;

    /// @notice Absolute fee floor in OLTIN. Kept well below the pegged fee for
    ///         a typical transaction so the peg — not the floor — prices gas.
    uint256 public minFeeOltin;

    /// @notice Per-transaction ceiling on sponsored ETH.
    uint256 public maxSponsoredEthWei;

    /// @notice Per-day, per-sender ceiling on sponsored ETH.
    uint256 public dailyEthCapSender;

    /// @notice Per-day, protocol-wide ceiling on sponsored ETH.
    uint256 public dailyEthCapGlobal;

    /// @notice OLTIN collected as fees (donations to this contract excluded).
    uint256 public totalFeesCollected;

    /// @notice Contracts whose calls this paymaster is willing to sponsor.
    mapping(address => bool) public sponsoredTarget;

    /// @dev One slot: the day bucket and what was spent in it.
    struct DaySpend {
        uint64 day;
        uint192 spentWei;
    }

    mapping(address => DaySpend) public senderSpend;
    DaySpend public globalSpend;

    event FeePaid(address indexed user, uint256 oltinFee, bytes32 indexed txHash);
    event FeesWithdrawn(address indexed to, uint256 amount);
    event EthWithdrawn(address indexed to, uint256 amount);
    event EthDeposited(address indexed from, uint256 amount);
    event FeeConfigUpdated(uint256 surchargeBps, uint256 minFeeOltin);
    event RateUpdated(uint256 oltinPerEth, uint256 updatedAt);
    event CapsUpdated(uint256 perTx, uint256 perSenderDaily, uint256 globalDaily);
    event SponsoredTargetSet(address indexed target, bool allowed);

    // Validation failures — distinct types so a client and a demo operator can
    // tell "gasless is broken" from "today's budget is spent".
    error NotBootloader();
    error InvalidPaymasterInput();
    error UnsupportedFlow();
    error WrongFeeToken(address got, address expected);
    error TargetNotSponsored(address target);
    error PerTxCapExceeded(uint256 requiredEth, uint256 cap);
    error SenderDailyCapExceeded(uint256 requiredEth, uint256 spent, uint256 cap);
    error GlobalDailyCapExceeded(uint256 requiredEth, uint256 spent, uint256 cap);
    error PaymasterOutOfFunds(uint256 requiredEth, uint256 balance);
    error RateStale(uint256 updatedAt, uint256 maxAge);
    error AllowanceBelowFee(uint256 fee, uint256 allowance);
    error BootloaderPaymentFailed();
    error EthTransferFailed();
    // Configuration / admin failures.
    error ZeroAddress();
    error ZeroAmount();
    error RateOutOfBounds(uint256 rate, uint256 min, uint256 max);
    error SurchargeTooHigh(uint256 bps, uint256 max);
    error MinFeeTooHigh(uint256 minFee, uint256 max);
    error AmountExceedsBalance(uint256 amount, uint256 balance);

    modifier onlyBootloader() {
        if (msg.sender != BOOTLOADER_FORMAL_ADDRESS) revert NotBootloader();
        _;
    }

    /**
     * @param _oltinToken  Fee token (OLTIN).
     * @param _minRate     Lower bound for {oltinPerEth}.
     * @param _maxRate     Upper bound for {oltinPerEth}.
     * @param _maxRateAge  Staleness window for the rate, in seconds.
     * @param _initialRate Rate at deployment; must lie within the bounds.
     * @param _surchargeBps Surcharge in bps (<= {MAX_SURCHARGE_BPS}).
     * @param _minFeeOltin  Fee floor in OLTIN (<= {MAX_MIN_FEE_OLTIN}).
     * @param _maxSponsoredEthWei Per-transaction ETH ceiling.
     * @param _dailyEthCapSender  Per-day, per-sender ETH ceiling.
     * @param _dailyEthCapGlobal  Per-day, protocol-wide ETH ceiling.
     */
    constructor(
        address _oltinToken,
        uint256 _minRate,
        uint256 _maxRate,
        uint256 _maxRateAge,
        uint256 _initialRate,
        uint256 _surchargeBps,
        uint256 _minFeeOltin,
        uint256 _maxSponsoredEthWei,
        uint256 _dailyEthCapSender,
        uint256 _dailyEthCapGlobal
    ) Ownable(msg.sender) {
        if (_oltinToken == address(0)) revert ZeroAddress();
        if (_minRate == 0 || _maxRate < _minRate) revert RateOutOfBounds(_minRate, _minRate, _maxRate);
        if (_maxRateAge == 0) revert ZeroAmount();
        if (_initialRate < _minRate || _initialRate > _maxRate) {
            revert RateOutOfBounds(_initialRate, _minRate, _maxRate);
        }
        if (_surchargeBps > MAX_SURCHARGE_BPS) revert SurchargeTooHigh(_surchargeBps, MAX_SURCHARGE_BPS);
        if (_minFeeOltin > MAX_MIN_FEE_OLTIN) revert MinFeeTooHigh(_minFeeOltin, MAX_MIN_FEE_OLTIN);
        if (_maxSponsoredEthWei == 0 || _dailyEthCapSender == 0 || _dailyEthCapGlobal == 0) revert ZeroAmount();

        oltinToken = IERC20(_oltinToken);
        minRate = _minRate;
        maxRate = _maxRate;
        maxRateAge = _maxRateAge;

        oltinPerEth = _initialRate;
        rateUpdatedAt = block.timestamp;
        surchargeBps = _surchargeBps;
        minFeeOltin = _minFeeOltin;
        maxSponsoredEthWei = _maxSponsoredEthWei;
        dailyEthCapSender = _dailyEthCapSender;
        dailyEthCapGlobal = _dailyEthCapGlobal;

        emit RateUpdated(_initialRate, block.timestamp);
        emit FeeConfigUpdated(_surchargeBps, _minFeeOltin);
        emit CapsUpdated(_maxSponsoredEthWei, _dailyEthCapSender, _dailyEthCapGlobal);
    }

    // ============ Quoting ============

    /**
     * @notice OLTIN fee for a transaction with these gas parameters.
     * @dev THE CLIENT MUST USE THIS to size `minimalAllowance` in
     *      `paymasterParams`. Do not mirror the formula off-chain: it drifts on
     *      the first {setRate}/{setFeeConfig} and every sponsored transaction
     *      then reverts with {AllowanceBelowFee}. Reverts with {RateStale} when
     *      sponsorship is unavailable, so a quote failure tells the client the
     *      real reason.
     */
    function quoteFee(uint256 gasLimit, uint256 maxFeePerGas) public view returns (uint256) {
        return _feeFor(gasLimit * maxFeePerGas);
    }

    /// @dev Pegged fee for `requiredEth`, rounded UP at every step — the mirror
    ///      of Exchange's floor rounding: both round in the protocol's favour.
    function _feeFor(uint256 requiredEth) internal view returns (uint256 fee) {
        uint256 updatedAt = rateUpdatedAt;
        if (block.timestamp - updatedAt > maxRateAge) revert RateStale(updatedAt, maxRateAge);

        fee = Math.mulDiv(requiredEth, oltinPerEth, 1e18, Math.Rounding.Ceil);
        fee = Math.mulDiv(fee, 10000 + surchargeBps, 10000, Math.Rounding.Ceil);

        uint256 floor_ = minFeeOltin;
        if (fee < floor_) fee = floor_;
    }

    // ============ Paymaster ============

    /**
     * @notice Everything the paymaster checks before sponsoring, as a view.
     * @dev A sponsored transaction has NO usable preflight otherwise: it cannot
     *      be auto-estimated (see {quoteFee}), and when validation refuses one
     *      the transaction is not reverted — it is simply never mined, so the
     *      client sees silence. `eth_call` this first and the client gets the
     *      typed reason ({TargetNotSponsored}, {PerTxCapExceeded},
     *      {SenderDailyCapExceeded}, {GlobalDailyCapExceeded},
     *      {PaymasterOutOfFunds}, {RateStale}) plus the fee to put in
     *      `minimalAllowance`.
     *
     *      The allowance is deliberately NOT checked here: in the approvalBased
     *      flow it is the account that sets it, during the very transaction
     *      being prepared, so at preflight time it is legitimately still zero.
     * @return fee OLTIN to approve for this transaction.
     */
    function checkSponsorship(
        address from,
        address to,
        uint256 gasLimit,
        uint256 maxFeePerGas
    ) external view returns (uint256 fee) {
        (fee, , , ) = _guard(from, to, gasLimit * maxFeePerGas);
    }

    /// @dev Single source of truth for the sponsorship rules: used by the
    ///      preflight view AND by validation, so the two can never disagree.
    ///      Pure reads — the caller performs the writes.
    function _guard(address from, address to, uint256 requiredEth)
        internal
        view
        returns (uint256 fee, uint256 senderSpent, uint256 globalSpent, uint64 today)
    {
        if (paused()) revert EnforcedPause();
        if (!sponsoredTarget[to]) revert TargetNotSponsored(to);
        if (requiredEth > maxSponsoredEthWei) revert PerTxCapExceeded(requiredEth, maxSponsoredEthWei);
        if (address(this).balance < requiredEth) {
            revert PaymasterOutOfFunds(requiredEth, address(this).balance);
        }

        today = uint64(block.timestamp / 1 days);

        DaySpend memory s = senderSpend[from];
        senderSpent = s.day == today ? s.spentWei : 0;
        if (senderSpent + requiredEth > dailyEthCapSender) {
            revert SenderDailyCapExceeded(requiredEth, senderSpent, dailyEthCapSender);
        }

        DaySpend memory g = globalSpend;
        globalSpent = g.day == today ? g.spentWei : 0;
        if (globalSpent + requiredEth > dailyEthCapGlobal) {
            revert GlobalDailyCapExceeded(requiredEth, globalSpent, dailyEthCapGlobal);
        }

        fee = _feeFor(requiredEth);
    }

    /// @inheritdoc IPaymaster
    function validateAndPayForPaymasterTransaction(
        bytes32,
        bytes32,
        Transaction calldata _transaction
    ) external payable onlyBootloader whenNotPaused returns (bytes4 magic, bytes memory context) {
        magic = PAYMASTER_VALIDATION_SUCCESS_MAGIC;

        if (_transaction.paymasterInput.length < 4) revert InvalidPaymasterInput();
        if (bytes4(_transaction.paymasterInput[0:4]) != IPaymasterFlow.approvalBased.selector) {
            revert UnsupportedFlow();
        }
        // `minAllowance` is deliberately ignored: it is the user's allowance
        // request, never an input to pricing.
        (address token, , ) = abi.decode(_transaction.paymasterInput[4:], (address, uint256, bytes));
        if (token != address(oltinToken)) revert WrongFeeToken(token, address(oltinToken));

        address user = address(uint160(_transaction.from));
        // Checks before effects: everything below is priced off THIS number.
        uint256 requiredEth = _transaction.gasLimit * _transaction.maxFeePerGas;

        (uint256 fee, uint256 senderSpent, uint256 globalSpent, uint64 today) =
            _guard(user, address(uint160(_transaction.to)), requiredEth);

        // The explicit allowance read duplicates the one inside `transferFrom`.
        // Deliberate: it costs one staticcall in validation and buys a typed
        // {AllowanceBelowFee} carrying BOTH numbers, which is what tells a
        // client its `minimalAllowance` was sized from a stale {quoteFee} — the
        // single most likely integration failure. ERC20's own error would say
        // the same thing in a form the client cannot map back to the quote.
        uint256 allowance = oltinToken.allowance(user, address(this));
        if (allowance < fee) revert AllowanceBelowFee(fee, allowance);

        senderSpend[user] = DaySpend(today, uint192(senderSpent + requiredEth));
        globalSpend = DaySpend(today, uint192(globalSpent + requiredEth));

        oltinToken.safeTransferFrom(user, address(this), fee);
        totalFeesCollected += fee;

        (bool ethSent, ) = payable(BOOTLOADER_FORMAL_ADDRESS).call{value: requiredEth}("");
        if (!ethSent) revert BootloaderPaymentFailed();

        context = abi.encode(user, fee);
    }

    /// @inheritdoc IPaymaster
    function postTransaction(
        bytes calldata _context,
        Transaction calldata,
        bytes32 _txHash,
        bytes32,
        ExecutionResult,
        uint256
    ) external payable override onlyBootloader {
        (address user, uint256 fee) = abi.decode(_context, (address, uint256));
        emit FeePaid(user, fee, _txHash);
    }

    // ============ Admin ============

    function setRate(uint256 _oltinPerEth) external onlyOwner {
        if (_oltinPerEth < minRate || _oltinPerEth > maxRate) {
            revert RateOutOfBounds(_oltinPerEth, minRate, maxRate);
        }
        oltinPerEth = _oltinPerEth;
        rateUpdatedAt = block.timestamp;
        emit RateUpdated(_oltinPerEth, block.timestamp);
    }

    function setFeeConfig(uint256 _surchargeBps, uint256 _minFeeOltin) external onlyOwner {
        if (_surchargeBps > MAX_SURCHARGE_BPS) revert SurchargeTooHigh(_surchargeBps, MAX_SURCHARGE_BPS);
        if (_minFeeOltin > MAX_MIN_FEE_OLTIN) revert MinFeeTooHigh(_minFeeOltin, MAX_MIN_FEE_OLTIN);
        surchargeBps = _surchargeBps;
        minFeeOltin = _minFeeOltin;
        emit FeeConfigUpdated(_surchargeBps, _minFeeOltin);
    }

    function setCaps(
        uint256 _maxSponsoredEthWei,
        uint256 _dailyEthCapSender,
        uint256 _dailyEthCapGlobal
    ) external onlyOwner {
        if (_maxSponsoredEthWei == 0 || _dailyEthCapSender == 0 || _dailyEthCapGlobal == 0) revert ZeroAmount();
        maxSponsoredEthWei = _maxSponsoredEthWei;
        dailyEthCapSender = _dailyEthCapSender;
        dailyEthCapGlobal = _dailyEthCapGlobal;
        emit CapsUpdated(_maxSponsoredEthWei, _dailyEthCapSender, _dailyEthCapGlobal);
    }

    function setSponsoredTarget(address _target, bool _allowed) external onlyOwner {
        if (_target == address(0)) revert ZeroAddress();
        sponsoredTarget[_target] = _allowed;
        emit SponsoredTargetSet(_target, _allowed);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    function withdrawFees(address _to) external onlyOwner {
        if (_to == address(0)) revert ZeroAddress();
        uint256 amount = totalFeesCollected;
        if (amount == 0) revert ZeroAmount();
        totalFeesCollected = 0;
        oltinToken.safeTransfer(_to, amount);
        emit FeesWithdrawn(_to, amount);
    }

    /// @dev Takes an explicit amount: the previous version swept the whole
    ///      balance to an unchecked address, so one typo burned the gas reserve.
    function withdrawETH(address payable _to, uint256 _amount) external onlyOwner {
        if (_to == address(0)) revert ZeroAddress();
        if (_amount == 0) revert ZeroAmount();
        uint256 balance = address(this).balance;
        if (_amount > balance) revert AmountExceedsBalance(_amount, balance);
        (bool success, ) = _to.call{value: _amount}("");
        if (!success) revert EthTransferFailed();
        emit EthWithdrawn(_to, _amount);
    }

    /// @notice Deposit ETH for gas coverage.
    receive() external payable {
        emit EthDeposited(msg.sender, msg.value);
    }
}
