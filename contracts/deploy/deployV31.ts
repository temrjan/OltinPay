/**
 * V3.1 — re-issue of the money edge (spec: .claude/specs/2026-07-24-v31-money-edge-SPEC.md).
 *
 * The legacy UZD (0x95b30Be4…) has totalSupply 0 and all roles held by a lost
 * V1/V2-era key; Exchange.uzd is immutable. This script deploys a fresh UZD
 * (deployer = admin/minter) and a fresh Exchange wired to the EXISTING OLTIN
 * and price feeds, then performs the wiring in one series:
 *
 *   1. OLTIN.grantRole(MINTER_ROLE, new Exchange)
 *   2. OLTIN.revokeRole(MINTER_ROLE, OLD Exchange) — the sleeper minter must
 *      not survive a future resurfacing of the V1/V2 key
 *   3. Paymaster.setSponsoredTarget: new UZD/Exchange = true, old = false
 *
 * Every step is verified by READING the chain (hasRole / sponsoredTarget),
 * and the deployed bytecode of both new contracts is keccak-compared against
 * the locally compiled artifacts (PR-4a′ practice).
 *
 * Untouched by design: OLTIN, feeds, reserve, staking, maxAge* values (the new
 * Exchange gets the SAME 3600 / 259200 as the old one).
 *
 * Run (Node 20 — zksolc breaks on newer):
 *   npx hardhat deploy-zksync --network zkSyncSepolia --script deployV31.ts
 *
 * Required env (contracts/.env):
 *   PRIVATE_KEY   deployer/admin (0x-prefixed) — OLTIN admin, paymaster owner
 */

import { Wallet, Provider, Contract } from "zksync-ethers";
import { Deployer } from "@matterlabs/hardhat-zksync";
import { HardhatRuntimeEnvironment } from "hardhat/types";
import { keccak256, getBytes } from "ethers";
import * as dotenv from "dotenv";

dotenv.config();

const RPC_URL = "https://sepolia.era.zksync.dev";

// Existing, UNTOUCHED stack (docs/DEPLOYMENTS.md)
const OLTIN_V3 = "0x906bcf6c92ed1b30aA453c69eB40aeDbb3d5B3A5";
const XAU_FEED = "0xe0AFc7eD0c6028b8172C2b108624168d235e8BFD";
const UZS_FEED = "0x637347fd661cFFAE9B562aFA394A392214fa24aD";
const PAYMASTER = "0x817ED8bd0C92703785CbCC500440840603DA0Bb4";

// Legacy, being retired
const OLD_UZD = "0x95b30Be4fdE1C48d7C5dC22C1EBA061219125A32";
const OLD_EXCHANGE = "0xc367D7761Cc2A1b4D15475017136085E3EF74e0C";

const ACCESS_ABI = [
  "function MINTER_ROLE() view returns (bytes32)",
  "function grantRole(bytes32 role, address account)",
  "function revokeRole(bytes32 role, address account)",
  "function hasRole(bytes32 role, address account) view returns (bool)",
];

const PAYMASTER_ABI = [
  "function setSponsoredTarget(address target, bool allowed)",
  "function sponsoredTarget(address) view returns (bool)",
  "function owner() view returns (address)",
];

function check(condition: boolean, label: string): void {
  if (!condition) throw new Error(`VERIFY FAILED: ${label}`);
  console.log(`  ✓ ${label}`);
}

