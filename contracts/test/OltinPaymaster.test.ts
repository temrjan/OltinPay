import { expect } from "chai";
import { ethers } from "hardhat";
import { impersonateAccount, setBalance, time } from "@nomicfoundation/hardhat-network-helpers";
import { ZeroAddress, parseEther } from "ethers";

/**
 * Plain-EVM suite: the bootloader is impersonated, so this covers pricing,
 * guards and admin surface. It deliberately does NOT claim the contract works
 * as a paymaster — account abstraction does not exist on this network. That
 * proof lives in test-vm/paymaster.e2e.ts, on the zkSync VM.
 */

const BOOTLOADER = "0x0000000000000000000000000000000000008001";

// Deployment configuration — the single source of truth shared with the deploy
// script and the VM suite.
import {
  RATE, MIN_RATE, MAX_RATE, MAX_RATE_AGE, SURCHARGE_BPS, MIN_FEE_OLTIN,
  PER_TX_CAP, SENDER_DAILY_CAP, GLOBAL_DAILY_CAP, paymasterArgs,
  SAMPLE_GAS_LIMIT, SAMPLE_MAX_FEE_PER_GAS,
} from "../config/paymasterConfig";

// The reference transaction, measured on the zkSync VM.
const GAS_LIMIT = SAMPLE_GAS_LIMIT;
const MAX_FEE_PER_GAS = SAMPLE_MAX_FEE_PER_GAS;
const REQUIRED_ETH = GAS_LIMIT * MAX_FEE_PER_GAS;

const APPROVAL_BASED_SELECTOR = ethers
  .id("approvalBased(address,uint256,bytes)")
  .slice(0, 10);

import { ceilDiv, expectedFee } from "./helpers/expectedFee";

function paymasterInput(token: string, minAllowance: bigint): string {
  const encoded = ethers.AbiCoder.defaultAbiCoder().encode(
    ["address", "uint256", "bytes"],
    [token, minAllowance, "0x"],
  );
  return APPROVAL_BASED_SELECTOR + encoded.slice(2);
}

function buildTx(overrides: {
  from: string;
  to: string;
  gasLimit?: bigint;
  maxFeePerGas?: bigint;
  paymasterInput: string;
}) {
  return {
    txType: 113n,
    from: BigInt(overrides.from),
    to: BigInt(overrides.to),
    gasLimit: overrides.gasLimit ?? GAS_LIMIT,
    gasPerPubdataByteLimit: 50_000n,
    maxFeePerGas: overrides.maxFeePerGas ?? MAX_FEE_PER_GAS,
    maxPriorityFeePerGas: 0n,
    paymaster: 0n,
    nonce: 0n,
    value: 0n,
    reserved: [0n, 0n, 0n, 0n],
    data: "0x",
    signature: "0x",
    factoryDeps: [],
    paymasterInput: overrides.paymasterInput,
    reservedDynamic: "0x",
  };
}

