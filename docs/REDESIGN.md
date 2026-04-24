# OltinPay — Context Handoff

> **Audience:** a fresh Claude Code session that knows nothing about this project yet.
> Read this document end-to-end before touching code.
> Last updated: 2026-04-24 (session by Claude Opus 4.7).

---

## 1. Цель задачи

OltinPay — Telegram Mini App: non-custodial wallet для токенизированного золота (OLTIN) и UZS-привязанного демо-стейблкоина (UZD) на zkSync Era Sepolia. Всё движение токенов **должно быть видно в публичном блокчейне** — именно это демонстрируется партнёру.

Дедлайн: **Week 6 (~2026-04-29)** — pitch-ready DEMO. Состояние: середина миграции от DB-based логики к полностью on-chain. Контракты задеплоены и работают, wallet UX готов, backend частично переписан, frontend частично рассинхронизирован. Финальные шаги — убрать мёртвые DB-методы и поднять автоматический деплой.

**Не переписывать с нуля.** 80% кода — solid (contracts, wallet crypto, welcome bonus, balances on-chain); rotten — локально (frontend api.ts + три страницы + transfers/ модуль). Хирургия дешевле rewrite. Решение зафиксировано 2026-04-24.

---

## 2. Воркфлоу

Пользователь работает по строгому воркфлоу. **Не пропускать шаги.**

**LIGHT mode** — вопросы, exploration, typos, comments:
→ отвечаем прямо, без `/codex` и скиллов.

**FULL mode** — любой нетривиальный код (feature, fix, refactor):

| Шаг | Действие | Скилл |
|-----|----------|-------|
| 1 | Изучаю — `Read`/`Grep` всех затронутых файлов полностью | — |
| 2 | Описываю план с pros/cons, озвучиваю допущения | — |
| 3 | Критикую план | `/check` |
| 4 | Исправляю план по критике | — |
| 5 | Загружаю стандарты стека | `/codex` + `/python` для Python, `/typescript` для TS, `/rust` для Rust |
| 6 | Реализую код | — |
| 7 | Ревью diff — ищу попутные правки, должно быть чисто | `/review`, для Python → `/python-review` |
| 8 | Commit → push → ждать зелёного CI | — |

**Правила коммуникации:**
- Перед destructive actions (push, rm, drop) — **всегда спрашивать**, даже если кажется очевидным. У пользователя сохранена feedback-memory: "Pause and confirm".
- Перед принятием любого решения (пропустить шаг, сменить подход, расширить scope) — **переспросить**. User сам решает.
- Никогда не удалять данные/файлы/пользователей без явного подтверждения.
- `>` для blockquote в промптах/примерах НЕ использовать — чистый текст.
- Читать файлы **полностью**, не по диагонали. Задачи выполнять **последовательно**, не параллельно (если не указано иначе).

**Стандарты кода (CORE):**
- Tool-first: перед утверждением о коде — `Read`/`Grep`, не по памяти. Всегда cite `filename:line`.
- Honesty: не знаешь — скажи "не знаю". "Работает" — только после запуска тестов.
- Fix root cause, not symptoms.
- No mutable defaults, no bare except, no `== None` (is None), no f-string в logging.
- Меняй только то, что просили. Никаких попутных улучшений.
- Never use `--no-verify`, `--amend` published commits, force-push to main.

---

## 3. Репозитории и файловая структура

**Основной репо:** `temrjan/OltinPay` (приватный).
**Локальный клон:** `C:\Claude\архив\OltinPay\`
**Git remote:** `https://github.com/temrjan/OltinPay.git`
**Default branch:** `main`. PR-flow для фич, прямой push `main` допустим для `chore:`/`docs:`.

