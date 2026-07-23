/**
 * UZS/USD keeper. Reads the official Central Bank of Uzbekistan JSON rate
 * (sum per 1 USD) and relays it (8 decimals) to our UzsUsdFeed {Attestor} on
 * zkSync Sepolia via postAnswer().
 *
 * Runs via the shared runner:  npm run keeper:all
 * or standalone (manual runs): npm run keeper:uzs
 *
 * Required env (contracts/.env):
 *   UZS_ATTESTOR_ADDRESS   our UzsUsdFeed Attestor on zkSync Sepolia
 *   KEY_UZS                POSTER private key for UzsUsdFeed (0x-prefixed)
 * Optional env:
 *   CBU_URL                default https://cbu.uz/ru/arkhiv-kursov-valyut/json/USD/
 *   ZKSYNC_RPC_URL         default https://sepolia.era.zksync.dev
 *   MAX_CB_AGE_DAYS        max age (days) of the CBU rate before we declare the
 *                          API broken and refuse (default 7 — the CBU
 *                          republishes the last business day over weekends, so
 *                          a 3-day-old Monday rate is normal; this guard
 *                          catches a broken API, not a weekend)
 *   MAX_JUMP_BPS           max deviation vs the current on-chain answer before
 *                          we refuse (needs a human), in basis points
 *                          (default 1000 = 10%)
 *   MIN_DELTA              skip posting when |new - on-chain| <= this (in feed
 *                          units, 8 decimals) UNLESS the heartbeat is due
 *                          (default 0)
 *   HEARTBEAT_AGE_UZS      force a post when the on-chain reading reaches this
 *                          age (s), even if the value is unchanged
 *                          (default 86400 = daily; maxAgeUzs is 3 days)
 *
 * Exit codes: 0 = posted, 2 = deliberate skip, 1 = refusal/error.
 */

import "dotenv/config";
import { Wallet, Provider, Contract } from "zksync-ethers";
import {
  decidePost,
  parseCbuResponse,
  parseDecimalToScaledInt,
  cbuRateAgeDays,
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
  const attestorAddress = requireEnv("UZS_ATTESTOR_ADDRESS");
  const keyUzs = requireEnv("KEY_UZS");
  const cbuUrl =
    process.env.CBU_URL ?? "https://cbu.uz/ru/arkhiv-kursov-valyut/json/USD/";
  const zkRpc = process.env.ZKSYNC_RPC_URL ?? "https://sepolia.era.zksync.dev";
  const maxCbAgeDays = Number(process.env.MAX_CB_AGE_DAYS ?? "7");
  const maxJumpBps = BigInt(process.env.MAX_JUMP_BPS ?? "1000"); // 10%
  const minDelta = BigInt(process.env.MIN_DELTA ?? "0");
  const heartbeatAge = BigInt(process.env.HEARTBEAT_AGE_UZS ?? "86400");

  console.log("=== UZS/USD keeper ===");

  // 1. Read the CBU rate. External input is untrusted: shape-check, then
  //    parse the decimal without floats. Bounded wait: a hung CBU must not
  //    hang keeper:all (and through it, the other feeds).
  const res = await fetch(cbuUrl, { signal: AbortSignal.timeout(30_000) });
  if (!res.ok) {
    console.error(`REFUSE: CBU API returned HTTP ${res.status}`);
    return EXIT_FAILED;
  }
  const body: unknown = await res.json();
  const { rateRaw, dateRaw } = parseCbuResponse(body);
  const next = parseDecimalToScaledInt(rateRaw, 8);
  if (next <= 0n) {
    console.error(`REFUSE: non-positive CBU rate: ${rateRaw}`);
    return EXIT_FAILED;
  }
  console.log(`CBU USD rate: ${rateRaw} (effective ${dateRaw}) -> ${next} (dec 8)`);

  // 2. Guard the source age. Calendar dates only — the local clock is fine
  //    here (a day of skew cannot produce a false refusal at a 7-day guard).
  const ageDays = cbuRateAgeDays(dateRaw, new Date());
  if (ageDays > maxCbAgeDays) {
    console.error(
      `REFUSE: CBU rate is ${ageDays} days old (> ${maxCbAgeDays}) — API looks broken`,
    );
    return EXIT_FAILED;
  }
  if (ageDays < 0) {
    console.error(`REFUSE: CBU rate date is in the future: ${dateRaw}`);
    return EXIT_FAILED;
  }

  // 3. Relay target.
  const zk = new Provider(zkRpc);
  const wallet = new Wallet(keyUzs, zk);
  const attestor = new Contract(attestorAddress, ATTESTOR_ABI, wallet);

  const attDecimals: bigint = await attestor.decimals();
  if (attDecimals !== 8n) {
    console.error(`REFUSE: expected 8-decimal UZS feed, got ${attDecimals}`);
    return EXIT_FAILED;
  }

  // 4. Decide (on-chain age measured against the L2 block timestamp).
  const [, current, , currentUpdatedAt] = await attestor.latestRoundData();
  const now = await chainNowSeconds(zk);
  const decision = decidePost({
    current: BigInt(current),
    currentUpdatedAt: BigInt(currentUpdatedAt),
    next,
    now,
    minDelta,
    maxJumpBps,
    heartbeatAge,
  });
  console.log(`Decision: ${decision.action} — ${decision.reason}`);
  if (decision.action === "skip") return EXIT_SKIPPED;
  if (decision.action === "refuse") return EXIT_FAILED;

  // 5. Post.
  console.log(`Posting answer=${next} to UzsUsdFeed ${attestorAddress} as ${wallet.address}`);
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
