/**
 * End-to-end proof on the zkSync VM (acceptance criterion #6).
 *
 * The plain-EVM suite (test/OltinPaymaster.test.ts) impersonates the bootloader:
 * it proves pricing and guards, never that the contract WORKS as a paymaster.
 * Here account abstraction is real — the bootloader validates, the DefaultAccount
 * processes `paymasterParams` (that is what sets the ERC20 allowance in the
 * approvalBased flow), and unused gas is refunded to the paymaster.
 *
 * Run (Node 20 — zksolc breaks on Node 24):
 *   npx hardhat node-zksync                                       # terminal 1
 *   npx hardhat test test-vm/paymaster.e2e.ts --network inMemoryNode
 *
 * TRAP this file exists to catch: `Wallet.createRandom()` returns an ethers
 * `HDNodeWallet`, which silently DROPS `customData.paymasterParams`. The
 * transaction then goes out as an ordinary one from an account with zero ETH and
 * hangs in the mempool forever — no error, no revert. The user must be a
 * zksync-ethers `Wallet`. (viem has the mirror trap: without
 * `eip712WalletActions` the 0x71 type is never built — see the 4c probe.)
 */
import { expect } from "chai";
import * as hre from "hardhat";
import { Wallet, Provider, Contract, ContractFactory, utils } from "zksync-ethers";
import { ethers } from "ethers";

// anvil-zksync rich account #0 (well-known genesis key of the local test node,
// not a secret and never used outside it).
const RICH_PK =
  "0x7726827caac94a7f9e1b160f7ea819f172f7b6f9d2a97f992c38edeab82d4110";

// Deployment configuration — shared with the deploy script and the plain-EVM
// suite, so all three provably run the same numbers.
import { MIN_FEE_OLTIN, paymasterArgs } from "../config/paymasterConfig";
import { expectedFee } from "../test/helpers/expectedFee";

