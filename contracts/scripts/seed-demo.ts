/**
 * Demo-bank seed (P1-C, "Ступень 1 — оно живое"). Drives the full money loop
 * on zkSync Sepolia with the REAL contracts and live feeds:
 *
 *   1. Mint UZD to the bank (deployer — the UZD minter in V3.1) and three
 *      demo clients.
 *   2. Fund the clients with a little ETH for gas.
 *   3. PROBE buy (1M UZD) — unit semantics check: the Bought event's oltinOut
 *      must match the off-chain formula against the live feeds (±0.5% for feed
 *      drift between the read and the mined tx).
 *   4. Main bank buy (~3.9B UZD → ~half the 5,000 g reserve capacity, К-3:
 *      public coverage ≈ 200%).
 *   5. Clients buy with their sums.
 *   6. Probe sell: client 1 sells 1 g back (treasury pays UZD).
 *   7. Print the final state (supply, treasury, balances, coverage).
 *
 * One-shot by design: it MINTS new UZD every run, so do not re-run blindly —
 * re-running doubles the clients' sums and buys more OLTIN. That is fine on a
 * testnet as long as it is deliberate.
 *
 * Required env (contracts/.env):
 *   PRIVATE_KEY     deployer = the "bank" (UZD minter, OLTIN admin, pays gas)
 *   DEMO_KEY_1..3   demo client keys (generated once, addresses in docs)
 *   UZD_ADDRESS     UZD token (V3.1)
 *   EXCHANGE_ADDRESS  Exchange (V3.1)
 * Optional env:
 *   ZKSYNC_RPC_URL  default https://sepolia.era.zksync.dev
 *   SLIPPAGE_BPS    min-out tolerance for buys/sells (default 200 = 2%)
 *
 * Exit code: 0 = seeded and verified, 1 = any check failed.
 */

import "dotenv/config";
import { Wallet, Provider, Contract } from "zksync-ethers";
import type { TransactionResponse } from "zksync-ethers/build/types";

const OLTIN = "0x906bcf6c92ed1b30aA453c69eB40aeDbb3d5B3A5";
const XAU_FEED = "0xe0AFc7eD0c6028b8172C2b108624168d235e8BFD";
const UZS_FEED = "0x637347fd661cFFAE9B562aFA394A392214fa24aD";
const RESERVE_FEED = "0x9413F60295dcf7D81fcb69eE256029900B107d1B";

const ERC20_ABI = [
  "function decimals() view returns (uint8)",
  "function balanceOf(address) view returns (uint256)",
  "function totalSupply() view returns (uint256)",
  "function approve(address spender, uint256 amount) returns (bool)",
  "function mint(address to, uint256 amount)",
];

const EXCHANGE_ABI = [
  "function buy(uint256 uzdInWei, uint256 minOltinOut) returns (uint256)",
  "function sell(uint256 oltinInWei, uint256 minUzdOut) returns (uint256)",
  "function treasuryBalance() view returns (uint256)",
];

const FEED_ABI = [
  "function latestRoundData() view returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound)",
];

const GRAMS_PER_OZ_1E8 = 3110347680n; // mirror Exchange.sol
const E8 = 100000000n;
const E18 = 1000000000000000000n;

const BANK_UZD = 4_000_000_000n * E18; // 4 млрд сум — оборотный счёт банка
const CLIENT_UZD = [50_000_000n * E18, 20_000_000n * E18, 10_000_000n * E18];
const CLIENT_GAS = 1_000_000_000_000_000n; // 0.001 ETH each
const PROBE_UZD = 1_000_000n * E18; // пробный buy — проверка единиц
const MAIN_UZD = 3_900_000_000n * E18; // ~половина ёмкости резерва (К-3)
const SELL_GRAMS = E18; // клиент-1 продаёт 1 г

function requireEnv(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`${name} not set in contracts/.env`);
  return v;
}

function fmt(wei: bigint): string {
  return `${(Number(wei) / 1e18).toFixed(4)} (${wei} wei)`;
}

async function mined(tx: TransactionResponse, label: string): Promise<void> {
  console.log(`  tx: ${tx.hash}`);
  const receipt = await tx.wait();
  if (!receipt || receipt.status !== 1) throw new Error(`${label} failed or not mined`);
}

