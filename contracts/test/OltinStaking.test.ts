import { expect } from "chai";
import { ethers } from "hardhat";
import { time } from "@nomicfoundation/hardhat-network-helpers";

const SEVEN_DAYS = 7 * 24 * 3600;
const APY_BPS = 700n;
const BPS = 10_000n;
const SECONDS_PER_YEAR = 365n * 24n * 3600n;

function expectedReward(principal: bigint, elapsedSec: bigint): bigint {
  return (principal * APY_BPS * elapsedSec) / (BPS * SECONDS_PER_YEAR);
}

describe("OltinStaking", function () {
  async function deploy() {
    const [admin, user1, user2] = await ethers.getSigners();

    // Deploy a fresh OLTIN-like ERC20 for testing (use UZD as a stand-in
    // — same interface, simpler than spinning up the full OltinTokenV2)
    const UZD = await ethers.getContractFactory("UZD");
    const oltin = await UZD.deploy();
    await oltin.waitForDeployment();

    const Staking = await ethers.getContractFactory("OltinStaking");
    const staking = await Staking.deploy(await oltin.getAddress());
    await staking.waitForDeployment();

    // Mint OLTIN to the test users + admin
    const big = ethers.parseUnits("10000", 18);
    await oltin.connect(admin).mint(admin.address, big);
    await oltin.connect(admin).mint(user1.address, big);
    await oltin.connect(admin).mint(user2.address, big);

    return { staking, oltin, admin, user1, user2 };
  }

  describe("constructor", function () {
    it("reverts on zero token address", async function () {
      const Staking = await ethers.getContractFactory("OltinStaking");
      await expect(Staking.deploy(ethers.ZeroAddress))
        .to.be.revertedWith("Zero token address");
    });

    it("grants all roles to deployer", async function () {
      const { staking, admin } = await deploy();
      const ADMIN = await staking.DEFAULT_ADMIN_ROLE();
      const PAUSER = await staking.PAUSER_ROLE();
      const FUNDER = await staking.FUNDER_ROLE();
      expect(await staking.hasRole(ADMIN, admin.address)).to.be.true;
      expect(await staking.hasRole(PAUSER, admin.address)).to.be.true;
      expect(await staking.hasRole(FUNDER, admin.address)).to.be.true;
    });

    it("exposes constants", async function () {
      const { staking } = await deploy();
      expect(await staking.APY_BPS()).to.equal(700n);
      expect(await staking.LOCK_PERIOD()).to.equal(BigInt(SEVEN_DAYS));
    });
  });

  describe("stake", function () {
    it("transfers OLTIN, creates a locked lot, increases totals", async function () {
      const { staking, oltin, user1 } = await deploy();
      const amount = ethers.parseUnits("100", 18);
      await oltin.connect(user1).approve(await staking.getAddress(), amount);
      const tx = await staking.connect(user1).stake(amount);
      const receipt = await tx.wait();
      const ts = (await ethers.provider.getBlock(receipt!.blockNumber!))!.timestamp;

      expect(await staking.totalStaked()).to.equal(amount);
      const info = await staking.getStakeInfo(user1.address);
      expect(info.totalPrincipal).to.equal(amount);
      expect(info.unlocked).to.equal(0n);
      expect(info.lotCount).to.equal(1n);
      expect(info.nextUnlockAt).to.equal(BigInt(ts + SEVEN_DAYS));
      expect(await oltin.balanceOf(await staking.getAddress())).to.equal(amount);
    });

    it("reverts on zero amount", async function () {
      const { staking, user1 } = await deploy();
      await expect(staking.connect(user1).stake(0))
        .to.be.revertedWith("Zero amount");
    });

    it("multiple deposits create multiple lots, do NOT extend old locks", async function () {
      const { staking, oltin, user1 } = await deploy();
      const stk = await staking.getAddress();
      const a = ethers.parseUnits("100", 18);
      const b = ethers.parseUnits("50", 18);
      await oltin.connect(user1).approve(stk, a + b);

      await staking.connect(user1).stake(a);
      const firstStakeTs = await time.latest();

      // Wait 4 days, then second stake — first lot still has 3 days lock left
      await time.increase(4 * 24 * 3600);
      await staking.connect(user1).stake(b);

      const info = await staking.getStakeInfo(user1.address);
      expect(info.totalPrincipal).to.equal(a + b);
      expect(info.lotCount).to.equal(2n);

      // First lot unlocks at firstStakeTs + 7d, second at now + 7d
      const lot0 = await staking.getLot(user1.address, 0);
      const lot1 = await staking.getLot(user1.address, 1);
      expect(lot0.lockedUntil).to.equal(BigInt(firstStakeTs + SEVEN_DAYS));
      expect(lot1.lockedUntil).to.be.gt(lot0.lockedUntil);
    });
  });

  describe("unstake — per-deposit lock", function () {
    it("reverts while only locked principal exists", async function () {
      const { staking, oltin, user1 } = await deploy();
      const amount = ethers.parseUnits("100", 18);
      await oltin.connect(user1).approve(await staking.getAddress(), amount);
      await staking.connect(user1).stake(amount);
      await expect(staking.connect(user1).unstake(amount))
        .to.be.revertedWith("Insufficient unlocked principal");
    });

    it("allows unstake of unlocked lot while keeping new lot locked", async function () {
      const { staking, oltin, user1 } = await deploy();
      const stk = await staking.getAddress();
      const a = ethers.parseUnits("100", 18);
      const b = ethers.parseUnits("50", 18);
      await oltin.connect(user1).approve(stk, a + b);

      await staking.connect(user1).stake(a);
      // Wait past first lock
      await time.increase(SEVEN_DAYS + 1);

      // Now do a second stake — fresh lock on b, but a is unlocked
      await staking.connect(user1).stake(b);

      // Can unstake `a` (unlocked), but not `b`
      const balBefore = await oltin.balanceOf(user1.address);
      await staking.connect(user1).unstake(a);
      const balAfter = await oltin.balanceOf(user1.address);
      expect(balAfter - balBefore).to.equal(a);

      // Try unstake more — reverts (b is still locked)
      await expect(staking.connect(user1).unstake(1n))
        .to.be.revertedWith("Insufficient unlocked principal");

      const info = await staking.getStakeInfo(user1.address);
      expect(info.totalPrincipal).to.equal(b);
      expect(info.unlocked).to.equal(0n);
    });

    it("unstaking part of unlocked principal works and compacts lots", async function () {
      const { staking, oltin, user1 } = await deploy();
      const stk = await staking.getAddress();
      const a = ethers.parseUnits("100", 18);
      await oltin.connect(user1).approve(stk, a);
      await staking.connect(user1).stake(a);
      await time.increase(SEVEN_DAYS + 1);

      await staking.connect(user1).unstake(a / 2n);
      const info = await staking.getStakeInfo(user1.address);
      expect(info.totalPrincipal).to.equal(a / 2n);
      expect(info.unlocked).to.equal(a / 2n);
      // Lot still exists with remaining amount
      expect(info.lotCount).to.equal(1n);

      // Drain rest, lot should be compacted away
      await staking.connect(user1).unstake(a / 2n);
      const info2 = await staking.getStakeInfo(user1.address);
      expect(info2.totalPrincipal).to.equal(0n);
      expect(info2.lotCount).to.equal(0n);
    });
  });

  describe("reward accrual", function () {
    it("accrues 7% APY pro-rata", async function () {
      const { staking, oltin, user1 } = await deploy();
      const amount = ethers.parseUnits("1000", 18);
      await oltin.connect(user1).approve(await staking.getAddress(), amount);
      await staking.connect(user1).stake(amount);

      // Warp 30 days
      await time.increase(30 * 24 * 3600);
      const pending = await staking.pendingReward(user1.address);
      const expected = expectedReward(amount, BigInt(30 * 24 * 3600));
      // Allow tiny rounding (off by 1 wei due to integer division order)
      expect(pending).to.be.closeTo(expected, 10n);
    });

    it("accrues correctly across multiple stakes via _accrue on touch", async function () {
      const { staking, oltin, user1 } = await deploy();
      const stk = await staking.getAddress();
      const a = ethers.parseUnits("1000", 18);
      const b = ethers.parseUnits("500", 18);
      await oltin.connect(user1).approve(stk, a + b);

      await staking.connect(user1).stake(a);
      await time.increase(10 * 24 * 3600); // 10 days on a alone
      await staking.connect(user1).stake(b);
      await time.increase(10 * 24 * 3600); // 10 days on (a + b)

      const pending = await staking.pendingReward(user1.address);
      const expected =
        expectedReward(a, BigInt(10 * 24 * 3600)) +
        expectedReward(a + b, BigInt(10 * 24 * 3600));
      // Allow jitter from extra block timestamps in stake/_accrue calls
      expect(pending).to.be.closeTo(expected, ethers.parseUnits("0.0001", 18));
    });
  });

  describe("claim and compound", function () {
    it("claim transfers reward and decreases pool", async function () {
      const { staking, oltin, admin, user1 } = await deploy();
      const stk = await staking.getAddress();
      const stake = ethers.parseUnits("1000", 18);
      const pool = ethers.parseUnits("100", 18);
      await oltin.connect(user1).approve(stk, stake);
      await staking.connect(user1).stake(stake);
      await oltin.connect(admin).approve(stk, pool);
      await staking.connect(admin).fundRewardPool(pool);

      await time.increase(30 * 24 * 3600);
      const pendingBefore = await staking.pendingReward(user1.address);
      const balBefore = await oltin.balanceOf(user1.address);

      await staking.connect(user1).claim();
      const balAfter = await oltin.balanceOf(user1.address);

      // Allow jitter from extra block timestamp during claim itself
      const tolerance = ethers.parseUnits("0.0001", 18);
      expect(balAfter - balBefore).to.be.closeTo(pendingBefore, tolerance);
      expect(await staking.rewardPool()).to.be.closeTo(pool - pendingBefore, tolerance);
    });

    it("claim returns 0 when reward is 0", async function () {
      const { staking, user1 } = await deploy();
      // No stake, no time passed
      await staking.connect(user1).claim();
      expect(await staking.pendingReward(user1.address)).to.equal(0n);
    });

    it("claim caps at rewardPool when pool is short", async function () {
      const { staking, oltin, admin, user1 } = await deploy();
      const stk = await staking.getAddress();
      const stake = ethers.parseUnits("1000", 18);
      await oltin.connect(user1).approve(stk, stake);
      await staking.connect(user1).stake(stake);

      // Tiny pool of 1 wei
      await oltin.connect(admin).approve(stk, 1n);
      await staking.connect(admin).fundRewardPool(1n);

      await time.increase(30 * 24 * 3600);
      const balBefore = await oltin.balanceOf(user1.address);
      await staking.connect(user1).claim();
      const balAfter = await oltin.balanceOf(user1.address);

      expect(balAfter - balBefore).to.equal(1n);
      expect(await staking.rewardPool()).to.equal(0n);
      // Remaining unpaid reward sits in unclaimedReward
      expect(await staking.pendingReward(user1.address)).to.be.gt(0n);
    });

    it("compound moves reward to a new locked lot", async function () {
      const { staking, oltin, admin, user1 } = await deploy();
      const stk = await staking.getAddress();
      const stake = ethers.parseUnits("1000", 18);
      const pool = ethers.parseUnits("100", 18);
      await oltin.connect(user1).approve(stk, stake);
      await staking.connect(user1).stake(stake);
      await oltin.connect(admin).approve(stk, pool);
      await staking.connect(admin).fundRewardPool(pool);

      await time.increase(30 * 24 * 3600);
      const pBefore = (await staking.getStakeInfo(user1.address)).totalPrincipal;
      const lotsBefore = (await staking.getStakeInfo(user1.address)).lotCount;
      await staking.connect(user1).compound();
      const info = await staking.getStakeInfo(user1.address);
      expect(info.totalPrincipal).to.be.gt(pBefore);
      expect(info.lotCount).to.equal(lotsBefore + 1n);
    });
  });

  describe("admin pool management", function () {
    it("non-funder cannot fund", async function () {
      const { staking, user1 } = await deploy();
      await expect(staking.connect(user1).fundRewardPool(100n))
        .to.be.revertedWithCustomError(staking, "AccessControlUnauthorizedAccount");
    });

    it("admin can withdraw unallocated pool", async function () {
      const { staking, oltin, admin } = await deploy();
      const pool = ethers.parseUnits("100", 18);
      await oltin.connect(admin).approve(await staking.getAddress(), pool);
      await staking.connect(admin).fundRewardPool(pool);

      const balBefore = await oltin.balanceOf(admin.address);
      await staking.connect(admin).withdrawRewardPool(pool);
      const balAfter = await oltin.balanceOf(admin.address);
      expect(balAfter - balBefore).to.equal(pool);
      expect(await staking.rewardPool()).to.equal(0n);
    });

    it("withdraw cannot exceed pool (cannot touch user principal)", async function () {
      const { staking, oltin, admin, user1 } = await deploy();
      const stk = await staking.getAddress();
      const stake = ethers.parseUnits("1000", 18);
      await oltin.connect(user1).approve(stk, stake);
      await staking.connect(user1).stake(stake);
      // pool is 0; admin tries to withdraw user principal
      await expect(staking.connect(admin).withdrawRewardPool(1n))
        .to.be.revertedWith("Invalid amount");
    });
  });

  describe("pause", function () {
    it("blocks stake/unstake/claim/compound when paused", async function () {
      const { staking, oltin, admin, user1 } = await deploy();
      const stk = await staking.getAddress();
      await oltin.connect(user1).approve(stk, 100n);
      await staking.connect(admin).pause();
      await expect(staking.connect(user1).stake(100n))
        .to.be.revertedWithCustomError(staking, "EnforcedPause");
    });
  });
});