```
OltinPay/
├── contracts/                  # Solidity (zkSync Era via hardhat-zksync)
│   ├── contracts/
│   │   ├── OltinTokenV2.sol    # OLTIN ERC20 — ✅ deployed
│   │   ├── UZD.sol             # UZS-pegged demo stablecoin — ✅ deployed
│   │   ├── OltinStaking.sol    # 7% APY, per-deposit 7-day lock — ✅ deployed
│   │   ├── OltinPaymaster.sol  # gasless — ⏳ not deployed
│   │   └── OltinToken.sol      # legacy v1, can ignore
│   ├── test/                   # hardhat, 32/32 passing
│   ├── deploy/                 # hardhat-zksync scripts (canonical location)
│   ├── scripts/deploy.sh       # interactive wrapper — asks PRIVATE_KEY on stdin
│   └── hardhat.config.ts       # zkSyncSepolia + zkSyncMainnet, no deployPaths override
│
├── oltinpay/
│   ├── oltinpay-api/           # FastAPI, Python 3.11+
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── config.py       # pydantic-settings, RPC/contract addresses baked in
│   │   │   ├── infrastructure/
│   │   │   │   ├── rpc.py          # thin JSON-RPC over httpx
│   │   │   │   ├── blockchain.py   # balanceOf, getStakeInfo read helpers
│   │   │   │   └── admin_tx.py     # EIP-1559 signing via eth-account
│   │   │   ├── auth/               # Telegram initData auth + JWT
│   │   │   ├── users/              # wallet_address binding
│   │   │   ├── balances/           # on-chain reads
│   │   │   ├── welcome/            # 1000 UZD mint per user, reserve-then-broadcast
│   │   │   ├── staking/            # read-only wrapper on getStakeInfo
│   │   │   ├── transfers/          # ⚠️ STILL DB-BASED, Week 6 rewrite on viem
│   │   │   ├── aylin/              # AI assistant — ❓ decide keep/drop for DEMO
│   │   │   ├── contacts/           # favorites/recents
│   │   │   └── notifications.py    # Telegram Bot API push, Cyrillic i18n
│   │   ├── alembic/versions/   # 001_initial, 002_wallet_address, 003_welcome_claims
│   │   ├── tests/              # pytest whitelist runs in CI (не все tests)
│   │   └── pyproject.toml      # ruff+mypy+pytest config, per-file-ignores for RUF001
│   │
│   ├── oltinpay-webapp/        # Next.js 16, React 19, TypeScript, Tailwind, viem
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── layout.tsx      # Telegram SDK via next/script beforeInteractive
│   │   │   │   ├── providers.tsx   # WalletGate, QueryClient, auth
│   │   │   │   ├── onboarding/     # BIP39 seed wizard + PIN
│   │   │   │   ├── wallet/         # 🔄 needs rewrite for on-chain balances
│   │   │   │   ├── staking/        # 🔄 Week 6 — on-chain reads via viem
│   │   │   │   ├── send/           # 🔄 Week 6 — on-chain transfers via viem
│   │   │   │   ├── exchange/       # ❌ DELETE — backend /exchange removed
│   │   │   │   ├── aylin/          # AI chat page
│   │   │   │   ├── receive/        # QR + address
│   │   │   │   └── profile/        # language
│   │   │   ├── lib/
│   │   │   │   ├── wallet.ts       # ✅ BIP39 + scrypt + AES-GCM + Cloud Storage
│   │   │   │   ├── chain.ts        # ✅ viem public/wallet clients for zkSync Sepolia
│   │   │   │   ├── contracts.ts    # ✅ addresses + minimal ABIs
│   │   │   │   ├── i18n.ts         # uz/ru/en
│   │   │   │   └── api.ts          # ⚠️ 22 dead method calls to removed endpoints
│   │   │   ├── stores/wallet.ts    # in-memory unlocked HDAccount, 15-min auto-lock
│   │   │   ├── components/
│   │   │   │   ├── PinUnlock.tsx
│   │   │   │   ├── DemoBadge.tsx
│   │   │   │   └── layout/BottomNav.tsx
│   │   │   └── hooks/useTelegram.ts
│   │   ├── eslint.config.mjs   # flat config v9, 3 rules downgraded to warn
│   │   └── package.json        # "lint": "eslint" (NOT "next lint")
│   │
│   ├── oltinpay-bot/           # aiogram 3, minimal
│   └── DevDocs/                # ⚠️ HISTORICAL product docs — не active source of truth
│
├── docs/                       # ← Active source of truth
│   ├── ARCHITECTURE.md
│   ├── PLAN.md                 # 6-week roadmap
│   ├── PROGRESS.md             # append-only milestone log
│   ├── TODO.md                 # active backlog P0-P3
│   ├── DEPLOY.md               # server migration + secrets
│   └── REDESIGN.md             # ← THIS FILE
│
├── docker-compose.yml          # Traefik + Postgres + Redis + api + webapp + bot
├── docker-compose.monitoring.yml
├── scripts/                    # backup / restore
└── .github/workflows/
    ├── api.yml                 # ruff + mypy + pytest whitelist
    ├── contracts.yml           # hardhat compile + test
    ├── webapp.yml              # tsc --noEmit + eslint
    └── deploy.yml              # SSH to 7demo, git reset --hard, docker compose up
```

