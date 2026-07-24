/**
 * Gasless smoke (P1-D) — a LIVE sponsored transaction end-to-end on zkSync
 * Sepolia. Client 1 sends 1 g OLTIN to client 2 WITHOUT spending ETH on gas:
 * the paymaster pays gas, the client pays the fee in OLTIN.
 *
 * The client contract (docs/DEPLOYMENTS.md operating notes, test-locked in 4a′):
 *   1. feeData from the provider -> maxFeePerGas.
 *   2. EXPLICIT gasLimit = bare estimate + AA overhead (150k, measured in
 *      test-vm/paymaster.e2e.ts) — auto-estimation is FORBIDDEN
 *      (zks_estimateFee probes with the max limit and hits the per-tx cap).
 *   3. minimalAllowance = quoteFee(gasLimit, maxFeePerGas) x MARGIN (1.2) —
 *      never an exact quote (a config drift between preflight and inclusion
 *      turns an exact match into a silent hang).
 *   4. Preflight checkSponsorship(from, to, gasLimit, maxFeePerGas) — a
 *      refusal arrives as a typed error, not silence.
 *   5. approve(paymaster, allowance) — the client's only ETH spend.
 *   6. Send with paymasterParams + explicit gasLimit.
 *   7. MINING TIMEOUT (default 120s): a refused sponsored tx is NOT reverted,
 *      it is never mined — time out and say so.
 *   8. Verify by reading: OLTIN moved, fee collected in OLTIN, client ETH
 *      spent on the approve only, paymaster ETH down by the gas.
 *
 * Run:  npm run smoke:gasless
 * Env (contracts/.env): DEMO_KEY_1 (sender, holds OLTIN + ~0.001 ETH),
 *   DEMO_KEY_2 (recipient address is derived from it).
 * Optional: ZKSYNC_RPC_URL, SMOKE_TIMEOUT_MS (default 120000).
 *
 * Exit codes: 0 = smoke green, 1 = any step failed.
 */

import "dotenv/config";
import { Wallet, Provider, Contract, utils } from "zksync-ethers";

const OLTIN = "0x906bcf6c92ed1b30aA453c69eB40aeDbb3d5B3A5";
const PAYMASTER = "0x817ED8bd0C92703785CbCC500440840603DA0Bb4";
const AA_OVERHEAD = 150_000n; // measured in test-vm/paymaster.e2e.ts
const MARGIN_BPS = 12_000n; // approve at 1.2x the quote, never exact
const ONE_GRAM = 1_000_000_000_000_000_000n;

const ERC20_ABI = [
  "function transfer(address to, uint256 amount) returns (bool)",
  "function approve(address spender, uint256 amount) returns (bool)",
  "function balanceOf(address) view returns (uint256)",
];

const PAYMASTER_ABI = [
  "function quoteFee(uint256 gasLimit, uint256 maxFeePerGas) view returns (uint256)",
  "function checkSponsorship(address from, address to, uint256 gasLimit, uint256 maxFeePerGas) view returns (uint256)",
  "function totalFeesCollected() view returns (uint256)",
  "error TargetNotSponsored(address target)",
];

function requireEnv(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`${name} not set in contracts/.env`);
  return v;
}

/** Pull revert data out of an ethers/zksync error without `any`. */
function revertData(e: unknown): string {
  if (typeof e !== "object" || e === null) return "";
  const err = e as Record<string, unknown>;
  if (typeof err.data === "string") return err.data;
  for (const key of ["error", "info"] as const) {
    const nested = err[key];
    if (typeof nested === "object" && nested !== null) {
      const d = (nested as Record<string, unknown>).data;
      if (typeof d === "string") return d;
      const deep = (nested as Record<string, unknown>).error;
      if (typeof deep === "object" && deep !== null) {
        const dd = (deep as Record<string, unknown>).data;
        if (typeof dd === "string") return dd;
      }
    }
  }
  return "";
}

