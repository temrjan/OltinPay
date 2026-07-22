/**
 * PR-4a′: deploys the FIXED OltinPaymaster and retires the vulnerable one.
 *
 * The first paymaster (0x77B0afE9…4dE8F, 2026-07-19) derived its fee from the
 * user-supplied `minAllowance` while paying `gasLimit * maxFeePerGas` of ETH —
 * an unmetered drain. It cannot be patched in place, so this deploys a new one
 * and, if OLD_PAYMASTER is given, sweeps the old one's ETH back to the deployer
 * first. Note the old contract keeps an open `receive()`: emptying it does NOT
 * make it safe. It must be recorded as NEVER FUND — drainable, and nothing may
 * point at it again.
 *
 * Configuration is anchored on measurements, not taste (see the Gate-1 spec):
 *   ETH ~ $1922, OLTIN (1 g of gold) ~ $106  =>  ~18 OLTIN per ETH.
 *   A real sponsored ERC20 transfer measured on the zkSync VM costs ~1.4e13 wei
 *   of gas, i.e. ~0.00026 OLTIN ~ $0.03 at this rate.
 *
 * Run (Node 20 — zksolc breaks on Node 24; clear stale artifacts first):
 *   rm -rf artifacts-zk cache-zk && npx hardhat compile --network zkSyncSepolia
 *   npx hardhat deploy-zksync --network zkSyncSepolia --script deployPaymasterFixed.ts
 *
 * Required env (contracts/.env):
 *   PRIVATE_KEY          deployer (with 0x prefix)
 * Optional env:
 *   OLTIN_ADDRESS        V3 OLTIN         (default: the 2026-07-18 deployment)
 *   UZD_ADDRESS          UZD              (default: docs/DEPLOYMENTS.md)
 *   EXCHANGE_ADDRESS     Exchange         (default: docs/DEPLOYMENTS.md)
 *   STAKING_ADDRESS      OltinStaking V3  (default: docs/DEPLOYMENTS.md)
 *   OLD_PAYMASTER        paymaster to sweep before funding the new one
 *   PAYMASTER_FUND_ETH   initial ETH funding for the new paymaster (default 0.01)
 *   PAYMASTER_ADDRESS    finish an ALREADY deployed paymaster (allowlist + fund
 *                        + sanity) instead of deploying another one. Use this
 *                        when a run died after the deploy transaction: a second
 *                        deploy would leave an orphan contract on chain, and
 *                        orphans are how "which address is live?" gets lost.
 */

import { Wallet, Provider, Contract } from "zksync-ethers";
import { Deployer } from "@matterlabs/hardhat-zksync";
import { HardhatRuntimeEnvironment } from "hardhat/types";
import * as dotenv from "dotenv";

dotenv.config();

const RPC_URL = "https://sepolia.era.zksync.dev";

// Canonical V3 stack — docs/DEPLOYMENTS.md.
const DEFAULT_OLTIN = "0x906bcf6c92ed1b30aA453c69eB40aeDbb3d5B3A5";
const DEFAULT_UZD = "0x95b30Be4fdE1C48d7C5dC22C1EBA061219125A32";
const DEFAULT_EXCHANGE = "0xc367D7761Cc2A1b4D15475017136085E3EF74e0C";
const DEFAULT_STAKING = "0xD3b6ffd1dE409e1C37BA5B867d6eC3897A721fAa";

// Fee configuration — shared with both test suites (config/paymasterConfig.ts),
// so what is deployed is exactly what the suites proved.
import {
  RATE, MAX_RATE_AGE, PER_TX_CAP, SENDER_DAILY_CAP, GLOBAL_DAILY_CAP,
  paymasterArgs, SAMPLE_GAS_LIMIT, SAMPLE_MAX_FEE_PER_GAS,
} from "../config/paymasterConfig";