describe("OltinPaymaster", function () {
  async function deploy() {
    const [owner, user, other] = await ethers.getSigners();

    const Token = await ethers.getContractFactory("MockERC20");
    const oltin = await Token.deploy("Oltin", "OLTIN", 18);
    await oltin.waitForDeployment();
    const oltinAddress = await oltin.getAddress();

    // Stand-in for a sponsored target (Exchange / staking / the token itself).
    const target = await Token.deploy("Target", "TGT", 18);
    await target.waitForDeployment();
    const targetAddress = await target.getAddress();

    const Paymaster = await ethers.getContractFactory("OltinPaymaster");
    const paymaster = await Paymaster.deploy(...paymasterArgs(oltinAddress));
    await paymaster.waitForDeployment();
    const paymasterAddress = await paymaster.getAddress();

    await paymaster.setSponsoredTarget(targetAddress, true);
    await owner.sendTransaction({ to: paymasterAddress, value: parseEther("1") });

    await oltin.mint(user.address, parseEther("100"));
    await oltin.connect(user).approve(paymasterAddress, parseEther("100"));

    await impersonateAccount(BOOTLOADER);
    await setBalance(BOOTLOADER, parseEther("100"));
    const bootloader = await ethers.getSigner(BOOTLOADER);

    const validate = (tx: ReturnType<typeof buildTx>) =>
      paymaster
        .connect(bootloader)
        .validateAndPayForPaymasterTransaction(ethers.ZeroHash, ethers.ZeroHash, tx);

    return {
      owner, user, other, oltin, oltinAddress, target, targetAddress,
      paymaster, paymasterAddress, bootloader, validate,
    };
  }

  describe("fee peg (blocker A — the ETH drain)", function () {
    it("charges the OLTIN equivalent of the gas it is about to pay, ignoring minAllowance", async function () {
      const f = await deploy();
      // minAllowance = 0 — the exact input that drained the old contract.
      const tx = buildTx({
        from: f.user.address,
        to: f.targetAddress,
        paymasterInput: paymasterInput(f.oltinAddress, 0n),
      });

      const before = await ethers.provider.getBalance(f.paymasterAddress);
      await f.validate(tx);

      const fee = expectedFee(REQUIRED_ETH);
      expect(await f.paymaster.totalFeesCollected()).to.equal(fee);
      expect(await f.oltin.balanceOf(f.paymasterAddress)).to.equal(fee);
      expect(before - (await ethers.provider.getBalance(f.paymasterAddress))).to.equal(
        REQUIRED_ETH,
      );
    });

    it("reverts when the user's allowance cannot cover the pegged fee (the drain attempt)", async function () {
      const f = await deploy();
      await f.oltin.connect(f.user).approve(f.paymasterAddress, 0n);

      const tx = buildTx({
        from: f.user.address,
        to: f.targetAddress,
        paymasterInput: paymasterInput(f.oltinAddress, 0n),
      });

      const before = await ethers.provider.getBalance(f.paymasterAddress);
      await expect(f.validate(tx))
        .to.be.revertedWithCustomError(f.paymaster, "AllowanceBelowFee")
        .withArgs(expectedFee(REQUIRED_ETH), 0n);
      expect(await ethers.provider.getBalance(f.paymasterAddress)).to.equal(before);
    });

    it("accepts an allowance exactly equal to the fee (the boundary the client aims at)", async function () {
      const f = await deploy();
      const fee = await f.paymaster.quoteFee(GAS_LIMIT, MAX_FEE_PER_GAS);
      await f.oltin.connect(f.user).approve(f.paymasterAddress, fee);

      await expect(
        f.validate(
          buildTx({
            from: f.user.address,
            to: f.targetAddress,
            paymasterInput: paymasterInput(f.oltinAddress, fee),
          }),
        ),
      ).to.not.be.reverted;
      expect(await f.paymaster.totalFeesCollected()).to.equal(fee);
    });

    it("rejects an allowance one wei below the fee", async function () {
      const f = await deploy();
      const fee = await f.paymaster.quoteFee(GAS_LIMIT, MAX_FEE_PER_GAS);
      await f.oltin.connect(f.user).approve(f.paymasterAddress, fee - 1n);

      await expect(
        f.validate(
          buildTx({
            from: f.user.address,
            to: f.targetAddress,
            paymasterInput: paymasterInput(f.oltinAddress, fee),
          }),
        ),
      )
        .to.be.revertedWithCustomError(f.paymaster, "AllowanceBelowFee")
        .withArgs(fee, fee - 1n);
    });

    it("prices a typical transaction by the peg, not by the floor (fee >> minFeeOltin)", async function () {
      const f = await deploy();
      const fee = await f.paymaster.quoteFee(GAS_LIMIT, MAX_FEE_PER_GAS);
      const floor = await f.paymaster.minFeeOltin();

      expect(fee).to.equal(expectedFee(REQUIRED_ETH));
      expect(fee).to.be.greaterThan(floor * 10n); // peg dominates by >10x
    });

    it("rounds the fee UP at both steps", async function () {
      const f = await deploy();
      // Rate chosen so requiredEth * rate is NOT a multiple of 1e18, and the
      // floor is removed so it cannot mask the rounding.
      const rate = parseEther("2") + 1n;
      await f.paymaster.setRate(rate);
      await f.paymaster.setFeeConfig(SURCHARGE_BPS, 0n);

      const requiredEth = 3n;
      const gasLimit = 3n;
      const maxFeePerGas = 1n;

      const pegged = ceilDiv(requiredEth * rate, parseEther("1"));
      const withSurcharge = ceilDiv(pegged * (10_000n + SURCHARGE_BPS), 10_000n);
      // Floor rounding would give 6 -> 6; ceil gives 7 -> 8.
      expect(pegged).to.equal(7n);
      expect(withSurcharge).to.equal(8n);
      expect(await f.paymaster.quoteFee(gasLimit, maxFeePerGas)).to.equal(withSurcharge);
    });

    it("quoteFee equals what validation actually charges", async function () {
      const f = await deploy();
      const quoted = await f.paymaster.quoteFee(GAS_LIMIT, MAX_FEE_PER_GAS);
      await f.validate(
        buildTx({
          from: f.user.address,
          to: f.targetAddress,
          paymasterInput: paymasterInput(f.oltinAddress, quoted),
        }),
      );
      expect(await f.paymaster.totalFeesCollected()).to.equal(quoted);
    });

    it("applies the floor when the pegged fee is dust", async function () {
      const f = await deploy();
      expect(await f.paymaster.quoteFee(1n, 1n)).to.equal(MIN_FEE_OLTIN);
    });
  });

  describe("allowlist (blocker B)", function () {
    it("sponsors an allowlisted target", async function () {
      const f = await deploy();
      await expect(
        f.validate(
          buildTx({
            from: f.user.address,
            to: f.targetAddress,
            paymasterInput: paymasterInput(f.oltinAddress, parseEther("1")),
          }),
        ),
      ).to.not.be.reverted;
    });

    it("refuses a target that is not on the allowlist", async function () {
      const f = await deploy();
      const stranger = f.other.address;
      await expect(
        f.validate(
          buildTx({
            from: f.user.address,
            to: stranger,
            paymasterInput: paymasterInput(f.oltinAddress, parseEther("1")),
          }),
        ),
      )
        .to.be.revertedWithCustomError(f.paymaster, "TargetNotSponsored")
        .withArgs(stranger);
    });

    it("owner can revoke a target", async function () {
      const f = await deploy();
      await expect(f.paymaster.setSponsoredTarget(f.targetAddress, false))
        .to.emit(f.paymaster, "SponsoredTargetSet")
        .withArgs(f.targetAddress, false);
      await expect(
        f.validate(
          buildTx({
            from: f.user.address,
            to: f.targetAddress,
            paymasterInput: paymasterInput(f.oltinAddress, parseEther("1")),
          }),
        ),
      ).to.be.revertedWithCustomError(f.paymaster, "TargetNotSponsored");
    });

    it("rejects the zero address as a target", async function () {
      const f = await deploy();
      await expect(
        f.paymaster.setSponsoredTarget(ZeroAddress, true),
      ).to.be.revertedWithCustomError(f.paymaster, "ZeroAddress");
    });
  });

  describe("spending ceilings", function () {
    it("refuses a transaction above the per-transaction cap", async function () {
      const f = await deploy();
      const gasLimit = PER_TX_CAP / MAX_FEE_PER_GAS + 1n;
      await expect(
        f.validate(
          buildTx({
            from: f.user.address,
            to: f.targetAddress,
            gasLimit,
            paymasterInput: paymasterInput(f.oltinAddress, parseEther("1")),
          }),
        ),
      )
        .to.be.revertedWithCustomError(f.paymaster, "PerTxCapExceeded")
        .withArgs(gasLimit * MAX_FEE_PER_GAS, PER_TX_CAP);
    });

    it("stops a single sender once its daily budget is spent, and resets the next day", async function () {
      const f = await deploy();
      // Tight caps so two transactions exhaust the sender budget.
      await f.paymaster.setCaps(REQUIRED_ETH, REQUIRED_ETH * 2n, GLOBAL_DAILY_CAP);
      const tx = buildTx({
        from: f.user.address,
        to: f.targetAddress,
        paymasterInput: paymasterInput(f.oltinAddress, parseEther("1")),
      });

      await f.validate(tx);
      await f.validate(tx);
      await expect(f.validate(tx))
        .to.be.revertedWithCustomError(f.paymaster, "SenderDailyCapExceeded")
        .withArgs(REQUIRED_ETH, REQUIRED_ETH * 2n, REQUIRED_ETH * 2n);

      await time.increase(24 * 60 * 60);
      await expect(f.validate(tx)).to.not.be.reverted;
    });

    it("stops a FRESH address once the global daily budget is spent (address rotation does not help)", async function () {
      const f = await deploy();
      await f.paymaster.setCaps(REQUIRED_ETH, REQUIRED_ETH, REQUIRED_ETH);

      await f.validate(
        buildTx({
          from: f.user.address,
          to: f.targetAddress,
          paymasterInput: paymasterInput(f.oltinAddress, parseEther("1")),
        }),
      );

      // A brand-new address with its own untouched per-sender budget.
      const fresh = ethers.Wallet.createRandom().address;
      await f.oltin.mint(fresh, parseEther("10"));
      await impersonateAccount(fresh);
      await setBalance(fresh, parseEther("1"));
      await f.oltin
        .connect(await ethers.getSigner(fresh))
        .approve(f.paymasterAddress, parseEther("10"));

      const freshTx = buildTx({
        from: fresh,
        to: f.targetAddress,
        paymasterInput: paymasterInput(f.oltinAddress, parseEther("1")),
      });
      await expect(f.validate(freshTx))
        .to.be.revertedWithCustomError(f.paymaster, "GlobalDailyCapExceeded")
        .withArgs(REQUIRED_ETH, REQUIRED_ETH, REQUIRED_ETH);

      // The GLOBAL bucket must roll over with the day as well. Without this the
      // contract would sponsor its global budget once and be dead forever —
      // and, before this assertion existed, the suite stayed green when the
      // global rollover was removed.
      await time.increase(24 * 60 * 60);
      await expect(f.validate(freshTx)).to.not.be.reverted;
      const spendAfter = await f.paymaster.globalSpend();
      expect(spendAfter.spentWei, "global bucket restarts from this tx alone").to.equal(
        REQUIRED_ETH,
      );
    });

    it("does not consume any budget when validation reverts", async function () {
      const f = await deploy();
      await f.oltin.connect(f.user).approve(f.paymasterAddress, 0n);
      await expect(
        f.validate(
          buildTx({
            from: f.user.address,
            to: f.targetAddress,
            paymasterInput: paymasterInput(f.oltinAddress, 0n),
          }),
        ),
      ).to.be.reverted;
      const spend = await f.paymaster.globalSpend();
      expect(spend.spentWei).to.equal(0n);
    });

    it("reports a shortfall instead of failing the bootloader payment", async function () {
      const f = await deploy();
      const balance = await ethers.provider.getBalance(f.paymasterAddress);
      await f.paymaster.withdrawETH(f.owner.address, balance);
      await expect(
        f.validate(
          buildTx({
            from: f.user.address,
            to: f.targetAddress,
            paymasterInput: paymasterInput(f.oltinAddress, parseEther("1")),
          }),
        ),
      )
        .to.be.revertedWithCustomError(f.paymaster, "PaymasterOutOfFunds")
        .withArgs(REQUIRED_ETH, 0n);
    });
  });

  describe("rate configuration", function () {
    it("refuses to sponsor once the rate is stale, and resumes after setRate", async function () {
      const f = await deploy();
      const tx = buildTx({
        from: f.user.address,
        to: f.targetAddress,
        paymasterInput: paymasterInput(f.oltinAddress, parseEther("1")),
      });

      await time.increase(Number(MAX_RATE_AGE) + 1);
      await expect(f.validate(tx)).to.be.revertedWithCustomError(f.paymaster, "RateStale");
      await expect(f.paymaster.quoteFee(GAS_LIMIT, MAX_FEE_PER_GAS)).to.be.revertedWithCustomError(
        f.paymaster,
        "RateStale",
      );

      await f.paymaster.setRate(RATE);
      await expect(f.validate(tx)).to.not.be.reverted;
    });

    it("rejects a rate outside the immutable bounds (fat finger, and rate = 0)", async function () {
      const f = await deploy();
      await expect(f.paymaster.setRate(0n))
        .to.be.revertedWithCustomError(f.paymaster, "RateOutOfBounds")
        .withArgs(0n, MIN_RATE, MAX_RATE);
      await expect(f.paymaster.setRate(MIN_RATE - 1n)).to.be.revertedWithCustomError(
        f.paymaster,
        "RateOutOfBounds",
      );
      await expect(f.paymaster.setRate(MAX_RATE + 1n)).to.be.revertedWithCustomError(
        f.paymaster,
        "RateOutOfBounds",
      );
      await expect(f.paymaster.setRate(MAX_RATE)).to.not.be.reverted;
    });

    it("self-stamps the rate timestamp — the owner cannot backdate it", async function () {
      const f = await deploy();
      const tx = await f.paymaster.setRate(RATE);
      const block = await ethers.provider.getBlock(tx.blockNumber!);
      expect(await f.paymaster.rateUpdatedAt()).to.equal(block!.timestamp);
    });

    it("refuses a zero cap in setCaps", async function () {
      const f = await deploy();
      await expect(
        f.paymaster.setCaps(0n, SENDER_DAILY_CAP, GLOBAL_DAILY_CAP),
      ).to.be.revertedWithCustomError(f.paymaster, "ZeroAmount");
      await expect(
        f.paymaster.setCaps(PER_TX_CAP, 0n, GLOBAL_DAILY_CAP),
      ).to.be.revertedWithCustomError(f.paymaster, "ZeroAmount");
      await expect(
        f.paymaster.setCaps(PER_TX_CAP, SENDER_DAILY_CAP, 0n),
      ).to.be.revertedWithCustomError(f.paymaster, "ZeroAmount");
    });

    it("treats a rate exactly at maxRateAge as still fresh (boundary)", async function () {
      const f = await deploy();
      const updatedAt = await f.paymaster.rateUpdatedAt();
      // Land the next call exactly ON the boundary: elapsed == maxRateAge.
      await time.setNextBlockTimestamp(updatedAt + MAX_RATE_AGE);
      await expect(
        f.validate(
          buildTx({
            from: f.user.address,
            to: f.targetAddress,
            paymasterInput: paymasterInput(f.oltinAddress, parseEther("1")),
          }),
        ),
      ).to.not.be.reverted;

      // One second past it, the same call is refused.
      await time.increase(1);
      await expect(
        f.validate(
          buildTx({
            from: f.user.address,
            to: f.targetAddress,
            paymasterInput: paymasterInput(f.oltinAddress, parseEther("1")),
          }),
        ),
      ).to.be.revertedWithCustomError(f.paymaster, "RateStale");
    });

    it("bounds the surcharge and the fee floor an owner may set", async function () {
      const f = await deploy();
      await expect(f.paymaster.setFeeConfig(501n, MIN_FEE_OLTIN))
        .to.be.revertedWithCustomError(f.paymaster, "SurchargeTooHigh")
        .withArgs(501n, 500n);
      await expect(
        f.paymaster.setFeeConfig(SURCHARGE_BPS, parseEther("0.01") + 1n),
      ).to.be.revertedWithCustomError(f.paymaster, "MinFeeTooHigh");
    });

    it("a zero surcharge and zero floor still charge the pegged fee (no free relay)", async function () {
      const f = await deploy();
      await f.paymaster.setFeeConfig(0n, 0n);
      expect(await f.paymaster.quoteFee(GAS_LIMIT, MAX_FEE_PER_GAS)).to.equal(
        expectedFee(REQUIRED_ETH, RATE, 0n, 0n),
      );
      expect(await f.paymaster.quoteFee(GAS_LIMIT, MAX_FEE_PER_GAS)).to.be.greaterThan(0n);
    });
  });

  describe("paymaster input validation", function () {
    it("rejects an input shorter than a selector", async function () {
      const f = await deploy();
      await expect(
        f.validate(
          buildTx({ from: f.user.address, to: f.targetAddress, paymasterInput: "0x1234" }),
        ),
      ).to.be.revertedWithCustomError(f.paymaster, "InvalidPaymasterInput");
    });

    it("rejects a non approvalBased flow", async function () {
      const f = await deploy();
      const general = ethers.id("general(bytes)").slice(0, 10);
      await expect(
        f.validate(
          buildTx({
            from: f.user.address,
            to: f.targetAddress,
            paymasterInput: general + "00".repeat(96),
          }),
        ),
      ).to.be.revertedWithCustomError(f.paymaster, "UnsupportedFlow");
    });

    it("rejects a fee token that is not OLTIN", async function () {
      const f = await deploy();
      await expect(
        f.validate(
          buildTx({
            from: f.user.address,
            to: f.targetAddress,
            paymasterInput: paymasterInput(f.targetAddress, parseEther("1")),
          }),
        ),
      )
        .to.be.revertedWithCustomError(f.paymaster, "WrongFeeToken")
        .withArgs(f.targetAddress, f.oltinAddress);
    });
  });

  describe("access control and pause", function () {
    it("only the bootloader may call validateAndPayForPaymasterTransaction", async function () {
      const f = await deploy();
      await expect(
        f.paymaster
          .connect(f.user)
          .validateAndPayForPaymasterTransaction(
            ethers.ZeroHash,
            ethers.ZeroHash,
            buildTx({
              from: f.user.address,
              to: f.targetAddress,
              paymasterInput: paymasterInput(f.oltinAddress, parseEther("1")),
            }),
          ),
      ).to.be.revertedWithCustomError(f.paymaster, "NotBootloader");
    });

    it("only the bootloader may call postTransaction", async function () {
      const f = await deploy();
      const context = ethers.AbiCoder.defaultAbiCoder().encode(
        ["address", "uint256"],
        [f.user.address, 1n],
      );
      await expect(
        f.paymaster
          .connect(f.user)
          .postTransaction(
            context,
            buildTx({
              from: f.user.address,
              to: f.targetAddress,
              paymasterInput: paymasterInput(f.oltinAddress, 1n),
            }),
            ethers.ZeroHash,
            ethers.ZeroHash,
            0,
            0,
          ),
      ).to.be.revertedWithCustomError(f.paymaster, "NotBootloader");
    });

    it("postTransaction emits FeePaid", async function () {
      const f = await deploy();
      const fee = expectedFee(REQUIRED_ETH);
      const context = ethers.AbiCoder.defaultAbiCoder().encode(
        ["address", "uint256"],
        [f.user.address, fee],
      );
      const txHash = ethers.id("some-tx");
      await expect(
        f.paymaster
          .connect(f.bootloader)
          .postTransaction(
            context,
            buildTx({
              from: f.user.address,
              to: f.targetAddress,
              paymasterInput: paymasterInput(f.oltinAddress, fee),
            }),
            txHash,
            ethers.ZeroHash,
            0,
            0,
          ),
      )
        .to.emit(f.paymaster, "FeePaid")
        .withArgs(f.user.address, fee, txHash);
    });

    it("pause stops sponsorship; unpause resumes it", async function () {
      const f = await deploy();
      const tx = buildTx({
        from: f.user.address,
        to: f.targetAddress,
        paymasterInput: paymasterInput(f.oltinAddress, parseEther("1")),
      });

      await f.paymaster.pause();
      await expect(f.validate(tx)).to.be.revertedWithCustomError(f.paymaster, "EnforcedPause");

      await f.paymaster.unpause();
      await expect(f.validate(tx)).to.not.be.reverted;
    });

    it("only the owner may pause or change configuration", async function () {
      const f = await deploy();
      await expect(f.paymaster.connect(f.user).pause()).to.be.revertedWithCustomError(
        f.paymaster,
        "OwnableUnauthorizedAccount",
      );
      await expect(f.paymaster.connect(f.user).setRate(RATE)).to.be.revertedWithCustomError(
        f.paymaster,
        "OwnableUnauthorizedAccount",
      );
      await expect(
        f.paymaster.connect(f.user).setCaps(1n, 1n, 1n),
      ).to.be.revertedWithCustomError(f.paymaster, "OwnableUnauthorizedAccount");
      await expect(
        f.paymaster.connect(f.user).setSponsoredTarget(f.targetAddress, true),
      ).to.be.revertedWithCustomError(f.paymaster, "OwnableUnauthorizedAccount");
    });

    it("only the owner may move funds out or unpause", async function () {
      const f = await deploy();
      await f.paymaster.pause();

      // The function that can empty the ETH reserve is the one that most needs
      // this test.
      await expect(
        f.paymaster.connect(f.user).withdrawETH(f.user.address, 1n),
      ).to.be.revertedWithCustomError(f.paymaster, "OwnableUnauthorizedAccount");
      await expect(
        f.paymaster.connect(f.user).withdrawFees(f.user.address),
      ).to.be.revertedWithCustomError(f.paymaster, "OwnableUnauthorizedAccount");
      await expect(
        f.paymaster.connect(f.user).setFeeConfig(0n, 0n),
      ).to.be.revertedWithCustomError(f.paymaster, "OwnableUnauthorizedAccount");
      await expect(
        f.paymaster.connect(f.user).unpause(),
      ).to.be.revertedWithCustomError(f.paymaster, "OwnableUnauthorizedAccount");
    });

    it("ownership transfer is two-step — a wrong address cannot lock the contract", async function () {
      const f = await deploy();
      await f.paymaster.transferOwnership(f.other.address);
      // Still ours until the new owner accepts.
      expect(await f.paymaster.owner()).to.equal(f.owner.address);
      await expect(f.paymaster.pause()).to.not.be.reverted;

      await f.paymaster.connect(f.other).acceptOwnership();
      expect(await f.paymaster.owner()).to.equal(f.other.address);
    });
  });

  describe("withdrawals", function () {
    it("withdraws a stated amount of ETH and emits it", async function () {
      const f = await deploy();
      const amount = parseEther("0.25");
      const before = await ethers.provider.getBalance(f.paymasterAddress);
      await expect(f.paymaster.withdrawETH(f.other.address, amount))
        .to.emit(f.paymaster, "EthWithdrawn")
        .withArgs(f.other.address, amount);
      expect(await ethers.provider.getBalance(f.paymasterAddress)).to.equal(before - amount);
    });

    it("refuses the zero address, a zero amount and more than the balance", async function () {
      const f = await deploy();
      const balance = await ethers.provider.getBalance(f.paymasterAddress);
      await expect(
        f.paymaster.withdrawETH(ZeroAddress, 1n),
      ).to.be.revertedWithCustomError(f.paymaster, "ZeroAddress");
      await expect(
        f.paymaster.withdrawETH(f.other.address, 0n),
      ).to.be.revertedWithCustomError(f.paymaster, "ZeroAmount");
      await expect(f.paymaster.withdrawETH(f.other.address, balance + 1n))
        .to.be.revertedWithCustomError(f.paymaster, "AmountExceedsBalance")
        .withArgs(balance + 1n, balance);
    });

    it("withdraws collected fees once and zeroes the counter", async function () {
      const f = await deploy();
      await f.validate(
        buildTx({
          from: f.user.address,
          to: f.targetAddress,
          paymasterInput: paymasterInput(f.oltinAddress, parseEther("1")),
        }),
      );
      const fee = await f.paymaster.totalFeesCollected();
      expect(fee).to.be.greaterThan(0n);

      await expect(f.paymaster.withdrawFees(f.other.address))
        .to.emit(f.paymaster, "FeesWithdrawn")
        .withArgs(f.other.address, fee);
      expect(await f.oltin.balanceOf(f.other.address)).to.equal(fee);
      expect(await f.paymaster.totalFeesCollected()).to.equal(0n);

      await expect(
        f.paymaster.withdrawFees(f.other.address),
      ).to.be.revertedWithCustomError(f.paymaster, "ZeroAmount");
    });

    it("refuses to send fees to the zero address", async function () {
      const f = await deploy();
      await expect(
        f.paymaster.withdrawFees(ZeroAddress),
      ).to.be.revertedWithCustomError(f.paymaster, "ZeroAddress");
    });

    it("emits on a plain ETH deposit", async function () {
      const f = await deploy();
      await expect(
        f.owner.sendTransaction({ to: f.paymasterAddress, value: parseEther("0.1") }),
      )
        .to.emit(f.paymaster, "EthDeposited")
        .withArgs(f.owner.address, parseEther("0.1"));
    });
  });

  describe("deployment guards", function () {
    it("rejects a nonsensical configuration", async function () {
      const Paymaster = await ethers.getContractFactory("OltinPaymaster");
      const Token = await ethers.getContractFactory("MockERC20");
      const token = await Token.deploy("Oltin", "OLTIN", 18);
      await token.waitForDeployment();
      const t = await token.getAddress();
      const [, ...rest] = paymasterArgs(t);

      await expect(Paymaster.deploy(ZeroAddress, ...rest)).to.be.revertedWithCustomError(
        Paymaster, "ZeroAddress",
      );
      // rate below the lower bound
      await expect(
        Paymaster.deploy(t, MIN_RATE, MAX_RATE, MAX_RATE_AGE, MIN_RATE - 1n, SURCHARGE_BPS,
          MIN_FEE_OLTIN, PER_TX_CAP, SENDER_DAILY_CAP, GLOBAL_DAILY_CAP),
      ).to.be.revertedWithCustomError(Paymaster, "RateOutOfBounds");
      // zero caps
      await expect(
        Paymaster.deploy(t, MIN_RATE, MAX_RATE, MAX_RATE_AGE, RATE, SURCHARGE_BPS,
          MIN_FEE_OLTIN, 0n, SENDER_DAILY_CAP, GLOBAL_DAILY_CAP),
      ).to.be.revertedWithCustomError(Paymaster, "ZeroAmount");
    });
  });

  describe("checkSponsorship — the client preflight", function () {
    it("returns the same fee validation charges, without needing an allowance", async function () {
      const f = await deploy();
      // A user who has approved nothing yet — the state a client is in when it
      // is deciding what minimalAllowance to request.
      await f.oltin.connect(f.user).approve(f.paymasterAddress, 0n);

      const fee = await f.paymaster.checkSponsorship(
        f.user.address, f.targetAddress, GAS_LIMIT, MAX_FEE_PER_GAS,
      );
      expect(fee).to.equal(expectedFee(REQUIRED_ETH));

      await f.oltin.connect(f.user).approve(f.paymasterAddress, fee);
      await f.validate(
        buildTx({
          from: f.user.address,
          to: f.targetAddress,
          paymasterInput: paymasterInput(f.oltinAddress, fee),
        }),
      );
      expect(await f.paymaster.totalFeesCollected()).to.equal(fee);
    });

    it("reports each refusal with its own typed error", async function () {
      const f = await deploy();
      const call = (to: string, gasLimit = GAS_LIMIT) =>
        f.paymaster.checkSponsorship(f.user.address, to, gasLimit, MAX_FEE_PER_GAS);

      await expect(call(f.other.address))
        .to.be.revertedWithCustomError(f.paymaster, "TargetNotSponsored")
        .withArgs(f.other.address);

      await expect(call(f.targetAddress, PER_TX_CAP / MAX_FEE_PER_GAS + 1n))
        .to.be.revertedWithCustomError(f.paymaster, "PerTxCapExceeded");

      await f.paymaster.setCaps(REQUIRED_ETH, REQUIRED_ETH, REQUIRED_ETH);
      await f.validate(
        buildTx({
          from: f.user.address,
          to: f.targetAddress,
          paymasterInput: paymasterInput(f.oltinAddress, parseEther("1")),
        }),
      );
      await expect(call(f.targetAddress)).to.be.revertedWithCustomError(
        f.paymaster, "SenderDailyCapExceeded",
      );

      await f.paymaster.pause();
      await expect(call(f.targetAddress)).to.be.revertedWithCustomError(
        f.paymaster, "EnforcedPause",
      );
    });

    it("reports an empty paymaster rather than staying silent", async function () {
      const f = await deploy();
      await f.paymaster.withdrawETH(
        f.owner.address, await ethers.provider.getBalance(f.paymasterAddress),
      );
      await expect(
        f.paymaster.checkSponsorship(f.user.address, f.targetAddress, GAS_LIMIT, MAX_FEE_PER_GAS),
      ).to.be.revertedWithCustomError(f.paymaster, "PaymasterOutOfFunds");
    });
  });

  describe("configuration invariants", function () {
    // The deploy script and both suites read config/paymasterConfig.ts, so a
    // fat-fingered constant would sail through all three. These are the
    // properties the numbers must hold whatever their values.
    it("caps are ordered per-tx <= per-sender <= global", function () {
      expect(PER_TX_CAP).to.be.lessThanOrEqual(SENDER_DAILY_CAP);
      expect(SENDER_DAILY_CAP).to.be.lessThanOrEqual(GLOBAL_DAILY_CAP);
    });

    it("one sender cannot exhaust the protocol day: global >= 10x sender", function () {
      expect(GLOBAL_DAILY_CAP / SENDER_DAILY_CAP).to.be.greaterThanOrEqual(10n);
    });

    it("the peg — not the floor — prices a typical transaction", async function () {
      const f = await deploy();
      const quote = await f.paymaster.quoteFee(GAS_LIMIT, MAX_FEE_PER_GAS);
      expect(quote).to.be.greaterThanOrEqual(MIN_FEE_OLTIN * 10n);
    });

    it("the bounds are derived from the rate, not chosen independently", function () {
      // Checking only "rate is inside its bounds" would pass with RATE = 100e18
      // against bounds built for 18e18 — exactly the fat finger this block
      // exists to catch. The bounds must BE the rate's x100 span.
      expect(MIN_RATE).to.equal(RATE / 10n);
      expect(MAX_RATE).to.equal(RATE * 10n);
      expect(RATE).to.be.greaterThan(MIN_RATE);
      expect(RATE).to.be.lessThan(MAX_RATE);
    });
  });

  describe("events and remaining guards", function () {
    it("emits on every configuration change", async function () {
      const f = await deploy();
      await expect(f.paymaster.setRate(MAX_RATE))
        .to.emit(f.paymaster, "RateUpdated");
      await expect(f.paymaster.setFeeConfig(100n, 1n))
        .to.emit(f.paymaster, "FeeConfigUpdated")
        .withArgs(100n, 1n);
      await expect(f.paymaster.setCaps(PER_TX_CAP, SENDER_DAILY_CAP, GLOBAL_DAILY_CAP))
        .to.emit(f.paymaster, "CapsUpdated")
        .withArgs(PER_TX_CAP, SENDER_DAILY_CAP, GLOBAL_DAILY_CAP);
    });

    it("surfaces a failed ETH transfer instead of silently succeeding", async function () {
      const f = await deploy();
      // A contract with no receive()/fallback — the ETH send must fail.
      await expect(f.paymaster.withdrawETH(f.oltinAddress, 1n)).to.be.revertedWithCustomError(
        f.paymaster, "EthTransferFailed",
      );
    });

    it("rejects every nonsensical constructor argument", async function () {
      const Paymaster = await ethers.getContractFactory("OltinPaymaster");
      const Token = await ethers.getContractFactory("MockERC20");
      const token = await Token.deploy("Oltin", "OLTIN", 18);
      await token.waitForDeployment();
      const t = await token.getAddress();
      const deployWith = (...a: unknown[]) =>
        Paymaster.deploy(...(a as Parameters<typeof Paymaster.deploy>));

      // minRate = 0 would allow a free-relay rate.
      await expect(
        deployWith(t, 0n, MAX_RATE, MAX_RATE_AGE, RATE, SURCHARGE_BPS, MIN_FEE_OLTIN,
          PER_TX_CAP, SENDER_DAILY_CAP, GLOBAL_DAILY_CAP),
      ).to.be.revertedWithCustomError(Paymaster, "RateOutOfBounds");
      // maxRate below minRate.
      await expect(
        deployWith(t, MAX_RATE, MIN_RATE, MAX_RATE_AGE, RATE, SURCHARGE_BPS, MIN_FEE_OLTIN,
          PER_TX_CAP, SENDER_DAILY_CAP, GLOBAL_DAILY_CAP),
      ).to.be.revertedWithCustomError(Paymaster, "RateOutOfBounds");
      // initial rate above maxRate.
      await expect(
        deployWith(t, MIN_RATE, MAX_RATE, MAX_RATE_AGE, MAX_RATE + 1n, SURCHARGE_BPS,
          MIN_FEE_OLTIN, PER_TX_CAP, SENDER_DAILY_CAP, GLOBAL_DAILY_CAP),
      ).to.be.revertedWithCustomError(Paymaster, "RateOutOfBounds");
      // a rate that can never go stale is not a staleness window.
      await expect(
        deployWith(t, MIN_RATE, MAX_RATE, 0n, RATE, SURCHARGE_BPS, MIN_FEE_OLTIN,
          PER_TX_CAP, SENDER_DAILY_CAP, GLOBAL_DAILY_CAP),
      ).to.be.revertedWithCustomError(Paymaster, "ZeroAmount");
      // zero daily caps.
      await expect(
        deployWith(t, MIN_RATE, MAX_RATE, MAX_RATE_AGE, RATE, SURCHARGE_BPS, MIN_FEE_OLTIN,
          PER_TX_CAP, 0n, GLOBAL_DAILY_CAP),
      ).to.be.revertedWithCustomError(Paymaster, "ZeroAmount");
      await expect(
        deployWith(t, MIN_RATE, MAX_RATE, MAX_RATE_AGE, RATE, SURCHARGE_BPS, MIN_FEE_OLTIN,
          PER_TX_CAP, SENDER_DAILY_CAP, 0n),
      ).to.be.revertedWithCustomError(Paymaster, "ZeroAmount");
      // surcharge and floor ceilings.
      await expect(
        deployWith(t, MIN_RATE, MAX_RATE, MAX_RATE_AGE, RATE, 501n, MIN_FEE_OLTIN,
          PER_TX_CAP, SENDER_DAILY_CAP, GLOBAL_DAILY_CAP),
      ).to.be.revertedWithCustomError(Paymaster, "SurchargeTooHigh");
      await expect(
        deployWith(t, MIN_RATE, MAX_RATE, MAX_RATE_AGE, RATE, SURCHARGE_BPS,
          parseEther("0.01") + 1n, PER_TX_CAP, SENDER_DAILY_CAP, GLOBAL_DAILY_CAP),
      ).to.be.revertedWithCustomError(Paymaster, "MinFeeTooHigh");
    });
  });
});
