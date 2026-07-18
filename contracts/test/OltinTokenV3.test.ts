import { expect } from "chai";
import { ethers } from "hardhat";
import { time } from "@nomicfoundation/hardhat-network-helpers";
import { ZeroAddress } from "ethers";
import { anyValue } from "@nomicfoundation/hardhat-chai-matchers/withArgs";

const MAX_AGE_RESERVE = 3600n;
const E18 = 10n ** 18n;

// Does the ABI expose a function with this name?
function hasFn(contract: any, name: string): boolean {
  return contract.interface.fragments.some(
    (f: any) => f.type === "function" && f.name === name,
  );
}

describe("OltinTokenV3", function () {
  // Real Attestor (decimals 0 = raw grams) as the reserve feed.
  async function deploy() {
    const [admin, minter, user1, user2] = await ethers.getSigners();

    const Attestor = await ethers.getContractFactory("Attestor");
    const reserve = await Attestor.deploy(0);
    await reserve.waitForDeployment();

    const Token = await ethers.getContractFactory("OltinTokenV3");
    const token = await Token.deploy(
      await reserve.getAddress(),
      MAX_AGE_RESERVE,
      admin.address, // dormant feeCollector
    );
    await token.waitForDeployment();

    // Grant MINTER to the `minter` signer to stand in for the Exchange.
    const MINTER = await token.MINTER_ROLE();
    await token.connect(admin).grantRole(MINTER, minter.address);

    return { token, reserve, admin, minter, user1, user2 };
  }

  describe("metadata", function () {
    it("has correct name, symbol and decimals", async function () {
      const { token } = await deploy();
      expect(await token.name()).to.equal("Oltin Gold Token");
      expect(await token.symbol()).to.equal("OLTIN");
      expect(await token.decimals()).to.equal(18);
      expect(await token.totalSupply()).to.equal(0n);
    });

    it("caches reserveDecimals, reserveScale and maxAgeReserve", async function () {
      const { token, reserve } = await deploy();
      expect(await token.reserveDecimals()).to.equal(0);
      // reserveScale = 10**(18 - decimals); decimals 0 -> 1e18.
      expect(await token.reserveScale()).to.equal(E18);
      expect(await token.maxAgeReserve()).to.equal(MAX_AGE_RESERVE);
      expect(await token.reserveFeed()).to.equal(await reserve.getAddress());
    });
  });

  describe("roles (non-custodial surface)", function () {
    it("grants ADMIN + PAUSER to deployer but NOT MINTER", async function () {
      // Fresh deploy without the test-only MINTER grant.
      const [admin] = await ethers.getSigners();
      const Attestor = await ethers.getContractFactory("Attestor");
      const reserve = await Attestor.deploy(0);
      const Token = await ethers.getContractFactory("OltinTokenV3");
      const token = await Token.deploy(
        await reserve.getAddress(),
        MAX_AGE_RESERVE,
        admin.address,
      );
      const ADMIN = await token.DEFAULT_ADMIN_ROLE();
      const MINTER = await token.MINTER_ROLE();
      const PAUSER = await token.PAUSER_ROLE();
      expect(await token.hasRole(ADMIN, admin.address)).to.be.true;
      expect(await token.hasRole(PAUSER, admin.address)).to.be.true;
      expect(await token.hasRole(MINTER, admin.address)).to.be.false;
    });

    it("has NO BURNER_ROLE (no custodial admin burn)", async function () {
      const { token } = await deploy();
      expect(hasFn(token, "BURNER_ROLE")).to.be.false;
    });

    it("has NO adminTransfer (balances are never admin-movable)", async function () {
      const { token } = await deploy();
      expect(hasFn(token, "adminTransfer")).to.be.false;
    });
  });

  describe("constructor PoR validation", function () {
    it("constructs when the reserve feed reports decimals == 18 (boundary passes)", async function () {
      // Two-sided with the >18 case below: kills a `<= 18` -> `< 18` mutant that
      // would reject the exactly-18 boundary.
      const [admin] = await ethers.getSigners();
      const Mock = await ethers.getContractFactory("MockAttestor");
      const ok = await Mock.deploy(18, 1000n, await time.latest());
      const Token = await ethers.getContractFactory("OltinTokenV3");
      const token = await Token.deploy(
        await ok.getAddress(),
        MAX_AGE_RESERVE,
        admin.address,
      );
      await token.waitForDeployment();
      expect(await token.reserveDecimals()).to.equal(18);
      expect(await token.reserveScale()).to.equal(1n); // 10**(18-18)
    });

    it("reverts when the reserve feed reports decimals > 18", async function () {
      const [admin] = await ethers.getSigners();
      const Mock = await ethers.getContractFactory("MockAttestor");
      const bad = await Mock.deploy(19, 1000n, await time.latest());
      const Token = await ethers.getContractFactory("OltinTokenV3");
      await expect(
        Token.deploy(await bad.getAddress(), MAX_AGE_RESERVE, admin.address),
      ).to.be.revertedWith("reserve decimals>18");
    });

    it("reverts on a zero reserve-feed address", async function () {
      const [admin] = await ethers.getSigners();
      const Token = await ethers.getContractFactory("OltinTokenV3");
      await expect(
        Token.deploy(ZeroAddress, MAX_AGE_RESERVE, admin.address),
      ).to.be.reverted; // decimals() call on address(0) reverts
    });
  });

  describe("mint (Secure-Mint / Proof-of-Reserve)", function () {
    it("mints up to the attested reserve and emits Minted", async function () {
      const { token, reserve, minter, user1 } = await deploy();
      await reserve.postAnswer(1000n); // 1000 grams -> cap 1000e18
      const cap = 1000n * E18;
      await expect(token.connect(minter).mint(user1.address, cap))
        .to.emit(token, "Minted")
        .withArgs(user1.address, cap, anyValue);
      expect(await token.balanceOf(user1.address)).to.equal(cap);
      expect(await token.totalSupply()).to.equal(cap);
    });

    it("reverts one wei over the reserve cap (exceeds reserve)", async function () {
      const { token, reserve, minter, user1 } = await deploy();
      await reserve.postAnswer(1000n);
      const cap = 1000n * E18;
      await expect(
        token.connect(minter).mint(user1.address, cap + 1n),
      ).to.be.revertedWith("exceeds reserve");
    });

    it("respects the cap cumulatively across mints", async function () {
      const { token, reserve, minter, user1 } = await deploy();
      await reserve.postAnswer(1000n);
      const cap = 1000n * E18;
      await token.connect(minter).mint(user1.address, cap);
      await expect(
        token.connect(minter).mint(user1.address, 1n),
      ).to.be.revertedWith("exceeds reserve");
    });

    it("reverts when the reserve reading is stale", async function () {
      const { token, reserve, minter, user1 } = await deploy();
      await reserve.postAnswer(1000n);
      await time.increase(Number(MAX_AGE_RESERVE) + 1);
      await expect(
        token.connect(minter).mint(user1.address, 1n),
      ).to.be.revertedWith("reserve stale");
    });

    it("mints at exactly maxAgeReserve (staleness == boundary passes)", async function () {
      // Two-sided with the +1 case below: kills a `<= maxAge` -> `< maxAge`
      // mutant that would reject the exactly-maxAge boundary.
      const { token, reserve, minter, user1 } = await deploy();
      await reserve.postAnswer(1000n);
      const upd = BigInt(await time.latest());
      await time.setNextBlockTimestamp(Number(upd + MAX_AGE_RESERVE));
      await expect(token.connect(minter).mint(user1.address, 1n)).to.emit(
        token,
        "Minted",
      );
    });

    it("reverts one second past maxAgeReserve (staleness == boundary + 1)", async function () {
      const { token, reserve, minter, user1 } = await deploy();
      await reserve.postAnswer(1000n);
      const upd = BigInt(await time.latest());
      await time.setNextBlockTimestamp(Number(upd + MAX_AGE_RESERVE + 1n));
      await expect(
        token.connect(minter).mint(user1.address, 1n),
      ).to.be.revertedWith("reserve stale");
    });

    it("reverts when the reserve is zero (reserve<=0)", async function () {
      const { token, reserve, minter, user1 } = await deploy();
      await reserve.postAnswer(0n);
      await expect(
        token.connect(minter).mint(user1.address, 1n),
      ).to.be.revertedWith("reserve<=0");
    });

    it("reverts when the reserve is negative (reserve<=0)", async function () {
      const { token, reserve, minter, user1 } = await deploy();
      await reserve.postAnswer(-5n);
      await expect(
        token.connect(minter).mint(user1.address, 1n),
      ).to.be.revertedWith("reserve<=0");
    });

    it("reverts with named error (no underflow) on a future-dated reading", async function () {
      const [admin, minter, user1] = await ethers.getSigners();
      const now = await time.latest();
      const Mock = await ethers.getContractFactory("MockAttestor");
      // decimals 0, positive answer, updatedAt far in the future
      const mock = await Mock.deploy(0, 1000n, BigInt(now) + 100000n);
      const Token = await ethers.getContractFactory("OltinTokenV3");
      const token = await Token.deploy(
        await mock.getAddress(),
        MAX_AGE_RESERVE,
        admin.address,
      );
      const MINTER = await token.MINTER_ROLE();
      await token.connect(admin).grantRole(MINTER, minter.address);
      await expect(
        token.connect(minter).mint(user1.address, 1n),
      ).to.be.revertedWith("reserve stale");
    });

    it("scales a non-zero-decimals reserve feed (decimals 2 -> x1e16)", async function () {
      const [admin, minter, user1] = await ethers.getSigners();
      const Attestor = await ethers.getContractFactory("Attestor");
      const reserve2 = await Attestor.deploy(2); // e.g. grams with 2 decimals
      const Token = await ethers.getContractFactory("OltinTokenV3");
      const token = await Token.deploy(
        await reserve2.getAddress(),
        MAX_AGE_RESERVE,
        admin.address,
      );
      const MINTER = await token.MINTER_ROLE();
      await token.connect(admin).grantRole(MINTER, minter.address);

      // answer 100000 at 2 decimals = 1000.00 grams -> cap = 100000 * 1e16 = 1000e18
      await reserve2.postAnswer(100000n);
      const cap = 100000n * 10n ** 16n;
      expect(cap).to.equal(1000n * E18);
      await token.connect(minter).mint(user1.address, cap);
      await expect(
        token.connect(minter).mint(user1.address, 1n),
      ).to.be.revertedWith("exceeds reserve");
    });

    it("reverts for a non-minter (deployer is not a minter)", async function () {
      const { token, reserve, admin, user1 } = await deploy();
      await reserve.postAnswer(1000n);
      await expect(
        token.connect(admin).mint(user1.address, 1n),
      ).to.be.revertedWithCustomError(token, "AccessControlUnauthorizedAccount");
      await expect(
        token.connect(user1).mint(user1.address, 1n),
      ).to.be.revertedWithCustomError(token, "AccessControlUnauthorizedAccount");
    });

    it("reverts on zero address / zero amount", async function () {
      const { token, reserve, minter, user1 } = await deploy();
      await reserve.postAnswer(1000n);
      await expect(
        token.connect(minter).mint(ZeroAddress, 1n),
      ).to.be.revertedWith("Zero address");
      await expect(
        token.connect(minter).mint(user1.address, 0n),
      ).to.be.revertedWith("Zero amount");
    });
  });

  describe("pause", function () {
    it("blocks minting when paused", async function () {
      const { token, reserve, admin, minter, user1 } = await deploy();
      await reserve.postAnswer(1000n);
      await token.connect(admin).pause();
      await expect(
        token.connect(minter).mint(user1.address, 1n),
      ).to.be.revertedWithCustomError(token, "EnforcedPause");
    });

    it("blocks transfers when paused", async function () {
      const { token, reserve, admin, minter, user1, user2 } = await deploy();
      await reserve.postAnswer(1000n);
      await token.connect(minter).mint(user1.address, 100n);
      await token.connect(admin).pause();
      await expect(
        token.connect(user1).transfer(user2.address, 10n),
      ).to.be.revertedWithCustomError(token, "EnforcedPause");
    });

    it("only PAUSER can pause", async function () {
      const { token, user1 } = await deploy();
      await expect(
        token.connect(user1).pause(),
      ).to.be.revertedWithCustomError(token, "AccessControlUnauthorizedAccount");
    });
  });

  describe("burn (allowance-gated, non-custodial)", function () {
    it("public burnFrom with allowance reduces totalSupply", async function () {
      const { token, reserve, minter, user1, user2 } = await deploy();
      await reserve.postAnswer(1000n);
      const amt = 500n * E18;
      await token.connect(minter).mint(user1.address, amt);
      await token.connect(user1).approve(user2.address, 200n * E18);
      await token.connect(user2).burnFrom(user1.address, 200n * E18);
      expect(await token.balanceOf(user1.address)).to.equal(300n * E18);
      expect(await token.totalSupply()).to.equal(300n * E18);
    });

    it("burnFrom without allowance reverts (cannot burn another holder)", async function () {
      const { token, reserve, minter, user1, user2 } = await deploy();
      await reserve.postAnswer(1000n);
      await token.connect(minter).mint(user1.address, 100n * E18);
      await expect(
        token.connect(user2).burnFrom(user1.address, 50n * E18),
      ).to.be.revertedWithCustomError(token, "ERC20InsufficientAllowance");
    });

    it("holder can burn their own balance", async function () {
      const { token, reserve, minter, user1 } = await deploy();
      await reserve.postAnswer(1000n);
      await token.connect(minter).mint(user1.address, 100n * E18);
      await token.connect(user1).burn(40n * E18);
      expect(await token.totalSupply()).to.equal(60n * E18);
    });
  });

  describe("transferFeeBps is DORMANT in this release", function () {
    it("plain transfer moves the full amount, no fee siphoned", async function () {
      const { token, reserve, admin, minter, user1, user2 } = await deploy();
      await reserve.postAnswer(1000n);
      expect(await token.transferFeeBps()).to.equal(50n); // stored but dormant
      const amt = 1000n * E18;
      await token.connect(minter).mint(user1.address, amt);
      await token.connect(user1).transfer(user2.address, amt);
      expect(await token.balanceOf(user2.address)).to.equal(amt); // full amount
      expect(await token.balanceOf(user1.address)).to.equal(0n);
      // feeCollector (admin) received nothing.
      expect(await token.balanceOf(admin.address)).to.equal(0n);
    });

    it("setFeeConfig is admin-only and stays dormant", async function () {
      const { token, reserve, admin, minter, user1, user2 } = await deploy();
      await expect(
        token.connect(user1).setFeeConfig(100n, user1.address),
      ).to.be.revertedWithCustomError(token, "AccessControlUnauthorizedAccount");
      await token.connect(admin).setFeeConfig(100n, admin.address);
      expect(await token.transferFeeBps()).to.equal(100n);
      // still dormant: transfer moves full amount even after setting a fee
      await reserve.postAnswer(1000n);
      const amt = 1000n * E18;
      await token.connect(minter).mint(user1.address, amt);
      await token.connect(user1).transfer(user2.address, amt);
      expect(await token.balanceOf(user2.address)).to.equal(amt);
    });
  });
});