export default async function (hre: HardhatRuntimeEnvironment) {
  const pk = process.env.PRIVATE_KEY;
  if (!pk) throw new Error("Set PRIVATE_KEY in contracts/.env (deployer)");

  const oltinAddress = process.env.OLTIN_ADDRESS ?? DEFAULT_OLTIN;
  const uzdAddress = process.env.UZD_ADDRESS ?? DEFAULT_UZD;
  const exchangeAddress = process.env.EXCHANGE_ADDRESS ?? DEFAULT_EXCHANGE;
  const stakingAddress = process.env.STAKING_ADDRESS ?? DEFAULT_STAKING;
  const oldPaymaster = process.env.OLD_PAYMASTER;
  const fundEth = process.env.PAYMASTER_FUND_ETH ?? "0.01";

  const provider = new Provider(RPC_URL);
  const wallet = new Wallet(pk, provider);
  const deployer = new Deployer(hre, wallet);

  console.log("Deployer:", wallet.address);
  console.log("V3 OLTIN:", oltinAddress);

  // --- 1. Retire the vulnerable paymaster (sweep its ETH) ------------------ //
  if (oldPaymaster) {
    const oldBalance = await provider.getBalance(oldPaymaster);
    console.log(`\nOld paymaster ${oldPaymaster}: ${hre.ethers.formatEther(oldBalance)} ETH`);
    if (oldBalance > 0n) {
      // The old contract's signature is withdrawETH(address payable) — it always
      // sweeps the full balance.
      const old = new Contract(
        oldPaymaster,
        ["function withdrawETH(address payable _to) external"],
        wallet,
      );
      const sweep = await old.withdrawETH(wallet.address);
      await sweep.wait();
      const left = await provider.getBalance(oldPaymaster);
      if (left !== 0n) throw new Error(`sweep failed: ${left} wei left on ${oldPaymaster}`);
      console.log("Swept to deployer. NOTE: receive() stays open — NEVER FUND it again.");
    }
  }

  // --- 2. Deploy the fixed paymaster --------------------------------------- //
  const artifact = await deployer.loadArtifact("OltinPaymaster");
  // hardhat-zksync writes the deployment record with JSON.stringify, which
  // throws on BigInt — the same failure PR #6 fixed for deployV3. The contract
  // deploys first and the saver dies afterwards, so the crash leaves a live
  // orphan. Pass decimal strings: ethers accepts them for uint256.
  const args = paymasterArgs(oltinAddress).map((a) =>
    typeof a === "bigint" ? a.toString() : a,
  );

  let paymasterAddress = process.env.PAYMASTER_ADDRESS ?? "";
  if (paymasterAddress) {
    console.log("\nFinishing the already deployed paymaster:", paymasterAddress);
  } else {
    console.log("\nDeploying OltinPaymaster (fixed)...");
    const paymaster = await deployer.deploy(artifact, args);
    paymasterAddress = await paymaster.getAddress();
    console.log("OltinPaymaster:", paymasterAddress);
  }

  // --- 3. Allowlist our own contracts -------------------------------------- //
  const targets: Array<[string, string]> = [
    ["OLTIN", oltinAddress],
    ["UZD", uzdAddress],
    ["Exchange", exchangeAddress],
    ["OltinStaking", stakingAddress],
  ];
  const pm = new Contract(paymasterAddress, artifact.abi, wallet);
  for (const [label, target] of targets) {
    const tx = await pm.setSponsoredTarget(target, true);
    await tx.wait();
    console.log(`  sponsored target: ${label} ${target}`);
  }

  // --- 4. Fund it (top up to the target, so a re-run is idempotent) --------- //
  const target = hre.ethers.parseEther(fundEth);
  const current = await provider.getBalance(paymasterAddress);
  if (current < target) {
    console.log(`\nFunding paymaster: ${hre.ethers.formatEther(current)} -> ${fundEth} ETH...`);
    const fundTx = await wallet.sendTransaction({
      to: paymasterAddress,
      value: target - current,
    });
    await fundTx.wait();
  } else {
    console.log(`\nPaymaster already holds ${hre.ethers.formatEther(current)} ETH — no top-up.`);
  }

  // --- 5. Sanity: read back what we wired, fail loudly ---------------------- //
  const read = new Contract(paymasterAddress, artifact.abi, provider);

  const boundToken: string = await read.oltinToken();
  if (boundToken.toLowerCase() !== oltinAddress.toLowerCase()) {
    throw new Error(`oltinToken() mismatch: ${boundToken} != ${oltinAddress}`);
  }
  const balance = await provider.getBalance(paymasterAddress);
  if (balance < target) {
    throw new Error(`balance too low: ${balance} wei (expected >= ${fundEth} ETH)`);
  }
  for (const [label, target] of targets) {
    if (!(await read.sponsoredTarget(target))) {
      throw new Error(`allowlist missing: ${label} ${target}`);
    }
  }
  const rate: bigint = await read.oltinPerEth();
  if (rate !== RATE) throw new Error(`rate mismatch: ${rate} != ${RATE}`);
  const quote: bigint = await read.quoteFee(SAMPLE_GAS_LIMIT, SAMPLE_MAX_FEE_PER_GAS);
  const floor: bigint = await read.minFeeOltin();
  // The peg — not the floor — must price a typical transaction, otherwise the
  // fee is a constant and the peg is decoration.
  if (quote <= floor * 10n) {
    throw new Error(`fee floor dominates the peg: quote=${quote} floor=${floor}`);
  }

  // Read the caps back from the chain — printing the TS constants would look
  // like verification without being it (the PR-4a lesson: verify against the
  // chain, never against the script's own output).
  const onChainCaps = {
    perTx: (await read.maxSponsoredEthWei()) as bigint,
    sender: (await read.dailyEthCapSender()) as bigint,
    global: (await read.dailyEthCapGlobal()) as bigint,
  };
  if (
    onChainCaps.perTx !== PER_TX_CAP ||
    onChainCaps.sender !== SENDER_DAILY_CAP ||
    onChainCaps.global !== GLOBAL_DAILY_CAP
  ) {
    throw new Error(
      `caps mismatch: on-chain ${JSON.stringify(onChainCaps, (_k, v) => String(v))} != config`,
    );
  }

  const rateUpdatedAt: bigint = await read.rateUpdatedAt();
  const expiry = new Date(Number(rateUpdatedAt + MAX_RATE_AGE) * 1000).toISOString();

  console.log("\n=== PR-4a′ deployment complete (sanity passed) ===");
  console.log(`PAYMASTER_ADDRESS=${paymasterAddress}`);
  console.log(`quoteFee(sample tx) = ${quote} OLTIN wei (floor ${floor})`);
  console.log(
    `caps (read from chain): perTx=${onChainCaps.perTx} sender/day=${onChainCaps.sender} global/day=${onChainCaps.global} wei`,
  );
  console.log(`RATE EXPIRES AT ${expiry} — after that sponsorship stops until setRate.`);
  // A verified source on the explorer is what makes "check it yourself" real
  // for a jury or a bank review; failure here must not fail the deployment.
  try {
    await hre.run("verify:verify", {
      address: paymasterAddress,
      constructorArguments: args,
    });
    console.log("Explorer verification: OK");
  } catch (e) {
    console.log(`Explorer verification FAILED (retry \`npm run verify\`): ${(e as Error).message}`);
  }

  console.log("\nNext:");
  console.log("1. Record the address and the rate expiry in docs/DEPLOYMENTS.md.");
  console.log("2. Mark the old paymaster NEVER FUND — drainable.");
  console.log("3. 4c: size minimalAllowance from quoteFee() and send an EXPLICIT");
  console.log("   gasLimit — a sponsored tx cannot be auto-estimated (per-tx cap).");
}
