# OltinPay — Progress Log

> Append-only log of completed milestones. Newest at top.

---

## 2026-04-22 — Week 5: Welcome bonus + on-chain staking pivot ✅

Commit `a352b69` on `main` — `feat(api): welcome bonus claim + on-chain staking pivot`.

### New

- `src/welcome/` — new module with:
  - `POST /api/v1/welcome/claim` — admin-signed `UZD.mint(user, 1000e18)`, one-time per user. Uses **reserve-then-broadcast**: INSERT + `flush()` with unique-constraint check precedes the on-chain mint, so concurrent claims fail fast with 409 instead of double-minting. On broadcast failure the reservation is rolled back (no orphan row pins the unique slot).
  - `GET /api/v1/welcome/status` — claim state (`claimed`, `tx_hash`, `claimed_at`).
- `src/infrastructure/admin_tx.py` — admin EIP-1559 signing on zkSync Era Sepolia:
  - `eth-account` dep added (no full web3.py)
  - Dynamic gas: `eth_estimateGas` + 20% headroom, `eth_maxPriorityFeePerGas` + `maxFee = base*2 + priority` (standard Ethereum formula)
  - `AdminUnconfigured` (missing key → 400) vs `AdminTxError` (RPC failure → 500) split for clean handler mapping
  - Logs tx hash; private key only from `SecretStr`, never to disk/logs
- `alembic/versions/003_welcome_claims.py` — `welcome_claims` table with unique(user_id) + FK CASCADE + index

### Modified

- `src/staking/` — pivoted to **fully read-only on-chain**. Removed `service.py` deposit/withdraw/claim logic, removed `models.py` (old `StakingDeposit`/`StakingReward` tables — users now sign stake/unstake/claim/compound client-side via viem directly against `OltinStaking`). Kept only `GET /api/v1/staking` that reads `getStakeInfo(address)` live from the contract.
- `src/staking/schemas.py` — `StakingInfoResponse` mirrors the 5-uint256 contract output plus `apy_bps=700`, `lock_period_days=7` for UI convenience. Wei values serialized as strings (JS BigInt-safe).
- `src/main.py` — registers `welcome_router` under `/api/v1/welcome`.
- `pyproject.toml` — added `eth-account>=0.13`.

### Tests (9 new, 70 total passing)

- `tests/test_welcome.py` — 6 integration tests: happy path, reject without wallet, idempotent conflict (409), auth required, status before/after claim. `send_admin_mint` patched so tests never touch the RPC.
- `tests/test_staking_onchain.py` — 3 tests with `respx`-mocked RPC: full `getStakeInfo` payload round-trip, reject without wallet, auth required.
- Pre-existing fixture errors in `test_contacts.py`/`test_users.py` (6) unchanged — unrelated.

### Verification

- `ruff check` clean on all touched files
- `mypy` clean on 10 source files (welcome/ + staking/ + admin_tx.py)
- `pytest`: **70 passed** (9 new + 61 pre-existing), 6 pre-existing fixture errors unrelated to this work
- `/python-review` loop: 1 critical + 4 error + 2 warning findings all fixed before commit (double-mint race, lost-mint on commit-fail, hardcoded gas=300k, priority-fee magic numbers, `/welcome` trailing-slash redirect, wallet normalization, redundant flush+commit)

### Outstanding (week 6)

- Webapp `app/staking/page.tsx` — read on-chain pending reward via viem
- Webapp first-login prompt to claim welcome bonus
- Commit cleanup of `oltinpay/staking-rewards-cron.sh` (custodial cron, already dead)
- Delete stale `contracts/scripts/deploy-uzd-staking.ts` (replaced by OltinStaking flow)
- Transfers service — still DB-based; migrate to viem-signed on-chain transfers

---

## 2026-04-21 — Week 4: Backend on-chain ✅

### New

- `src/config.py` — `zksync_rpc_url`, `zksync_chain_id` (300), `oltin/uzd/staking_contract_address` (live Sepolia addresses baked in as defaults)
- `src/infrastructure/rpc.py` — thin JSON-RPC client over existing httpx: `eth_call`, `pad_address`, `decode_uint256`, address validation regex. No `web3.py`/`eth-account` added.
- `src/infrastructure/blockchain.py` — high-level reads: `get_oltin_balance`, `get_uzd_balance`, `get_stake_info`. Function selectors verified against a live contract call (`getStakeInfo` selector `0xc3453153`, confirmed via on-chain try).
- `src/balances/db.py` — legacy DB helper `get_balance(db, user_id, account_type, currency)` kept in a separate module so `transfers/` and `staking/` (week-5 migration) keep compiling.
- `alembic/versions/002_add_wallet_address.py` — adds `users.wallet_address` String(42), unique index

### Modified

