# OltinPay — Implementation Plan

> 6-week roadmap to a pitch-ready DEMO.

---

## Week 1 — Security & cleanup (DONE 2026-04-21)

- ✅ Rotate admin/minter keys on Sepolia (8 transactions, all 4 roles transferred from compromised `0xbf334c…b1c8` to new `0xa0A78aA9…779e`)
- ✅ Scrub leaked `BLOCKCHAIN_CONFIG.md` and `BLOCKCHAIN_CLIENT_BACKUP.py` from git history (`git filter-repo` + `--force` push)
- ✅ Remove `oltinchain-*` exchange subsystem (5 services, 36 011 LOC)
- ✅ Move contracts to top-level `contracts/`
- ✅ Update `docker-compose.yml` (drop dead services, rename DB to `oltinpay`)
- ✅ Create `README.md`

---

## Week 2 — New smart contracts (DONE 2026-04-21)

- [x] `contracts/contracts/UZD.sol` — ERC20 + AccessControl, mint/burn by admin, 18 decimals
- [x] `contracts/contracts/OltinStaking.sol` — ports DB logic with one important change: **per-deposit lock** (each `stake()` creates its own Lot with its own 7-day lock; new deposits do NOT extend old locks)
  - `APY = 7%` (700 bps)
  - `LOCK_PERIOD = 7 days` per lot
  - Functions: `stake`, `unstake`, `claim`, `compound`, `pendingReward`, `getStakeInfo`
  - Emits `Staked`, `Unstaked`, `Claimed`, `Compounded`, `RewardPoolFunded`
  - Reward source: `rewardPool` funded by FUNDER_ROLE, **reward in OLTIN** (same currency as principal, matches Python service)
- [x] hardhat tests: 32/32 passing
- [x] Deployed on Sepolia:
  - UZD: `0x95b30Be4fdE1C48d7C5dC22C1EBA061219125A32`
  - OltinStaking: `0x63e537A3a150d06035151E29904C1640181C8314`
- [ ] Verify on explorer (standard hardhat verify fails; needs zkSync plugin tuning — carried forward)
- [x] Updated `docs/ARCHITECTURE.md` and `README.md`

---

## Week 3 — Wallet UX (client-side, non-custodial) (DONE 2026-04-21)

- [x] Installed in `oltinpay-webapp`: `@scure/bip39`, `@noble/hashes`, `viem` (~60KB gzipped)
- [x] `lib/wallet.ts` — BIP39 + scrypt + AES-GCM + Telegram Cloud Storage (with localStorage fallback for dev)
- [x] `lib/contracts.ts` + `lib/chain.ts` — viem clients for zkSync Sepolia, helpers for balanceOf/transfer/stake/unstake/claim
- [x] `stores/wallet.ts` — in-memory unlocked HDAccount + 15-min idle auto-lock
- [x] `app/onboarding/page.tsx` — 4-step wizard: Welcome → Show seed → Verify (3 random words) → Set PIN
- [x] `app/onboarding/restore/page.tsx` — restore from seed + new PIN
- [x] `components/PinUnlock.tsx` — PIN entry screen for locked sessions
- [x] `components/DemoBadge.tsx` — yellow DEMO pill (used in onboarding)
- [x] `WalletGate` in `providers.tsx` — checks Cloud Storage, redirects to /onboarding, shows PinUnlock if locked
- [x] Localization keys uz/ru/en (~25 keys × 3)
- [x] `npx tsc --noEmit` clean
- [ ] DEMO badge in existing wallet/staking/exchange page headers (deferred to week 4)
- [ ] Manual test in Telegram Mobile — needs deployed staging (deferred)
- [ ] Backend alembic `add_wallet_address_to_users` — moved to week 4 (Python work)

---

## Week 4 — Backend on-chain integration

**Goal:** all balances and transfers flow through the blockchain. DB only caches.

- [ ] `src/infrastructure/rpc.py` — JSON-RPC helper using existing httpx (no `web3.py` dep needed)
- [ ] Rewrite `src/balances/service.py` — `balanceOf(wallet_address, token)` for OLTIN + UZD
- [ ] Rewrite `src/transfers/service.py` — index `Transfer` events; user-side signing in webapp
- [ ] Drop `src/exchange/` module (orderbook gone)
- [ ] Add `src/swap/` — simple fixed-rate swap endpoint using a smart contract (or admin-signed)
- [ ] All Python written **with `/python` skill loaded**, reviewed **with `/python-review`**

---

## Week 5 — Staking on-chain + Welcome bonus (DONE 2026-04-22)

**Goal:** staking is fully on-chain, observable in explorer. Every new user gets 1000 UZD.

- [x] Rewrite `src/staking/service.py` — read-only wrapper around `OltinStaking.getStakeInfo`; write actions (stake/unstake/claim/compound) moved to viem client-side. Legacy `models.py` + DB schema dropped.
- [x] `src/welcome/` module — `POST /api/v1/welcome/claim` admin-signs `UZD.mint(user, 1000e18)`, `GET /api/v1/welcome/status` reports state. Reserve-then-broadcast pattern (INSERT + flush with unique(user_id) before mint) prevents double-mint on concurrent claims.
- [x] `src/infrastructure/admin_tx.py` — EIP-1559 signing via eth-account, dynamic gas (`eth_estimateGas` + 20% headroom, `eth_maxPriorityFeePerGas` + `maxFee = base*2 + priority`).
- [x] alembic 003 — `welcome_claims` ledger with unique(user_id), FK CASCADE.
- [x] 9 new tests, 70 total passing. ruff + mypy clean. `/python-review` findings fixed before commit.
- [x] Commit `a352b69` on `main`.
- [ ] Delete `staking-rewards-cron.sh` + stale `contracts/scripts/deploy-uzd-staking.ts` — separate `chore:` commit
- [ ] Frontend `app/staking/page.tsx` — on-chain pending reward via viem (deferred to week 6)
- [ ] Frontend welcome-claim prompt on first login (deferred to week 6)

---

## Week 6 — Polish & pitch pack

- [ ] Run all 6 demo scenarios end-to-end on Sepolia, screenshot every step + explorer link:
  1. Register → wallet created on-chain
  2. Claim welcome bonus → mint 1000 UZD
  3. Buy OLTIN with UZD (swap)
  4. Send OLTIN to another user
  5. Stake OLTIN → earn UZD
  6. Claim staking rewards + unstake
- [ ] Demo video (Loom, 3–5 min)
- [ ] Pitch deck (10 slides) — see `docs/PITCH.md` (TBD)
- [ ] Partner onboarding checklist (what they need: licence, reserve, banking, KYC)
- [ ] Pricing sheet (Starter / Growth / Enterprise tiers)
- [ ] Live staging URL deployed via Docker Compose

---

## Out of scope for v2 DEMO

- Mainnet deployment (after partner signs)
- Real fiat ↔ UZD pegging mechanism (partner's bank)
- Multi-language docs translation (post-MVP)
- Hardware wallet support
- Multi-chain (only zkSync Era)
- AMM / DEX (only fixed-rate swap)
- DAO governance
