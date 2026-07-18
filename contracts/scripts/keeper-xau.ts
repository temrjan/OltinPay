/**
 * XAU/USD keeper. Reads the canonical Chainlink XAU/USD feed on Ethereum mainnet
 * and relays the answer (8 decimals) to our XauUsdFeed {Attestor} on zkSync
 * Sepolia via postAnswer(). The Attestor self-stamps updatedAt on-chain, so this
 * keeper only forwards the raw answer.
 *
 * Run periodically (e.g. every few minutes):
 *   npx hardhat run scripts/keeper-xau.ts --network zkSyncSepolia
 * or:  npm run keeper:xau
 *
 * Required env (contracts/.env):
 *   MAINNET_RPC_URL        Ethereum mainnet RPC (reads Chainlink)
 *   XAU_FEED_ADDRESS       Chainlink XAU/USD aggregator on mainnet
 *   XAU_ATTESTOR_ADDRESS   our XauUsdFeed Attestor on zkSync Sepolia
 *   KEY_XAU                POSTER private key for XauUsdFeed (0x-prefixed)
 * Optional env:
 *   ZKSYNC_RPC_URL         default https://sepolia.era.zksync.dev
 *   MAX_SOURCE_AGE         max age (s) of the mainnet reading before we refuse
 *                          to relay (default 3600)
 */

import { JsonRpcProvider, Contract as EthersContract } from "ethers";
import { Wallet, Provider, Contract } from "zksync-ethers";

const AGGREGATOR_ABI = [
  "function decimals() view returns (uint8)",
  "function latestRoundData() view returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound)",
];

const ATTESTOR_ABI = [
  "function postAnswer(int256 answer)",
  "function decimals() view returns (uint8)",
];

function requireEnv(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`${name} not set in contracts/.env`);
  return v;
}

async function main() {
  const mainnetRpc = requireEnv("MAINNET_RPC_URL");
  const feedAddress = requireEnv("XAU_FEED_ADDRESS");
  const attestorAddress = requireEnv("XAU_ATTESTOR_ADDRESS");
  const keyXau = requireEnv("KEY_XAU");
  const zkRpc = process.env.ZKSYNC_RPC_URL ?? "https://sepolia.era.zksync.dev";
  const maxSourceAge = BigInt(process.env.MAX_SOURCE_AGE ?? "3600");

  console.log("=== XAU/USD keeper ===");

  // 1. Read Chainlink XAU/USD from mainnet.
  const mainnet = new JsonRpcProvider(mainnetRpc);
  const feed = new EthersContract(feedAddress, AGGREGATOR_ABI, mainnet);
  const feedDecimals: bigint = await feed.decimals();
  const [roundId, answer, , updatedAt] = await feed.latestRoundData();

  console.log(`Chainlink XAU/USD: answer=${answer} (dec ${feedDecimals}) round=${roundId}`);

  // 2. Guard the source reading before relaying.
  if (answer <= 0n) throw new Error(`Refusing to relay non-positive answer: ${answer}`);
  if (feedDecimals !== 8n) {
    throw new Error(`Expected 8-decimal XAU feed, got ${feedDecimals}`);
  }
  const now = BigInt(Math.floor(Date.now() / 1000));
  if (updatedAt > now) throw new Error(`Source updatedAt is in the future: ${updatedAt}`);
  const age = now - updatedAt;
  if (age > maxSourceAge) {
    throw new Error(`Source reading is stale: age ${age}s > ${maxSourceAge}s`);
  }

  // 3. Relay to our XauUsdFeed Attestor on zkSync Sepolia.
  const zk = new Provider(zkRpc);
  const wallet = new Wallet(keyXau, zk);
  const attestor = new Contract(attestorAddress, ATTESTOR_ABI, wallet);

  const attDecimals: bigint = await attestor.decimals();
  if (attDecimals !== feedDecimals) {
    throw new Error(
      `Decimals mismatch: source ${feedDecimals} vs attestor ${attDecimals}`,
    );
  }

  console.log(`Posting answer=${answer} to XauUsdFeed ${attestorAddress} as ${wallet.address}`);
  const tx = await attestor.postAnswer(answer);
  console.log(`  tx: ${tx.hash}`);
  await tx.wait();
  console.log("  ✓ Posted");
}

main().catch((e: unknown) => {
  console.error(e instanceof Error ? e.message : e);
  process.exit(1);
});
