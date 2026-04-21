# OltinPay — TODO

> Active backlog. Items move to `docs/PROGRESS.md` when done.

---

## P0 — Blocking week 2

- [ ] Top up new admin `0xa0A78aA9…779e` with Sepolia ETH (≥0.1) for contract deployments
- [ ] Verify `OltinTokenV2` on `block-explorer.sepolia.zksync.dev` (so partners can read source)

## P1 — Week 2 (smart contracts)

- [x] Write `contracts/contracts/UZD.sol` — ERC20 + AccessControl, mint/burn admin
- [x] Write `contracts/contracts/OltinStaking.sol` — port DB logic (APY 7%, **per-deposit** 7-day lock)
- [x] hardhat tests: 32/32 passing on UZD + OltinStaking
- [x] Deploy script `deploy/deploy-uzd-staking.ts` + interactive `scripts/deploy.sh`
- [x] **Deployed on zkSync Sepolia 2026-04-21:**
  - UZD: `0x95b30Be4fdE1C48d7C5dC22C1EBA061219125A32`
  - OltinStaking: `0x63e537A3a150d06035151E29904C1640181C8314`
- [x] Recorded addresses in `docs/PROGRESS.md`
- [ ] Verify both on `block-explorer.sepolia.zksync.dev` (standard verify fails — needs zkSync verify plugin tuning)
- [ ] Fund `OltinStaking.rewardPool` with starter OLTIN (admin: approve + fundRewardPool)

## P1 — Week 3 (wallet UX)

- [x] Add to `oltinpay-webapp/package.json`: `@scure/bip39`, `@noble/hashes`, `viem`
- [x] `oltinpay-webapp/src/lib/wallet.ts` — BIP39 + scrypt + AES-GCM + Cloud Storage
- [x] `oltinpay-webapp/src/lib/contracts.ts` + `chain.ts` — viem client for zkSync Sepolia
- [x] `oltinpay-webapp/src/stores/wallet.ts` — in-memory unlocked session
- [x] `oltinpay-webapp/src/components/{DemoBadge,PinUnlock}.tsx`
- [x] `oltinpay-webapp/src/app/onboarding/page.tsx` — 4-step wizard
- [x] `oltinpay-webapp/src/app/onboarding/restore/page.tsx`
- [x] `WalletGate` in `providers.tsx` — checks Cloud Storage, redirects/locks
- [x] i18n keys for Demo/Onboarding/PIN (uz, ru, en)
- [x] `npx tsc --noEmit` clean
- [ ] DEMO badge in existing wallet/staking/exchange page headers
- [ ] Manual test in Telegram Mobile (iOS + Android)
- [ ] alembic migration: `add_wallet_address_to_users` (week 4)

## P1 — Week 4 (backend on-chain)

- [ ] `src/infrastructure/rpc.py` — JSON-RPC helper (httpx-based)
- [ ] Rewrite `src/balances/service.py` to read `balanceOf` from chain
- [ ] Rewrite `src/transfers/service.py` — index Transfer events, client signs
- [ ] Drop `src/exchange/` module entirely
- [ ] Add simple `src/swap/` module — fixed-rate OLTIN ↔ UZD

## P1 — Week 5 (staking + welcome)

- [ ] Rewrite `src/staking/service.py` — wrap `OltinStaking` contract
- [ ] Delete `oltinpay/staking-rewards-cron.sh` (no longer needed)
- [ ] `oltinpay-webapp/src/app/staking/page.tsx` — read on-chain pending reward
- [ ] `src/welcome/router.py` + service: `POST /users/welcome/claim` → mint 1000 UZD
- [ ] Frontend prompt to claim on first login

## P1 — Week 6 (polish)

- [ ] Run all 6 demo scenarios end-to-end on Sepolia
- [ ] Demo video (Loom, 3-5 min)
- [ ] `docs/PITCH.md` — 10-slide deck content
- [ ] `docs/PARTNER_ONBOARDING.md` — what partner needs (licence, reserve, banking, KYC)
- [ ] `docs/PRICING.md` — Starter / Growth / Enterprise tiers
- [ ] Live staging URL deployed via Docker Compose

---

## P2 — Tech debt

- [ ] Add `.github/workflows/ci.yml` — lint (ruff) + typecheck (mypy) + tests (pytest) on push
- [ ] Add `.github/workflows/contracts.yml` — hardhat tests + slither security scan
- [ ] Add `gitleaks` pre-commit hook
- [ ] Drop `contracts/artifacts-zk/` and `contracts/cache-zk/` from git (build artifacts) + add to `.gitignore`
- [ ] Drop `contracts/deployments-zk/` review — keep deployment records, drop build mess
- [ ] `oltinpay/DevDocs/standards/` — duplicate of global Codex `standards/`. Decide: keep, delete, or symlink

## P2 — Product

- [ ] Decide: do we keep `aylin/` (AI assistant module) or drop for v2 DEMO?
- [ ] Telegram Cloud Storage size limits — confirm encrypted seed (≈200 bytes base64) fits
- [ ] WebCrypto `crypto.subtle` compatibility test in Telegram WebView on iOS + Android
- [ ] Decide DEMO badge style (3 options in `docs/ARCHITECTURE.md`): plate / inline badge / full banner

## P2 — Regulatory (ask the partner / lawyer)

- [ ] Find exact text of НАПП stablecoin regulation: where reserve is held, does it earn interest?
- [ ] Confirm "wallet as technology" ≠ "stablecoin issuer licence" — i.e. partner holds licence, we provide tech
- [ ] OLTIN as commodity token — under what RUz law (gold derivative? digital asset?)

## P3 — Future / partner phase

- [ ] Mainnet deployment (after partner signs)
- [ ] Real fiat ↔ UZD reserve mechanism (partner's bank integrates)
- [ ] AML/KYC integration (partner's compliance)
- [ ] Hardware wallet support
- [ ] Multi-language docs (uz, ru, en, kz, kg)
- [ ] AMM / DEX upgrade (v3 feature)
- [ ] Multi-chain support beyond zkSync Era
