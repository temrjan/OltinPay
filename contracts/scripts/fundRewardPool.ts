/**
 * Fund OltinStaking.rewardPool to a target balance.
 *
 * Idempotent: ensures rewardPool >= FUND_AMOUNT_OLTIN. Mints OLTIN to admin
 * if balance is insufficient, approves the staking contract, then calls
 * fundRewardPool with the delta. Skips early if pool is already at target.
 *
 * Run:
 *   PRIVATE_KEY=0x... npx hardhat run scripts/fundRewardPool.ts --network zkSyncSepolia
 *
 * Override amount (default 1000):
 *   FUND_AMOUNT_OLTIN=2000 npx hardhat run scripts/fundRewardPool.ts --network zkSyncSepolia
 */
// Hardhat loads contracts/.env via hardhat.config.ts (dotenv.config()) before
// running any script, so PRIVATE_KEY is already in process.env here.
import { Wallet, Provider, Contract } from "zksync-ethers";

const OLTIN_ADDRESS = "0x4A56B78DBFc2E6c914f5413B580e86ee1A474347";
const STAKING_ADDRESS = "0x63e537A3a150d06035151E29904C1640181C8314";
const FUND_ORDER_ID = "fund-reward-pool";

const OLTIN_ABI = [
  "function mint(address to, uint256 amount, string orderId)",
  "function balanceOf(address) view returns (uint256)",
  "function approve(address spender, uint256 amount) returns (bool)",
  "function allowance(address owner, address spender) view returns (uint256)",
];

const STAKING_ABI = [
  "function fundRewardPool(uint256 amount)",
  "function rewardPool() view returns (uint256)",
];

function formatOltin(wei: bigint): string {
  return `${(Number(wei) / 1e18).toFixed(4)} OLTIN`;
}

async function main() {
  const privateKey = process.env.PRIVATE_KEY;
  if (!privateKey) {
    throw new Error("PRIVATE_KEY not set in contracts/.env");
  }

  const fundAmountRaw = process.env.FUND_AMOUNT_OLTIN ?? "1000";
  if (!/^\d+$/.test(fundAmountRaw)) {
    throw new Error(
      `FUND_AMOUNT_OLTIN must be a positive integer, got: ${fundAmountRaw}`,
    );
  }
  const fundAmountOltin = BigInt(fundAmountRaw);
  const targetAmount = fundAmountOltin * 10n ** 18n;

  const provider = new Provider("https://sepolia.era.zksync.dev");
  const wallet = new Wallet(privateKey, provider);

  console.log("=== Fund OltinStaking.rewardPool ===");
  console.log(`Admin:             ${wallet.address}`);
  console.log(`Target rewardPool: ${formatOltin(targetAmount)}`);

  const oltin = new Contract(OLTIN_ADDRESS, OLTIN_ABI, wallet);
  const staking = new Contract(STAKING_ADDRESS, STAKING_ABI, wallet);

  // 1. Check current rewardPool — skip if already funded.
  const rewardPoolBefore: bigint = await staking.rewardPool();
  console.log(`\nCurrent rewardPool: ${formatOltin(rewardPoolBefore)}`);

  if (rewardPoolBefore >= targetAmount) {
    console.log("Already at or above target. Nothing to do.");
    return;
  }

  const toFund = targetAmount - rewardPoolBefore;
  console.log(`Need to add: ${formatOltin(toFund)}`);

  // 2. Read admin's OLTIN balance and current allowance in parallel.
  const [balance, currentAllowance]: [bigint, bigint] = await Promise.all([
    oltin.balanceOf(wallet.address),
    oltin.allowance(wallet.address, STAKING_ADDRESS),
  ]);
  console.log(`Admin OLTIN balance: ${formatOltin(balance)}`);

  // 3. Mint OLTIN to admin if balance insufficient.
  if (balance < toFund) {
    const toMint = toFund - balance;
    console.log(`\nMinting ${formatOltin(toMint)} to admin...`);
    const mintTx = await oltin.mint(wallet.address, toMint, FUND_ORDER_ID);
    console.log(`  tx: ${mintTx.hash}`);
    await mintTx.wait();
    console.log(`  ✓ Minted`);
  }

  // 4. Approve staking contract for the delta.
  if (currentAllowance < toFund) {
    console.log(`\nApproving ${formatOltin(toFund)} for staking contract...`);
    const approveTx = await oltin.approve(STAKING_ADDRESS, toFund);
    console.log(`  tx: ${approveTx.hash}`);
    await approveTx.wait();
    console.log(`  ✓ Approved`);
  }

  // 5. Fund the reward pool.
  console.log(`\nCalling fundRewardPool(${formatOltin(toFund)})...`);
  const fundTx = await staking.fundRewardPool(toFund);
  console.log(`  tx: ${fundTx.hash}`);
  await fundTx.wait();
  console.log(`  ✓ Funded`);

  // 6. Verify final state.
  const rewardPoolAfter: bigint = await staking.rewardPool();
  console.log(
    `\nRewardPool: ${formatOltin(rewardPoolBefore)} → ${formatOltin(rewardPoolAfter)}`,
  );

  console.log("\n=== Done ===");
}

main().catch((e: unknown) => {
  console.error(e instanceof Error ? e.message : e);
  process.exit(1);
});
