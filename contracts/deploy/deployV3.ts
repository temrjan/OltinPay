/**
 * Deploys the OltinChain V3 Proof-of-Reserve stack on zkSync Sepolia:
 *
 *   - 3x Attestor:  ReserveAttestor (decimals 0), XauUsdFeed (decimals 8),
 *                   UzsUsdFeed (decimals 8)
 *   - OltinTokenV3(reserveFeed = ReserveAttestor, maxAgeReserve, feeCollector)
 *   - Exchange(oltin, uzd, xauFeed, uzsFeed, maxAgeXau, maxAgeUzs)
 *
 * Post-deploy wiring:
 *   - grants OLTIN MINTER_ROLE to the Exchange (the Exchange is the SOLE minter)
 *   - grants each Attestor POSTER_ROLE to its keeper EOA (KEY_RESERVE / KEY_XAU
 *     / KEY_UZS), if provided.
 *
 * The Exchange IS the UZD treasury (buys deposit UZD into it; sells pay UZD from
 * it). To demo `sell` before any `buy`, seed the treasury by transferring UZD to
 * the printed Exchange address (see the note at the end).
 *
 * Run:
 *   npx hardhat deploy-zksync --network zkSyncSepolia --script deployV3.ts
 *
 * Required env (contracts/.env):
 *   PRIVATE_KEY   deployer/admin (with 0x prefix)
 *   UZD_ADDRESS   existing UZD stablecoin on zkSync Sepolia
 * Optional env (all staleness windows are DEMO values — set explicitly for prod):
 *   MAX_AGE_RESERVE  reserve staleness window, seconds (default 3600 = 1h)
 *   MAX_AGE_XAU      XAU/USD staleness window, seconds (default 3600 = 1h;
 *                    the XAU keeper relays frequently)
 *   MAX_AGE_UZS      UZS/USD staleness window, seconds (default 259200 = 3 days;
 *                    the CBU posts ~daily, so this must survive weekend/holiday
 *                    gaps or buy/sell would revert almost all day)
 *   FEE_COLLECTOR    dormant fee sink (default = deployer)
 *   KEY_RESERVE / KEY_XAU / KEY_UZS   keeper private keys -> granted POSTER_ROLE
 */

import { Wallet, Provider } from "zksync-ethers";
import { Deployer } from "@matterlabs/hardhat-zksync";
import { HardhatRuntimeEnvironment } from "hardhat/types";
import * as dotenv from "dotenv";

dotenv.config();

const RPC_URL = "https://sepolia.era.zksync.dev";

function posterAddress(key?: string): string | undefined {
  if (!key) return undefined;
  return new Wallet(key).address;
}

