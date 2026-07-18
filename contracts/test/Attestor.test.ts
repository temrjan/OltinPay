import { expect } from "chai";
import { ethers } from "hardhat";
import { time } from "@nomicfoundation/hardhat-network-helpers";
import { anyValue } from "@nomicfoundation/hardhat-chai-matchers/withArgs";

describe("Attestor", function () {
  async function deploy(decimals = 8) {
    const [admin, poster, user] = await ethers.getSigners();
    const Attestor = await ethers.getContractFactory("Attestor");
    const attestor = await Attestor.deploy(decimals);
    await attestor.waitForDeployment();
    return { attestor, admin, poster, user };
  }

  describe("metadata / roles", function () {
    it("reports the constructor decimals", async function () {
      const { attestor } = await deploy(8);
      expect(await attestor.decimals()).to.equal(8);
    });

    it("supports different decimals per instance (0 for reserve, 8 for price)", async function () {
      const Attestor = await ethers.getContractFactory("Attestor");
      const reserve = await Attestor.deploy(0);
      const price = await Attestor.deploy(8);
      expect(await reserve.decimals()).to.equal(0);
      expect(await price.decimals()).to.equal(8);
    });

    it("grants admin + poster roles to the deployer", async function () {
      const { attestor, admin } = await deploy();
      const ADMIN = await attestor.DEFAULT_ADMIN_ROLE();
      const POSTER = await attestor.POSTER_ROLE();
      expect(await attestor.hasRole(ADMIN, admin.address)).to.be.true;
      expect(await attestor.hasRole(POSTER, admin.address)).to.be.true;
    });
  });

  describe("postAnswer", function () {
    it("reverts for a non-poster", async function () {
      const { attestor, user } = await deploy();
      await expect(
        attestor.connect(user).postAnswer(100n),
      ).to.be.revertedWithCustomError(
        attestor,
        "AccessControlUnauthorizedAccount",
      );
    });

    it("self-stamps updatedAt = block.timestamp (poster passes no time)", async function () {
      const { attestor, admin } = await deploy();
      await attestor.connect(admin).postAnswer(330000000000n);
      const now = await time.latest();
      const [, answer, startedAt, updatedAt] = await attestor.latestRoundData();
      expect(answer).to.equal(330000000000n);
      expect(updatedAt).to.equal(BigInt(now));
      expect(startedAt).to.equal(BigInt(now));
    });

    it("emits AnswerPosted with the self-stamped time", async function () {
      const { attestor, admin } = await deploy();
      await expect(attestor.connect(admin).postAnswer(123n))
        .to.emit(attestor, "AnswerPosted")
        .withArgs(anyValue, 123n, anyValue);
    });

    it("increments a monotonic roundId (starts at 1)", async function () {
      const { attestor, admin } = await deploy();
      await attestor.connect(admin).postAnswer(1n);
      const [r1] = await attestor.latestRoundData();
      await attestor.connect(admin).postAnswer(2n);
      const [r2] = await attestor.latestRoundData();
      expect(r1).to.equal(1n);
      expect(r2).to.equal(2n);
    });

    it("latestRoundData reflects the most recent answer", async function () {
      const { attestor, admin } = await deploy();
      await attestor.connect(admin).postAnswer(500n);
      await attestor.connect(admin).postAnswer(700n);
      const [, answer] = await attestor.latestRoundData();
      expect(answer).to.equal(700n);
    });
  });
});
