import { expect } from "chai";
import { ethers } from "hardhat";
import { time } from "@nomicfoundation/hardhat-network-helpers";
import { parseUnits, ZeroAddress } from "ethers";

// Money-path constants — MUST mirror Exchange.sol.
const GRAMS = 3110347680n; // grams per troy oz * 1e8
const E8 = 100000000n; // 1e8
const XAU_ANS = 330000000000n; // 3300 USD/oz @ 8 decimals
const UZS_ANS = 7937n; // ~0.00007937 USD/UZS @ 8 decimals
// Per-feed staleness windows, deliberately DIFFERENT so a mutant that swaps
// maxAgeXau <-> maxAgeUzs (or points a feed at the wrong window) is caught.
const MAX_AGE_XAU = 900n; // short: XAU is relayed frequently
const MAX_AGE_UZS = 259200n; // 3 days: CBU posts ~daily (survives weekend gaps)
const MAX_AGE_RESERVE = 3600n;
const RESERVE_GRAMS = 1000000000n; // 1e9 grams — far above anything minted here

// Exact integer-floor mirror of the on-chain mulDiv formulas.
function expectedBuy(uzdIn: bigint, xau = XAU_ANS, uzs = UZS_ANS): bigint {
  return (uzdIn * (uzs * GRAMS)) / (E8 * xau);
}
function buyRemainder(uzdIn: bigint, xau = XAU_ANS, uzs = UZS_ANS): bigint {
  return (uzdIn * (uzs * GRAMS)) % (E8 * xau);
}
function expectedSell(oltinIn: bigint, xau = XAU_ANS, uzs = UZS_ANS): bigint {
  return (oltinIn * (xau * E8)) / (GRAMS * uzs);
}
function sellRemainder(oltinIn: bigint, xau = XAU_ANS, uzs = UZS_ANS): bigint {
  return (oltinIn * (xau * E8)) % (GRAMS * uzs);
}