describe("OltinPaymaster — zkSync VM end-to-end", function () {
  this.timeout(180_000);

  async function fixture() {
    const url = (hre.network.config as { url?: string }).url;
    if (!url) throw new Error("run with --network inMemoryNode (no url in config)");
    const provider = new Provider(url);
    const rich = new Wallet(RICH_PK, provider);

    const tokenArt = await hre.artifacts.readArtifact("MockERC20");
    const pmArt = await hre.artifacts.readArtifact("OltinPaymaster");

    const token = await new ContractFactory(
      tokenArt.abi, tokenArt.bytecode, rich, "create",
    ).deploy("Oltin", "OLTIN", 18);
    await token.waitForDeployment();
    const tokenAddress = await token.getAddress();

    const paymaster = await new ContractFactory(
      pmArt.abi, pmArt.bytecode, rich, "create",
    ).deploy(...paymasterArgs(tokenAddress));
    await paymaster.waitForDeployment();
    const pmAddress = await paymaster.getAddress();

    // The token itself stands in for a sponsored target (Exchange / staking).
    await (await (paymaster as any).setSponsoredTarget(tokenAddress, true)).wait();
    await (await rich.sendTransaction({ to: pmAddress, value: ethers.parseEther("0.05") })).wait();

    // A brand-new user holding OLTIN and NOT ONE WEI of ETH.
    const user = new Wallet(ethers.Wallet.createRandom().privateKey, provider);
    const tokenAsRich = new Contract(tokenAddress, tokenArt.abi, rich);
    await (await tokenAsRich.mint(user.address, ethers.parseEther("100"))).wait();
    await (await tokenAsRich.mint(rich.address, ethers.parseEther("100"))).wait();

    // A sponsored tx cannot be auto-estimated (see the client-contract test),
    // so size gas the way the 4c client must: estimate the bare call from a
    // funded account, then add the account-abstraction overhead (validation +
    // postTransaction). Measured overhead on this VM: ~80k gas.
    const AA_OVERHEAD = 150_000n;
    async function gasParams(req: { to: string; data: string }) {
      const bare = await provider.estimateGas({ from: rich.address, to: req.to, data: req.data });
      const feeData = await provider.getFeeData();
      return { gasLimit: bare + AA_OVERHEAD, maxFeePerGas: feeData.gasPrice ?? 45_250_000n };
    }

    return { provider, rich, user, token: tokenAsRich, tokenAddress, pmArt, paymaster, pmAddress, gasParams };
  }

  function transferRequest(
    f: Awaited<ReturnType<typeof fixture>>,
    minimalAllowance: bigint,
    to?: string,
  ) {
    const paymasterParams = utils.getPaymasterParams(f.pmAddress, {
      type: "ApprovalBased",
      token: f.tokenAddress,
      minimalAllowance,
      innerInput: new Uint8Array(),
    });
    const data = new ethers.Interface([
      "function transfer(address,uint256) returns (bool)",
    ]).encodeFunctionData("transfer", [f.rich.address, ethers.parseEther("1")]);

    return {
      to: to ?? f.tokenAddress,
      data,
      customData: {
        gasPerPubdata: utils.DEFAULT_GAS_PER_PUBDATA_LIMIT,
        paymasterParams,
      },
    };
  }

  /**
   * A transaction the paymaster refuses is NOT reverted on chain: it is accepted
   * into the pool and simply never mined (measured — the receipt stays null and
   * the paymaster balance is untouched). 4c must therefore time out and tell the
   * user, instead of waiting for a receipt that will never come.
   */
  async function expectNotSponsored(
    f: Awaited<ReturnType<typeof fixture>>,
    request: Record<string, unknown>,
  ) {
    const ethBefore = await f.provider.getBalance(f.pmAddress);
    const feesBefore: bigint = await (f.paymaster as any).totalFeesCollected();

    const tx = await f.user.sendTransaction(request as any);
    const mined = await Promise.race([
      tx.wait().then((r) => r?.status === 1).catch(() => false),
      new Promise<boolean>((resolve) => setTimeout(() => resolve(false), 5_000)),
    ]);

    expect(mined, "the transaction must not be sponsored").to.equal(false);
    expect(await f.provider.getBalance(f.pmAddress), "not one wei left the paymaster").to.equal(ethBefore);
    expect(await (f.paymaster as any).totalFeesCollected()).to.equal(feesBefore);
  }

  it("a user with ZERO ETH transacts: fee paid in OLTIN, gas paid by the paymaster", async function () {
    const f = await fixture();
    expect(await f.provider.getBalance(f.user.address)).to.equal(0n);

    const pmEthBefore = await f.provider.getBalance(f.pmAddress);
    const userTokenBefore: bigint = await f.token.balanceOf(f.user.address);

    const req = transferRequest(f, ethers.parseEther("1"));
    const { gasLimit, maxFeePerGas } = await f.gasParams(req);
    // The client sizes minimalAllowance from quoteFee — never from a formula
    // mirrored off-chain (it drifts on the first setRate/setFeeConfig).
    const quoted: bigint = await (f.paymaster as any).quoteFee(gasLimit, maxFeePerGas);

    const tx = await f.user.sendTransaction({
      ...req, gasLimit, maxFeePerGas, maxPriorityFeePerGas: 0n,
    } as any);
    const receipt = await tx.wait();
    expect(receipt!.status).to.equal(1);

    const feeCharged: bigint = await (f.paymaster as any).totalFeesCollected();
    const pmEthAfter = await f.provider.getBalance(f.pmAddress);
    const prefunded = gasLimit * maxFeePerGas;
    const spent = pmEthBefore - pmEthAfter;

    console.log(`        prefunded to bootloader : ${prefunded} wei (gasLimit x maxFeePerGas)`);
    console.log(`        paymaster net ETH spent : ${spent} wei`);
    console.log(`        refunded to paymaster   : ${prefunded - spent} wei`);
    console.log(`        fee quoted / charged    : ${quoted} / ${feeCharged} OLTIN wei`);

    // What the plain-EVM suite can never show:
    expect(await f.provider.getBalance(f.user.address), "user spends no ETH").to.equal(0n);
    expect(spent, "paymaster really paid gas").to.be.greaterThan(0n);
    // Independent of the contract: the expected number comes from the mirror,
    // not from quoteFee (which shares _feeFor with validation and would agree
    // with itself even if the formula were wrong).
    expect(feeCharged, "fee matches the off-chain mirror").to.equal(expectedFee(prefunded));
    expect(feeCharged, "quote equals what was charged").to.equal(quoted);
    expect(await f.token.balanceOf(f.pmAddress)).to.equal(feeCharged);
    expect(
      userTokenBefore - (await f.token.balanceOf(f.user.address)),
      "user paid exactly the transfer plus the fee",
    ).to.equal(ethers.parseEther("1") + feeCharged);
    expect(feeCharged, "fee comes from the peg, not the dust floor").to.be.greaterThan(MIN_FEE_OLTIN);

    // M-2, measured rather than assumed: the bootloader is prefunded the gas
    // LIMIT and refunds the unused part TO THE PAYMASTER.
    expect(prefunded).to.be.greaterThan(spent);
  });

  it("CLIENT CONTRACT: automatic fee estimation is refused by the per-tx cap", async function () {
    // zks_estimateFee probes with the MAXIMUM gas limit, so requiredEth during
    // estimation is orders of magnitude above any meaningful ceiling (measured:
    // ~9.3e15 wei vs a 5e14 cap). A paymaster with real per-transaction limits
    // therefore cannot be auto-estimated: the 4c client MUST send an explicit
    // gasLimit (estimate the bare call, add the AA overhead — see gasParams).
    // This test pins that constraint so it is discovered here and not in the UI.
    const f = await fixture();
    await expect(
      f.provider.estimateFee({
        from: f.user.address,
        ...transferRequest(f, ethers.parseEther("1")),
      } as any),
    ).to.be.rejectedWith(/PerTxCapExceeded/);
  });

  it("the drain attempt fails on the live flow: minAllowance = 0 buys nothing", async function () {
    const f = await fixture();
    // Exactly the input that emptied the old contract: request no allowance and
    // let the paymaster pay for the gas.
    const req = transferRequest(f, 0n);
    const gas = await f.gasParams(req);
    await expectNotSponsored(f, { ...req, ...gas, maxPriorityFeePerGas: 0n });
  });

  it("refuses to sponsor a target that is not on the allowlist", async function () {
    const f = await fixture();

    // A deployed contract we never allowlisted.
    const tokenArt = await hre.artifacts.readArtifact("MockERC20");
    const stranger = await new ContractFactory(
      tokenArt.abi, tokenArt.bytecode, f.rich, "create",
    ).deploy("Stranger", "STR", 18);
    await stranger.waitForDeployment();
    const strangerAddress = await stranger.getAddress();

    const req = transferRequest(f, ethers.parseEther("1"), strangerAddress);
    const gas = await f.gasParams({ to: f.tokenAddress, data: req.data });
    await expectNotSponsored(f, { ...req, ...gas, maxPriorityFeePerGas: 0n });
  });
});
