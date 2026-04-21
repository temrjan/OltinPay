# OltinPay — Architecture

> Non-custodial wallet for tokenized gold (OLTIN) and a UZS-pegged stablecoin (UZD), built as a Telegram Mini App on zkSync Era.

---

## Product positioning

**DEMO** technological showcase for B2B partners (banks / payment orgs / crypto licence holders in Uzbekistan and Central Asia). Partner brings: legal entity, regulatory licence, fiat reserve, banking integration. We provide: full smart-contract stack, non-custodial wallet UX, Telegram Mini App, on-chain proof of every operation.

Regulatory window: НАПП stablecoin pilot started 2026-01-01, runs 12 months (extendable to 36). We sell the technology — the partner runs the pilot.

---

## High-level diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│  USER (Telegram Mini App)                                            │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  oltinpay-webapp (Next.js 14 + tma.js)                         │  │
│  │  - BIP39 seed gen + scrypt + AES-GCM (client-side)             │  │
│  │  - Encrypted wallet stored in Telegram Cloud Storage           │  │
│  │  - viem signs transactions locally                             │  │
│  │  - paymaster pays gas (gasless UX)                             │  │
│  └─────────────────────┬──────────────────────────────────────────┘  │
└────────────────────────┼─────────────────────────────────────────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
┌──────────────────────┐    ┌──────────────────────────────────────┐
│  oltinpay-api        │    │  zkSync Era (Sepolia testnet)        │
│  FastAPI             │    │  ┌────────────────────────────────┐  │
│  - users (KYC meta)  │    │  │ OltinTokenV2 (OLTIN)           │  │
│  - balances (RPC     │◄───┼──│   ERC20 + AccessControl        │  │
│      read-only)      │    │  │   mint/burn by admin           │  │
│  - transfers (event  │    │  ├────────────────────────────────┤  │
│      indexing)       │    │  │ UZD (TBD week 2)               │  │
│  - staking (event    │    │  │   ERC20 + AccessControl        │  │
│      indexing)       │    │  │   mint/burn by admin           │  │
│  - aylin (AI chat)   │    │  ├────────────────────────────────┤  │
│  PostgreSQL + Redis  │    │  │ OltinStaking (TBD week 2)      │  │
└──────────────────────┘    │  │   deposit OLTIN, reward in UZD │  │
                            │  ├────────────────────────────────┤  │
                            │  │ OltinPaymaster                 │  │
                            │  │   sponsors gas for whitelisted │  │
                            │  └────────────────────────────────┘  │
                            └──────────────────────────────────────┘
