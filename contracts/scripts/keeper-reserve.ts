/**
 * Reserve keeper. Publishes the demo-bank reserve (grams, 0 decimals) to our
 * ReserveAttestor on zkSync Sepolia via postAnswer(). Methodology (К-1): the
 * bank signs a statement once a day; the operator puts the statement figure
 * into RESERVE_GRAMS; this keeper republishes that same number on a heartbeat
 * so the on-chain reading never goes stale against maxAgeReserve (3600s).
 *
 * The reserve is the number that authorizes minting, so a change beyond
 * MAX_RESERVE_JUMP_BPS is REFUSED unless RESERVE_CONFIRM is set to the exact
 * new value — a typo in env must not reach the chain automatically.
 *
 * Runs via the shared runner:  npm run keeper:all
 * or standalone (manual runs): npm run keeper:reserve
 *
 * Required env (contracts/.env):
 *   RESERVE_ATTESTOR_ADDRESS  our ReserveAttestor on zkSync Sepolia
 *   KEY_RESERVE               POSTER private key for ReserveAttestor (0x-prefixed)
 *   RESERVE_GRAMS             reserve in grams from the bank statement
 * Optional env:
 *   RESERVE_CONFIRM           exact new gram value to confirm a change beyond
 *                             the jump guard (deliberate, manual operation)
 *   MAX_RESERVE_JUMP_BPS      guard for reserve changes, basis points
 *                             (default 1000 = 10%)
 *   HEARTBEAT_AGE             force a post when the on-chain reading reaches
 *                             this age (s), even if the value is unchanged
 *                             (default 1800 = half of maxAgeReserve)
 *   ZKSYNC_RPC_URL            default https://sepolia.era.zksync.dev
 *
 * Exit codes: 0 = posted, 2 = deliberate skip, 1 = refusal/error.
 */

import "dotenv/config";
import { Wallet, Provider, Contract } from "zksync-ethers";
import {
  decideReservePost,
  parsePositiveInt,
  chainNowSeconds,
  EXIT_POSTED,
  EXIT_SKIPPED,
  EXIT_FAILED,
} from "./keeper-lib";

const ATTESTOR_ABI = [
  "function postAnswer(int256 answer)",
  "function decimals() view returns (uint8)",
  "function latestRoundData() view returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound)",
];

function requireEnv(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`${name} not set in contracts/.env`);
  return v;
}

export async function run(): Promise<number> {
  const attestorAddress = requireEnv("RESERVE_ATTESTOR_ADDRESS");
  const keyReserve = requireEnv("KEY_RESERVE");
  const zkRpc = process.env.ZKSYNC_RPC_URL ?? "https://sepolia.era.zksync.dev";
  const maxJumpBps = BigInt(process.env.MAX_RESERVE_JUMP_BPS ?? "1000"); // 10%
  const heartbeatAge = BigInt(process.env.HEARTBEAT_AGE ?? "1800");
  const next = parsePositiveInt(requireEnv("RESERVE_GRAMS"), "RESERVE_GRAMS");
  const confirm = process.env.RESERVE_CONFIRM || undefined;

  console.log("=== Reserve keeper ===");
  console.log(`Statement figure: ${next}g (RESERVE_GRAMS)`);

  // 1. Relay target.
  const zk = new Provider(zkRpc);
  const wallet = new Wallet(keyReserve, zk);
  const attestor = new Contract(attestorAddress, ATTESTOR_ABI, wallet);

  const attDecimals: bigint = await attestor.decimals();
  if (attDecimals !== 0n) {
    console.error(`REFUSE: expected 0-decimal reserve feed, got ${attDecimals}`);
    return EXIT_FAILED;
  }

  // 2. Decide (on-chain age measured against the L2 block timestamp).
  const [, current, , currentUpdatedAt] = await attestor.latestRoundData();
  const now = await chainNowSeconds(zk);
  const decision = decideReservePost({
    current: BigInt(current),
    currentUpdatedAt: BigInt(currentUpdatedAt),
    next,
    now,
    heartbeatAge,
    maxJumpBps,
    confirm,
  });
  console.log(`Decision: ${decision.action} — ${decision.reason}`);
  if (decision.action === "skip") return EXIT_SKIPPED;
  if (decision.action === "refuse") return EXIT_FAILED;

  // 3. Post.
  console.log(`Posting reserve=${next}g to ReserveAttestor ${attestorAddress} as ${wallet.address}`);
  const tx = await attestor.postAnswer(next);
  console.log(`  tx: ${tx.hash}`);
  await tx.wait();
  console.log("  ✓ Posted");
  return EXIT_POSTED;
}

if (require.main === module) {
  run()
    .then((code) => process.exit(code))
    .catch((e: unknown) => {
      console.error(e instanceof Error ? e.message : e);
      process.exit(EXIT_FAILED);
    });
}
