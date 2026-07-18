/**
 * UZS/USD keeper. Fetches the official CBU (Central Bank of Uzbekistan) USD rate
 * (UZS per 1 USD), converts it to a UZS/USD price (USD per 1 UZS) scaled to 8
 * decimals, and posts it to our UzsUsdFeed {Attestor} on zkSync Sepolia. The CBU
 * publishes roughly daily, so run this ~daily.
 *
 *   npx hardhat run scripts/keeper-uzs.ts --network zkSyncSepolia
 * or:  npm run keeper:uzs
 *
 * Required env (contracts/.env):
 *   UZS_ATTESTOR_ADDRESS   our UzsUsdFeed Attestor on zkSync Sepolia
 *   KEY_UZS                POSTER private key for UzsUsdFeed (0x-prefixed)
 * Optional env:
 *   CBU_API_URL            default https://cbu.uz/ru/arkhiv-kursov-valyut/json/
 *   ZKSYNC_RPC_URL         default https://sepolia.era.zksync.dev
 *   MAX_JUMP_BPS           max deviation vs the current on-chain answer before
 *                          we refuse to post, in basis points (default 1000 =
 *                          10%) — a guard against posting a wild/garbage rate
 *   MIN_DELTA              skip posting when |new - on-chain| <= this (in feed
 *                          units, 8 decimals) to avoid empty/no-op L2 txs
 *                          (default 0 = skip only when identical)
 */

import { Wallet, Provider, Contract } from "zksync-ethers";

const ATTESTOR_ABI = [
  "function postAnswer(int256 answer)",
  "function decimals() view returns (uint8)",
  "function latestRoundData() view returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound)",
];

// UZS/USD is quoted at 8 decimals: answer = round( 1e8 / (UZS per USD) ).
const PRICE_DECIMALS = 8;

function requireEnv(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`${name} not set in contracts/.env`);
  return v;
}

async function fetchUzsPerUsd(apiUrl: string): Promise<number> {
  const res = await fetch(apiUrl);
  if (!res.ok) throw new Error(`CBU API HTTP ${res.status}`);
  const data: Array<{ Ccy: string; Rate: string }> = await res.json();
  const usd = data.find((r) => r.Ccy === "USD");
  if (!usd) throw new Error("USD entry not found in CBU response");
  const rate = Number(usd.Rate);
  if (!Number.isFinite(rate) || rate <= 0) {
    throw new Error(`Invalid CBU USD rate: ${usd.Rate}`);
  }
  return rate; // UZS per 1 USD, e.g. 12600.42
}

async function main() {
  const attestorAddress = requireEnv("UZS_ATTESTOR_ADDRESS");
  const keyUzs = requireEnv("KEY_UZS");
  const apiUrl =
    process.env.CBU_API_URL ?? "https://cbu.uz/ru/arkhiv-kursov-valyut/json/";
  const zkRpc = process.env.ZKSYNC_RPC_URL ?? "https://sepolia.era.zksync.dev";
  const maxJumpBps = BigInt(process.env.MAX_JUMP_BPS ?? "1000"); // 10%
  const minDelta = BigInt(process.env.MIN_DELTA ?? "0"); // skip if |Δ| <= this

  console.log("=== UZS/USD keeper ===");

  // 1. Fetch the CBU USD rate (UZS per USD) and invert to USD per UZS @ 1e8.
  const uzsPerUsd = await fetchUzsPerUsd(apiUrl);
  const answer = BigInt(Math.round(10 ** PRICE_DECIMALS / uzsPerUsd));
  if (answer <= 0n) throw new Error(`Computed non-positive answer from rate ${uzsPerUsd}`);
  console.log(
    `CBU USD rate: ${uzsPerUsd} UZS/USD  ->  UZS/USD answer=${answer} (dec ${PRICE_DECIMALS})`,
  );

  // 2. Post to our UzsUsdFeed Attestor.
  const zk = new Provider(zkRpc);
  const wallet = new Wallet(keyUzs, zk);
  const attestor = new Contract(attestorAddress, ATTESTOR_ABI, wallet);

  const attDecimals: bigint = await attestor.decimals();
  if (attDecimals !== BigInt(PRICE_DECIMALS)) {
    throw new Error(
      `Decimals mismatch: expected ${PRICE_DECIMALS}, attestor reports ${attDecimals}`,
    );
  }

  // 3. Compare against the current on-chain answer before spending a tx.
  const current = BigInt((await attestor.latestRoundData())[1]);
  if (current > 0n) {
    const delta = answer > current ? answer - current : current - answer;
    // F9/F10: skip an unchanged reading (within epsilon) — avoids an empty L2 tx.
    if (delta <= minDelta) {
      console.log(
        `On-chain answer unchanged (current=${current}, new=${answer}, |Δ|=${delta} <= ε=${minDelta}). Skipping post.`,
      );
      return;
    }
    // F12/F14: refuse to post a wild deviation instead of posting a bad rate.
    const jumpBps = (delta * 10000n) / current;
    if (jumpBps > maxJumpBps) {
      console.log(
        `SKIP: deviation ${jumpBps}bps exceeds MAX_JUMP_BPS=${maxJumpBps} ` +
          `(current=${current}, new=${answer}). Refusing to post a wild value.`,
      );
      return;
    }
    console.log(`Deviation OK: ${jumpBps}bps (<= ${maxJumpBps}bps).`);
  } else {
    console.log("No prior on-chain answer (first post) — deviation guard skipped.");
  }

  console.log(`Posting answer=${answer} to UzsUsdFeed ${attestorAddress} as ${wallet.address}`);
  const tx = await attestor.postAnswer(answer);
  console.log(`  tx: ${tx.hash}`);
  await tx.wait();
  console.log("  ✓ Posted");
}

main().catch((e: unknown) => {
  console.error(e instanceof Error ? e.message : e);
  process.exit(1);
});