**Не трогать без явной задачи:**
- `contracts/contracts/*.sol` — задеплоено, admin keys ротированы, 32 теста. Любая правка = редеплой.
- `oltinpay-webapp/src/lib/wallet.ts` — crypto primitives. Менять ТОЛЬКО если знаешь scrypt/AES-GCM и consequences.
- `docs/PROGRESS.md` — **append-only** лог. Добавлять в начало, не переписывать прошлое.
- `oltinpay/DevDocs/` — historical, не active reference.
- `oltinpay-api/src/welcome/` — reserve-then-broadcast pattern с race-protection, хрупкий.

---

## 4. Технические детали

### Стек

| Слой | Технология | Версия | Заметки |
|------|-----------|--------|---------|
| Smart contracts | Solidity, hardhat-zksync | solc 0.8.24, zksolc 1.5.8 | OpenZeppelin AccessControl |
| Chain | zkSync Era Sepolia | chainId 300 | Mainnet — future |
| Backend | FastAPI + SQLAlchemy 2.0 + asyncpg | Python 3.11+ (CI=3.12) | strict mypy, ruff |
| Frontend | Next.js + React + Tailwind | Next 16.1.4, React 19.2.3, Tailwind 3.4 | App Router, TypeScript strict |
| Wallet | `@scure/bip39` + `@noble/hashes` + `viem` | viem 2.48+ | Non-custodial, seed in Telegram Cloud Storage |
| Bot | aiogram | 3.x | Minimal |
| DB | PostgreSQL | 16 | Stores users, wallet_address, welcome_claims, transfers (legacy), contacts |
| Cache | Redis | 7 | Sessions |
| Proxy | Traefik + Let's Encrypt | — | Routes `api.oltinpay.com` / `app.oltinpay.com` |

### Деплоенные контракты (zkSync Sepolia)

```
OltinTokenV2 (OLTIN)  0x4A56B78DBFc2E6c914f5413B580e86ee1A474347
UZD                    0x95b30Be4fdE1C48d7C5dC22C1EBA061219125A32
OltinStaking           0x63e537A3a150d06035151E29904C1640181C8314
Admin / Minter         0xa0A78aA9B9619fbc3bC12b5756442BD7A7D6779e  (rotated 2026-04-21)

Старый скомпрометированный (zero roles):  0xbf334c...b1c8
```

Все контракты unverified на explorer (стандартный `hardhat verify` не работает — нужен zkSync plugin tuning, carried forward).

### Server

**Host:** `62.169.20.2`, port `9281`, user `root`, alias `7demo` в `~/.ssh/config`.
SSH identity: `~/.ssh/oltinkey` (локально).
OS: Ubuntu, kernel 6.8.0-106, hostname `vitrina`.
Docker 29.3.1, Compose v5.1.1.

**Текущее состояние серверa (2026-04-24):**
- `/opt/oltinpay/` — **пустая**, deploy pipeline сюда никогда не запускался.
- `/opt/oltinchain/` — **старая папка**, содержит работающий контейнер `oltinpay-webapp` (image `oltinchain-oltinpay-webapp`, Feb 17, healthy 7 days).
- Backend API и bot на сервере **НЕ запущены** — только webapp со старым фронтом без реальных данных.
- Ports 80/443 заняты напрямую webapp-контейнером (не через Traefik).
- Другие проекты на этом сервере: dorify-v2, crypto-signals, ledger-ai, aqllify, znai-cloud, sulum, openclaw, vaultwarden. Trafic уже не через единый Traefik — каждый проект публикует порты сам. ⚠️ Планируемая Traefik в новой compose **конфликтует с 80/443** до миграции.

