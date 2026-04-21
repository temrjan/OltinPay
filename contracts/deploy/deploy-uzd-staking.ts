/**
 * Deploys UZD + OltinStaking on zkSync Sepolia, prints addresses, then prints
 * follow-up steps for verification.
 *
 * Run: npx hardhat deploy-zksync --network zkSyncSepolia --script deploy-uzd-staking.ts
 *
 * Requires `PRIVATE_KEY` of the admin wallet in .env (the one with admin role
 * on OltinTokenV2 — currently `0xa0A78aA9…779e`).
 */

import { Wallet } from "zksync-ethers";
import { Deployer } from "@matterlabs/hardhat-zksync";
import { HardhatRuntimeEnvironment } from "hardhat/types";
import * as dotenv from "dotenv";

dotenv.config();

// OLTIN already deployed on zkSync Sepolia (rotated 2026-04-21)
const OLTIN_ADDRESS = "0x4A56B78DBFc2E6c914f5413B580e86ee1A474347";

export default async function (hre: HardhatRuntimeEnvironment) {
  const pk = process.env.PRIVATE_KEY;
  if (!pk) throw new Error("Set PRIVATE_KEY in .env (admin wallet)");

  const wallet = new Wallet(pk);
  const deployer = new Deployer(hre, wallet);

  console.log(`Deployer: ${wallet.address}`);

  // Deploy UZD
  const uzdArtifact = await deployer.loadArtifact("UZD");
  const uzd = await deployer.deploy(uzdArtifact, []);
  const uzdAddr = await uzd.getAddress();
  console.log(`UZD deployed at:          ${uzdAddr}`);

  // Deploy OltinStaking with OLTIN as the staking token
  const stakingArtifact = await deployer.loadArtifact("OltinStaking");
  const staking = await deployer.deploy(stakingArtifact, [OLTIN_ADDRESS]);
  const stakingAddr = await staking.getAddress();
  console.log(`OltinStaking deployed at: ${stakingAddr}`);

  console.log("\n=== Next steps ===");
  console.log(`1. Verify UZD:`);
  console.log(`   npx hardhat verify --network zkSyncSepolia ${uzdAddr}`);
  console.log(`2. Verify OltinStaking:`);
  console.log(`   npx hardhat verify --network zkSyncSepolia ${stakingAddr} ${OLTIN_ADDRESS}`);
  console.log(`3. Fund the reward pool by calling OltinStaking.fundRewardPool(amount)`);
  console.log(`   (admin must approve OLTIN to staking first)`);
  console.log(`4. Update docs/PROGRESS.md with the deployed addresses.`);
}