export default async function (hre: HardhatRuntimeEnvironment) {
  const pk = process.env.PRIVATE_KEY;
  if (!pk) throw new Error("Set PRIVATE_KEY in contracts/.env (deployer/admin)");

  const uzdAddress = process.env.UZD_ADDRESS;
  if (!uzdAddress) {
    throw new Error("Set UZD_ADDRESS in contracts/.env (existing UZD on zkSync Sepolia)");
  }

  // DEMO staleness windows (see header). Per-feed for prices: XAU refreshes
  // often (short window); UZS is CBU-daily (long window, survives weekend gaps).
  const maxAgeReserve = BigInt(process.env.MAX_AGE_RESERVE ?? "3600"); // demo: 1h
  const maxAgeXau = BigInt(process.env.MAX_AGE_XAU ?? "3600"); // demo: 1h
  const maxAgeUzs = BigInt(process.env.MAX_AGE_UZS ?? "259200"); // demo: 3 days

  const provider = new Provider(RPC_URL);
  const wallet = new Wallet(pk, provider);
  const deployer = new Deployer(hre, wallet);
  const feeCollector = process.env.FEE_COLLECTOR ?? wallet.address;

  console.log("=== Deploying OltinChain V3 (Proof-of-Reserve) ===");
  console.log(`Deployer:      ${wallet.address}`);
  console.log(`UZD:           ${uzdAddress}`);
  console.log(
    `maxAgeReserve: ${maxAgeReserve}s   maxAgeXau: ${maxAgeXau}s   maxAgeUzs: ${maxAgeUzs}s`,
  );

  // --- 3x Attestor (one code, three instances) ---
  const attestorArtifact = await deployer.loadArtifact("Attestor");

  const reserveFeed = await deployer.deploy(attestorArtifact, [0]); // grams, 0 dec
  const reserveAddr = await reserveFeed.getAddress();
  console.log(`ReserveAttestor (dec 0): ${reserveAddr}`);

  const xauFeed = await deployer.deploy(attestorArtifact, [8]); // XAU/USD, 8 dec
  const xauAddr = await xauFeed.getAddress();
  console.log(`XauUsdFeed (dec 8):      ${xauAddr}`);

  const uzsFeed = await deployer.deploy(attestorArtifact, [8]); // UZS/USD, 8 dec
  const uzsAddr = await uzsFeed.getAddress();
  console.log(`UzsUsdFeed (dec 8):      ${uzsAddr}`);

  // --- OltinTokenV3 ---
  const tokenArtifact = await deployer.loadArtifact("OltinTokenV3");
  const oltin = await deployer.deploy(tokenArtifact, [
    reserveAddr,
    maxAgeReserve,
    feeCollector,
  ]);
  const oltinAddr = await oltin.getAddress();
  console.log(`OltinTokenV3:            ${oltinAddr}`);

  // --- Exchange ---
  const exchangeArtifact = await deployer.loadArtifact("Exchange");
  const exchange = await deployer.deploy(exchangeArtifact, [
    oltinAddr,
    uzdAddress,
    xauAddr,
    uzsAddr,
    maxAgeXau,
    maxAgeUzs,
  ]);
  const exchangeAddr = await exchange.getAddress();
  console.log(`Exchange (treasury):     ${exchangeAddr}`);

  // === Wiring ===
  console.log("\n=== Wiring roles ===");

  // Exchange is the SOLE OLTIN minter.
  const MINTER_ROLE = await oltin.MINTER_ROLE();
  const grantMinter = await oltin.grantRole(MINTER_ROLE, exchangeAddr);
  await grantMinter.wait();
  console.log(`Granted OLTIN MINTER_ROLE -> Exchange (${exchangeAddr})`);

  // Grant POSTER_ROLE on each feed to its keeper EOA (if configured).
  const POSTER_ROLE = await reserveFeed.POSTER_ROLE();
  const keepers: Array<[string, any, string, string | undefined]> = [
    ["ReserveAttestor", reserveFeed, reserveAddr, posterAddress(process.env.KEY_RESERVE)],
    ["XauUsdFeed", xauFeed, xauAddr, posterAddress(process.env.KEY_XAU)],
    ["UzsUsdFeed", uzsFeed, uzsAddr, posterAddress(process.env.KEY_UZS)],
  ];
  for (const [name, feed, , keeper] of keepers) {
    if (!keeper) {
      console.log(`(skip) ${name}: no keeper key set — deployer remains sole POSTER`);
      continue;
    }
    const tx = await feed.grantRole(POSTER_ROLE, keeper);
    await tx.wait();
    console.log(`Granted ${name} POSTER_ROLE -> ${keeper}`);
  }

  // === Verify ===
  console.log("\n=== Verifying on explorer ===");
  const toVerify: Array<[string, string, any[]]> = [
    ["Attestor(Reserve)", reserveAddr, [0]],
    ["Attestor(XAU)", xauAddr, [8]],
    ["Attestor(UZS)", uzsAddr, [8]],
    ["OltinTokenV3", oltinAddr, [reserveAddr, maxAgeReserve, feeCollector]],
    [
      "Exchange",
      exchangeAddr,
      [oltinAddr, uzdAddress, xauAddr, uzsAddr, maxAgeXau, maxAgeUzs],
    ],
  ];
  for (const [name, address, constructorArguments] of toVerify) {
    try {
      await hre.run("verify:verify", { address, constructorArguments });
      console.log(`Verified ${name}`);
    } catch (e) {
      console.log(`Verify ${name} failed (may already be verified):`, e);
    }
  }

  // === Next steps ===
  console.log("\n=== Deployment complete — record these addresses ===");
  console.log(`RESERVE_ATTESTOR_ADDRESS=${reserveAddr}`);
  console.log(`XAU_ATTESTOR_ADDRESS=${xauAddr}`);
  console.log(`UZS_ATTESTOR_ADDRESS=${uzsAddr}`);
  console.log(`OLTIN_V3_ADDRESS=${oltinAddr}`);
  console.log(`EXCHANGE_ADDRESS=${exchangeAddr}`);
  console.log("\nNext:");
  console.log("1. Post an initial reserve:  ReserveAttestor.postAnswer(<grams>)");
  console.log("2. Start keepers:            npm run keeper:xau ; npm run keeper:uzs");
  console.log(
    `3. Seed the treasury for sell demos: transfer UZD to the Exchange (${exchangeAddr}).`,
  );
  console.log("4. Update docs/PROGRESS.md with the addresses above.");
}
