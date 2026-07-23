/**
 * XAU/USD keeper (P1-E, 24/7 price). Source of truth is the MEDIAN of
 * tokenized-gold quotes (PAXG + XAUT, USD pairs) from the Alchemy Prices API —
 * these trade around the clock, so our price no longer freezes with the
 * metals market. Chainlink XAU/USD stays on as a LIVENESS DETECTOR ONLY (no
 * price cross-check, Captain's decision): if the token sources are dead while
 * Chainlink is fresh, WE are broken; if both are dead, it is an infra outage.
 * Both cases refuse (exit 1) and need a human.
 *
 * Posts the median (8 decimals) to our XauUsdFeed {Attestor} on zkSync
 * Sepolia via postAnswer(). The Attestor self-stamps updatedAt on-chain.
 *
 * Runs via the shared runner (one wallet, one nonce stream):
 *   npm run keeper:all
 * or standalone (manual runs):
 *   npm run keeper:xau
 *
 * Required env (contracts/.env):
 *   ALCHEMY_PRICES_URL     Alchemy Prices API base, same account/key as the
 *                          RPC, e.g. https://api.g.alchemy.com/prices/v1/<key>/tokens/by-symbol
 *   MAINNET_RPC_URL        Ethereum mainnet RPC (Chainlink detector + L1 clock)
 *   XAU_FEED_ADDRESS       Chainlink XAU/USD aggregator on mainnet (detector)
 *   XAU_ATTESTOR_ADDRESS   our XauUsdFeed Attestor on zkSync Sepolia
 *   KEY_XAU                POSTER private key for XauUsdFeed (0x-prefixed)
 * Optional env:
 *   PRICE_SYMBOLS          default "PAXG,XAUT"
 *   MAX_TOKEN_PRICE_AGE    max age (s) of a token quote before it counts as
 *                          dead (default 3600)
 *   SOURCE_WARN_AGE        Chainlink counts as fresh at or below this age (s)
 *                          for the detector (default 82800 = 23h, above its
 *                          22h20m heartbeat)
 *   ZKSYNC_RPC_URL         default https://sepolia.era.zksync.dev
 *   MAX_JUMP_BPS           max deviation vs the current on-chain answer before
 *                          we refuse (needs a human), in basis points
 *                          (default 1000 = 10%)
 *   MIN_DELTA              skip posting when |new - on-chain| <= this (in feed
 *                          units, 8 decimals) UNLESS the heartbeat is due
 *                          (default 0 = skip only when identical)
 *   HEARTBEAT_AGE          force a post when the on-chain reading reaches this
 *                          age (s), even if the value is unchanged
 *                          (default 1800 = half of maxAgeXau)
 *
 * Exit codes: 0 = posted, 2 = deliberate skip, 1 = refusal/error.
 */

import "dotenv/config";
import { JsonRpcProvider, Contract as EthersContract } from "ethers";
import { Wallet, Provider, Contract } from "zksync-ethers";
import {
  decidePost,
  decideGoldPrice,
  parsePricesBySymbolResponse,
  chainNowSeconds,
  EXIT_POSTED,
  EXIT_SKIPPED,
  EXIT_FAILED,
  type TokenUsdPrice,
} from "./keeper-lib";

const AGGREGATOR_ABI = [
  "function decimals() view returns (uint8)",
  "function latestRoundData() view returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound)",
];

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
  const pricesUrl = requireEnv("ALCHEMY_PRICES_URL");
  const mainnetRpc = requireEnv("MAINNET_RPC_URL");
  const feedAddress = requireEnv("XAU_FEED_ADDRESS");
  const attestorAddress = requireEnv("XAU_ATTESTOR_ADDRESS");
  const keyXau = requireEnv("KEY_XAU");
  const zkRpc = process.env.ZKSYNC_RPC_URL ?? "https://sepolia.era.zksync.dev";
  const symbols = (process.env.PRICE_SYMBOLS ?? "PAXG,XAUT")
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  const maxTokenPriceAge = BigInt(process.env.MAX_TOKEN_PRICE_AGE ?? "3600");
  const chainlinkFreshAge = BigInt(process.env.SOURCE_WARN_AGE ?? "82800"); // 23h
  const maxJumpBps = BigInt(process.env.MAX_JUMP_BPS ?? "1000"); // 10%
  const minDelta = BigInt(process.env.MIN_DELTA ?? "0");
  const heartbeatAge = BigInt(process.env.HEARTBEAT_AGE ?? "1800");

  console.log("=== XAU/USD keeper (24/7 median) ===");

  const mainnet = new JsonRpcProvider(mainnetRpc);

  // 1. Shared clock: the L1 block timestamp. If it is unreachable, token
  //    quotes cannot be freshness-validated either (age < 0 discards them),
  //    which funnels into the detector path below.
  let nowL1 = 0n;
  try {
    nowL1 = await chainNowSeconds(mainnet);
  } catch (e: unknown) {
    console.log(`WARN: cannot read the L1 block time: ${e instanceof Error ? e.message : e}`);
  }

  // 2. Chainlink — liveness detector only. Never compared on price.
  let chainlinkAgeSeconds: bigint | undefined;
  if (nowL1 > 0n) {
    try {
      const feed = new EthersContract(feedAddress, AGGREGATOR_ABI, mainnet);
      const [roundId, answer, , updatedAt] = await feed.latestRoundData();
      chainlinkAgeSeconds = nowL1 - BigInt(updatedAt);
      console.log(`Chainlink XAU/USD (detector): answer=${answer} age=${chainlinkAgeSeconds}s round=${roundId}`);
    } catch (e: unknown) {
      console.log(`WARN: chainlink read failed: ${e instanceof Error ? e.message : e}`);
    }
  }

  // 3. Token sources (24/7) via the Alchemy Prices API.
  let tokenPrices: TokenUsdPrice[] = [];
  try {
    const res = await fetch(`${pricesUrl}?symbols=${symbols.join(",")}`, {
      signal: AbortSignal.timeout(30_000),
    });
    if (!res.ok) {
      console.error(`WARN: prices API returned HTTP ${res.status} — token sources count as dead`);
    } else {
      const body: unknown = await res.json();
      tokenPrices = parsePricesBySymbolResponse(body);
    }
  } catch (e: unknown) {
    console.error(`WARN: prices API failed: ${e instanceof Error ? e.message : e}`);
  }

  // 4. Median + detector.
  const gold = decideGoldPrice({
    prices: tokenPrices,
    nowSeconds: nowL1,
    maxTokenPriceAge,
    minSaneUsd: 100_00000000n, // $100
    maxSaneUsd: 100000_00000000n, // $100,000
    chainlinkAgeSeconds,
    chainlinkFreshAge,
  });
  if (gold.action === "refuse") {
    console.error(`REFUSE: ${gold.reason}`);
    return EXIT_FAILED;
  }
  console.log(`Gold price: ${gold.reason}`);
  const next = gold.price;

  // 5. Relay to our XauUsdFeed Attestor on zkSync Sepolia.
  const zk = new Provider(zkRpc);
  const wallet = new Wallet(keyXau, zk);
  const attestor = new Contract(attestorAddress, ATTESTOR_ABI, wallet);

  const attDecimals: bigint = await attestor.decimals();
  if (attDecimals !== 8n) {
    console.error(`REFUSE: expected 8-decimal XAU feed, got ${attDecimals}`);
    return EXIT_FAILED;
  }

  // 6. Decide. The on-chain age is measured against the L2 block timestamp.
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

  // 7. Post.
  console.log(`Posting answer=${next} to XauUsdFeed ${attestorAddress} as ${wallet.address}`);
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
