# OltinChain - Полный анализ архитектуры

**Дата:** 2026-01-24
**Цель:** Документация для следующей сессии разработки

---

## 1. ОБЗОР ПРОЕКТА

OltinChain - платформа для торговли токенизированным золотом (OLTIN).
- **1 OLTIN = 1 грамм золота**
- Telegram Mini App как основной интерфейс
- zkSync Era (Ethereum L2) для блокчейна
- Биржа с ботами для создания ликвидности

---

## 2. ТЕКУЩАЯ АРХИТЕКТУРА

### 2.1 Стек технологий

| Компонент | Технология |
|-----------|------------|
| Backend API | FastAPI + SQLAlchemy + PostgreSQL |
| Frontend | Next.js 14 (App Router) + Tailwind |
| Blockchain | zkSync Era + Solidity (ERC20) |
| State Management | Zustand |
| Real-time | WebSocket + Redis Pub/Sub |
| Auth | JWT + Telegram initData |
| Deployment | Docker Compose + Traefik |

### 2.2 Сервисы Docker

- oltinchain-api - FastAPI backend (port 8000)
- oltinchain-webapp - Next.js Mini App (port 3000)
- oltinchain-bots-v3 - Trading bots (Python)
- oltinchain-miniapp-bot - Telegram bot
- postgres - PostgreSQL 16
- redis - Redis 7
- traefik - Reverse proxy + SSL

---

## 3. БЛОКЧЕЙН - КРИТИЧЕСКИ ВАЖНО СОХРАНИТЬ

### 3.1 Смарт-контракт OltinTokenV2

**Сеть:** zkSync Era (chainId: 324)
**RPC:** https://mainnet.era.zksync.io

Основные функции контракта:
- `mint(address to, uint256 amount)` - Создать OLTIN (при покупке)
- `burn(address from, uint256 amount)` - Сжечь OLTIN (при продаже)
- `adminTransfer(from, to, amount)` - Перевод без газа для юзера
- `balanceOf(address)` - Баланс на блокчейне
- `totalSupply()` - Общая эмиссия

**Особенности:**
- Fee: 0.5% на переводы (50 bps)
- Pausable для экстренных случаев
- Minter role - только один адрес может минтить

### 3.2 Переменные окружения для блокчейна

```
ZKSYNC_RPC_URL=https://mainnet.era.zksync.io
OLTIN_CONTRACT_ADDRESS=<адрес контракта из .env>
MINTER_PRIVATE_KEY=<приватный ключ минтера из .env>
```

### 3.3 Файл клиента блокчейна

**Путь:** `/root/server/oltinchain-api/app/infrastructure/blockchain/zksync_client.py`

Класс ZkSyncClient:
- `mint(to_address, grams, order_id)` -> tx_hash
- `burn(from_address, grams, order_id)` -> tx_hash
- `admin_transfer(from, to, amount, transfer_id)` -> tx_hash
- `get_balance(address)` -> Decimal
- `get_total_supply()` -> Decimal

---

## 4. ТЕКУЩАЯ ПРОБЛЕМА - ДВЕ НЕСВЯЗАННЫЕ СИСТЕМЫ

### 4.1 Система 1: Market Orders (для пользователей)

Покупка: User USD -> mint OLTIN на блокчейне -> User OLTIN balance
Продажа: User OLTIN -> burn на блокчейне -> User USD balance

- Цена берётся из orderbook (best bid/ask)
- НО ордера в orderbook НЕ исполняются
- OLTIN создаётся/уничтожается на блокчейне

### 4.2 Система 2: Orderbook (только для ботов)

Bot A (sell) <-> Matching Engine <-> Bot B (buy)
                      |
                      v
            Balance Transfer (DB only)

- 20 Market Maker ботов + 10 Active Traders
- Ордера матчатся между собой
- Баланс переходит между ботами (без блокчейна)
- Пользователи НЕ ИМЕЮТ доступа

### 4.3 Результат

Две системы работают ПАРАЛЛЕЛЬНО И НЕЗАВИСИМО:
- Пользователи минтят/бёрнят токены
- Боты торгуют между собой
- Никакой связи между ними

---

## 5. БАЗА ДАННЫХ - ОСНОВНЫЕ ТАБЛИЦЫ

### users
- id UUID PRIMARY KEY
- phone VARCHAR(20) UNIQUE
- password_hash VARCHAR(255)
- wallet_address VARCHAR(42) - Ethereum адрес
- encrypted_private_key TEXT - Зашифрованный приватный ключ
- telegram_id BIGINT UNIQUE
- telegram_username VARCHAR(32)

### balances
- id UUID PRIMARY KEY
- user_id UUID REFERENCES users(id)
- asset VARCHAR(10) - 'USD' или 'OLTIN'
- available NUMERIC(20,8)
- locked NUMERIC(20,8)
- UNIQUE(user_id, asset)

### orders (Market Orders через блокчейн)
- id UUID PRIMARY KEY
- user_id UUID
- type VARCHAR(10) - 'buy' или 'sell'
- status VARCHAR(20) - 'pending', 'completed', 'failed'
- amount_uzs NUMERIC(20,2) - Сумма в USD
- amount_oltin NUMERIC(20,18)
- price_per_gram NUMERIC(20,2)
- fee_uzs NUMERIC(20,2)
- tx_hash VARCHAR(66) - Blockchain tx hash