**Ключи на сервере:**
- `/root/.ssh/id_ed25519` — универсальный GitHub deploy key, **работает для clone `temrjan/OltinPay`** (verified `git ls-remote` returns HEAD = `5f69c2a`).
- Семейство `{project}_deploy` — для SSH GHA→сервер. Нет `oltinpay_deploy` — создать на шаге Task #6.

### CI/CD статус (2026-04-24)

| Workflow | Состояние | Последний зелёный |
|---|---|---|
| Webapp (Next.js) | 🟢 | `12378ab` (fixed сегодня) |
| API (Python) | 🟢 | `5f69c2a` (fixed сегодня) |
| Contracts (Solidity) | 🟢 | `d3dfc7b` (не триггерился с тех пор — paths не задеты) |
| Deploy to 7demo | 🔴 | Никогда. Missing secrets `DEPLOY_SSH_KEY`, `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PORT` + нужна миграция `/opt/oltinchain → /opt/oltinpay` |

GitHub environment `production` существует, **protection_rules пусты**, `can_admins_bypass: true` — готов принимать secrets.

### Команды подключения

```bash
# SSH на сервер
ssh 7demo

# Склонированный репо локально
cd /c/Claude/архив/OltinPay

# GitHub CLI (auth как temrjan)
gh run list --repo temrjan/OltinPay
gh pr list --repo temrjan/OltinPay
gh api repos/temrjan/OltinPay/environments
```

### Палитра / UI

Тёмная тема Telegram Mini App. В `layout.tsx`:
- `bg-background text-text-primary min-h-screen`
- Header/background цвет: `#0D0D0D` (через `tg.setHeaderColor` / `setBackgroundColor` в `useTelegram.ts`)
- DEMO badge — жёлтый (`bg-yellow-*`), компонент `DemoBadge.tsx`
- Tailwind конфиг: `oltinpay/oltinpay-webapp/tailwind.config.ts`

---

## 5. Архитектурные решения

Эти решения приняты и не пересматриваются без сильной причины.

**On-chain pivot (Weeks 4-5):** Все движения токенов происходят on-chain. Backend **читает** баланс из контракта (`balanceOf`, `getStakeInfo`), **не хранит** ledger. Исключение: `welcome_claims` таблица — учёт однократного mint'а 1000 UZD новому юзеру (admin подписывает, reserve-then-broadcast паттерн для предотвращения double-mint).
*Почему:* партнёру нужно "видеть в блокчейне". DB ledger это противоречит.

**Non-custodial wallet.** BIP39 мнемоника генерируется у клиента, шифруется scrypt (`N=2^17, r=8, p=1`) + AES-256-GCM, хранится в Telegram Cloud Storage. Seed **никогда** не покидает клиента в незашифрованном виде, бэкенд не видит приватники.
*Почему:* regulatory distance (мы — wallet as tech, не custodian), security.

**Клиент подписывает транзакции через viem.** Staking deposit/unstake/claim, transfers — всё client-side. Admin-signed — только welcome bonus mint (одна операция, контролируемая нами).
*Почему:* минимизация trust surface.

**zkSync Era Sepolia для DEMO, mainnet — после сделки с партнёром.**
*Почему:* zkSync = низкие комиссии, совместимость с EVM-инструментами (viem, hardhat). Paymaster опционален (gasless UX — future).

**Per-deposit lock в OltinStaking.** Каждый `stake()` создаёт свой Lot с независимым 7-дневным lock. Новый stake НЕ продлевает старые locks.
*Почему:* защита от стратегии "скинуть и сразу застейкать для продления", справедливое UX.

**Admin key ротирован (Week 1).** Старый `0xbf334c…b1c8` скомпрометирован (утёк в commit), все 4 роли (`DEFAULT_ADMIN`, `MINTER`, `BURNER`, `PAUSER`) переведены на `0xa0A78aA9…779e`. Git history санитизирован через `git filter-repo`.
*Почему:* security incident response.

**Frontend=Backend mid-migration рассинхрон — известный и ожидаемый.** `src/lib/api.ts` в webapp содержит методы к эндпоинтам `/exchange/*`, `/staking/deposit|withdraw|rewards`, `/balances/transfer` — всё удалено в backend. Не баги — work-in-progress Week 6.
*Почему зафиксировано:* чтобы не "чинить" мёртвый код.

