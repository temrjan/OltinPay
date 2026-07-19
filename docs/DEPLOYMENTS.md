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
| **OltinPaymaster** (approvalBased, fee in OLTIN; funded 0.01 ETH) | `0x77B0afE91F15A9AAb065c5a49b8199D38884dE8F` |
| **OltinStaking (V3-bound)** | `0xD3b6ffd1dE409e1C37BA5B867d6eC3897A721fAa` |
| ~~OltinStaking (V2-bound)~~ retired — immutably bound to the V2 token | `0x63e537A3a150d06035151E29904C1640181C8314` |

Explorer: `https://sepolia-era.zksync.network/address/<addr>`

## Wiring (verified on-chain)
- OLTIN `reserveFeed` → ReserveAttestor (PoR-gated mint).
- Exchange granted OLTIN `MINTER_ROLE` (sole minter); `xauFeed`/`uzsFeed` wired; `maxAgeXau=3600`, `maxAgeUzs=259200`.
- OLTIN totalSupply = 0 (fresh).
- PR-4a: new `OltinStaking.oltin()` == V3 OLTIN (independent `eth_call` verified);
  paymaster ETH balance == 0.01 (`eth_getBalance` verified). Reward pool NOT yet
  funded — V3 OLTIN is mintable only via the Exchange, so the seed
  (deposit UZD → `Exchange.buy` → `npm run fund:rewards`) is a 4d ops step.

## Next (demo readiness)
1. Post initial reserve: `ReserveAttestor.postAnswer(<grams>)` (deployer is POSTER).
2. Seed Exchange treasury with UZD for sell demos.
3. Start keepers: `npm run keeper:xau` / `npm run keeper:uzs`.
4. Explorer verify pending (zksolc-verify flaky) — retry `hardhat verify`.