async function main(): Promise<number> {
  const zkRpc = process.env.ZKSYNC_RPC_URL ?? "https://sepolia.era.zksync.dev";
  const slippageBps = BigInt(process.env.SLIPPAGE_BPS ?? "200"); // 2%
  const zk = new Provider(zkRpc);
  const bank = new Wallet(requireEnv("PRIVATE_KEY"), zk);
  const clients = [1, 2, 3].map((i) => new Wallet(requireEnv(`DEMO_KEY_${i}`), zk));
  const UZD = requireEnv("UZD_ADDRESS");
  const EXCHANGE = requireEnv("EXCHANGE_ADDRESS");

  const uzd = new Contract(UZD, ERC20_ABI, zk);
  const oltin = new Contract(OLTIN, ERC20_ABI, zk);
  const exchange = new Contract(EXCHANGE, EXCHANGE_ABI, zk);
  const xauFeed = new Contract(XAU_FEED, FEED_ABI, zk);
  const uzsFeed = new Contract(UZS_FEED, FEED_ABI, zk);
  const reserveFeed = new Contract(RESERVE_FEED, FEED_ABI, zk);

  async function livePrices(): Promise<{ xau: bigint; uzs: bigint; reserve: bigint }> {
    const [, xau] = await xauFeed.latestRoundData();
    const [, uzs] = await uzsFeed.latestRoundData();
    const [, reserve] = await reserveFeed.latestRoundData();
    return { xau: BigInt(xau), uzs: BigInt(uzs), reserve: BigInt(reserve) };
  }

  // Mirrors Exchange.sol buy: oltinOut = uzdIn * uzsAns * GRAMS / (1e8 * xauAns)
  function expectedBuy(uzdIn: bigint, xau: bigint, uzs: bigint): bigint {
    return (uzdIn * uzs * GRAMS_PER_OZ_1E8) / (E8 * xau);
  }
  // Mirrors Exchange.sol sell: uzdOut = oltinIn * xauAns * 1e8 / (GRAMS * uzsAns)
  function expectedSell(oltinIn: bigint, xau: bigint, uzs: bigint): bigint {
    return (oltinIn * xau * E8) / (GRAMS_PER_OZ_1E8 * uzs);
  }
  function minOut(expected: bigint): bigint {
    return (expected * (10000n - slippageBps)) / 10000n;
  }

  console.log("=== P1-C demo-bank seed ===");
  console.log(`bank (deployer): ${bank.address}`);
  clients.forEach((c, i) => console.log(`client ${i + 1}:      ${c.address}`));

  const before = {
    supply: await oltin.totalSupply(),
    treasury: await exchange.treasuryBalance(),
    bankUzd: await uzd.balanceOf(bank.address),
  };
  console.log(`BEFORE: supply=${before.supply} treasury=${before.treasury} bankUzd=${before.bankUzd}`);

  // 1. Mint UZD (bank + clients).
  console.log("\n[1] Mint UZD (deployer is the UZD minter in V3.1)");
  const uzdAsBank = uzd.connect(bank) as Contract;
  await mined(await uzdAsBank.mint(bank.address, BANK_UZD), "mint bank UZD");
  for (const [i, c] of clients.entries()) {
    await mined(await uzdAsBank.mint(c.address, CLIENT_UZD[i]), `mint client ${i + 1} UZD`);
  }

  // 2. Fund clients with gas.
  console.log("\n[2] Fund clients with ETH");
  for (const [i, c] of clients.entries()) {
    await mined(await bank.transfer({ to: c.address, amount: CLIENT_GAS }), `fund client ${i + 1}`);
  }

  // 3. PROBE buy — unit semantics check.
  console.log("\n[3] Probe buy 1M UZD (unit check)");
  let prices = await livePrices();
  const probeExpected = expectedBuy(PROBE_UZD, prices.xau, prices.uzs);
  const exchangeAsBank = exchange.connect(bank) as Contract;
  await mined(await uzdAsBank.approve(EXCHANGE, PROBE_UZD), "approve probe");
  const probeTx = await exchangeAsBank.buy(PROBE_UZD, minOut(probeExpected));
  console.log(`  tx: ${probeTx.hash}`);
  const probeReceipt = await probeTx.wait();
  const boughtEvent = probeReceipt?.logs
    .map((l: { topics: string[]; data: string }) => {
      try {
        return exchange.interface.parseLog(l);
      } catch {
        return null;
      }
    })
    .find((e: { name: string } | null) => e?.name === "Bought");
  if (!boughtEvent) throw new Error("Bought event not found in probe receipt");
  const probeOut = BigInt(boughtEvent.args.oltinOutWei);
  const drift =
    probeOut > probeExpected
      ? ((probeOut - probeExpected) * 10000n) / probeExpected
      : ((probeExpected - probeOut) * 10000n) / probeExpected;
  console.log(`  expected≈${fmt(probeExpected)} got=${fmt(probeOut)} drift=${drift}bps`);
  if (drift > 50n) {
    throw new Error(`UNIT CHECK FAILED: drift ${drift}bps > 50bps — feed semantics wrong?`);
  }
  console.log("  ✓ unit check passed (≤50bps drift)");

  // 4. Main bank buy.
  console.log("\n[4] Main bank buy ~3.9B UZD");
  prices = await livePrices();
  const mainExpected = expectedBuy(MAIN_UZD, prices.xau, prices.uzs);
  await mined(await uzdAsBank.approve(EXCHANGE, MAIN_UZD), "approve main");
  await mined(await exchangeAsBank.buy(MAIN_UZD, minOut(mainExpected)), "main buy");

  // 5. Clients buy with all their UZD.
  console.log("\n[5] Clients buy");
  for (const [i, c] of clients.entries()) {
    prices = await livePrices();
    const amount = CLIENT_UZD[i];
    const expected = expectedBuy(amount, prices.xau, prices.uzs);
    const uzdAsClient = uzd.connect(c) as Contract;
    const exchangeAsClient = exchange.connect(c) as Contract;
    await mined(await uzdAsClient.approve(EXCHANGE, amount), `client ${i + 1} approve`);
    await mined(await exchangeAsClient.buy(amount, minOut(expected)), `client ${i + 1} buy`);
    console.log(`  client ${i + 1} OLTIN: ${fmt(await oltin.balanceOf(c.address))}`);
  }

  // 6. Probe sell: client 1 sells 1 g.
  console.log("\n[6] Probe sell: client 1 sells 1 g");
  prices = await livePrices();
  const sellExpected = expectedSell(SELL_GRAMS, prices.xau, prices.uzs);
  const oltinAsC1 = oltin.connect(clients[0]) as Contract;
  const exchangeAsC1 = exchange.connect(clients[0]) as Contract;
  await mined(await oltinAsC1.approve(EXCHANGE, SELL_GRAMS), "client 1 approve sell");
  const uzdBefore = await uzd.balanceOf(clients[0].address);
  await mined(await exchangeAsC1.sell(SELL_GRAMS, minOut(sellExpected)), "client 1 sell");
  const uzdGot = BigInt(await uzd.balanceOf(clients[0].address)) - BigInt(uzdBefore);
  console.log(`  sold 1 g → got ${fmt(uzdGot)} UZD (expected≈${fmt(sellExpected)})`);

  // 7. Final state.
  console.log("\n[7] Final state");
  const supply = BigInt(await oltin.totalSupply());
  const treasury = BigInt(await exchange.treasuryBalance());
  const reserve = (await livePrices()).reserve;
  const coverageBps = supply > 0n ? (reserve * E18 * 10000n) / supply : 0n;
  console.log(`  OLTIN totalSupply:  ${fmt(supply)}`);
  console.log(`  Reserve:            ${reserve} g`);
  console.log(`  Coverage:           ${Number(coverageBps) / 100}%`);
  console.log(`  Exchange treasury:  ${fmt(treasury)} UZD`);
  console.log(`  bank OLTIN:         ${fmt(await oltin.balanceOf(bank.address))}`);
  for (const [i, c] of clients.entries()) {
    console.log(`  client ${i + 1} OLTIN: ${fmt(await oltin.balanceOf(c.address))}`);
  }

  if (supply === 0n) throw new Error("seed failed: totalSupply is still 0");
  if (treasury === 0n) throw new Error("seed failed: treasury is still 0");
  console.log("\n  ✓ Seed complete");
  return 0;
}

main()
  .then((code) => process.exit(code))
  .catch((e: unknown) => {
    console.error(e instanceof Error ? e.message : e);
    process.exit(1);
  });
