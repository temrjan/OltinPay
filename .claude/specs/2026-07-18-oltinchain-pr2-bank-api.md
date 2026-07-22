# СПЕКА (Гейт-1): PR-2 — Bank Connector API + SignerPool + PoR-эндпоинты + индексер

> Статус: **СПЕКА на ревью (Гейт-1).** Порядок: спека → ревью Ревьюером (аппрув/дополнения) → «го» → код (ultracode) → Гейт-2.
> Кресло: Инженер. Репо: `temrjan/OltinPay`, main @ `7ec3616` (PR-1 смержен). Родитель: эпик + PR-1 SPEC.
> Все факты §2 проверены чтением этой сессии (file:line). ИИ в проект не вшиваем (решение Капитана).

## 1. Цель
Перевести **банковскую/регуляторную сторону OltinPay полностью on-chain**: банк подключается стандартным
набором эндпоинтов и (а) аттестует золотой резерв → потолок эмиссии OLTIN, (б) подтверждает фиат-депозиты/
выводы → mint/burn UZD; публичный PoR-дашборд читает живую цепь. Все серверные on-chain записи идут через
**безопасный SignerPool** (Дизайн-А: разнос ключей + сериализованный nonce + идемпотентность). Это ядро
демо для банков/ЦБ (провабельное обеспечение), без front-run пользовательской money-path (она — PR-4).

## 2. Текущее состояние (проверено)
- **On-chain серверная подпись УЖЕ есть, но небезопасна для многоключевого сценария:** `admin_tx.py:78-134
  send_admin_mint` шлёт EIP-1559 mint, но `nonce = eth_getTransactionCount(addr,"pending")` **per-call без
  сериализации** (гонка при конкуренции — БЛОКЕР A1). `config.py:53 admin_private_key` (один ключ).
- **Идемпотентность reserve-then-broadcast УЖЕ есть эталоном:** `welcome/service.py:33-86` — insert строки с
  UNIQUE(user_id) → `flush` → `IntegrityError`→ConflictException → только потом `send_admin_mint` → update
  `tx_hash`. **Это шаблон A2** (insert-first, не check-then-act) — переиспользуем дословно.
- **Money-path пользователя — DB-ledger:** `transfers/service.py` двигает строки `balances` (Numeric),
  `OLTIN_PRICE_USD = Decimal("100")` фикс (service.py:26); `balances/models.py` — таблица `balances`
  (user×account×currency, amount). Это НЕ трогаем в PR-2 (см. §8 — флип в PR-4, иначе ломаем webapp).
- **Redis в стеке:** `config.py:28 redis_url` (для A1-Redis-варианта).
- **Существующие роуты:** auth/telegram, users/{me,oltin-id,search,wallet,...}, balances GET, transfers,
  welcome/{status,claim}, staking, contacts, aylin/chat, health.
- **Контракты на цепи (main, PR-1):** OltinTokenV3 (mint=Exchange, PoR-gated), Attestor×3 (Reserve/XAU/UZS,
  POSTER-gated postAnswer), Exchange, UZD (задеплоен Sepolia `0x95b3…5A32`). Адреса V3 — из deploy PR-1
  (env-параметризованы; см. deploy-хвост).

## 3. ДИЗАЙН-А — SignerPool (nonce & keys), с добитыми A1/A2 (обязательный раздел)

**Разнос ключей по ролям** (каждый — свой EOA, независимый поток nonce; ни один не используется конкурентно):
`KEY_BANK_OPS` (UZD mint/burn), `KEY_RESERVE` (ReserveAttestor POSTER), `KEY_XAU` (XauUsdFeed POSTER),
`KEY_UZS` (UzsUsdFeed POSTER). Все — тестовые демо-ключи в gitignored `.env`.

**Сериализованный signer на ключ (рефактор `admin_tx.py` → `infrastructure/signer_pool.py`):**
- `SignerPool.for_key(role)` → `NonceManagedSigner` (кеш по адресу).
- Метод `send(contract, calldata) -> tx_hash`: под **per-key lock** берёт следующий nonce из локального
  счётчика (init = `getTransactionCount(addr,"latest")` при старте; инкремент после успешного
  `sendRawTransaction`; ресинк из "latest" при `nonce too low`/рестарте) → подпись → броадкаст. Один
  in-flight tx на ключ by construction → гонки nonce нет.

**A1 (nonce) — РАТИФИЦИРОВАНО Капитаном: single-worker + one-process-per-key** (НЕ Redis). Инвариант —
не «один uvicorn-воркер», а **«ровно ОДИН пишущий процесс на ключ»** (находка Ревьюера, сильнее исходного A1):
- API стартует **single-worker** на каждый пишущий ключ (задокументированный деплой-инвариант).
- **`KEY_UZS` принадлежит ТОЛЬКО `/fx` в API → `keeper-uzs.ts` (PR-1) РЕТАЙРИТСЯ** (банк постит курс ЦБ через
  `/fx`; иначе keeper-uzs + /fx = два процесса на один ключ → гонка, которую single-worker-в-API не решает).
