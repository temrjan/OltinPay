// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title OltinStaking
 * @notice Stake OLTIN, earn OLTIN reward at 7% APY. Per-deposit 7-day lock.
 *
 * @dev Each deposit creates its own lot with its own lock. New deposit does
 *      NOT extend the lock on previously-staked OLTIN. User can withdraw any
 *      OLTIN whose lot has unlocked, while keeping fresh lots locked.
 *
 *      Reward currency: OLTIN (same as principal). Source: rewardPool funded
 *      by FUNDER_ROLE. Pull-based — user calls claim() to withdraw or
 *      compound() to re-stake.
 *
 *      Note: on-chain stake = `OLTIN.transferFrom(user, this)`. The
 *      "WALLET→STAKING account transfer" abstraction from the off-chain
 *      Python service maps to a real ERC20 Transfer event here.
 */
contract OltinStaking is AccessControl, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant FUNDER_ROLE = keccak256("FUNDER_ROLE");

    IERC20 public immutable oltin;

    uint256 public constant APY_BPS = 700;             // 7%
    uint256 public constant LOCK_PERIOD = 7 days;
    uint256 public constant SECONDS_PER_YEAR = 365 days;
    uint256 public constant BPS_DENOMINATOR = 10_000;

    /// @notice One deposit ("lot") with its own lock and remaining amount.
    struct Lot {
        uint128 amount;       // remaining OLTIN in this lot
        uint64 lockedUntil;   // unix seconds
        uint64 reserved;      // padding for future use, keeps slot aligned
    }

    struct StakeInfo {
        uint256 totalPrincipal;   // sum of all lots' amount
        uint256 lastAccrualAt;
        uint256 unclaimedReward;
        Lot[] lots;
    }

    mapping(address => StakeInfo) private _stakes;
    uint256 public totalStaked;
    uint256 public rewardPool;

    event Staked(
        address indexed user,
        uint256 amount,
        uint256 newPrincipal,
        uint256 lockedUntil
    );
    event Unstaked(
        address indexed user,
        uint256 amount,
        uint256 newPrincipal
    );
    event Claimed(address indexed user, uint256 amount);
    event Compounded(
        address indexed user,
        uint256 amount,
        uint256 newPrincipal
    );
    event RewardPoolFunded(
        address indexed funder,
        uint256 amount,
        uint256 newPool
    );
    event RewardPoolWithdrawn(address indexed admin, uint256 amount);

    constructor(address _oltin) {
        require(_oltin != address(0), "Zero token address");
        oltin = IERC20(_oltin);
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(PAUSER_ROLE, msg.sender);
        _grantRole(FUNDER_ROLE, msg.sender);
    }

    // === User-facing ===

    /// @notice Deposit OLTIN. The new amount is locked for 7 days but does
    ///         NOT extend the lock on previous deposits.
    function stake(uint256 amount) external whenNotPaused nonReentrant {
        require(amount > 0, "Zero amount");
        require(amount <= type(uint128).max, "Amount too large");
        _accrue(msg.sender);
        oltin.safeTransferFrom(msg.sender, address(this), amount);
        StakeInfo storage s = _stakes[msg.sender];
        uint64 lockedUntil = uint64(block.timestamp + LOCK_PERIOD);
        s.lots.push(Lot({amount: uint128(amount), lockedUntil: lockedUntil, reserved: 0}));
        s.totalPrincipal += amount;
        totalStaked += amount;
        emit Staked(msg.sender, amount, s.totalPrincipal, lockedUntil);
    }

    /// @notice Withdraw `amount` of OLTIN. Pulls FIFO from unlocked lots.
    ///         Reverts if `amount` exceeds the unlocked principal.
    function unstake(uint256 amount) external whenNotPaused nonReentrant {
        require(amount > 0, "Zero amount");
        _accrue(msg.sender);
        StakeInfo storage s = _stakes[msg.sender];
        require(s.totalPrincipal >= amount, "Insufficient principal");

        uint256 remaining = amount;
        uint256 nowTs = block.timestamp;
        uint256 len = s.lots.length;
        for (uint256 i = 0; i < len && remaining > 0; i++) {
            Lot storage lot = s.lots[i];
            if (lot.amount == 0) continue;
            if (lot.lockedUntil > nowTs) continue;
            uint256 take = lot.amount > remaining ? remaining : lot.amount;
            lot.amount -= uint128(take);
            remaining -= take;
        }
        require(remaining == 0, "Insufficient unlocked principal");

        s.totalPrincipal -= amount;
        totalStaked -= amount;
        _compactLots(msg.sender);

        oltin.safeTransfer(msg.sender, amount);
        emit Unstaked(msg.sender, amount, s.totalPrincipal);
    }

    /// @notice Claim accrued reward to wallet (limited by rewardPool).
    function claim()
        external
        whenNotPaused
        nonReentrant
        returns (uint256 paid)
    {
        _accrue(msg.sender);
        StakeInfo storage s = _stakes[msg.sender];
        uint256 owed = s.unclaimedReward;
        if (owed == 0) return 0;
        paid = owed > rewardPool ? rewardPool : owed;
        if (paid > 0) {
            s.unclaimedReward -= paid;
            rewardPool -= paid;
            oltin.safeTransfer(msg.sender, paid);
            emit Claimed(msg.sender, paid);
        }
    }

    /// @notice Move accrued reward into a new locked lot (re-stake).
    function compound()
        external
        whenNotPaused
        nonReentrant
        returns (uint256 added)
    {
        _accrue(msg.sender);
        StakeInfo storage s = _stakes[msg.sender];
        uint256 owed = s.unclaimedReward;
        if (owed == 0) return 0;
        added = owed > rewardPool ? rewardPool : owed;
        if (added > 0) {
            require(added <= type(uint128).max, "Reward too large");
            s.unclaimedReward -= added;
            rewardPool -= added;
            uint64 lockedUntil = uint64(block.timestamp + LOCK_PERIOD);
            s.lots.push(Lot({amount: uint128(added), lockedUntil: lockedUntil, reserved: 0}));
            s.totalPrincipal += added;
            totalStaked += added;
            emit Compounded(msg.sender, added, s.totalPrincipal);
        }
    }

    // === Admin ===

    function fundRewardPool(uint256 amount) external onlyRole(FUNDER_ROLE) {
        require(amount > 0, "Zero amount");
        oltin.safeTransferFrom(msg.sender, address(this), amount);
        rewardPool += amount;
        emit RewardPoolFunded(msg.sender, amount, rewardPool);
    }

    function withdrawRewardPool(uint256 amount)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        require(amount > 0 && amount <= rewardPool, "Invalid amount");
        rewardPool -= amount;
        oltin.safeTransfer(msg.sender, amount);
        emit RewardPoolWithdrawn(msg.sender, amount);
    }

    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    // === Views ===

    function pendingReward(address user) external view returns (uint256) {
        StakeInfo storage s = _stakes[user];
        return s.unclaimedReward + _calcReward(s.totalPrincipal, s.lastAccrualAt);
    }

    function unlockedPrincipal(address user) external view returns (uint256 unlocked) {
        StakeInfo storage s = _stakes[user];
        uint256 nowTs = block.timestamp;
        uint256 len = s.lots.length;
        for (uint256 i = 0; i < len; i++) {
            Lot storage lot = s.lots[i];
            if (lot.amount > 0 && lot.lockedUntil <= nowTs) {
                unlocked += lot.amount;
            }
        }
    }

    function getStakeInfo(address user)
        external
        view
        returns (
            uint256 totalPrincipal,
            uint256 unlocked,
            uint256 pending,
            uint256 lotCount,
            uint256 nextUnlockAt
        )
    {
        StakeInfo storage s = _stakes[user];
        totalPrincipal = s.totalPrincipal;
        pending = s.unclaimedReward + _calcReward(s.totalPrincipal, s.lastAccrualAt);
        uint256 nowTs = block.timestamp;
        uint256 len = s.lots.length;
        nextUnlockAt = type(uint256).max;
        for (uint256 i = 0; i < len; i++) {
            Lot storage lot = s.lots[i];
            if (lot.amount == 0) continue;
            if (lot.lockedUntil <= nowTs) {
                unlocked += lot.amount;
            } else if (lot.lockedUntil < nextUnlockAt) {
                nextUnlockAt = lot.lockedUntil;
            }
        }
        if (nextUnlockAt == type(uint256).max) nextUnlockAt = 0;
        lotCount = len;
    }

    function getLot(address user, uint256 index)
        external
        view
        returns (uint256 amount, uint256 lockedUntil)
    {
        Lot storage lot = _stakes[user].lots[index];
        return (lot.amount, lot.lockedUntil);
    }

    // === Internal ===

    function _accrue(address user) internal {
        StakeInfo storage s = _stakes[user];
        if (s.lastAccrualAt == 0) {
            s.lastAccrualAt = block.timestamp;
            return;
        }
        if (s.totalPrincipal > 0) {
            uint256 reward = _calcReward(s.totalPrincipal, s.lastAccrualAt);
            if (reward > 0) {
                s.unclaimedReward += reward;
            }
        }
        s.lastAccrualAt = block.timestamp;
    }

    function _calcReward(uint256 principal, uint256 lastAccrualAt)
        internal
        view
        returns (uint256)
    {
        if (principal == 0 || lastAccrualAt == 0 || block.timestamp <= lastAccrualAt) {
            return 0;
        }
        uint256 elapsed = block.timestamp - lastAccrualAt;
        return (principal * APY_BPS * elapsed) / (BPS_DENOMINATOR * SECONDS_PER_YEAR);
    }

    /// @notice Remove fully-drained lots from the array to keep iteration cheap.
    function _compactLots(address user) internal {
        Lot[] storage lots = _stakes[user].lots;
        uint256 write = 0;
        uint256 len = lots.length;
        for (uint256 read = 0; read < len; read++) {
            if (lots[read].amount == 0) continue;
            if (write != read) {
                lots[write] = lots[read];
            }
            write++;
        }
        // Truncate trailing slots
        while (lots.length > write) {
            lots.pop();
        }
    }
}
