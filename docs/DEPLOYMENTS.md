# Deployments — zkSync Era Sepolia (testnet)

> DEMO — testnet only, tokens have no monetary value.
> Deployed 2026-07-18 from `contracts/deploy/deployV3.ts` (PR-1 stack, F16/F8 final).

## OltinChain V3 (Proof-of-Reserve stack)

| Contract | Address |
|---|---|
| ReserveAttestor (dec 0) | `0x9413F60295dcf7D81fcb69eE256029900B107d1B` |
| XauUsdFeed (dec 8) | `0xe0AFc7eD0c6028b8172C2b108624168d235e8BFD` |
| UzsUsdFeed (dec 8) | `0x637347fd661cFFAE9B562aFA394A392214fa24aD` |
| **OltinTokenV3 (OLTIN)** | `0x906bcf6c92ed1b30aA453c69eB40aeDbb3d5B3A5` |
| ~~Exchange (UZD treasury)~~ → **V3.1 ниже** | `0xc367D7761Cc2A1b4D15475017136085E3EF74e0C` (retired) |
| ~~UZD (existing, reused)~~ → **V3.1 ниже** | `0x95b30Be4fdE1C48d7C5dC22C1EBA061219125A32` (retired) |

## V3.1 — money edge re-issued (2026-07-24)

Legacy UZD had totalSupply 0 with all roles on a lost V1/V2-era key
(`0xa0A7…779e`), and `Exchange.uzd` is immutable — so the money edge was
redeployed (spec `.claude/specs/2026-07-24-v31-money-edge-SPEC.md`):

| Contract | Address |
|---|---|
| **UZD (V3.1, deployer = admin/minter)** | `0x51232fd0065bD2ca50551761Acef476E3CDf02aA` |
| **Exchange (V3.1, UZD treasury)** | `0x99D733E64eb60c3B3D5f3DeDe4CC4adC92BCd1c9` |

- Bytecode of both == local artifacts (keccak `0x28fe52…a608d` UZD,
  `0x7b0196…aeb0` Exchange).
- `OLTIN.MINTER_ROLE`: granted to Exchange2 (`0x3e66ee…c41d`), **revoked from
  the legacy Exchange** (`0x0e7ee2…b47b64`) — the sleeper minter is closed.
- Paymaster `sponsoredTarget`: UZD2/Exchange2 = true; legacy UZD/Exchange =
  false (`0xbc4bf6…e1ff4`, `0x18e218…dff85`, `0x7aec43…82cb6`, `0x263fb9…06fcc`).
- RETIRED: legacy UZD `0x95b30Be4…` (supply 0, roles on lost key) and legacy
  Exchange `0xc367D776…` (minter revoked, sponsorship removed). They stay
  on-chain (immutable) but are dead ends.

**Demo clients (P1-C, 2026-07-24):** `0x57cE0560A7373d1B6B4C24804C3941F796362208`,
`0x87A7D8dB6b291e27BF7b8B808786ABdFbE12164B`,
`0x5e6Eb7cF3E600f589A32cC7cBeDCAC14508c66EC` (keys in `contracts/.env`).

**Keeper poster (P1-B, 2026-07-24):** `0xfaFB46cC23705058EE9E1a96f64B0f273B87405e`.

## PR-4a companions (deployed 2026-07-19 from `deploy/deployPaymasterStaking.ts`)

| Contract | Address |
|---|---|
| **OltinStaking (V3-bound)** | `0xD3b6ffd1dE409e1C37BA5B867d6eC3897A721fAa` |

## OltinPaymaster (PR-4a′, `deploy/deployPaymasterFixed.ts`)

| Contract | Address |
|---|---|
| **OltinPaymaster (fixed)** | `0x817ED8bd0C92703785CbCC500440840603DA0Bb4` |

Deployed 2026-07-22, funded 0.01 ETH (recovered from the retired paymaster).
**The rate expires 2026-08-21T17:08:33Z** — after that sponsorship stops until
`setRate` is called. That is after the 10 August deadline, so it will not fire
during the contest window.

