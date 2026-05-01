# OltinPay

Non-custodial wallet for tokenized gold (OLTIN) and a UZS-pegged stablecoin (UZD), built as a Telegram Mini App on zkSync Era.

**Status:** DEMO — tokens have no monetary value. The platform demonstrates fully on-chain transaction flow for partner integration.

---

## Architecture

```
OltinPay/
├── contracts/                 — Solidity (zkSync Era)
│   └── contracts/
│       ├── OltinTokenV2.sol   — OLTIN ERC20 (deployed Sepolia)
│       ├── OltinPaymaster.sol — gasless paymaster
│       └── OltinToken.sol     — legacy v1
├── oltinpay/
│   ├── oltinpay-api/          — FastAPI backend (Python 3.11+)
│   ├── oltinpay-webapp/       — Next.js 14 Telegram Mini App
│   ├── oltinpay-bot/          — aiogram Telegram bot
│   └── DevDocs/               — product docs (specs, API, tokenomics)
├── docker-compose.yml         — production stack (Traefik + Postgres + Redis + 3 services)
├── docker-compose.monitoring.yml
└── scripts/                   — backup / restore
```

---

## Tech stack

| Layer | Tech |
|-------|------|
| Smart contracts | Solidity, hardhat-zksync, OpenZeppelin AccessControl |
| Network | zkSync Era (Sepolia testnet, mainnet planned) |
| Backend | FastAPI, SQLAlchemy 2.0, alembic, Python 3.11+ |
| Frontend | Next.js 14 App Router, TypeScript, TailwindCSS, tma.js |
| Wallet | non-custodial — BIP39 seed encrypted with scrypt + AES-GCM, stored in Telegram Cloud Storage |
| Bot | aiogram 3 |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Reverse proxy | Traefik + Let's Encrypt |

---

## Tokens

| Symbol | Type | Status |
|--------|------|--------|
| **OLTIN** | commodity (1 token = 1 gram gold) | deployed Sepolia, mint/burn by admin |
| **UZD** | UZS-pegged stablecoin (DEMO) | deployed Sepolia, mint/burn by admin |

---

## Deployed contracts (zkSync Sepolia, chainId 300)

| Contract | Address |
|----------|---------|
| OltinTokenV2 (OLTIN) | `0x4A56B78DBFc2E6c914f5413B580e86ee1A474347` |
| UZD                  | `0x95b30Be4fdE1C48d7C5dC22C1EBA061219125A32` |
| OltinStaking         | `0x63e537A3a150d06035151E29904C1640181C8314` |
| Admin / Minter       | `0xa0A78aA9B9619fbc3bC12b5756442BD7A7D6779e` |

---

## Local development

```bash
# Backend
cd oltinpay/oltinpay-api
cp .env.example .env  # edit values
docker compose up -d postgres redis
uv venv && source .venv/bin/activate
uv pip install -e .
alembic upgrade head
uvicorn src.main:app --reload

# Frontend
cd oltinpay/oltinpay-webapp
npm install
npm run dev

# Bot
cd oltinpay/oltinpay-bot
pip install -r requirements.txt
python bot.py
```

---

## Production deployment

```bash
# On server
git pull
docker compose up -d --build
```

Services exposed via Traefik:
- `api.oltinpay.com` → oltinpay-api
- `api.oltinpay.com/scalar` → interactive API reference (Scalar) for partner integration
- `app.oltinpay.com` → oltinpay-webapp (Telegram Mini App)

---

## Security

- All admin keys rotated 2026-04-21. Old compromised key (`0xbf334c…b1c8`) has zero roles on contract.
- Secrets must live in `.env` only. **Never commit private keys, tokens, or RPC URLs with credentials.** `.gitignore` covers `.env*` patterns.
- pre-commit hook with `gitleaks` recommended.