- `src/users/models.py` — `wallet_address` column (nullable, unique, indexed)
- `src/users/schemas.py` — `WalletRegister` with `^0x[a-fA-F0-9]{40}$` pattern; `UserResponse` now exposes `wallet_address`
- `src/users/router.py` — `POST /users/wallet` endpoint (idempotent if same address, 409 if already bound or claimed by another user)
- `src/users/service.py` — `get_user_by_wallet_address`, `set_wallet_address` (normalizes lowercase)
- `src/balances/schemas.py` — fully rewritten: `WalletBalances(oltin_wei, uzd_wei)`, `StakingBalances(total_principal, unlocked, pending_reward, lot_count, next_unlock_at)`, `BalancesResponse(wallet_address, wallet, staking)` — wei values serialized as strings to avoid JS 2^53 overflow
- `src/balances/service.py` — reads on-chain; three calls (OLTIN balanceOf, UZD balanceOf, staking.getStakeInfo) run concurrently over a single httpx.AsyncClient
- `src/balances/router.py` — simplified: only `GET /balances`. Internal transfer endpoint removed (on-chain transfers happen client-side via viem)
- `src/transfers/service.py`, `src/staking/service.py` — import `get_balance` from `src/balances/db` instead of deleted service helper
- `src/main.py` — drops `exchange_router` import + include

### Removed

- `src/exchange/` (full module — orderbook, market maker bots, swap scaffolding all gone)

### Verification

- `ruff check src/infrastructure/ src/balances/ src/users/ src/main.py` — **all checks passed**
- `mypy` on all my files — no errors (5 pre-existing errors only in `auth/`, `aylin/`, `staking/` legacy code I did not touch)
- On-chain selectors verified against a live contract:
  - `balanceOf(address) = 0x70a08231` — returned 0 for admin (expected, no OLTIN minted yet)
  - `getStakeInfo(address) = 0xc3453153` — returned 5×32 zero bytes (expected, admin has no stake)
- Followed Python standards: `from __future__ import annotations`, `TYPE_CHECKING` for typing-only imports, Pydantic v2 patterns, no bare `except`, `is None`/`is not None`

### Tests added (43 new tests, all green)

- `tests/test_rpc.py` — 23 unit tests (address validation, padding, uint256 decoding)
- `tests/test_blockchain.py` — 5 respx-mocked tests for `get_oltin_balance`, `get_uzd_balance`, `get_stake_info`
- `tests/test_users_wallet.py` — 11 integration tests for `POST /users/wallet` (success, idempotency, rebind rejection, cross-user conflict, malformed input, auth)
- `tests/test_balances_onchain.py` — 4 integration tests for `GET /balances` with mocked RPC
- Fixed conftest.py bugs along the way: `_db_session`→`db_session` alias in `client` fixture; `Balance(..., account=...)`→`account_type=`. This also unblocked `test_auth.py` (6 tests now pass).

### CI/CD added

- `.github/workflows/api.yml` — ruff + mypy + pytest for `oltinpay/oltinpay-api`
- `.github/workflows/webapp.yml` — `tsc --noEmit` + `next lint` for `oltinpay/oltinpay-webapp`
- `.github/workflows/contracts.yml` — `hardhat compile` + `hardhat test` for `contracts/`
- `.github/workflows/deploy.yml` — SSH into `7demo`, `git pull`, `docker compose up -d --build` on push to main
- `docs/DEPLOY.md` — first-time server migration from `/opt/oltinchain` → `/opt/oltinpay`, required GitHub Secrets, rollback guide

### Outstanding (week 5)

- `transfers/` and `staking/` services still DB-based; migrate to on-chain event indexing + client signing
- `POST /users/welcome/claim` endpoint (mint 1000 UZD via admin private key)
- DEMO badge on existing wallet/staking/exchange-page headers
- Wire `oltinpay-webapp` `wallet/page.tsx` + `staking/page.tsx` to the new `/balances` response shape

---

## 2026-04-21 — Week 3: Non-custodial wallet UX ✅

### Crypto / chain libs

- `src/lib/wallet.ts` — BIP39 + scrypt + AES-256-GCM
  - `newMnemonic()` / `isValidMnemonic()` / `mnemonicToAddress()` / `mnemonicToHDAccount()`
  - `encryptMnemonic(seed, pin)` / `decryptMnemonic(blob, pin)` — scrypt KDF (`N=2^17, r=8, p=1`), random 16-byte salt, AES-GCM with random 12-byte nonce
  - `saveEncryptedWallet()` / `loadEncryptedWallet()` / `removeEncryptedWallet()` — Telegram Cloud Storage with `localStorage` fallback for browser dev
- `src/lib/contracts.ts` — addresses (OLTIN, UZD, STAKING) + minimal ABIs
- `src/lib/chain.ts` — viem public/wallet clients for `zksyncSepoliaTestnet`, helpers for balanceOf, transfer, stake/unstake/claim