Verified by reading the chain, not by trusting the deploy script's output:
- deployed bytecode == locally compiled artifact, keccak
  `0x10cd4d24faef13fb0d4f5522ffadc43b521d01bf27853a66e9c15274bf48ffad` on both sides;
- `oltinToken()` == V3 OLTIN, `owner()` == deployer, `paused()` false;
- rate 18e18 inside bounds [1.8e18, 180e18], caps 5e14 / 5e14 / 5e15;
- allowlist true for OLTIN / UZD / Exchange / staking, false for anything else;
- live `eth_call` probes: `checkSponsorship` returns 258679734705000 for a sample
  transaction and reverts `TargetNotSponsored` / `PerTxCapExceeded` on the
  refusal paths.
- Explorer source verification still pending (`hardhat verify` reports a bytecode
  mismatch it cannot resolve for zksolc builds — the same flakiness noted for the
  V3 stack). The keccak comparison above is what currently establishes that the
  deployed code is the reviewed code; retry `npm run verify` later.

⚠️ NOT yet proven on production: a live gasless transaction end-to-end. OLTIN
has no supply and the price feeds have never been posted, so the smoke test is a
named acceptance item of PR-4d. Until it passes, this paymaster is proven by the
zkSync VM suite, not by prod.

Operating notes:
- The fee is pegged to the gas being sponsored. **A client MUST size
  `minimalAllowance` from `quoteFee(gasLimit, maxFeePerGas)`** — never from a
  formula mirrored off-chain, which drifts on the first `setRate`. **Approve with
  a margin, not the exact quote:** only the fee is ever taken, over-approving
  costs nothing, and an exact match turns any config change between preflight and
  inclusion into a silent hang.
- **Preflight with `checkSponsorship(from, to, gasLimit, maxFeePerGas)`.** It runs
  the same rules as validation and returns the fee, so a refusal arrives as a
  typed error instead of silence.
- **A sponsored transaction cannot be auto-estimated.** `zks_estimateFee` probes
  with the maximum gas limit (~9.3e15 wei of implied ETH), which any meaningful
  per-transaction cap refuses. The client must send an **explicit `gasLimit`**:
  estimate the bare call and add the account-abstraction overhead (~80k gas
  measured; `test-vm/paymaster.e2e.ts` uses +150k).
- A refused transaction is **not reverted — it is never mined**. The client needs
  a timeout and a clear message, or the UI waits forever.
- **The rate expires.** `maxRateAge` is 30 days from the last `setRate`; after
  that sponsorship stops until the rate is refreshed. Record the expiry date here
  at deploy time (a deploy on 2026-07-22..25 expires 2026-08-21..24 — after the
  10 August deadline, so it will not fire during the contest window).
- Deployed caps: 0.0005 ETH per transaction, 0.002 ETH per sender per day,
  0.005 ETH per day in total. All are owner-settable (`setCaps`) — a demo that
  hits a ceiling is a one-transaction fix, not a redeploy.

## Retired / orphan — do not use, do not reference

Full on-chain inventory taken 2026-07-22 by scanning `ContractDeployed` events of
the system `ContractDeployer` for every project key (indexed topic — a paginated
transaction list silently misses deployments). 19 deployments in total.