describe("Exchange", function () {
  async function deploy() {
    const [admin, user1, user2] = await ethers.getSigners();

    const Attestor = await ethers.getContractFactory("Attestor");
    const reserve = await Attestor.deploy(0);
    const xau = await Attestor.deploy(8);
    const uzs = await Attestor.deploy(8);
    await reserve.waitForDeployment();
    await xau.waitForDeployment();
    await uzs.waitForDeployment();

    await reserve.postAnswer(RESERVE_GRAMS);
    await xau.postAnswer(XAU_ANS);
    await uzs.postAnswer(UZS_ANS);

    const Token = await ethers.getContractFactory("OltinTokenV3");
    const oltin = await Token.deploy(
      await reserve.getAddress(),
      MAX_AGE_RESERVE,
      admin.address,
    );
    await oltin.waitForDeployment();

    const UZD = await ethers.getContractFactory("UZD");
    const uzd = await UZD.deploy();
    await uzd.waitForDeployment();

    const Exchange = await ethers.getContractFactory("Exchange");
    const exchange = await Exchange.deploy(
      await oltin.getAddress(),
      await uzd.getAddress(),
      await xau.getAddress(),
      await uzs.getAddress(),
      MAX_AGE_XAU,
      MAX_AGE_UZS,
    );
    await exchange.waitForDeployment();

    // The Exchange is the SOLE OLTIN minter.
    const MINTER = await oltin.MINTER_ROLE();
    await oltin.connect(admin).grantRole(MINTER, await exchange.getAddress());

    // Seed users with UZD.
    const seed = parseUnits("100000000", 18); // 100M UZD
    await uzd.connect(admin).mint(user1.address, seed);
    await uzd.connect(admin).mint(user2.address, seed);

    return { exchange, oltin, uzd, reserve, xau, uzs, admin, user1, user2 };
  }

  // Fresh stack using the MaliciousReentrant token in place of UZD.
  async function deployMalicious() {
    const [admin, user1] = await ethers.getSigners();

    const Attestor = await ethers.getContractFactory("Attestor");
    const reserve = await Attestor.deploy(0);
    const xau = await Attestor.deploy(8);
    const uzs = await Attestor.deploy(8);
    await reserve.postAnswer(RESERVE_GRAMS);
    await xau.postAnswer(XAU_ANS);
    await uzs.postAnswer(UZS_ANS);

    const Token = await ethers.getContractFactory("OltinTokenV3");
    const oltin = await Token.deploy(
      await reserve.getAddress(),
      MAX_AGE_RESERVE,
      admin.address,
    );

    const Mal = await ethers.getContractFactory("MaliciousReentrant");
    const mal = await Mal.deploy();

    const Exchange = await ethers.getContractFactory("Exchange");
    const exchange = await Exchange.deploy(
      await oltin.getAddress(),
      await mal.getAddress(),
      await xau.getAddress(),
      await uzs.getAddress(),
      MAX_AGE_XAU,
      MAX_AGE_UZS,
    );

    const MINTER = await oltin.MINTER_ROLE();
    await oltin.connect(admin).grantRole(MINTER, await exchange.getAddress());
    await mal.setExchange(await exchange.getAddress());
    await mal.mint(user1.address, parseUnits("100000000", 18));

    return { exchange, oltin, mal, admin, user1 };
  }

  describe("constructor zero-address guards", function () {
    // Every address arg must be non-zero, with the pinned reason "Zero address".
    async function validArgs() {
      const { oltin, uzd, xau, uzs } = await deploy();
      return {
        oltin: await oltin.getAddress(),
        uzd: await uzd.getAddress(),
        xau: await xau.getAddress(),
        uzs: await uzs.getAddress(),
      };
    }

    it("reverts when oltin is address(0)", async function () {
      const a = await validArgs();
      const Exchange = await ethers.getContractFactory("Exchange");
      await expect(
        Exchange.deploy(ZeroAddress, a.uzd, a.xau, a.uzs, MAX_AGE_XAU, MAX_AGE_UZS),
      ).to.be.revertedWith("Zero address");
    });

    it("reverts when uzd is address(0)", async function () {
      const a = await validArgs();
      const Exchange = await ethers.getContractFactory("Exchange");
      await expect(
        Exchange.deploy(a.oltin, ZeroAddress, a.xau, a.uzs, MAX_AGE_XAU, MAX_AGE_UZS),
      ).to.be.revertedWith("Zero address");
    });

    it("reverts when xauFeed is address(0)", async function () {
      const a = await validArgs();
      const Exchange = await ethers.getContractFactory("Exchange");
      await expect(
        Exchange.deploy(a.oltin, a.uzd, ZeroAddress, a.uzs, MAX_AGE_XAU, MAX_AGE_UZS),
      ).to.be.revertedWith("Zero address");
    });

    it("reverts when uzsFeed is address(0)", async function () {
      const a = await validArgs();
      const Exchange = await ethers.getContractFactory("Exchange");
      await expect(
        Exchange.deploy(a.oltin, a.uzd, a.xau, ZeroAddress, MAX_AGE_XAU, MAX_AGE_UZS),
      ).to.be.revertedWith("Zero address");
    });
  });

  describe("buy", function () {
    it("mints OLTIN by the formula and routes UZD to the treasury", async function () {
      const { exchange, oltin, uzd, user1 } = await deploy();
      const uzdIn = parseUnits("1000000", 18); // 1M UZD
      const out = expectedBuy(uzdIn);
      expect(out).to.be.greaterThan(0n);

      const uzdBefore = await uzd.balanceOf(user1.address);
      await uzd.connect(user1).approve(await exchange.getAddress(), uzdIn);
      await expect(exchange.connect(user1).buy(uzdIn, 1n))
        .to.emit(exchange, "Bought")
        .withArgs(user1.address, uzdIn, out, XAU_ANS, UZS_ANS);

      expect(await oltin.balanceOf(user1.address)).to.equal(out);
      expect(await oltin.totalSupply()).to.equal(out);
      expect(await exchange.treasuryBalance()).to.equal(uzdIn);
      expect(await uzd.balanceOf(await exchange.getAddress())).to.equal(uzdIn);
      expect(await uzd.balanceOf(user1.address)).to.equal(uzdBefore - uzdIn);
    });

    it("reverts when the XAU feed is stale", async function () {
      const { exchange, uzd, uzs, user1 } = await deploy();
      const uzdIn = parseUnits("1000000", 18);
      await uzd.connect(user1).approve(await exchange.getAddress(), uzdIn);
      await time.increase(Number(MAX_AGE_XAU) + 1);
      await uzs.postAnswer(UZS_ANS); // keep UZS fresh, XAU stays stale
      await expect(
        exchange.connect(user1).buy(uzdIn, 1n),
      ).to.be.revertedWith("price stale");
    });

    it("reverts when the UZS feed is stale", async function () {
      const { exchange, uzd, xau, user1 } = await deploy();
      const uzdIn = parseUnits("1000000", 18);
      await uzd.connect(user1).approve(await exchange.getAddress(), uzdIn);
      // Advance past the (much larger) UZS window; re-post XAU so ONLY UZS is
      // stale — proving buy checks the UZS feed against maxAgeUzs, not maxAgeXau.
      await time.increase(Number(MAX_AGE_UZS) + 1);
      await xau.postAnswer(XAU_ANS); // keep XAU fresh, UZS stays stale
      await expect(
        exchange.connect(user1).buy(uzdIn, 1n),
      ).to.be.revertedWith("price stale");
    });

    it("reverts a dust buy that rounds to 0 OLTIN (no silent UZD grab)", async function () {
      const { exchange, uzd, user1 } = await deploy();
      expect(expectedBuy(1n)).to.equal(0n); // 1 wei UZD -> 0 OLTIN
      await uzd.connect(user1).approve(await exchange.getAddress(), 1n);
      const uzdBefore = await uzd.balanceOf(user1.address);
      await expect(
        exchange.connect(user1).buy(1n, 1n),
      ).to.be.revertedWith("dust");
      // no UZD was pulled
      expect(await uzd.balanceOf(user1.address)).to.equal(uzdBefore);
    });

    it("reverts when minOltinOut is 0", async function () {
      const { exchange, uzd, user1 } = await deploy();
      const uzdIn = parseUnits("1000000", 18);
      await uzd.connect(user1).approve(await exchange.getAddress(), uzdIn);
      await expect(
        exchange.connect(user1).buy(uzdIn, 0n),
      ).to.be.revertedWith("dust");
    });

    it("reverts on slippage (minOltinOut unmet)", async function () {
      const { exchange, uzd, user1 } = await deploy();
      const uzdIn = parseUnits("1000000", 18);
      const out = expectedBuy(uzdIn);
      await uzd.connect(user1).approve(await exchange.getAddress(), uzdIn);
      await expect(
        exchange.connect(user1).buy(uzdIn, out + 1n),
      ).to.be.revertedWith("dust");
    });

    it("reverts on zero UZD in", async function () {
      const { exchange, user1 } = await deploy();
      await expect(
        exchange.connect(user1).buy(0n, 1n),
      ).to.be.revertedWith("Zero amount");
    });
  });

  describe("sell", function () {
    // buy first so the user holds OLTIN and the treasury holds UZD.
    async function seededSell() {
      const ctx = await deploy();
      const { exchange, oltin, uzd, user1 } = ctx;
      const uzdIn = parseUnits("2000000", 18); // 2M UZD
      await uzd.connect(user1).approve(await exchange.getAddress(), uzdIn);
      await exchange.connect(user1).buy(uzdIn, 1n);
      return { ...ctx, uzdIn };
    }

    it("burns OLTIN (reduces totalSupply) and pays UZD by the formula", async function () {
      const { exchange, oltin, uzd, user1 } = await seededSell();
      const oltinIn = await oltin.balanceOf(user1.address);
      const supplyBefore = await oltin.totalSupply();
      const uzdBefore = await uzd.balanceOf(user1.address);
      const out = expectedSell(oltinIn);
      expect(out).to.be.greaterThan(0n);

      await oltin.connect(user1).approve(await exchange.getAddress(), oltinIn);
      await expect(exchange.connect(user1).sell(oltinIn, 1n))
        .to.emit(exchange, "Sold")
        .withArgs(user1.address, oltinIn, out, XAU_ANS, UZS_ANS);

      expect(await oltin.balanceOf(user1.address)).to.equal(0n);
      expect(await oltin.totalSupply()).to.equal(supplyBefore - oltinIn);
      expect(await uzd.balanceOf(user1.address)).to.equal(uzdBefore + out);
    });

    it("reverts BEFORE any state change when the treasury is short", async function () {
      // Fresh Exchange whose treasury is empty; mint OLTIN to user directly.
      const { exchange, oltin, admin, user1 } = await deploy();
      const MINTER = await oltin.MINTER_ROLE();
      await oltin.connect(admin).grantRole(MINTER, admin.address);
      const oltinIn = parseUnits("1", 18);
      await oltin.connect(admin).mint(user1.address, oltinIn);

      const supplyBefore = await oltin.totalSupply();
      await oltin.connect(user1).approve(await exchange.getAddress(), oltinIn);
      await expect(
        exchange.connect(user1).sell(oltinIn, 0n),
      ).to.be.revertedWith("treasury empty");

      // no state change: OLTIN not burned.
      expect(await oltin.balanceOf(user1.address)).to.equal(oltinIn);
      expect(await oltin.totalSupply()).to.equal(supplyBefore);
    });

    it("reverts on slippage (minUzdOut unmet)", async function () {
      const { exchange, oltin, user1 } = await seededSell();
      const oltinIn = await oltin.balanceOf(user1.address);
      const out = expectedSell(oltinIn);
      await oltin.connect(user1).approve(await exchange.getAddress(), oltinIn);
      await expect(
        exchange.connect(user1).sell(oltinIn, out + 1n),
      ).to.be.revertedWith("slippage");
    });

    it("reverts without an OLTIN allowance to the Exchange (non-custodial)", async function () {
      const { exchange, oltin, user1 } = await seededSell();
      const oltinIn = await oltin.balanceOf(user1.address);
      // user1 does NOT approve the Exchange to burn.
      await expect(
        exchange.connect(user1).sell(oltinIn, 1n),
      ).to.be.revertedWithCustomError(oltin, "ERC20InsufficientAllowance");
    });

    it("a caller cannot redeem another holder's gold via sell", async function () {
      // user2 buys and holds OLTIN; user1 holds none. user1 cannot cause
      // user2's OLTIN to be burned — sell only ever burns msg.sender.
      const { exchange, oltin, uzd, user1, user2 } = await deploy();
      const uzdIn = parseUnits("2000000", 18);
      await uzd.connect(user2).approve(await exchange.getAddress(), uzdIn);
      await exchange.connect(user2).buy(uzdIn, 1n);
      const victimBalBefore = await oltin.balanceOf(user2.address);

      const amt = parseUnits("0.1", 18);
      await oltin.connect(user1).approve(await exchange.getAddress(), amt);
      await expect(
        exchange.connect(user1).sell(amt, 0n),
      ).to.be.revertedWithCustomError(oltin, "ERC20InsufficientBalance");
      // victim untouched.
      expect(await oltin.balanceOf(user2.address)).to.equal(victimBalBefore);
    });

    it("reverts on zero OLTIN in", async function () {
      const { exchange, user1 } = await deploy();
      await expect(
        exchange.connect(user1).sell(0n, 0n),
      ).to.be.revertedWith("Zero amount");
    });
  });

  describe("rounding is always protocol-safe (floored)", function () {
    it("buy rounds DOWN — user never receives extra OLTIN", async function () {
      const { exchange, oltin, uzd, user1 } = await deploy();
      const uzdIn = parseUnits("1234567", 18) + 7n; // awkward amount
      const out = expectedBuy(uzdIn);
      expect(buyRemainder(uzdIn)).to.not.equal(0n); // genuinely a rounding case
      await uzd.connect(user1).approve(await exchange.getAddress(), uzdIn);
      await exchange.connect(user1).buy(uzdIn, 1n);
      expect(await oltin.balanceOf(user1.address)).to.equal(out); // floored, not ceil
    });

    it("sell rounds DOWN — protocol never overpays UZD", async function () {
      const { exchange, oltin, uzd, user1 } = await deploy();
      const uzdIn = parseUnits("5000000", 18);
      await uzd.connect(user1).approve(await exchange.getAddress(), uzdIn);
      await exchange.connect(user1).buy(uzdIn, 1n);

      const oltinIn = (await oltin.balanceOf(user1.address)) - 3n; // awkward
      expect(sellRemainder(oltinIn)).to.not.equal(0n);
      const out = expectedSell(oltinIn);
      const uzdBefore = await uzd.balanceOf(user1.address);
      await oltin.connect(user1).approve(await exchange.getAddress(), oltinIn);
      await exchange.connect(user1).sell(oltinIn, 1n);
      expect(await uzd.balanceOf(user1.address)).to.equal(uzdBefore + out); // floored
    });
  });

  describe("reentrancy is blocked", function () {
    it("reverts a re-entrant buy via a malicious UZD token", async function () {
      const { exchange, mal, user1 } = await deployMalicious();
      const uzdIn = parseUnits("1000000", 18);
      await mal.connect(user1).approve(await exchange.getAddress(), uzdIn);
      await mal.setAttackBuy(true);
      await expect(
        exchange.connect(user1).buy(uzdIn, 1n),
      ).to.be.revertedWithCustomError(exchange, "ReentrancyGuardReentrantCall");
    });

    it("reverts a re-entrant sell via a malicious UZD token", async function () {
      const { exchange, oltin, mal, user1 } = await deployMalicious();
      const uzdIn = parseUnits("2000000", 18);
      // normal buy first (attack off): user1 gets OLTIN, treasury funded.
      await mal.connect(user1).approve(await exchange.getAddress(), uzdIn);
      await exchange.connect(user1).buy(uzdIn, 1n);

      const oltinIn = await oltin.balanceOf(user1.address);
      await oltin.connect(user1).approve(await exchange.getAddress(), oltinIn);
      await mal.setAttackSell(true);
      await expect(
        exchange.connect(user1).sell(oltinIn, 0n),
      ).to.be.revertedWithCustomError(exchange, "ReentrancyGuardReentrantCall");
    });
  });

  describe("price staleness boundary (two-sided)", function () {
    // Kills a `<=` -> `<` mutant on each feed's staleness guard: age EXACTLY ==
    // maxAge must PASS, age == maxAge + 1 must REVERT. setNextBlockTimestamp
    // pins the exact age at the buy block.
    it("XAU: age == maxAgeXau passes", async function () {
      const { exchange, uzd, xau, user1 } = await deploy();
      const uzdIn = parseUnits("1000000", 18);
      await uzd.connect(user1).approve(await exchange.getAddress(), uzdIn);
      await xau.postAnswer(XAU_ANS);
      const xauUpd = BigInt(await time.latest());
      await time.setNextBlockTimestamp(Number(xauUpd + MAX_AGE_XAU));
      await expect(exchange.connect(user1).buy(uzdIn, 1n)).to.emit(
        exchange,
        "Bought",
      );
    });

    it("XAU: age == maxAgeXau + 1 reverts (price stale)", async function () {
      const { exchange, uzd, xau, user1 } = await deploy();
      const uzdIn = parseUnits("1000000", 18);
      await uzd.connect(user1).approve(await exchange.getAddress(), uzdIn);
      await xau.postAnswer(XAU_ANS);
      const xauUpd = BigInt(await time.latest());
      await time.setNextBlockTimestamp(Number(xauUpd + MAX_AGE_XAU + 1n));
      await expect(
        exchange.connect(user1).buy(uzdIn, 1n),
      ).to.be.revertedWith("price stale");
    });

    it("UZS: age == maxAgeUzs passes", async function () {
      const { exchange, uzd, reserve, xau, uzs, user1 } = await deploy();
      const uzdIn = parseUnits("1000000", 18);
      await uzd.connect(user1).approve(await exchange.getAddress(), uzdIn);
      await uzs.postAnswer(UZS_ANS);
      const uzsUpd = BigInt(await time.latest());
      // maxAgeUzs (3 days) is well past the reserve/XAU windows, so re-post both
      // just before the buy — ONLY the UZS age sits at its boundary.
      await time.setNextBlockTimestamp(Number(uzsUpd + MAX_AGE_UZS - 2n));
      await reserve.postAnswer(RESERVE_GRAMS);
      await time.setNextBlockTimestamp(Number(uzsUpd + MAX_AGE_UZS - 1n));
      await xau.postAnswer(XAU_ANS);
      await time.setNextBlockTimestamp(Number(uzsUpd + MAX_AGE_UZS));
      await expect(exchange.connect(user1).buy(uzdIn, 1n)).to.emit(
        exchange,
        "Bought",
      );
    });

    it("UZS: age == maxAgeUzs + 1 reverts (price stale)", async function () {
      const { exchange, uzd, xau, uzs, user1 } = await deploy();
      const uzdIn = parseUnits("1000000", 18);
      await uzd.connect(user1).approve(await exchange.getAddress(), uzdIn);
      await uzs.postAnswer(UZS_ANS);
      const uzsUpd = BigInt(await time.latest());
      // Re-post XAU fresh right before the buy so the revert is due to UZS only.
      await time.setNextBlockTimestamp(Number(uzsUpd + MAX_AGE_UZS));
      await xau.postAnswer(XAU_ANS);
      await time.setNextBlockTimestamp(Number(uzsUpd + MAX_AGE_UZS + 1n));
      await expect(
        exchange.connect(user1).buy(uzdIn, 1n),
      ).to.be.revertedWith("price stale");
    });
  });

  describe("respects the OLTIN pause (cross-contract)", function () {
    it("buy reverts when OLTIN is paused (mint blocked)", async function () {
      const { exchange, oltin, uzd, admin, user1 } = await deploy();
      const uzdIn = parseUnits("1000000", 18);
      await uzd.connect(user1).approve(await exchange.getAddress(), uzdIn);
      await oltin.connect(admin).pause();
      await expect(
        exchange.connect(user1).buy(uzdIn, 1n),
      ).to.be.revertedWithCustomError(oltin, "EnforcedPause");
    });

    it("sell reverts when OLTIN is paused (burnFrom blocked)", async function () {
      // Buy first (unpaused) so user holds OLTIN and the treasury holds UZD.
      const { exchange, oltin, uzd, admin, user1 } = await deploy();
      const uzdIn = parseUnits("2000000", 18);
      await uzd.connect(user1).approve(await exchange.getAddress(), uzdIn);
      await exchange.connect(user1).buy(uzdIn, 1n);
      const oltinIn = await oltin.balanceOf(user1.address);
      await oltin.connect(user1).approve(await exchange.getAddress(), oltinIn);
      await oltin.connect(admin).pause();
      await expect(
        exchange.connect(user1).sell(oltinIn, 1n),
      ).to.be.revertedWithCustomError(oltin, "EnforcedPause");
    });
  });

  describe("wiring", function () {
    it("exposes the treasury as the Exchange itself", async function () {
      const { exchange } = await deploy();
      expect(await exchange.treasury()).to.equal(await exchange.getAddress());
    });

    it("uses the pinned grams-per-ounce constant", async function () {
      const { exchange } = await deploy();
      expect(await exchange.GRAMS_PER_OZ_1E8()).to.equal(GRAMS);
    });
  });
});