### State

- `src/stores/wallet.ts` — in-memory `useWalletStore` holding the unlocked HD account, auto-locks after 15 min idle. Seed is never persisted unencrypted.

### UI

- `src/app/onboarding/page.tsx` — 4-step wizard: Welcome → Show seed → Verify (3 random words) → Set PIN. After PIN — encrypts and saves to Cloud Storage, unlocks session, redirects to `/wallet`.
- `src/app/onboarding/restore/page.tsx` — paste 12 words + new PIN
- `src/components/PinUnlock.tsx` — full-screen PIN entry shown when wallet exists but session is locked/expired
- `src/components/DemoBadge.tsx` — yellow "DEMO" pill, used in onboarding
- `src/app/providers.tsx` — added `WalletGate` wrapper that:
  - On mount, checks Cloud Storage for an existing encrypted wallet
  - If absent → redirects to `/onboarding`
  - If present but session locked → renders `PinUnlock`
  - Onboarding routes pass through unchanged
  - Auto-locks expired sessions
- `src/lib/i18n.ts` — added Demo/Onboarding/PIN keys for uz, ru, en (~25 keys × 3 langs)

### Verification

- `npx tsc --noEmit` — clean (zero errors)
- Bundle additions: `@scure/bip39 @noble/hashes viem` ≈ 60KB gzipped
- KDF choice: scrypt over Argon2 (paulmillr's own recommendation for JS due to Argon2 perf)

### Outstanding (week 4)

- Backend: alembic migration `add_wallet_address_to_users`, register endpoint
- Wire wallet/staking/transfers screens to read on-chain via `chain.ts`
- DEMO badge into existing wallet/staking/exchange page headers
- Manual testing inside Telegram Mobile (iOS + Android) to confirm Cloud Storage + WebCrypto

---

## 2026-04-21 — Week 2: Smart contracts (UZD + OltinStaking) ✅

### Contracts written

`contracts/contracts/UZD.sol` — DEMO stablecoin
- `ERC20("Uzbek Sum Digital", "UZD")`, 18 decimals
- `ERC20Burnable + AccessControl + Pausable`
- 4 roles: `DEFAULT_ADMIN_ROLE`, `MINTER_ROLE`, `BURNER_ROLE`, `PAUSER_ROLE`
- Functions: `mint`, `adminBurn`, `pause`, `unpause`
- Events: `Minted`, `AdminBurned`

`contracts/contracts/OltinStaking.sol` — on-chain staking
- 7% APY, **per-deposit 7-day lock** (new deposits do NOT extend old locks)
- Reward currency: OLTIN (same as principal — matches Python service)
- Pull-based — user calls `claim()` (to wallet) or `compound()` (re-stake)
- Each `stake()` creates a new locked `Lot` in user's array
- `unstake()` walks lots FIFO, takes from unlocked, reverts if not enough unlocked
- Reward pool funded by `FUNDER_ROLE`; if empty → partial payout, remainder stays as `unclaimedReward`
- Admin can withdraw unallocated pool but cannot touch user principal
- `Pausable`, `ReentrancyGuard`, `SafeERC20`

### Tests — 32/32 passing

- `contracts/test/UZD.test.ts` — 13 tests (metadata, mint, burn, transfer, pause)
- `contracts/test/OltinStaking.test.ts` — 19 tests covering:
  - Constructor + role grants
  - stake creates locked lot, multiple stakes don't extend old locks
  - unstake reverts while locked, allows partial of unlocked, compacts lots
  - Reward accrual at 7% APY pro-rata across multiple stakes
  - claim transfers + decreases pool, returns 0 when nothing, caps at pool when short
  - compound moves reward to new locked lot
  - Admin pool funding, withdrawal limits, non-funder cannot fund
  - Pause blocks all user actions

### Deploy script

`contracts/scripts/deploy-uzd-staking.ts` — deploys both on zkSync Sepolia, uses existing OLTIN `0x4A56…4347` for staking. Requires `PRIVATE_KEY` of admin (`0xa0A78aA9…779e`) in `contracts/.env`.

### Deployed addresses (zkSync Era Sepolia)

| Contract | Address | Status |
|---|---|---|
| OltinTokenV2 (OLTIN) | `0x4A56B78DBFc2E6c914f5413B580e86ee1A474347` | deployed earlier |
| **UZD** | `0x95b30Be4fdE1C48d7C5dC22C1EBA061219125A32` | ✅ deployed 2026-04-21 |
| **OltinStaking** | `0x63e537A3a150d06035151E29904C1640181C8314` | ✅ deployed 2026-04-21 |
| OltinPaymaster | source ready | not yet deployed |

All three live contracts are administered by `0xa0A78aA9B9619fbc3bC12b5756442BD7A7D6779e` (rotated admin from week 1).

### Sanity check (post-deploy)

- `UZD.decimals()` = 18 ✓
- `UZD.hasRole(DEFAULT_ADMIN_ROLE, admin)` = true ✓

### Outstanding

- [ ] Verify both contracts on `block-explorer.sepolia.zksync.dev` — standard `hardhat verify` failed with bytecode mismatch; needs zkSync-specific verify plugin tuning. Source is in repo (`contracts/contracts/UZD.sol`, `OltinStaking.sol`) so partner can read it.
- [ ] Fund `OltinStaking.fundRewardPool(amount)` — admin must `OLTIN.approve(OltinStaking, X)` then call `fundRewardPool(X)` to seed yield.

---

## 2026-04-21 — Week 1: Security & Repo Cleanup ✅

### Key rotation (zkSync Sepolia)

Compromised admin key (`0x42a8…62e6`, leaked in `BLOCKCHAIN_CONFIG.md`) is now worthless. All 4 roles transferred to new admin.

| Role | Old holder | New holder | Status |
|---|---|---|---|
| `DEFAULT_ADMIN_ROLE` | `0xbf334c…b1c8` | `0xa0A78aA9…779e` | ✅ revoked + granted |
| `MINTER_ROLE` | `0xbf334c…b1c8` | `0xa0A78aA9…779e` | ✅ revoked + granted |
| `BURNER_ROLE` | `0xbf334c…b1c8` | `0xa0A78aA9…779e` | ✅ revoked + granted |
| `PAUSER_ROLE` | `0xbf334c…b1c8` | `0xa0A78aA9…779e` | ✅ revoked + granted |

**Transactions** (zkSync Sepolia explorer):
- grant `DEFAULT_ADMIN`: `0x0a67756396f798c26cc7aba781dc7df0bf75e57b149302be6eaca5b34695df18`
- grant `MINTER`:        `0x5416c8fd4106b19fae8b384d0a2215d8f6dc109216a12ce7cbc7d48c20766d66`
- grant `BURNER`:        `0x486db429cfcdec0dfd28734f7868e221a9a832c9c3b05fa5372163e7540a394f`
- grant `PAUSER`:        `0xb6c417f8d8e161bcb93c664226ee580ed66ebd28bf9a0f2ef8c3701e9fe4f272`
- revoke `MINTER`:        `0x42b06a6043743eb675290813f89d5b0d06d856e371eb0644e971dbf795a6a487`
- revoke `BURNER`:        `0x553247128d6420e386ac9d9d5f848042d5867f82e307406c4b32cb5d4f90205d`
- revoke `PAUSER`:        `0xebd3f228e5a34fa25bb5dfc38a818163a4e60641003683585fb7ed5c189ddd61`
- revoke `DEFAULT_ADMIN`: `0xb186b370fc44e4255171a3567d27381e227d9acd14cdf3df291cd72c82d3ac4e`

### Git history sanitization

- `git filter-repo` removed 4 leaked files from all 23 commits:
  - `BLOCKCHAIN_CONFIG.md` (root)
  - `oltinpay/DevDocs/architecture/BLOCKCHAIN_CONFIG.md` (copy)
  - `BLOCKCHAIN_CLIENT_BACKUP.py` (root)
  - `oltinpay/DevDocs/guides/BLOCKCHAIN_CLIENT_BACKUP.py` (copy)
- Force-pushed cleaned history to `origin/main`
- Verified: leaked private key `0x42a8…62e6` is not present in any blob in the repo

### Repo restructure

Removed (5 services + 4 docs + landing):
- `oltinchain-api/`, `oltinchain-bots-v3/`, `oltinchain-dashboard/`, `oltinchain-miniapp-bot/`, `oltinchain-webapp/`
- `landing/`
- `ARCHITECTURE_ANALYSIS.md`, `OLTIN_EXCHANGE_SPEC.md`, `oltinpay/DevDocs/architecture/ARCHITECTURE_ANALYSIS.md`
- `docker-compose.yml.bak`

Renamed:
- `oltinchain-contracts/` → `contracts/` (top-level)

Added:
- `README.md` (was missing)

Updated:
- `docker-compose.yml` — only Traefik, Postgres, Redis, oltinpay-api, oltinpay-webapp, oltinpay-bot. DB renamed `oltinchain` → `oltinpay`.

**Stats:** 322 files changed, +108 / −36 011 lines. Single commit `5a16c91`.

### Deployed contracts

| Contract | Network | Address |
|---|---|---|
| `OltinTokenV2` | zkSync Sepolia | `0x4A56B78DBFc2E6c914f5413B580e86ee1A474347` |

### Unverified contracts (TODO: verify via hardhat-zksync)

`OltinTokenV2` source is in `contracts/contracts/OltinTokenV2.sol` but not yet verified on the explorer. Verification will land alongside week-2 deployments.

---
