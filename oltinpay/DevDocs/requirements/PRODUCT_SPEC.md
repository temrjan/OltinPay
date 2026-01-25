# OltinPay — Product Specification

> **Version:** 1.0
> **Date:** 2026-01-25
> **Status:** Draft

---

## 1. OVERVIEW

### 1.1 Product Vision

**OltinPay** — Telegram Mini App для торговли токенизированным золотом (OLTIN).

```
1 OLTIN = 1 грамм золота
```

### 1.2 Core Value Proposition

- Простая покупка/продажа цифрового золота
- Переводы между пользователями по username
- Пассивный доход через стейкинг (7% APY)
- Удобный интерфейс в Telegram

### 1.3 Target Audience

- Пользователи Telegram в Узбекистане
- Люди, желающие инвестировать в золото
- Крипто-энтузиасты

### 1.4 Project Type

```
Current:  DEMO (тестовая версия)
Future:   PRODUCTION (с реальными платежами)
```

---

## 2. ARCHITECTURE

### 2.1 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
├─────────────────────────────────────────────────────────────┤
│  oltinpay.com          │  app.oltinpay.com                  │
│  Landing Page          │  Telegram Mini App                 │
│  (Next.js)             │  (Next.js + tma.js)                │
└────────────┬───────────┴────────────┬───────────────────────┘
             │                        │
             ▼                        ▼
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                              │
├─────────────────────────────────────────────────────────────┤
│                   api.oltinpay.com                          │
│                   FastAPI + PostgreSQL                      │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   Auth   │  │  Wallet  │  │ Exchange │  │ Staking  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      BLOCKCHAIN                             │
├─────────────────────────────────────────────────────────────┤
│              zkSync Era (Ethereum L2)                       │
│              OltinToken Smart Contract                      │
│              (только переводы между пользователями)         │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, TailwindCSS, tma.js |
| Backend | FastAPI, Python 3.11+, SQLAlchemy 2.0 |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Blockchain | zkSync Era, web3.py |
| AI Assistant | znai-cloud RAG |
| Infra | Docker, Traefik, Let's Encrypt |

### 2.3 Domains

| Domain | Purpose |
|--------|---------|
| `oltinpay.com` | Landing page |
| `app.oltinpay.com` | Telegram Mini App |
| `api.oltinpay.com` | Backend API |

---

## 3. USER ACCOUNTS

### 3.1 Authentication

**Method:** Telegram initData (OAuth)

```
Telegram ID → Unique User Identifier
No phone/email registration required
```

### 3.2 User Identity (oltin_id)

Каждый пользователь имеет уникальный OltinPay ID для переводов.

**Правила:**
- Источник: Telegram username (если есть) или создаётся вручную
- Формат: `@lowercase_123` (3-32 символа, a-z, 0-9, _)
- Изменение: **ЗАПРЕЩЕНО** после создания
- Уникальность: проверяется в реальном времени

**Примеры:**
```
Telegram @alisher_uz → OltinPay @alisher_uz
Telegram без username → OltinPay @gold_fan_2026 (создаёт сам)
```

### 3.3 Account Structure

Каждый пользователь имеет **3 счёта** с **2 валютами**:

```
User Account
├── Wallet Account
│   ├── USD balance     ← для хранения
│   └── OLTIN balance   ← для хранения и переводов
│
├── Exchange Account
│   ├── USD balance     ← для торговли
│   └── OLTIN balance   ← для торговли
│
└── Staking Account
    └── OLTIN balance   ← для стейкинга (только OLTIN)
```

**Переводы между своими счетами:**
- Мгновенные
- Бесплатные
- Только в БД (без блокчейна)

---

## 4. WALLET MODULE

### 4.1 Features

| Feature | Description |
|---------|-------------|
| View Balance | Общий баланс + breakdown по счетам |
| Send OLTIN | Перевод другому пользователю по @oltin_id |
| Receive OLTIN | Получение от других пользователей |
| Transfer Internal | Перевод между своими счетами |
| History | История транзакций с фильтрами |

### 4.2 Send OLTIN Flow

```
1. Нажать "Send"
2. Ввести @oltin_id получателя (или выбрать из недавних/избранных)
3. Ввести сумму OLTIN
4. Увидеть preview: сумма, комиссия, получит
5. Подтвердить
6. Транзакция записывается в блокчейн
7. Уведомление получателю
```

### 4.3 Fees (Wallet → External)

| Parameter | Value |
|-----------|-------|
| Fee rate | 1% |
| Minimum fee | 0.05 USD equivalent |
| Minimum transfer | 1 USD equivalent |

**Пример при цене 100 USD/OLTIN:**
```
Отправляю:  1.0 OLTIN (100 USD)
Комиссия:   0.01 OLTIN (1 USD) = 1%
Получит:    0.99 OLTIN (99 USD)
```

### 4.4 Contacts

**Недавние:** Последние 5 получателей
**Избранные:** Сохранённые контакты (добавить/удалить)
**Поиск:** По @oltin_id (автодополнение)

### 4.5 Transaction History

**Фильтры:**
- Все (default)
- Wallet (переводы)
- Exchange (сделки)
- Staking (награды)