**CI правила ослаблены, не отключены:**
- `@typescript-eslint/no-explicit-any` → warn (22 из 34 warnings в `api.ts` исчезнут при Week 6 переписке)
- `@typescript-eslint/no-unused-vars` → warn (dev velocity)
- `react-hooks/set-state-in-effect` → warn (valid pattern для one-time Telegram SDK mount)
- Ruff `RUF001` per-file-ignore для `notifications.py` (Cyrillic i18n — RUF001 путает кириллицу с латиницей)

*Почему:* "Fix root cause" требует переписать код, который скоро удалится. Warn сохраняет видимость долга без блокировки мигрирующего кода.

**Не переписывать проект с нуля.** Решение 2026-04-24. 80% кода чистые и ценные (contracts, wallet crypto, welcome, balances, CI). Rotted — 20%, локально (api.ts + 3 frontend pages + transfers/ backend + server migration). Хирургия за 3-5 дней, rewrite за 3-5 недель = не попадает в Week 6 deadline, теряем deployed contracts + ротированные ключи + git history.

**ADMIN_PRIVATE_KEY через Docker Compose `secrets:`.** Решение 2026-04-24. Env vars утекают через crash logs, `docker inspect`, error trackers (OWASP §5.1). Всё остальное — в `.env` с `chmod 600`. Деплой добавляет `docker compose config` как sanity check.

---

## 6. Прогресс

Статус-легенда: ✅ DONE · 🔄 IN PROGRESS · ⏳ TODO · ❌ BLOCKED

### Week 1 — Security & cleanup (2026-04-21)

- ✅ Admin keys rotated (все 4 роли, 8 транзакций)
- ✅ Git history sanitized (`git filter-repo` removed 4 leaked files from 23 commits)
- ✅ `oltinchain-*` services removed (5 services, 36011 LOC, commit `5a16c91`)
- ✅ Monorepo restructure, `contracts/` at top level
- ✅ `README.md` created
- ✅ `docker-compose.yml` updated (drop dead services, DB renamed `oltinchain` → `oltinpay`)

### Week 2 — Smart contracts (2026-04-21)

- ✅ `contracts/contracts/UZD.sol` — ERC20 + AccessControl + Pausable
- ✅ `contracts/contracts/OltinStaking.sol` — 7% APY, per-deposit 7-day lock, FIFO unstake
- ✅ 32/32 hardhat tests passing (UZD 13, OltinStaking 19)
- ✅ Deployed UZD `0x95b30Be4fdE1...`, OltinStaking `0x63e537A3a150...`
- ⏳ Verify on `block-explorer.sepolia.zksync.dev` (standard `hardhat verify` fails, needs zkSync plugin tuning)
- ⏳ Fund `OltinStaking.rewardPool` via admin (`approve` + `fundRewardPool`)

### Week 3 — Wallet UX (2026-04-21)

- ✅ `src/lib/wallet.ts` — BIP39 + scrypt + AES-GCM + Telegram Cloud Storage
- ✅ `src/lib/contracts.ts` + `chain.ts` — viem clients for zkSync Sepolia
- ✅ `src/stores/wallet.ts` — in-memory HDAccount, 15-min auto-lock
- ✅ `src/app/onboarding/page.tsx` — 4-step wizard (Welcome → Show seed → Verify → PIN)
- ✅ `src/app/onboarding/restore/page.tsx` — restore from seed
- ✅ `src/components/PinUnlock.tsx`, `DemoBadge.tsx`
- ✅ `WalletGate` in `providers.tsx` — redirect to onboarding / show PIN unlock
- ✅ i18n keys (uz, ru, en, ~25 × 3)
- ✅ `npx tsc --noEmit` clean
- ⏳ DEMO badge in wallet/staking page headers
- ⏳ Manual test on iOS + Android Telegram mobile

### Week 4 — Backend on-chain (2026-04-21, commit `1c8f61a`)

- ✅ `src/infrastructure/rpc.py`, `blockchain.py` — JSON-RPC helpers, selectors verified on-chain
- ✅ `users/wallet_address` + `POST /users/wallet` + alembic 002
- ✅ `src/balances/` rewritten — on-chain reads, 3 parallel calls (OLTIN, UZD, staking)
- ✅ `src/exchange/` deleted
- ✅ ruff + mypy clean (touched files)
- ✅ 43 new tests (rpc, blockchain, users_wallet, balances_onchain)

