/**
 * PR-4a: deploys the two V3-companion contracts on zkSync Sepolia:
 *
 *   - OltinPaymaster(OLTIN)  approvalBased gasless sponsor: the paymaster pays
 *     the ETH gas, the user pays a small fee in OLTIN. Funded with ETH here.
 *   - OltinStaking(OLTIN)    7% APY staking RE-deployed against the V3 token.
 *     The previously deployed staking (0x63e537…) is immutably bound to the
 *     retired V2 OLTIN (verified on-chain via `oltin()` 2026-07-19) and can
 *     never accept V3 — same source, new constructor argument.
 *
 * No Solidity changes — deploy-only (like the PR #6 deploy fixes).
 *
 * Post-deploy sanity (fails loudly instead of printing a broken address):
 *   - staking.oltin() must equal the OLTIN address it was constructed with;
 *   - the paymaster ETH balance must equal the funding amount.
 *
 * Run (Node 20 — zksolc breaks on Node 24; clear stale artifacts first):
 *   rm -rf artifacts-zk cache-zk && npx hardhat compile --network zkSyncSepolia
 *   npx hardhat deploy-zksync --network zkSyncSepolia --script deployPaymasterStaking.ts
 *
 * Required env (contracts/.env):
 *   PRIVATE_KEY         deployer (with 0x prefix)
 * Optional env:
 *   OLTIN_ADDRESS       V3 OLTIN (default: the 2026-07-18 Sepolia deployment)
 *   PAYMASTER_FUND_ETH  initial ETH funding for the paymaster (default 0.01)
 *
 * NOTE: the reward pool is NOT funded here. V3 OLTIN is mintable only via the
 * Exchange, so the ops seed (deposit UZD -> Exchange.buy -> fund:rewards) is a
 * 4d step once the demo stack is live.
 */

import { Wallet, Provider, Contract } from "zksync-ethers";
import { Deployer } from "@matterlabs/hardhat-zksync";
import { HardhatRuntimeEnvironment } from "hardhat/types";
import * as dotenv from "dotenv";

dotenv.config();

const RPC_URL = "https://sepolia.era.zksync.dev";

// V3 OLTIN from the 2026-07-18 deployment (docs/DEPLOYMENTS.md).
const DEFAULT_OLTIN = "0x906bcf6c92ed1b30aA453c69eB40aeDbb3d5B3A5";

export default async function (hre: HardhatRuntimeEnvironment) {
  const pk = process.env.PRIVATE_KEY;
  if (!pk) throw new Error("Set PRIVATE_KEY in contracts/.env (deployer)");

  const oltinAddress = process.env.OLTIN_ADDRESS ?? DEFAULT_OLTIN;
  const fundEth = process.env.PAYMASTER_FUND_ETH ?? "0.01";

  const provider = new Provider(RPC_URL);
  const wallet = new Wallet(pk, provider);
  const deployer = new Deployer(hre, wallet);

  console.log("Deployer:", wallet.address);
  console.log("V3 OLTIN:", oltinAddress);

  // --- OltinPaymaster(OLTIN) + ETH funding --------------------------------- //
  console.log("\nDeploying OltinPaymaster...");
  const paymasterArtifact = await deployer.loadArtifact("OltinPaymaster");
  const paymaster = await deployer.deploy(paymasterArtifact, [oltinAddress]);
  const paymasterAddress = await paymaster.getAddress();
  console.log("OltinPaymaster:", paymasterAddress);

  console.log(`Funding paymaster with ${fundEth} ETH...`);
  const fundTx = await wallet.sendTransaction({
    to: paymasterAddress,
    value: hre.ethers.parseEther(fundEth),
  });
  await fundTx.wait();

  // --- OltinStaking(OLTIN) -------------------------------------------------- //
  console.log("\nDeploying OltinStaking (V3-bound)...");
  const stakingArtifact = await deployer.loadArtifact("OltinStaking");
  const staking = await deployer.deploy(stakingArtifact, [oltinAddress]);
  const stakingAddress = await staking.getAddress();
  console.log("OltinStaking:", stakingAddress);

  // --- Sanity: read back what we just wired -------------------------------- //
  const stakingRead = new Contract(stakingAddress, stakingArtifact.abi, provider);
  const boundOltin: string = await stakingRead.oltin();
  if (boundOltin.toLowerCase() !== oltinAddress.toLowerCase()) {
    throw new Error(
      `staking.oltin() mismatch: bound=${boundOltin}, expected=${oltinAddress}`,
    );
  }
  const paymasterBalance = await provider.getBalance(paymasterAddress);
  if (paymasterBalance !== hre.ethers.parseEther(fundEth)) {
    throw new Error(
      `paymaster balance mismatch: ${paymasterBalance} wei (expected ${fundEth} ETH)`,
    );
  }

  console.log("\n=== PR-4a deployment complete (sanity passed) ===");
  console.log(`PAYMASTER_ADDRESS=${paymasterAddress}`);
  console.log(`STAKING_ADDRESS=${stakingAddress}`);
  console.log("\nNext:");
  console.log("1. Record both addresses in docs/DEPLOYMENTS.md.");
  console.log("2. 4d seed: deposit UZD -> Exchange.buy -> npm run fund:rewards");
  console.log("   (V3 OLTIN is mintable only via the Exchange).");
  console.log("3. Gasless smoke = the 4c viem x paymaster probe (MINOR-3),");
  console.log("   once OLTIN is in circulation.");
}