**Данные транзакции:**
```
↑ +5.00 OLTIN
From: @friend_123
Date: 25 Jan 2026, 14:32
Status: Completed
TX: 0x1234...abcd
```

---

## 5. EXCHANGE MODULE

### 5.1 Trading Model

**P2P Order Book** — пользователи торгуют друг с другом.

```
┌─────────────────────────────────────────┐
│              ORDER BOOK                 │
├─────────────────────────────────────────┤
│  SELL Orders          BUY Orders        │
│  ───────────          ──────────        │
│  101.50 (2.5)         99.50 (1.0)       │
│  101.00 (1.0)         99.00 (3.0)       │
│  100.50 (0.5) ←ASK    98.50 (2.0)       │
│               BID→    98.00 (1.5)       │
└─────────────────────────────────────────┘
```

### 5.2 Order Types

| Type | Description |
|------|-------------|
| Market Order | Исполнить по лучшей цене сейчас |
| Limit Order | Исполнить по указанной цене или лучше |

### 5.3 Trading Fee

```
Fee: 0.1% с каждой сделки
```

### 5.4 Price Source

```
До запуска биржи:  100 USD/OLTIN (фиксированная)
После запуска:     Mid price из orderbook
```

---

## 6. STAKING MODULE

### 6.1 Mechanics

```
APY:           7% (фиксированный)
Lock period:   7 дней
Rewards:       Ежедневно в 07:00 UTC+5
Compound:      Автоматический (награды → баланс)
Source:        Treasury Pool
```

### 6.2 Lock Logic (Simple Lock)

```
При депозите: весь баланс locked на 7 дней
При новом депозите: lock продлевается на 7 дней

Пример:
День 1: deposit 1.0 OLTIN → unlock День 8
День 5: deposit 0.3 OLTIN → unlock День 12 (reset)
День 12: можно вывести всё (1.3 OLTIN + rewards)
```

### 6.3 Rewards Calculation

```python
daily_reward = staked_balance * (0.07 / 365)

# Пример: 10 OLTIN стейкнуто
daily = 10 * 0.07 / 365 = 0.00192 OLTIN/день
monthly = 0.0575 OLTIN
yearly = 0.7 OLTIN
```

### 6.4 Withdrawal

- Можно вывести только после unlock (7 дней)
- Rewards доступны сразу (не имеют lock)
- Вывод: Staking → Wallet или Staking → Exchange

---

## 7. TOKENOMICS

### 7.1 Supply Distribution

```
Total Supply:     1,000,000 OLTIN (fixed, no mint/burn)

┌─────────────────────────────────────────┐
│  Treasury    │  200,000  │  20%         │
│  Liquidity   │  500,000  │  50%         │
│  Reserve     │  300,000  │  30%         │
└─────────────────────────────────────────┘
```

### 7.2 Pool Purposes

| Pool | Amount | Purpose |
|------|--------|---------|
| **Treasury** | 200,000 | Staking rewards, bonuses, promotions |
| **Liquidity** | 500,000 | Exchange trading (bots + users) |
| **Reserve** | 300,000 | Future development, partnerships |

### 7.3 Token Flow

```
STAKING REWARDS:
Treasury Pool ──(daily)──→ User Staking Account

TRADING:
User USD ←──(orderbook)──→ Liquidity Pool OLTIN

TRANSFERS:
User A OLTIN ──(blockchain)──→ User B OLTIN
Fee 1% ──→ Treasury Pool
```

### 7.4 Sustainability

```
Staking rewards/year (if 100k staked at 7%): 7,000 OLTIN
Treasury pool: 200,000 OLTIN
Runway: 200,000 / 7,000 = 28+ years

Transfer fees replenish Treasury:
1% of all transfers → Treasury
```

---

## 8. BLOCKCHAIN

### 8.1 Network

```
Network:    zkSync Era
Chain ID:   324 (Mainnet) / 300 (Sepolia Testnet)
RPC:        https://sepolia.era.zksync.dev (Demo)
```

### 8.2 Smart Contract

```
Contract:   OltinTokenV2
Address:    0x4A56B78DBFc2E6c914f5413B580e86ee1A474347
Standard:   ERC-20
Decimals:   18
```

### 8.3 Blockchain Operations

| Operation | Blockchain | DB |
|-----------|------------|-----|
| Transfer OLTIN (user→user) | ✅ adminTransfer | ✅ |
| Trade on Exchange | ❌ | ✅ |
| Staking deposit/withdraw | ❌ | ✅ |
| Internal transfer | ❌ | ✅ |

### 8.4 Gas Fees

```
Paid by:    System (from minter wallet)
User sees:  Commission deducted from amount
Actual gas: ~0.03 USD (zkSync)
```

---

## 9. AI ASSISTANT (Aylin)

### 9.1 Purpose

Помощник для пользователей — отвечает на вопросы о приложении.

### 9.2 Integration

```
Provider:   znai-cloud RAG
Endpoint:   https://znai.cloud/mcp
Method:     kb_search
```

### 9.3 Knowledge Base Topics

