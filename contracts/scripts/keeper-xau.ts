/**
 * XAU/USD keeper. Reads the canonical Chainlink XAU/USD feed on Ethereum mainnet
 * and relays the answer (8 decimals) to our XauUsdFeed {Attestor} on zkSync
 * Sepolia via postAnswer(). The Attestor self-stamps updatedAt on-chain, so this
 * keeper only forwards the raw answer.
 *
 * Runs via the shared runner (one wallet, one nonce stream):
 *   npm run keeper:all
 * or standalone (manual runs):
 *   npm run keeper:xau
 *
 * Required env (contracts/.env):
 *   MAINNET_RPC_URL        Ethereum mainnet RPC, keyed provider (reads Chainlink)
 *   XAU_FEED_ADDRESS       Chainlink XAU/USD aggregator on mainnet
 *   XAU_ATTESTOR_ADDRESS   our XauUsdFeed Attestor on zkSync Sepolia
 *   KEY_XAU                POSTER private key for XauUsdFeed (0x-prefixed)
 * Optional env:
 *   ZKSYNC_RPC_URL         default https://sepolia.era.zksync.dev
 *   MAX_SOURCE_AGE         max age (s) of the mainnet reading before we declare
 *                          the source broken and refuse (default 259200 = 72h;
 *                          never below 26h — the Chainlink heartbeat of 22h20m
 *                          legitimately leaves readings ~22h old on weekends)
 *   SOURCE_WARN_AGE        age (s) above which we relay with a "source heartbeat
 *                          exceeded" warning in the log (default 82800 = 23h)
 *   MAX_JUMP_BPS           max deviation vs the current on-chain answer before
 *                          we skip, in basis points (default 1000 = 10%)
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
  checkSourceAge,
  chainNowSeconds,
  EXIT_POSTED,
  EXIT_SKIPPED,
  EXIT_FAILED,
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
  const mainnetRpc = requireEnv("MAINNET_RPC_URL");
  const feedAddress = requireEnv("XAU_FEED_ADDRESS");
  const attestorAddress = requireEnv("XAU_ATTESTOR_ADDRESS");
  const keyXau = requireEnv("KEY_XAU");
  const zkRpc = process.env.ZKSYNC_RPC_URL ?? "https://sepolia.era.zksync.dev";
  const maxSourceAge = BigInt(process.env.MAX_SOURCE_AGE ?? "259200"); // 72h
  const sourceWarnAge = BigInt(process.env.SOURCE_WARN_AGE ?? "82800"); // 23h
  const maxJumpBps = BigInt(process.env.MAX_JUMP_BPS ?? "1000"); // 10%
  const minDelta = BigInt(process.env.MIN_DELTA ?? "0");
  const heartbeatAge = BigInt(process.env.HEARTBEAT_AGE ?? "1800");

  console.log("=== XAU/USD keeper ===");

  // 1. Read Chainlink XAU/USD from mainnet.
  const mainnet = new JsonRpcProvider(mainnetRpc);
  const feed = new EthersContract(feedAddress, AGGREGATOR_ABI, mainnet);
  const feedDecimals: bigint = await feed.decimals();
  const [roundId, answer, , updatedAt] = await feed.latestRoundData();

  console.log(`Chainlink XAU/USD: answer=${answer} (dec ${feedDecimals}) round=${roundId}`);

  // 2. Guard the source reading before relaying. The source clock is the
  //    mainnet block timestamp, not the local clock.
  if (answer <= 0n) {
    console.error(`REFUSE: non-positive answer: ${answer}`);
    return EXIT_FAILED;
  }
  if (feedDecimals !== 8n) {
    console.error(`REFUSE: expected 8-decimal XAU feed, got ${feedDecimals}`);
    return EXIT_FAILED;
  }
  const l1Now = await chainNowSeconds(mainnet);
  if (updatedAt > l1Now) {
    console.error(`REFUSE: source updatedAt is in the future: ${updatedAt}`);
    return EXIT_FAILED;
  }
  const sourceAge = l1Now - BigInt(updatedAt);
  const verdict = checkSourceAge(sourceAge, maxSourceAge, sourceWarnAge);
  if (verdict.level === "refuse") {
    console.error(`REFUSE: ${verdict.reason}`);
    return EXIT_FAILED;
  }
  if (verdict.level === "warn") {
    console.log(`WARN: ${verdict.message}`);
  }

  // 3. Relay to our XauUsdFeed Attestor on zkSync Sepolia.
  const zk = new Provider(zkRpc);
  const wallet = new Wallet(keyXau, zk);
  const attestor = new Contract(attestorAddress, ATTESTOR_ABI, wallet);

  const attDecimals: bigint = await attestor.decimals();
  if (attDecimals !== feedDecimals) {
    console.error(
      `REFUSE: decimals mismatch: source ${feedDecimals} vs attestor ${attDecimals}`,
    );
    return EXIT_FAILED;
  }

  // 4. Decide. The on-chain age is measured against the L2 block timestamp.
  const [, current, , currentUpdatedAt] = await attestor.latestRoundData();
  const now = await chainNowSeconds(zk);
  const decision = decidePost({
    current: BigInt(current),
    currentUpdatedAt: BigInt(currentUpdatedAt),
    next: BigInt(answer),
    now,
    minDelta,
    maxJumpBps,
    heartbeatAge,
  });
  console.log(`Decision: ${decision.action} — ${decision.reason}`);
  if (decision.action === "skip") return EXIT_SKIPPED;
  if (decision.action === "refuse") return EXIT_FAILED;

  // 5. Post.
  console.log(`Posting answer=${answer} to XauUsdFeed ${attestorAddress} as ${wallet.address}`);
  const tx = await attestor.postAnswer(answer);
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
