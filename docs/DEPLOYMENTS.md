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
| **Exchange (UZD treasury)** | `0xc367D7761Cc2A1b4D15475017136085E3EF74e0C` |
| UZD (existing, reused) | `0x95b30Be4fdE1C48d7C5dC22C1EBA061219125A32` |

## PR-4a companions (deployed 2026-07-19 from `deploy/deployPaymasterStaking.ts`)

| Contract | Address |
|---|---|
| **OltinStaking (V3-bound)** | `0xD3b6ffd1dE409e1C37BA5B867d6eC3897A721fAa` |

## OltinPaymaster (PR-4a′, `deploy/deployPaymasterFixed.ts`)

| Contract | Address |
|---|---|
| **OltinPaymaster (fixed)** | _pending deploy — filled in after the Gate-2 review_ |

Operating notes once deployed:
- The fee is pegged to the gas being sponsored. **A client MUST size
  `minimalAllowance` from `quoteFee(gasLimit, maxFeePerGas)`** — never from a
  formula mirrored off-chain, which drifts on the first `setRate`.
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
| `0x77B0afE91F15A9AAb065c5a49b8199D38884dE8F` | OltinPaymaster #1 | **NEVER FUND — drainable.** Its fee came from the user-supplied `minAllowance` while it paid the real gas: anyone could empty it for dust. Its ETH was swept, but `receive()` is open, so any new funding is drainable again. Replaced by the PR-4a′ paymaster. |
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

> 🔴 **No feed has ever published a value** (checked 2026-07-22: all nine Attestor
> instances report `roundId = 0`, `updatedAt = 0`). Until the three canonical
> feeds are posted, `Exchange.buy/sell` reverts with "price stale" and V3 cannot
> mint at all — the on-chain demo does not run, paymaster or no paymaster.

1. Post initial reserve: `ReserveAttestor.postAnswer(<grams>)` (deployer is POSTER).
2. Seed Exchange treasury with UZD for sell demos.
3. Start keepers: `npm run keeper:xau` / `npm run keeper:uzs`.
4. Explorer verify pending (zksolc-verify flaky) — retry `hardhat verify`.