/** Approve margin: ceil(quote * marginBps / 10000) — never rounds down. */
export function allowanceWithMargin(quote: bigint, marginBps: bigint): bigint {
  const num = quote * marginBps;
  return (num + 9999n) / 10000n;
}

export type MiningOutcome =
  | { status: "mined" }
  | { status: "reverted" }
  | { status: "silentlyRefused" };

/** A sponsored tx has three outcomes, not two: no receipt at all is a refusal. */
export function classifyMining(
  receiptStatus: number | null,
  timedOut: boolean,
): MiningOutcome {
  if (receiptStatus === 1) return { status: "mined" };
  if (receiptStatus === 0) return { status: "reverted" };
  if (timedOut) return { status: "silentlyRefused" };
  throw new Error("no receipt and no timeout — invalid wait state");
}

async function main(): Promise<number> {
  const zkRpc = process.env.ZKSYNC_RPC_URL ?? "https://sepolia.era.zksync.dev";
  const timeoutMs = Number(process.env.SMOKE_TIMEOUT_MS ?? "120000");
  const zk = new Provider(zkRpc);
  const client = new Wallet(requireEnv("DEMO_KEY_1"), zk);
  const recipient = new Wallet(requireEnv("DEMO_KEY_2"), zk).address;

  const oltin = new Contract(OLTIN, ERC20_ABI, zk);
  const paymaster = new Contract(PAYMASTER, PAYMASTER_ABI, zk);

  console.log("=== P1-D gasless smoke (LIVE) ===");
  console.log(`client:    ${client.address}`);
  console.log(`recipient: ${recipient}`);
  console.log(`paymaster: ${PAYMASTER}`);

  // 1–2. feeData + explicit gasLimit (bare estimate + AA overhead).
  const data = oltin.interface.encodeFunctionData("transfer", [recipient, ONE_GRAM]);
  const bare = await zk.estimateGas({ from: client.address, to: OLTIN, data });
  const feeData = await zk.getFeeData();
  const gasLimit = bare + AA_OVERHEAD;
  const maxFeePerGas = feeData.gasPrice ?? 45_250_000n;
  console.log(`gas: bare=${bare} limit=${gasLimit} maxFeePerGas=${maxFeePerGas}`);

  // 3. Allowance from the LIVE quote x margin.
  const quoted: bigint = await paymaster.quoteFee(gasLimit, maxFeePerGas);
  const allowance = allowanceWithMargin(quoted, MARGIN_BPS);
  console.log(`fee: quoted=${quoted} allowance(+20%)=${allowance} OLTIN wei`);

  // 4. Preflight — typed refusal, not silence.
  const preflightFee: bigint = await paymaster.checkSponsorship(
    client.address, OLTIN, gasLimit, maxFeePerGas,
  );
  console.log(`preflight checkSponsorship: fee=${preflightFee} ✓`);

  // 4b. Negative preflight (free eth_call): unsponsored target must revert typed.
  try {
    await paymaster.checkSponsorship(
      client.address, client.address, gasLimit, maxFeePerGas,
    );
    throw new Error("negative preflight did NOT revert — checkSponsorship broken");
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    const selector =
      paymaster.interface.getError("TargetNotSponsored")?.selector ?? "0xd12eb37e";
    const data = revertData(e);
    if (!msg.includes("TargetNotSponsored") && !data.startsWith(selector)) throw e;
    console.log(`negative preflight: TargetNotSponsored ✓ (typed, selector ${selector})`);
  }

  // 5. Approve — the client's only ETH spend.
  const oltinAsClient = oltin.connect(client) as Contract;
  const approveTx = await oltinAsClient.approve(PAYMASTER, allowance);
  console.log(`approve tx: ${approveTx.hash}`);
  await approveTx.wait();

  // Deltas — BEFORE the sponsored transaction.
  const clientEthBefore = await zk.getBalance(client.address);
  const pmEthBefore = await zk.getBalance(PAYMASTER);
  const clientOltinBefore = BigInt(await oltin.balanceOf(client.address));
  const recipientOltinBefore = BigInt(await oltin.balanceOf(recipient));
  const feesBefore: bigint = await paymaster.totalFeesCollected();

  // 6. Send the sponsored transaction.
  const paymasterParams = utils.getPaymasterParams(PAYMASTER, {
    type: "ApprovalBased",
    token: OLTIN,
    minimalAllowance: allowance,
    innerInput: new Uint8Array(),
  });
  const t0 = Date.now();
  const tx = await client.sendTransaction({
    to: OLTIN,
    data,
    gasLimit,
    maxFeePerGas,
    maxPriorityFeePerGas: 0n,
    customData: {
      gasPerPubdata: utils.DEFAULT_GAS_PER_PUBDATA_LIMIT,
      paymasterParams,
    },
  });
  console.log(`sponsored tx: ${tx.hash}`);

  // 7. Mining timeout — no receipt at all IS the refusal signal.
  let receiptStatus: number | null = null;
  let timedOut = false;
  const receipt = await Promise.race([
    tx.wait().catch(() => null),
    new Promise<null>((resolve) => setTimeout(() => resolve(null), timeoutMs)),
  ]);
  if (receipt === null) {
    timedOut = true;
  } else {
    receiptStatus = receipt.status;
  }
  const outcome = classifyMining(receiptStatus, timedOut);
  if (outcome.status === "silentlyRefused") {
    console.error(`FAIL: not mined within ${timeoutMs}ms — silently refused by the paymaster`);
    return 1;
  }
  if (outcome.status === "reverted") {
    console.error("FAIL: sponsored tx reverted on chain");
    return 1;
  }
  const minedMs = Date.now() - t0;
  console.log(`mined in ${minedMs}ms ✓`);

  // 8. Verify by reading.
  const clientEthAfter = await zk.getBalance(client.address);
  const pmEthAfter = await zk.getBalance(PAYMASTER);
  const clientOltinAfter = BigInt(await oltin.balanceOf(client.address));
  const recipientOltinAfter = BigInt(await oltin.balanceOf(recipient));
  const feesAfter: bigint = await paymaster.totalFeesCollected();

  console.log("\n=== Balance deltas ===");
  console.log(`client OLTIN:    ${clientOltinBefore} -> ${clientOltinAfter} (delta ${clientOltinAfter - clientOltinBefore})`);
  console.log(`recipient OLTIN: ${recipientOltinBefore} -> ${recipientOltinAfter} (delta ${recipientOltinAfter - recipientOltinBefore})`);
  console.log(`fee collected:   ${feesBefore} -> ${feesAfter} (delta ${feesAfter - feesBefore} OLTIN wei)`);
  console.log(`client ETH:      ${clientEthBefore} -> ${clientEthAfter} (delta ${clientEthAfter - clientEthBefore})`);
  console.log(`paymaster ETH:   ${pmEthBefore} -> ${pmEthAfter} (delta ${pmEthAfter - pmEthBefore})`);

  const checks: [boolean, string][] = [
    [recipientOltinAfter - recipientOltinBefore === ONE_GRAM, "recipient got exactly 1 g"],
    [clientOltinBefore - clientOltinAfter === ONE_GRAM + (feesAfter - feesBefore), "client paid 1 g + fee"],
    [feesAfter > feesBefore, "fee collected in OLTIN"],
    [clientEthBefore === clientEthAfter, "client spent NO ETH on the sponsored tx"],
    [pmEthBefore > pmEthAfter, "paymaster really paid gas"],
  ];
  let ok = true;
  for (const [cond, label] of checks) {
    console.log(`  ${cond ? "✓" : "✗"} ${label}`);
    if (!cond) ok = false;
  }
  console.log(ok ? "\n  ✓ GASLESS SMOKE GREEN" : "\n  ✗ SMOKE FAILED");
  return ok ? 0 : 1;
}

if (require.main === module) {
  main()
    .then((code) => process.exit(code))
    .catch((e: unknown) => {
      console.error(e instanceof Error ? e.message : e);
      process.exit(1);
    });
}