export default async function (hre: HardhatRuntimeEnvironment) {
  const pk = process.env.PRIVATE_KEY;
  if (!pk) throw new Error("Set PRIVATE_KEY in contracts/.env (deployer/admin)");

  // Identical staleness windows to the legacy Exchange.
  const maxAgeXau = Number(process.env.MAX_AGE_XAU ?? "3600");
  const maxAgeUzs = Number(process.env.MAX_AGE_UZS ?? "259200");

  const provider = new Provider(RPC_URL);
  const wallet = new Wallet(pk, provider);
  const deployer = new Deployer(hre, wallet);

  console.log("=== V3.1: re-issuing the money edge (UZD + Exchange) ===");
  console.log(`Deployer:  ${wallet.address}`);
  console.log(`OLTIN V3:  ${OLTIN_V3} (untouched)`);
  console.log(`Feeds:     XAU ${XAU_FEED}\n           UZS ${UZS_FEED} (untouched)`);
  console.log(`Windows:   maxAgeXau=${maxAgeXau}s maxAgeUzs=${maxAgeUzs}s (same as legacy)`);

  // --- Deploy UZD2 (same UZD.sol, deployer gets all roles) ---
  const uzdArtifact = await deployer.loadArtifact("UZD");
  const uzd = await deployer.deploy(uzdArtifact, []);
  const uzdAddr = await uzd.getAddress();
  console.log(`\nUZD2:      ${uzdAddr}`);

  // --- Deploy Exchange2(OLTIN, UZD2, feeds, same windows) ---
  const exchangeArtifact = await deployer.loadArtifact("Exchange");
  const exchange = await deployer.deploy(exchangeArtifact, [
    OLTIN_V3,
    uzdAddr,
    XAU_FEED,
    UZS_FEED,
    maxAgeXau,
    maxAgeUzs,
  ]);
  const exchangeAddr = await exchange.getAddress();
  console.log(`Exchange2: ${exchangeAddr}`);

  // --- Bytecode keccak vs local artifacts ---
  console.log("\n=== Bytecode verification (keccak vs local artifacts) ===");
  for (const [name, addr, artifact] of [
    ["UZD2", uzdAddr, uzdArtifact],
    ["Exchange2", exchangeAddr, exchangeArtifact],
  ] as const) {
    const onchain = keccak256(getBytes(await provider.getCode(addr)));
    const local = keccak256(getBytes(artifact.deployedBytecode));
    console.log(`  ${name}: onchain ${onchain}`);
    console.log(`  ${name}: local   ${local}`);
    check(onchain === local, `${name} bytecode == local artifact`);
  }

  // --- Wiring (one series) ---
  console.log("\n=== Wiring ===");
  const oltin = new Contract(OLTIN_V3, ACCESS_ABI, wallet);
  const minter = await oltin.MINTER_ROLE();

  const grant = await oltin.grantRole(minter, exchangeAddr);
  await grant.wait();
  console.log(`  grantRole(MINTER, Exchange2) tx: ${grant.hash}`);
  check(await oltin.hasRole(minter, exchangeAddr), "MINTER_ROLE: Exchange2 = true");

  const revoke = await oltin.revokeRole(minter, OLD_EXCHANGE);
  await revoke.wait();
  console.log(`  revokeRole(MINTER, OLD Exchange) tx: ${revoke.hash}`);
  check(!(await oltin.hasRole(minter, OLD_EXCHANGE)), "MINTER_ROLE: OLD Exchange = false");

  const paymaster = new Contract(PAYMASTER, PAYMASTER_ABI, wallet);
  check(
    (await paymaster.owner()).toLowerCase() === wallet.address.toLowerCase(),
    "paymaster owner == deployer",
  );
  for (const [target, allowed, label] of [
    [uzdAddr, true, "sponsoredTarget(UZD2) = true"],
    [exchangeAddr, true, "sponsoredTarget(Exchange2) = true"],
    [OLD_UZD, false, "sponsoredTarget(OLD UZD) = false"],
    [OLD_EXCHANGE, false, "sponsoredTarget(OLD Exchange) = false"],
  ] as const) {
    const tx = await paymaster.setSponsoredTarget(target, allowed);
    await tx.wait();
    console.log(`  setSponsoredTarget tx: ${tx.hash}`);
    check((await paymaster.sponsoredTarget(target)) === allowed, label);
  }

  console.log("\n=== V3.1 complete — record these addresses ===");
  console.log(`UZD_ADDRESS=${uzdAddr}`);
  console.log(`EXCHANGE_ADDRESS=${exchangeAddr}`);
  console.log("Next: migrate pointers (see spec §3 checklist), then npm run seed:demo");
}
