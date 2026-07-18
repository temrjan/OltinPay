/**
 * Deploys a SECOND asset stack (its own reserve Attestor + its own OltinTokenV3
 * instance) in one command — to prove "gold is the example, not the limit".
 *
 * There is deliberately NO multi-asset factory: we simply reuse the exact same
 * Attestor + OltinTokenV3 code with different constructor args (a different
 * reserve feed, e.g. a cotton- or grain-backed reserve). The token metadata is
 * fixed in OltinTokenV3 for this release; the asset differentiation here is the
 * independent reserve feed backing the second instance.
 *
 * Run:
 *   npx hardhat deploy-zksync --network zkSyncSepolia --script deploySecondAsset.ts
 * or:  npm run deploy:second
 *
 * Required env (contracts/.env):
 *   PRIVATE_KEY   deployer/admin (with 0x prefix)
 * Optional env:
 *   SECOND_ASSET_LABEL       human label for logs (default "Cotton")
 *   SECOND_MAX_AGE_RESERVE   reserve staleness window, seconds (default 86400)
 *   FEE_COLLECTOR            dormant fee sink (default = deployer)
 *   KEY_RESERVE_2            keeper private key -> granted POSTER_ROLE
 *   SECOND_MINTER            address granted MINTER_ROLE on the second token so
 *                            it is actually mintable (default = deployer). We do
 *                            NOT deploy a gold-priced Exchange for a non-gold
 *                            asset; granting MINTER to an explicit minter is the
 *                            one-code way to make the second token live.
 */

import { Wallet, Provider } from "zksync-ethers";
import { Deployer } from "@matterlabs/hardhat-zksync";
import { HardhatRuntimeEnvironment } from "hardhat/types";
import * as dotenv from "dotenv";

dotenv.config();

const RPC_URL = "https://sepolia.era.zksync.dev";

export default async function (hre: HardhatRuntimeEnvironment) {
  const pk = process.env.PRIVATE_KEY;
  if (!pk) throw new Error("Set PRIVATE_KEY in contracts/.env (deployer/admin)");

  const label = process.env.SECOND_ASSET_LABEL ?? "Cotton";
  const maxAgeReserve = BigInt(process.env.SECOND_MAX_AGE_RESERVE ?? "86400"); // 1 day

  const provider = new Provider(RPC_URL);
  const wallet = new Wallet(pk, provider);
  const deployer = new Deployer(hre, wallet);
  const feeCollector = process.env.FEE_COLLECTOR ?? wallet.address;

  console.log(`=== Deploying second asset stack: ${label} ===`);
  console.log(`Deployer:      ${wallet.address}`);
  console.log(`maxAgeReserve: ${maxAgeReserve}s`);

  // Same Attestor code, decimals 0 (a raw unit-count reserve).
  const attestorArtifact = await deployer.loadArtifact("Attestor");
  const reserveFeed = await deployer.deploy(attestorArtifact, [0]);
  const reserveAddr = await reserveFeed.getAddress();
  console.log(`${label} ReserveAttestor (dec 0): ${reserveAddr}`);

  // Same OltinTokenV3 code, different reserve feed + maxAge.
  const tokenArtifact = await deployer.loadArtifact("OltinTokenV3");
  const token = await deployer.deploy(tokenArtifact, [
    reserveAddr,
    maxAgeReserve,
    feeCollector,
  ]);
  const tokenAddr = await token.getAddress();
  console.log(`${label} OltinTokenV3:            ${tokenAddr}`);

  // Make the second token actually mintable. OltinTokenV3 grants NO MINTER_ROLE
  // in its constructor, so without this grant the token is inert (mint always
  // reverts with AccessControl) and the "gold is only the example" proof fails.
  // We reuse the SAME OltinTokenV3 code (no factory); the PoR mint guard applies
  // to this asset exactly as it does to OLTIN. For a non-gold asset a gold-priced
  // Exchange makes no sense, so we grant MINTER_ROLE to an explicit minter EOA
  // (default = deployer) rather than deploying a second Exchange.
  const MINTER_ROLE = await token.MINTER_ROLE();
  const minter = process.env.SECOND_MINTER ?? wallet.address;
  const grantMinter = await token.grantRole(MINTER_ROLE, minter);
  await grantMinter.wait();
  console.log(`Granted ${label} OltinTokenV3 MINTER_ROLE -> ${minter}`);

  // Optional: grant POSTER to a dedicated keeper.
  const keeperKey = process.env.KEY_RESERVE_2;
  if (keeperKey) {
    const keeper = new Wallet(keeperKey).address;
    const POSTER_ROLE = await reserveFeed.POSTER_ROLE();
    const tx = await reserveFeed.grantRole(POSTER_ROLE, keeper);
    await tx.wait();
    console.log(`Granted ${label} ReserveAttestor POSTER_ROLE -> ${keeper}`);
  }

  console.log("\n=== Verifying on explorer ===");
  const toVerify: Array<[string, string, any[]]> = [
    [`${label} Attestor`, reserveAddr, [0]],
    [`${label} OltinTokenV3`, tokenAddr, [reserveAddr, maxAgeReserve, feeCollector]],
  ];
  for (const [name, address, constructorArguments] of toVerify) {
    try {
      await hre.run("verify:verify", { address, constructorArguments });
      console.log(`Verified ${name}`);
    } catch (e) {
      console.log(`Verify ${name} failed (may already be verified):`, e);
    }
  }

  console.log("\n=== Done — one code, two assets (no factory) ===");
  console.log(`SECOND_RESERVE_ATTESTOR_ADDRESS=${reserveAddr}`);
  console.log(`SECOND_ASSET_TOKEN_ADDRESS=${tokenAddr}`);
  console.log(`SECOND_ASSET_MINTER=${minter}`);
  console.log("\nNext (prove it mints):");
  console.log(`1. Post a reserve:  ReserveAttestor(${reserveAddr}).postAnswer(<units>)`);
  console.log(
    `2. Mint from the minter (${minter}):  ${label}Token.mint(<to>, <amount <= reserve>)`,
  );
}