### limit_orders (Orderbook)
- id UUID PRIMARY KEY
- user_id UUID
- side VARCHAR(4) - 'buy' или 'sell'
- price NUMERIC(20,2)
- quantity NUMERIC(20,8)
- filled_quantity NUMERIC(20,8)
- status VARCHAR(20) - 'open', 'partial', 'filled', 'cancelled'
- bot_id UUID REFERENCES bot_states(id)

### trades (сделки между лимитными ордерами)
- id UUID PRIMARY KEY
- buy_order_id UUID
- sell_order_id UUID
- price NUMERIC(20,2)
- quantity NUMERIC(20,8)
- taker_side VARCHAR(4)

### bot_states
- id UUID PRIMARY KEY
- user_id UUID
- bot_number INTEGER
- bot_type VARCHAR(20) - 'market_maker' или 'active_trader'
- level INTEGER
- state VARCHAR(20)

---

## 6. API ENDPOINTS

### Аутентификация
- POST /auth/register - Регистрация по телефону
- POST /auth/login - Логин по телефону
- POST /auth/refresh - Обновить токен
- POST /auth/telegram - Авторизация через Telegram initData

### Кошелёк
- GET /wallet/balance - Баланс USD + OLTIN
- GET /wallet/transactions - История
- POST /wallet/transfer - Перевод на адрес (блокчейн)
- POST /wallet/deposit - Demo депозит USD

### Market Orders (через блокчейн)
- POST /orders/buy - Купить OLTIN (mint)
- POST /orders/sell - Продать OLTIN (burn)
- GET /orders - История ордеров

### Orderbook (лимитные ордера)
- GET /orderbook - Текущий orderbook
- POST /orderbook/orders - Разместить лимитный ордер
- DELETE /orderbook/orders/{id} - Отменить ордер
- GET /orderbook/trades - Недавние сделки

### Цены
- GET /price/current - Текущая цена (mid/bid/ask)
- POST /price/quote/buy - Котировка на покупку
- POST /price/quote/sell - Котировка на продажу

---

## 7. ЧТО РАБОТАЕТ ХОРОШО

- Telegram Mini App авторизация
- Блокчейн интеграция (mint/burn/transfer)
- Orderbook matching engine
- Market Making боты (создают ликвидность)
- Real-time broadcasting (WebSocket)
- Чистая архитектура кода

---

## 8. ЧТО НУЖНО ИСПРАВИТЬ

- Две несвязанные системы (market orders и orderbook)
- Нет UI для лимитных ордеров
- Market orders не используют ликвидность orderbook
- Путаница с ценами (раньше был oracle, теперь orderbook)

---

## 9. РЕКОМЕНДУЕМАЯ НОВАЯ АРХИТЕКТУРА

### Концепция: ЕДИНАЯ БИРЖА

```
Deposit USD --> Balance (DB)
Deposit OLTIN --> Balance (DB) <-- Blockchain sync

         +------------------+
User --> |   Order Book     | <--- Bots
         |  (Limit Orders)  |
         +--------+---------+
                  |
           Matching Engine
                  |
         Balance Transfer (DB)

Withdraw USD <-- Balance (DB)
Withdraw OLTIN --> Blockchain transfer
```

### Ключевые принципы:
1. **Торговля = только DB операции** (быстро, без газа)
2. **Блокчейн = только депозит/вывод** (mint при депозите, transfer при выводе)
3. **Единый orderbook** для всех (пользователи + боты)
4. **Market orders = агрессивные лимитные ордера** (IOC - Immediate Or Cancel)

### Упрощённый стек для нового проекта
- Backend: FastAPI + PostgreSQL (сохраняем)
- Frontend: Next.js или Vite + React (упростить)
- Blockchain: zkSync + существующий контракт
- Auth: Только Telegram (убрать phone/password)
- Bots: Упростить до 5-10 ботов

---

## 10. ФАЙЛЫ ДЛЯ СОХРАНЕНИЯ ПРИ СОЗДАНИИ НОВОГО ПРОЕКТА

### Обязательно сохранить:
- `/root/server/oltinchain-api/app/infrastructure/blockchain/zksync_client.py`
- `/root/server/.env` (переменные блокчейна)

### Можно переиспользовать:
- `/root/server/oltinchain-api/app/infrastructure/telegram.py` (Telegram auth)
- `/root/server/oltinchain-api/app/application/services/orderbook_service.py` (matching engine)

---

## 11. ДОСТУПЫ

**Сервер:** oltinkey (SSH alias)
**IP:** 62.169.20.2
**Проект:** /root/server
**GitHub:** github.com/temrjan/oltinchain

**Домены:**
- https://oltinchain.com - Landing
- https://app.oltinchain.com - Webapp
- https://api.oltinchain.com - API

---

## 12. МОЖНО ЛИ СОЗДАТЬ НОВЫЙ ПРОЕКТ С СОХРАНЕНИЕМ БЛОКЧЕЙНА?

**ДА, МОЖНО!**

Блокчейн полностью независим от backend кода. Нужно только:

1. Сохранить из .env файла:
   - ZKSYNC_RPC_URL
   - OLTIN_CONTRACT_ADDRESS
   - MINTER_PRIVATE_KEY

2. Скопировать ZkSyncClient класс (или написать новый по тому же принципу)

3. Контракт уже задеплоен на zkSync - его не нужно передеплоивать

4. Все существующие балансы на блокчейне сохранятся

**Важно:** Приватный ключ минтера даёт полный контроль над эмиссией токенов. Хранить безопасно!

---

*Документ создан для передачи контекста в следующую сессию разработки.*