- `keeper-xau` остаётся отдельным внешним процессом на `KEY_XAU` (API XAU не постит); `KEY_RESERVE` и
  `KEY_BANK_OPS` — только API. **Каждый ключ = ровно один писатель.**
- `SignerPool` строим со **швом под будущий Redis-своп**, но Redis НЕ реализуем сейчас (rules #5: инфра под
  гипотетику + crash-window INCR↔broadcast). Локальный сериализованный nonce на ключ; прод-путь
  (распределённый nonce) — в honesty-box доке.

**A2 (TOCTOU идемпотентность) — reserve-then-broadcast, шаблон `welcome/service.py`:** каждый банк-write
(attestation/deposit/withdrawal) — сначала **insert строки с UNIQUE(idempotency_key)** (`auditRef`/`bankTxId`)
→ `flush` → `IntegrityError`→ConflictException (второй параллельный запрос падает быстро, второго броадкаста
нет) → только потом on-chain через SignerPool → update `tx_hash`. **Rollback-on-broadcast-failure (условие
Ревьюера):** если on-chain send упал ПОСЛЕ insert'а резервации — откатить строку (как `welcome/service.py:69-82`),
иначе orphan блокирует ретрай банка. Никакого check-then-act.

## 4. API-поверхность (7 bank / 6 user / 4 public)

### 4.1 Bank Connector `/api/v1/bank/*` (auth: **HMAC-подпись, РАТИФИЦИРОВАНО** — `X-Bank-Signature=HMAC-SHA256(secret, body+timestamp+nonce)` + `X-Bank-Timestamp`/`X-Bank-Nonce`; отклонять stale-timestamp/replay-nonce; HTTPS-only; прод=mTLS) — 7
| Метод Путь | Действие |
|---|---|
| `POST /attestations` | `{grams, auditRef}` → идемпотентно (UNIQUE auditRef) → `ReserveAttestor.postAnswer(grams)` через KEY_RESERVE → строка `reserve_attestations` |
| `GET /attestations/latest` | последняя аттестация + on-chain `latestRoundData` |
| `POST /fx` | `{uzsPerUsd|usdPerUzs, source}` → `UzsUsdFeed.postAnswer` через **KEY_UZS (владеет /fx; keeper-uzs ретайрен — A1)**; XAU релеит внешний keeper-xau (KEY_XAU), не банк |
| `POST /deposits` | `{userId|oltinId, amountUzs, bankTxId}` → идемпотентно (UNIQUE bankTxId) → `UZD.mint(user, amt)` через KEY_BANK_OPS → строка `bank_deposits` |
| `GET /withdrawals?status=pending` | очередь заявок на вывод (созданы юзером, §4.2) |
| `POST /withdrawals/{id}/confirm` | банк выдал фиат → `UZD burn` у юзера через KEY_BANK_OPS (burn-after-confirm, см. §8) |
| `POST /withdrawals/{id}/reject` | освободить заявку (без on-chain) |

### 4.2 User (auth: Telegram initData, как есть) — 6
| Метод Путь | Действие |
|---|---|
| `auth/telegram`, `users/*` | как есть (не трогаем) |
| `GET /balances` | **остаётся DB-ledger в PR-2 (Q5)** — не трогаем `balances/router.py`; chain-read при живом DB-transfers = split-brain (юзеру ещё не минтили через цепь → нули). Флип баланса+переводов → PR-4 |
| `POST /deposits` | интент юзера «завести N UZS» → demo-реквизиты (банк подтвердит через `/bank/deposits`) |
| `POST /withdrawals` | заявка на вывод `{amountUzd}` → строка `withdrawals` (status pending); burn — на confirm банка (§8) |
| `GET /transactions` | лента из индексера (§5) + explorer-links |
| `GET /quote` | превью цены buy/sell из XAU+UZS фидов (read-only `latestRoundData`, формула PR-1) |

### 4.3 Public (без auth) — 4
`GET /por` (reserve grams, OLTIN supply, coverage ratio, freshness/updatedAt, contract addresses) ·
`GET /por/history` (аттестации из индексера) · `GET /rates` (XAU/UZS live) · `GET /health`.

## 5. Индексер (finding #6 — намеренно ПРОСТОЙ поллер)
Фоновый поллер (не reorg-устойчивый, не backfill): периодически (`INDEXER_POLL_SEC`, деф 15с) тянет
последние N событий (`Minted/Burned` UZD, `Transfer` OLTIN/UZD, `AnswerPosted` Attestor) через
`eth_getLogs` от `lastSeenBlock`, пишет в таблицу `chain_events` (UNIQUE txHash+logIndex — идемпотентно),
кормит `GET /transactions` и `GET /por/history`. **Ограничение задокументировать** (log()): last-N,
без reorg-обработки — приемлемо для testnet-демо; reorg-устойчивость вне скоупа.