### Week 5 — Welcome + staking pivot (2026-04-22, commit `a352b69`)

- ✅ `POST /api/v1/welcome/claim` — admin-signed mint, reserve-then-broadcast
- ✅ `GET /api/v1/welcome/status`
- ✅ `src/infrastructure/admin_tx.py` — EIP-1559 signing, dynamic gas
- ✅ alembic 003 — `welcome_claims` table (unique user_id, FK CASCADE)
- ✅ `src/staking/` rewritten — read-only wrapper on `getStakeInfo`, write actions client-side
- ✅ 9 new tests, 70 total passing
- ✅ `/python-review` findings fixed

### Week 6 — Polish + pitch (🔄 in progress)

**Frontend rewrite (main scope):**
- ⏳ `webapp/src/lib/api.ts` — remove 22 dead methods, type living ones properly
- ⏳ `webapp/src/app/staking/page.tsx` — on-chain pending reward via viem (read `OltinStaking.pendingReward`)
- ⏳ `webapp/src/app/send/page.tsx` — on-chain transfers via viem (`ERC20.transfer`)
- ⏳ `webapp/src/app/exchange/page.tsx` — **delete** (backend `/exchange` gone, no replacement in v2 DEMO)
- ⏳ `webapp/src/app/wallet/page.tsx` — wire to new `/balances` response shape
- ⏳ Welcome-claim prompt on first login → `POST /welcome/claim`
- ⏳ DEMO badge in wallet/staking page headers
- ⏳ Manual test iOS + Android

**Backend cleanup:**
- ⏳ `src/transfers/service.py` — drop DB-based transfers, expose read-only `/transfers/{user_id}` (indexed events)
- ❓ Decide: keep or drop `src/aylin/` AI assistant for v2 DEMO (P2 question, blocks nothing)

**CI/CD & deploy:**
- ✅ Webapp CI migrated to Next.js 16 ESLint flat config (commit `12378ab`)
- ✅ API CI unblocked (ruff `RUF001` per-file-ignore, ruff `RUF006` real GC fix, mypy Optional[str] and UUID fixes — commit `5f69c2a`)
- ✅ Chore cleanup: removed `staking-rewards-cron.sh` + duplicate `deploy-uzd-staking.ts` (commits `e4b3502`, `bb15733`)
- 🔄 **Server migration `/opt/oltinchain` → `/opt/oltinpay`** — in progress, blocked on user decisions (downtime OK, ADMIN_PRIVATE_KEY via secrets:, DNS confirmed)
- ⏳ Create `.env.example` in repo (template for all required vars)
- ⏳ Add GHA secrets to `production` env: `DEPLOY_SSH_KEY` (new `oltinpay_deploy`), `DEPLOY_HOST=62.169.20.2`, `DEPLOY_USER=root`, `DEPLOY_PORT=9281`
- ⏳ Fix `deploy.yml`: add `-p $SSH_PORT` to ssh + ssh-keyscan, add `StrictHostKeyChecking=accept-new`, add `docker compose config` as post-step sanity check

**Pitch pack:**
- ⏳ Run 6 demo scenarios end-to-end on Sepolia with screenshots + explorer links
- ⏳ Demo video (Loom, 3-5 min)
- ⏳ `docs/PITCH.md` — 10-slide deck content
- ⏳ `docs/PARTNER_ONBOARDING.md` — licence, reserve, banking, KYC checklist
- ⏳ `docs/PRICING.md` — Starter / Growth / Enterprise tiers
- ⏳ Live staging URL after successful automated deploy

### P0 on-chain (parallel, independent of CI)

- ⏳ Top up admin `0xa0A78aA9…779e` with ≥ 0.1 Sepolia ETH
- ⏳ Verify OltinTokenV2 / UZD / OltinStaking on block-explorer.sepolia.zksync.dev (needs zkSync verify plugin config)
- ⏳ Fund `OltinStaking.rewardPool` (admin `approve` OLTIN → `fundRewardPool`)

### P2 — Tech debt (no deadline)

