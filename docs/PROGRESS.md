# OltinPay — Progress Log

> Append-only log of completed milestones. Newest at top.

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