## 6. Затронутые файлы (оценка)
- **NEW** `src/infrastructure/signer_pool.py` (рефактор admin_tx.py; single-worker, шов под Redis); `src/infrastructure/chain_read.py` (latestRoundData/getLogs хелперы).
- **NEW** `src/bank/{router,service,schemas,models,deps}.py` (7 эндпоинтов + **HMAC-auth dep**); `src/por/{router,service,schemas}.py` (4 public); `src/withdrawals/{router,service,schemas,models}.py`; `src/indexer/{poller,models}.py`.
- **MOD** `src/main.py` (роутеры + indexer lifespan); `src/config.py` (KEY_*, BANK_HMAC_SECRET, INDEXER_POLL_SEC, V3-адреса из docs/DEPLOYMENTS.md); alembic-миграции (reserve_attestations/bank_deposits/withdrawals/chain_events).
- **RETIRE** `contracts/scripts/keeper-uzs.ts` (UZS теперь через `/fx`, A1); keeper-xau остаётся.
- **НЕ трогаем:** `transfers/*`, `balances/{models,router}.py` (DB-ledger + chain-read флип → PR-4), staking, aylin, contacts.

## 7. Критерии приёмки
- Bank: attestation → on-chain postAnswer (verify `latestRoundData`); deposit → on-chain UZD.mint; повтор
  auditRef/bankTxId → 409, второго on-chain-write НЕТ; withdrawal confirm → UZD burn.
- SignerPool: конкурентные записи одним ключом → монотонный nonce, без дублей/потерь; ресинк после «nonce too low».
- Public `/por`: coverage = supply/reserve из живой цепи; freshness из updatedAt.
- `GET /balances` остаётся DB-ledger (без изменений в PR-2); `GET /transactions` — из индексера с tx-ссылками.
- Гейты: `uv run ruff/mypy/pytest` зелёные; CI api.yml зелёный.

## 8. Отклонения от эпика (к ратификации на Гейте-1)
1. **DB-ledger пользователя НЕ выпиливаем в PR-2** (эпик говорил «PR-2 выпил DB-ledger»). Причина: user
   buy/sell/transfer станут client-signed только в PR-4 (webapp+paymaster); удалить DB-ledger сейчас =
   сломать webapp между PR-2 и PR-4. **PR-2 = банк/регулятор on-chain + user READ on-chain (balances/
   `/quote`; `/balances` остаётся DB — Q5); флип баланса+переводов (и удаление DB-ledger) → PR-4.** Осознанное непбрейкинг-разбиение.
2. **Escrow вывода — burn-after-confirm с pending-строкой в БД** (не on-chain escrow) — по решающему правилу
   спеки PR-1 §8 (on-chain escrow только если PR-4 в скоупе; здесь — pending+confirm, бёрн on-chain).
3. **A1 — РАТИФИЦИРОВАНО: single-worker + one-process-per-key** (см. §3; keeper-uzs ретайр, /fx владеет KEY_UZS). Redis отклонён как скоуп-оверран (rules #5).
4. **Bank-auth — РАТИФИЦИРОВАНО: HMAC-подпись** (см. §4.1). Документировать (условие #5): withdrawal-window без лока UZD (юзер может подвинуть между /withdrawals и /confirm → полный лок в PR-4 через on-chain escrow); testnet-ключи blast-radius (4 ключа в .env → прод KMS/HSM); индексер last-N/no-reorg.

## 9. Тест-план (скелет; полнота — в коде)
pytest: A2-идемпотентность (повтор auditRef/bankTxId → один on-chain-write, шаблон welcome-теста);
SignerPool nonce-гонка (конкурентные send одним ключом → монотонно, ресинк); bank-эндпоинты против
стаба цепи (SignerPool замокан); por-эндпоинты (coverage/freshness); индексер (idempotent upsert по
txHash+logIndex); withdrawal двухфазный (confirm→burn / reject→release / нет двойного burn). Стаб цепи
через фейковый RPC (как admin_tx-тесты, если есть) или замоканный SignerPool. Красная мутация: снять
UNIQUE на idempotency_key → тест даблминта краснеет.

## 10. Код-гейты (перед Гейтом-2)
PR-2 = серверные ключи + mint/burn = граница доверия → `/security-review` обязателен (SignerPool, bank-auth,
идемпотентность) + `/testing` + `/python-review`. Ревью дифа — Ревьюер (флот+scorer).

## 11. Открытые вопросы Ревьюеру
1. **A1**: Redis-nonce (рекомендую) или single-worker-документ?
2. **Отклонение №1** (DB-ledger → PR-4, не PR-2) — принимаешь непбрейкинг-разбиение?
3. **Bank auth**: статичный API-key в `.env` для демо — ок, или сразу mTLS/подпись?
4. **Индексер** как простой поллер (finding #6) без reorg — подтверждаешь для демо?
5. **`GET /balances` chain-read** при живом DB-ledger transfers — не создаёт ли путаницы до PR-4? (моя
   позиция: balances=истина-цепь, transfers DB-ledger помечаем legacy до PR-4; альтернатива — отложить
   chain-read balances в PR-4 тоже).