- ⏳ `.github/workflows/ci.yml` → consolidated lint/typecheck/tests (replace 3 separate)
- ⏳ `gitleaks` pre-commit hook
- ⏳ Drop `contracts/artifacts-zk/` + `cache-zk/` from git, add to `.gitignore`
- ⏳ Normalize `oltinpay/DevDocs/standards/` vs global Codex — decide: keep, delete, or symlink
- ⏳ Move `ADMIN_PRIVATE_KEY` from `.env` into `docker-compose.yml` `secrets:` mount (read from `/run/secrets/admin_private_key`)

---

## 7. Что делать дальше

**Приоритет 1 — Server migration + GHA deploy (Task #6, 🔄 активно).**
Перед стартом собрать ответы пользователя: backup БД из `/opt/oltinchain` (pg_dumpall или снести?), downtime OK, DNS подтверждён. Шаги:
1. Прочесть `/opt/oltinchain/docker-compose.yml` + `/opt/oltinchain/.env` (если есть) — понять что нужно перенести.
2. `docker exec` → pg_dumpall старой БД в `/root/oltinchain-backup-$(date).sql`.
3. `docker compose down -v` в `/opt/oltinchain` (освобождает 80/443).
4. `GIT_SSH_COMMAND='ssh -i /root/.ssh/id_ed25519' git clone git@github.com:temrjan/OltinPay.git /opt/oltinpay`.
5. Создать `.env.example` в репо и `/opt/oltinpay/.env` на сервере (chmod 600). `ADMIN_PRIVATE_KEY` — через `docker compose secrets:` (требует правки compose + чтение из `/run/secrets/admin_private_key` в `src/config.py`).
6. `docker compose up -d --build` в `/opt/oltinpay`. Проверить: Traefik работает, все сервисы healthy, `api.oltinpay.com` / `app.oltinpay.com` отвечают.
7. На сервере: `ssh-keygen -t ed25519 -N "" -f /root/.ssh/oltinpay_deploy`, добавить `.pub` в `authorized_keys`, тестнуть `ssh -p 9281 -i ... root@62.169.20.2`.
8. `gh secret set` 4 секрета в env `production`.
9. Fix `deploy.yml` (порт, StrictHostKeyChecking, `docker compose config` step).
10. Commit deploy.yml → push → wait green deploy run.

**Приоритет 2 — Frontend Week 6 cleanup (независимо от migration).**
Можно делать параллельно, пока пользователь решает про сервер.
1. Delete `webapp/src/app/exchange/page.tsx` + все exchange/swap методы из `api.ts`.
2. Переписать `webapp/src/lib/api.ts` — только живые методы (`authenticate`, `getMe`, `updateMe`, `setToken`, `getBalances`, welcome endpoints), строгие типы response.
3. `webapp/src/app/wallet/page.tsx` — привести к новому shape `BalancesResponse`.
4. `webapp/src/app/staking/page.tsx` — читать `pendingReward` через viem, писать через `chain.ts` helpers.
5. `webapp/src/app/send/page.tsx` — `ERC20.transfer(OLTIN, to, amount)` через viem, показывать tx hash.
6. Welcome prompt на первом login → `POST /welcome/claim`, показать status.
7. DEMO badge в headers страниц.
8. `npm run lint` должен давать < 10 warnings (после удаления api.ts долг схлопнется).

**Приоритет 3 — P0 on-chain (не блокирует остальное).**
1. Top up админа из тестового faucet (https://sepoliafaucet.com или zkSync sepolia bridge).
2. `cd contracts && npm install @matterlabs/hardhat-zksync-verify` — попробовать verify scripts.
3. Admin approve OLTIN → `OltinStaking.fundRewardPool(1000e18)` для стартового reward.

**Приоритет 4 — Pitch pack (финальная неделя).**
По `docs/PLAN.md` Week 6 список: 6 demo-сценариев с скринами + explorer ссылками, Loom-видео, PITCH.md, PARTNER_ONBOARDING.md, PRICING.md.

**Что НЕ делать:**
- Не переписывать проект с нуля.
- Не трогать `contracts/contracts/*.sol`, deployed.
- Не чинить mypy/ruff warnings в коде, который удаляется в приоритете 2.
- Не пытаться задать GHA secrets через `--body` с многострочными значениями (используй stdin: `cat key | gh secret set ...`).

---

## 8. Стартовые команды

Запустить в начале новой сессии, чтобы сориентироваться:

```bash
# 1. Перейти в репо
cd /c/Claude/архив/OltinPay

# 2. Синхронизироваться с удалённым
git fetch origin
git status
git log --oneline -10

# 3. Проверить CI состояние
gh run list --repo temrjan/OltinPay --limit 6 --json name,status,conclusion,displayTitle,headSha \
  --jq '.[] | "\(.name)  \(.status)/\(.conclusion // "-")  \(.displayTitle | .[:50])  \(.headSha[:7])"'

# 4. Проверить состояние сервера (быстрая проверка)
ssh 7demo 'bash -s' <<'EOF'
echo "=== containers ==="
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -iE 'oltin|traefik'
echo "=== /opt/oltinpay (target) ==="
ls -la /opt/oltinpay 2>/dev/null | head -5
echo "=== /opt/oltinchain (legacy) ==="
ls -la /opt/oltinchain 2>/dev/null | head -5
echo "=== ports 80/443 ==="
ss -tlnp 2>/dev/null | awk '$4 ~ /:(80|443)$/ {print $1, $4, $NF}' | head -3
EOF

# 5. Свериться с TODO
cat docs/TODO.md | head -80

# 6. Прочесть этот документ (REDESIGN.md) целиком — это приоритет 0
cat docs/REDESIGN.md
```

Перед любой Python-работой:
```
/python           # загрузить стандарты
```

Перед любой TypeScript-работой:
```
/typescript       # загрузить стандарты TS/NestJS (подходит и для Next.js)
```

Перед review:
```
/review           # общее
/python-review    # для Python diff'ов
/typescript-review
```

---

## 9. Ссылки

### Repo / CI

- GitHub: <https://github.com/temrjan/OltinPay>
- Actions: <https://github.com/temrjan/OltinPay/actions>
- Environments: <https://github.com/temrjan/OltinPay/settings/environments>
- Clone: `git@github.com:temrjan/OltinPay.git` (user — `temrjan`, auth via ssh key `~/.ssh/github_temrjan`)

### Deployed contracts (zkSync Sepolia)

- Explorer: <https://sepolia.explorer.zksync.io/>
- OltinTokenV2: <https://sepolia.explorer.zksync.io/address/0x4A56B78DBFc2E6c914f5413B580e86ee1A474347>
- UZD: <https://sepolia.explorer.zksync.io/address/0x95b30Be4fdE1C48d7C5dC22C1EBA061219125A32>
- OltinStaking: <https://sepolia.explorer.zksync.io/address/0x63e537A3a150d06035151E29904C1640181C8314>
- Admin wallet: `0xa0A78aA9B9619fbc3bC12b5756442BD7A7D6779e`
- RPC: `https://sepolia.era.zksync.dev`
- Sepolia faucet: <https://sepoliafaucet.com> or zkSync portal bridge

### Server / DNS

- Host: `62.169.20.2`, port `9281`, user `root`
- SSH alias: `7demo` (in local `~/.ssh/config`, uses `~/.ssh/oltinkey`)
- Domains (DNS already points to server per user):
  - `api.oltinpay.com` → backend
  - `app.oltinpay.com` → webapp

### Local paths

- Repo clone: `C:\Claude\архив\OltinPay\`
- Memory: `C:\Users\omadg\.claude\projects\C--Claude\memory\MEMORY.md`
- Codex standards: `C:\Claude\codex\python\`, `C:\Claude\codex\typescript\`, `C:\Claude\codex\rust\`

### Docs

- Active: `docs/ARCHITECTURE.md`, `docs/PLAN.md`, `docs/PROGRESS.md`, `docs/TODO.md`, `docs/DEPLOY.md`, `docs/REDESIGN.md` (this file)
- Historical (read-only reference): `oltinpay/DevDocs/`

### Rotation log

| Event | Date | Reference |
|-------|------|-----------|
| Admin key compromise discovered | pre-2026-04-21 | `BLOCKCHAIN_CONFIG.md` leak |
| Admin rotated `bf334c…` → `a0A78a…` | 2026-04-21 | PROGRESS.md Week 1, 8 tx |
| Git history sanitized | 2026-04-21 | `git filter-repo`, force-push |
