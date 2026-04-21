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

## Week 2 — New smart contracts

**Goal:** `UZD` and `OltinStaking` deployed on Sepolia, tested.

- [ ] `contracts/contracts/UZD.sol` — ERC20 + AccessControl, mint/burn by admin, 18 decimals
- [ ] `contracts/contracts/OltinStaking.sol` — port the existing DB logic from `oltinpay/oltinpay-api/src/staking/service.py`:
  - `APY = 7%`
  - `LOCK_DAYS = 7`
  - Functions: `deposit(uint256 amount)`, `claim()`, `withdraw()`, `getStakeInfo(address)`
  - Emits `Staked`, `Claimed`, `Withdrawn` events
  - Reward source: `rewardPool` (admin tops up with UZD)
- [ ] hardhat-zksync test suite for both contracts
- [ ] Deploy both to Sepolia, record addresses in `docs/PROGRESS.md`
- [ ] Verify on `block-explorer.sepolia.zksync.dev` (so partners can read the source)
- [ ] Update `docs/ARCHITECTURE.md` with new addresses

---

## Week 3 — Wallet UX (client-side, non-custodial)

**Goal:** user creates a wallet inside Telegram Mini App in <60 seconds.

- [ ] Install in `oltinpay-webapp`: `@scure/bip39`, `@noble/hashes`, `viem`
- [ ] `lib/wallet.ts` — BIP39 + scrypt + AES-GCM + Telegram Cloud Storage
- [ ] `lib/chain.ts` — viem client for zkSync Sepolia, paymaster wrap helpers
- [ ] `app/onboarding/page.tsx` — 4-step wizard:
  1. Welcome → Create wallet
  2. Show 12-word seed (warning: write it down)
  3. Verify (enter words 3, 7, 11)
  4. Set PIN
- [ ] `app/onboarding/restore/page.tsx` — restore from seed + PIN
- [ ] DEMO badge on Hero (and bottom nav, and footer)
- [ ] Localization keys (uz/ru/en) for new strings
- [ ] Backend: alembic migration `add_wallet_address_to_users`

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

## Week 5 — Staking on-chain + Welcome bonus

**Goal:** staking is fully on-chain, observable in explorer. Every new user gets 1000 UZD.

- [ ] Rewrite `src/staking/service.py` to wrap calls to `OltinStaking` contract
- [ ] Delete `staking-rewards-cron.sh` (rewards are calculated by the contract)
- [ ] Frontend `app/staking/page.tsx` — call contract via viem, show on-chain pending reward
- [ ] `src/welcome/router.py` + service — `POST /users/welcome/claim`:
  - Verify user not yet claimed (DB flag)
  - Admin signs `UZD.mint(user_address, 1000e18)`
  - Mark `welcome_claimed=true`
- [ ] Frontend prompts to claim on first login

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
