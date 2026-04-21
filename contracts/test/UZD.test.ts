import { expect } from "chai";
import { ethers } from "hardhat";
import { ZeroAddress } from "ethers";
import { anyValue } from "@nomicfoundation/hardhat-chai-matchers/withArgs";

describe("UZD", function () {
  async function deploy() {
    const [admin, user1, user2] = await ethers.getSigners();
    const UZD = await ethers.getContractFactory("UZD");
    const uzd = await UZD.deploy();
    await uzd.waitForDeployment();
    return { uzd, admin, user1, user2 };
  }

  describe("metadata", function () {
    it("has correct name, symbol and decimals", async function () {
      const { uzd } = await deploy();
      expect(await uzd.name()).to.equal("Uzbek Sum Digital");
      expect(await uzd.symbol()).to.equal("UZD");
      expect(await uzd.decimals()).to.equal(18);
      expect(await uzd.totalSupply()).to.equal(0);
    });

    it("grants all four roles to the deployer", async function () {
      const { uzd, admin } = await deploy();
      const ADMIN = await uzd.DEFAULT_ADMIN_ROLE();
      const MINTER = await uzd.MINTER_ROLE();
      const BURNER = await uzd.BURNER_ROLE();
      const PAUSER = await uzd.PAUSER_ROLE();
      expect(await uzd.hasRole(ADMIN, admin.address)).to.be.true;
      expect(await uzd.hasRole(MINTER, admin.address)).to.be.true;
      expect(await uzd.hasRole(BURNER, admin.address)).to.be.true;
      expect(await uzd.hasRole(PAUSER, admin.address)).to.be.true;
    });
  });

  describe("mint", function () {
    it("mints to address and emits Minted", async function () {
      const { uzd, admin, user1 } = await deploy();
      const amount = ethers.parseUnits("1000", 18);
      await expect(uzd.connect(admin).mint(user1.address, amount))
        .to.emit(uzd, "Minted")
        .withArgs(user1.address, amount, anyValue);
      expect(await uzd.balanceOf(user1.address)).to.equal(amount);
      expect(await uzd.totalSupply()).to.equal(amount);
    });

    it("reverts for non-minter", async function () {
      const { uzd, user1 } = await deploy();
      await expect(uzd.connect(user1).mint(user1.address, 100n))
        .to.be.revertedWithCustomError(uzd, "AccessControlUnauthorizedAccount");
    });

    it("reverts on zero address", async function () {
      const { uzd, admin } = await deploy();
      await expect(uzd.connect(admin).mint(ZeroAddress, 100n))
        .to.be.revertedWith("Zero address");
    });

    it("reverts on zero amount", async function () {
      const { uzd, admin, user1 } = await deploy();
      await expect(uzd.connect(admin).mint(user1.address, 0))
        .to.be.revertedWith("Zero amount");
    });

    it("reverts when paused", async function () {
      const { uzd, admin, user1 } = await deploy();
      await uzd.connect(admin).pause();
      await expect(uzd.connect(admin).mint(user1.address, 100n))
        .to.be.revertedWithCustomError(uzd, "EnforcedPause");
    });
  });

  describe("adminBurn", function () {
    it("burns from address and emits AdminBurned", async function () {
      const { uzd, admin, user1 } = await deploy();
      await uzd.connect(admin).mint(user1.address, 1000n);
      await expect(uzd.connect(admin).adminBurn(user1.address, 400n))
        .to.emit(uzd, "AdminBurned");
      expect(await uzd.balanceOf(user1.address)).to.equal(600n);
      expect(await uzd.totalSupply()).to.equal(600n);
    });

    it("reverts for non-burner", async function () {
      const { uzd, admin, user1 } = await deploy();
      await uzd.connect(admin).mint(user1.address, 1000n);
      await expect(uzd.connect(user1).adminBurn(user1.address, 400n))
        .to.be.revertedWithCustomError(uzd, "AccessControlUnauthorizedAccount");
    });
  });

  describe("transfer", function () {
    it("transfers between users when not paused", async function () {
      const { uzd, admin, user1, user2 } = await deploy();
      await uzd.connect(admin).mint(user1.address, 1000n);
      await uzd.connect(user1).transfer(user2.address, 300n);
      expect(await uzd.balanceOf(user1.address)).to.equal(700n);
      expect(await uzd.balanceOf(user2.address)).to.equal(300n);
    });

    it("reverts when paused", async function () {
      const { uzd, admin, user1, user2 } = await deploy();
      await uzd.connect(admin).mint(user1.address, 1000n);
      await uzd.connect(admin).pause();
      await expect(uzd.connect(user1).transfer(user2.address, 100n))
        .to.be.revertedWithCustomError(uzd, "EnforcedPause");
    });
  });

  describe("pause / unpause", function () {
    it("admin can pause and unpause", async function () {
      const { uzd, admin } = await deploy();
      await uzd.connect(admin).pause();
      expect(await uzd.paused()).to.be.true;
      await uzd.connect(admin).unpause();
      expect(await uzd.paused()).to.be.false;
    });

    it("non-pauser cannot pause", async function () {
      const { uzd, user1 } = await deploy();
      await expect(uzd.connect(user1).pause())
        .to.be.revertedWithCustomError(uzd, "AccessControlUnauthorizedAccount");
    });
  });
});