| Address | What it is | Why it is dead |
|---|---|---|
| `0x77B0afE91F15A9AAb065c5a49b8199D38884dE8F` | OltinPaymaster #1 | **NEVER FUND — drainable.** Its fee came from the user-supplied `minAllowance` while it paid the real gas: anyone could empty it for dust. Swept to the deployer 2026-07-22 (balance confirmed 0 on chain), but `receive()` is open, so any new funding is drainable again. Replaced by `0x817ED8bd…0Bb4`. |
| `0x63e537A3a150d06035151E29904C1640181C8314` | OltinStaking | Immutably bound to the V2 token |
| `0xA7E92168517864359B6Fa9e2247B01e0280A7dAa` | OLTIN V1 (2025-12-26) | Superseded; supply 2985 |
| `0x4A56B78DBFc2E6c914f5413B580e86ee1A474347` | OLTIN V2 | Superseded; supply 3280. The webapp still points here (`contracts.ts`) — PR-4c moves it to V3 |
| `0xBE6419B3113e16BA2b8A4EAcD64bE1899E6cAC73`, `0xeCCaa1d4E6197e8365Dd299c2F52805E025e6391` | OLTIN V3, orphan | Repeat runs of the 2026-07-18 deploy before the PR #6 fix; supply 0, never wired |
| `0x88c4323357BC31984E261137E7BE96c1a7Cb3ed0`, `0xca7b153D177eDbfCd4d8e9Cc4332C287ea431631`, `0x9b9e8D7D3A9546F535E86EC2c26656014d1f9BAa`, `0xAF7F4916a37DD17BF1C8F91B844218d8557122c9`, `0x60Be3d3141801F47138135243C3F51D8AF4329A0`, `0x276ecc0d8Afe1ea19DDbc575a2A3B597289fEF97` | Attestor / feeds, orphan (2 sets) | Same repeat runs; never posted an answer, never referenced |

Contracts cannot be deleted on zkSync — there is no selfdestruct in this code.
"Retired" therefore means: no funds, no references anywhere in the repo, and
listed here so the question "which one is live?" has one answer.

Explorer: `https://sepolia-era.zksync.network/address/<addr>`

## Wiring (verified on-chain)
- OLTIN `reserveFeed` → ReserveAttestor (PoR-gated mint).
- Exchange granted OLTIN `MINTER_ROLE` (sole minter); `xauFeed`/`uzsFeed` wired; `maxAgeXau=3600`, `maxAgeUzs=259200`.
- OLTIN totalSupply = 0 (fresh).
- PR-4a: new `OltinStaking.oltin()` == V3 OLTIN (independent `eth_call` verified).
  The paymaster deployed alongside it was retired in PR-4a′ (see above). Reward pool NOT yet
  funded — V3 OLTIN is mintable only via the Exchange, so the seed
  (deposit UZD → `Exchange.buy` → `npm run fund:rewards`) is a 4d ops step.

## Next (demo readiness)

> ✅ **All three canonical feeds are live since 2026-07-23** (P1-A/P1-E): XAU is
> the PAXG+XAUT median (24/7), RESERVE 5000 g, UZS the CBU rate — all verified
> by reading the chain. `Exchange.buy/sell` no longer reverts on "price stale".
> Feeds still need a scheduled keeper run (cron is P4-A); refresh manually with
> `npm run keeper:all` before any demo.

**Keeper poster key (P1-B, 2026-07-24):** address
`0xfaFB46cC23705058EE9E1a96f64B0f273B87405e` holds `POSTER_ROLE` on all three
canonical Attestors (grant txs `0xa1cd7c2aff488e6267d89dcbe71b2782373b3bacb20e311d506450529d246023` XAU,
`0x94fe845c4c68a4f1384cbee2ac02708ef214293f23e8271ffdfb8e138e39bc66` UZS,
`0x16b8db6d0add994ccf6d3a5dca64b28510238812ee815223eb6a63fb41aa377c` RESERVE)
and 0.03 ETH. The private key lives only on 7demo
(`/root/oltinpay-keeper/poster.key`, mode 600, never transmitted); the
deployer key keeps its roles as the manual fallback path.

1. ~~Post initial reserve~~ ✅ done (ReserveAttestor roundId ≥ 1, 5000 g).
2. Seed Exchange treasury with UZD for sell demos (P1-C, open).
3. ~~Start keepers~~ ✅ manual runs work; cron on 7demo = P4-A (open).
4. Explorer verify pending (zksolc-verify flaky) — retry `hardhat verify`.