- Как работает кошелёк
- Как отправить OLTIN
- Как работает стейкинг
- Как торговать на бирже
- FAQ
- Troubleshooting

### 9.4 UI Location

- Кнопка в Profile tab
- Floating button на всех экранах (optional)

---

## 10. NOTIFICATIONS

### 10.1 Push Notifications (Telegram)

| Event | Delivery |
|-------|----------|
| Incoming OLTIN transfer | Immediate |
| Staking daily reward | 07:00 UTC+5 |

### 10.2 In-App Badges

| Event | Location |
|-------|----------|
| Trade executed | Exchange tab |
| Staking unlocked | Staking tab |

---

## 11. LOCALIZATION

### 11.1 Languages

| Code | Language |
|------|----------|
| `uz` | O'zbek (Latin) — default |
| `ru` | Русский |

### 11.2 Implementation

- i18n library (next-intl or react-i18next)
- JSON translation files
- Language selector in Profile

---

## 12. UI/UX

### 12.1 Navigation (Bottom Tabs)

```
┌──────────┬──────────┬─────────┬─────────┐
│    💰    │    📉    │    💎   │    👤   │
│  Wallet  │ Exchange │ Staking │ Profile │
└──────────┴──────────┴─────────┴─────────┘
```

### 12.2 Color Palette (Dark Theme)

```
Background:      #0D0D0D
Card:            #1A1A1A
Text Primary:    #FFFFFF
Text Secondary:  #8A8A8A

Accent Buy:      #22C55E (green)
Accent Sell:     #EF4444 (red)
Accent Gold:     #F59E0B (OLTIN brand)
Border:          #F59E0B (gold)
```

### 12.3 Main Screen (Wallet)

```
┌─────────────────────────────────────────┐
│              OltinPay                   │
├─────────────────────────────────────────┤
│                                         │
│  Total Balance                          │
│  ┌─────────────────────────────────┐   │
│  │     $1,234.56                   │   │
│  │     ───────────                 │   │
│  │     💰 Wallet:    $500 + 5 OLTIN│   │
│  │     📉 Exchange:  $234 + 2 OLTIN│   │
│  │     💎 Staking:   5 OLTIN       │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────┐ ┌─────────┐               │
│  │  Send   │ │ Receive │               │
│  └─────────┘ └─────────┘               │
│                                         │
│  Recent Transactions                    │
│  ───────────────────                    │
│  ↑ +5 OLTIN from @friend1              │
│  ↓ -2 OLTIN to @friend2                │
│  ↔ Transfer to Exchange                │
│                                         │
├─────────────────────────────────────────┤
│  💰      📉      💎      👤            │
└─────────────────────────────────────────┘
```

---

## 13. DEMO MODE

### 13.1 Initial State

```
New user receives:
├── 1,000 USD in Wallet Account
├── 0 OLTIN
└── Access to all features
```

### 13.2 Demo Limitations

- No real money deposits
- No real money withdrawals
- Blockchain on Testnet (Sepolia)

### 13.3 Purpose

- User education
- Feature testing
- Investor demonstration
- UX refinement

---

## 14. DEVELOPMENT PHASES

### Phase 1: Foundation (Current)
- [ ] Documentation (this spec)
- [ ] Database schema
- [ ] API specification
- [ ] UI wireframes

### Phase 2: Backend
- [ ] Auth (Telegram initData)
- [ ] User management
- [ ] Wallet module
- [ ] Internal transfers

### Phase 3: Frontend
- [ ] Landing page
- [ ] Mini App shell
- [ ] Wallet UI
- [ ] Profile UI

### Phase 4: Blockchain
- [ ] ZkSyncClient integration
- [ ] External transfers
- [ ] Transaction history

### Phase 5: Exchange
- [ ] Order book
- [ ] Matching engine
- [ ] Trading UI

### Phase 6: Staking
- [ ] Staking logic
- [ ] Rewards distribution
- [ ] Staking UI

### Phase 7: AI & Polish
- [ ] Aylin integration
- [ ] Notifications
- [ ] Localization
- [ ] Testing

---

## 15. SUCCESS METRICS

### 15.1 Demo Phase

| Metric | Target |
|--------|--------|
| Registered users | 1,000 |
| Daily active users | 100 |
| Avg session time | 3 min |
| Transactions/day | 500 |

### 15.2 User Satisfaction

- Onboarding completion rate > 80%
- Feature discovery rate > 60%
- NPS > 40

---

## APPENDIX A: Glossary

| Term | Definition |
|------|------------|
| OLTIN | Token representing 1 gram of gold |
| oltin_id | Unique username for transfers (@username) |
| Staking | Locking OLTIN to earn rewards |
| APY | Annual Percentage Yield |
| Treasury | Pool for rewards and expenses |
| Liquidity | Pool for exchange trading |

---

## APPENDIX B: Related Documents

| Document | Path |
|----------|------|
| Database Schema | `architecture/DATABASE.md` |
| Tokenomics | `architecture/TOKENOMICS.md` |
| API Specification | `api/ENDPOINTS.md` |
| UI Screens | `requirements/UI_SCREENS.md` |

---

*Document created following OltinPay Development Standards*
*Last updated: 2026-01-25*