```

---

## Wallet model — non-custodial

**Why non-custodial:** AML/legal scope of "wallet provider" is much narrower than "custodian of user funds". Partner gets a stablecoin issuer licence, we never touch user keys.

**Key flow (client-side only):**
1. `@scure/bip39` → 12-word mnemonic → user writes it down
2. User sets PIN (4-6 digits)
3. PIN + 16-byte salt → scrypt (`N=2^17, r=8, p=1, dkLen=32`) → key
4. Key + AES-GCM → encrypt seed → blob
5. Blob → Telegram Cloud Storage (`cloudStorage.setItem`)
6. `viem mnemonicToAccount(seed, "m/44'/60'/0'/0/0")` → EVM address
7. `POST /users/register { telegram_init_data, wallet_address }`

**Backend never sees the seed or private key.** It only stores `wallet_address` to read on-chain balances.

**KDF choice:** scrypt over argon2 — paulmillr's own README warns Argon2 is slow in JS. Rustok uses Argon2 because Rust runs it natively (≪100ms). JS Argon2 takes ~3s, scrypt ~400ms.

---

## Smart contracts

| Contract | Status | Purpose |
|---|---|---|
| `OltinTokenV2` | Deployed Sepolia `0x4A56…4347` | OLTIN — commodity token, 1 token = 1 g gold (DEMO declarative) |
| `OltinPaymaster` | Source in `contracts/contracts/` | Sponsors gas for our user transactions |
| `UZD` | TBD week 2 | UZS-pegged stablecoin, ERC20 + AccessControl, mint/burn by admin |
| `OltinStaking` | TBD week 2 | Deposit OLTIN, earn UZD reward (7% APY, 7-day lock) |

**Roles** (OpenZeppelin AccessControl):
- `DEFAULT_ADMIN_ROLE`, `MINTER_ROLE`, `BURNER_ROLE`, `PAUSER_ROLE` — all held by `0xa0A78aA9…779e` (admin/minter, MetaMask in Vivaldi)

---

## Backend — what stays / what changes

**Keep as-is:**
- `auth/`, `users/`, `contacts/`, `notifications.py`, `aylin/`, `common/`, `database.py`, `redis_client.py`, `main.py`, `config.py`

**Rewrite to read on-chain (week 4):**
- `balances/service.py` → `balanceOf(wallet_address)` via JSON-RPC
- `transfers/service.py` → index Transfer events from contract; user signs and broadcasts on the client
- `staking/service.py` → wrap calls to `OltinStaking` contract; rewards calculated on-chain by contract

**Remove:**
- `exchange/` module (orderbook + market makers — out of scope)
- `staking-rewards-cron.sh` (no longer needed — rewards are on-chain)

**Add:**
- `src/infrastructure/rpc.py` — thin JSON-RPC helper using existing httpx
- `src/users` — alembic migration for `wallet_address` column
- `src/welcome/` — endpoint to mint 1000 UZD on registration (admin signs)

---

## Frontend — what stays / what changes

**Keep:**
- `app/wallet/`, `app/send/`, `app/receive/`, `app/profile/`, `app/staking/`, `app/aylin/`
- `components/layout/BottomNav.tsx`, `LanguageSelector.tsx`
- `hooks/useTelegram.ts`, `hooks/useTranslation.ts`
- `lib/api.ts`, `lib/i18n.ts`
- `stores/app.ts` (Zustand)

**Rewrite:**
- `app/exchange/page.tsx` → simple swap UI (fixed-rate OLTIN ↔ UZD), not orderbook

**Add:**
- `lib/wallet.ts` — BIP39 + scrypt + AES-GCM + Telegram Cloud Storage
- `lib/chain.ts` — viem client + paymaster wrap for zkSync Era
- `app/onboarding/` — 4-step wizard: create / show seed / verify / set PIN
- `app/onboarding/restore/` — restore from seed
- DEMO badge in Hero / footer

---

## Stack summary

| Layer | Tech |
|---|---|
| Smart contracts | Solidity 0.8.x, hardhat-zksync, OpenZeppelin AccessControl |
| Network | zkSync Era Sepolia (chainId 300) → mainnet (324) |
| Backend | FastAPI, SQLAlchemy 2.0, alembic, Python 3.11+, httpx |
| Frontend | Next.js 14 App Router, TypeScript, TailwindCSS, tma.js |
| Wallet | `@scure/bip39`, `@noble/hashes`, `viem` |
| Bot | aiogram 3 |
| DB | PostgreSQL 16 |
| Cache | Redis 7 |
| Reverse proxy | Traefik + Let's Encrypt |

---

## Security

- Admin keys rotated 2026-04-21. The compromised key from leaked `BLOCKCHAIN_CONFIG.md` (`0x42a8…`) holds zero roles on the contract.
- Git history was rewritten with `git filter-repo` to scrub the leaked file from all 23 prior commits.
- Secrets must live only in `.env` (not in repo). `.gitignore` covers `.env*` patterns.
- Recommended: `gitleaks` pre-commit hook to catch future leaks.

---

## What's out of scope (by partner contract)

- Fiat ↔ stablecoin reserve management (partner's bank does that)
- AML/KYC verification (partner's compliance team)
- Stablecoin issuer licence (partner's lawyers)
- Customer support, marketing (partner's ops)
