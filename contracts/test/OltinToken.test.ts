import { expect } from "chai";
import { ethers } from "hardhat";
import { OltinToken } from "../typechain-types";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("OltinToken", function () {
  let token: OltinToken;
  let owner: SignerWithAddress;
  let minter: SignerWithAddress;
  let user1: SignerWithAddress;
  let user2: SignerWithAddress;

  const MINTER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("MINTER_ROLE"));
  const BURNER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("BURNER_ROLE"));
  const PAUSER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("PAUSER_ROLE"));

  beforeEach(async function () {
    [owner, minter, user1, user2] = await ethers.getSigners();

    const OltinToken = await ethers.getContractFactory("OltinToken");
    token = await OltinToken.deploy();
    await token.waitForDeployment();
  });

  describe("Deployment", function () {
    it("should set correct name and symbol", async function () {
      expect(await token.name()).to.equal("Oltin Gold Token");
      expect(await token.symbol()).to.equal("OLTIN");
    });

    it("should set 18 decimals", async function () {
      expect(await token.decimals()).to.equal(18);
    });

    it("should grant all roles to deployer", async function () {
      expect(await token.hasRole(await token.DEFAULT_ADMIN_ROLE(), owner.address)).to.be.true;
      expect(await token.hasRole(MINTER_ROLE, owner.address)).to.be.true;
      expect(await token.hasRole(BURNER_ROLE, owner.address)).to.be.true;
      expect(await token.hasRole(PAUSER_ROLE, owner.address)).to.be.true;
    });

    it("should start with zero total supply", async function () {
      expect(await token.totalSupply()).to.equal(0);
    });
  });

  describe("Minting", function () {
    it("should mint tokens with orderId", async function () {
      const amount = ethers.parseEther("1.5"); // 1.5 grams

      await expect(token.mint(user1.address, amount, "order-123"))
        .to.emit(token, "Minted")
        .withArgs(user1.address, amount, "order-123", (value: bigint) => value > 0n);

      expect(await token.balanceOf(user1.address)).to.equal(amount);
      expect(await token.totalSupply()).to.equal(amount);
    });

    it("should fail mint without MINTER_ROLE", async function () {
      const amount = ethers.parseEther("1");

      await expect(
        token.connect(user1).mint(user1.address, amount, "order-456")
      ).to.be.reverted;
    });

    it("should fail mint to zero address", async function () {
      const amount = ethers.parseEther("1");

      await expect(
        token.mint(ethers.ZeroAddress, amount, "order-789")
      ).to.be.revertedWith("OltinToken: mint to zero address");
    });

    it("should fail mint with zero amount", async function () {
      await expect(
        token.mint(user1.address, 0, "order-000")
      ).to.be.revertedWith("OltinToken: amount must be positive");
    });

    it("should fail mint with empty orderId", async function () {
      const amount = ethers.parseEther("1");

      await expect(
        token.mint(user1.address, amount, "")
      ).to.be.revertedWith("OltinToken: orderId required");
    });
  });

  describe("Burning", function () {
    beforeEach(async function () {
      // Mint some tokens first
      await token.mint(user1.address, ethers.parseEther("10"), "setup-order");
    });

    it("should burn tokens with orderId", async function () {
      const amount = ethers.parseEther("5");

      await expect(token.burn(user1.address, amount, "sell-order-1"))
        .to.emit(token, "Burned")
        .withArgs(user1.address, amount, "sell-order-1", (value: bigint) => value > 0n);

      expect(await token.balanceOf(user1.address)).to.equal(ethers.parseEther("5"));
    });

    it("should fail burn without BURNER_ROLE", async function () {
      await expect(
        token.connect(user1).burn(user1.address, ethers.parseEther("1"), "order")
      ).to.be.reverted;
    });

    it("should fail burn with insufficient balance", async function () {
      await expect(
        token.burn(user1.address, ethers.parseEther("100"), "order")
      ).to.be.revertedWith("OltinToken: insufficient balance");
    });
  });

  describe("Pausable", function () {
    it("should pause and unpause", async function () {
      await token.pause();
      expect(await token.paused()).to.be.true;

      await token.unpause();
      expect(await token.paused()).to.be.false;
    });

    it("should block minting when paused", async function () {
      await token.pause();

      await expect(
        token.mint(user1.address, ethers.parseEther("1"), "order")
      ).to.be.reverted;
    });

    it("should block transfers when paused", async function () {
      await token.mint(user1.address, ethers.parseEther("10"), "order");
      await token.pause();

      await expect(
        token.connect(user1).transfer(user2.address, ethers.parseEther("1"))
      ).to.be.reverted;
    });
  });

  describe("Access Control", function () {
    it("should allow admin to grant minter role", async function () {
      await token.grantRole(MINTER_ROLE, minter.address);
      expect(await token.hasRole(MINTER_ROLE, minter.address)).to.be.true;

      // New minter can mint
      await token.connect(minter).mint(user1.address, ethers.parseEther("1"), "order");
      expect(await token.balanceOf(user1.address)).to.equal(ethers.parseEther("1"));
    });

    it("should allow admin to revoke minter role", async function () {
      await token.grantRole(MINTER_ROLE, minter.address);
      await token.revokeRole(MINTER_ROLE, minter.address);

      await expect(
        token.connect(minter).mint(user1.address, ethers.parseEther("1"), "order")
      ).to.be.reverted;
    });
  });
});
