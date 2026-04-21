# OltinPay — Progress Log

> Append-only log of completed milestones. Newest at top.

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
