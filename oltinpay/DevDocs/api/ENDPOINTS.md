# OltinPay API Specification

> **Version:** 1.0
> **Base URL:** https://api.oltinpay.com/v1
> **Auth:** Bearer JWT Token

---

## Overview

| Module | Prefix | Description |
|--------|--------|-------------|
| Auth | /auth | Telegram авторизация |
| Users | /users | Управление профилем |
| Wallet | /wallet | Кошелёк и переводы |
| Exchange | /exchange | Торговля |
| Staking | /staking | Стейкинг |
| Assistant | /assistant | AI помощник Aylin |

---

## 1. AUTH

### POST /auth/telegram

Авторизация через Telegram initData.

**Request:**
```json
{
  "init_data": "query_id=AAHdF...&user=%7B%22id%22%3A123..."
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "telegram_id": 123456789,
    "telegram_username": "alisher_uz",
    "oltin_id": "@alisher_uz",
    "created_at": "2026-01-25T10:00:00Z"
  }
}
```

**Response 401:**
```json
{
  "error": "invalid_init_data",
  "message": "Telegram initData validation failed"
}
```

---

### POST /auth/refresh

Обновление access token.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

## 2. USERS

### GET /users/me

Текущий пользователь.

**Response 200:**
```json
{
  "id": "uuid",
  "telegram_id": 123456789,
  "telegram_username": "alisher_uz",
  "oltin_id": "@alisher_uz",
  "wallet_address": "0x1234...abcd",
  "language": "uz",
  "created_at": "2026-01-25T10:00:00Z"
}
```

---

### PUT /users/me/oltin_id

Установить OltinPay ID (только один раз).

**Request:**
```json
{
  "oltin_id": "gold_investor"
}
```

**Response 200:**
```json
{
  "oltin_id": "@gold_investor",
  "message": "OltinPay ID set successfully"
}
```

**Response 400:**
```json
{
  "error": "oltin_id_already_set",
  "message": "OltinPay ID cannot be changed once set"
}
```

**Response 409:**
```json
{
  "error": "oltin_id_taken",
  "message": "This OltinPay ID is already in use"
}
```

---

### GET /users/search?q={query}

Поиск пользователя по oltin_id.

**Query params:**
- `q` (required): Поисковый запрос (минимум 2 символа)

**Response 200:**
```json
{
  "users": [
    {
      "oltin_id": "@alisher_uz",
      "telegram_username": "alisher_uz"
    }
  ]
}
```

---

### PUT /users/me/language

Изменить язык.

**Request:**
```json
{
  "language": "ru"
}
```

**Response 200:**
```json
{
  "language": "ru"
}
```

---

## 3. WALLET

### GET /wallet/balance

Баланс всех счетов.

**Response 200:**
```json
{
  "total_usd": "1234.56",
  "accounts": {
    "wallet": {
      "usd": "500.00",
      "oltin": "5.00000000"
    },
    "exchange": {
      "usd": "234.56",
      "oltin": "2.00000000"
    },
    "staking": {
      "oltin": "5.00000000",
      "locked_until": "2026-02-01T10:00:00Z"
    }
  },
  "price_per_oltin": "100.00"
}
```

---

### POST /wallet/transfer

Перевод OLTIN другому пользователю (через блокчейн).

**Request:**
```json
{
  "to_oltin_id": "@friend_123",
  "amount": "1.5",
  "note": "For coffee"
}
```

**Response 200:**
```json
{
  "transaction_id": "uuid",
  "tx_hash": "0x1234...abcd",
  "from": "@alisher_uz",
  "to": "@friend_123",
  "amount": "1.5",
  "fee": "0.015",
  "received": "1.485",
  "status": "completed",
  "created_at": "2026-01-25T10:00:00Z"
}
```

**Response 400:**
```json
{
  "error": "insufficient_balance",
  "message": "Not enough OLTIN in wallet",
  "available": "1.0",
  "required": "1.515"
}
```

---

### POST /wallet/internal

Перевод между своими счетами (без блокчейна).

**Request:**
```json
{
  "from_account": "wallet",
  "to_account": "exchange",
  "asset": "OLTIN",
  "amount": "2.0"
}
```

**Response 200:**
```json
{
  "transaction_id": "uuid",
  "from_account": "wallet",
  "to_account": "exchange",
  "asset": "OLTIN",
  "amount": "2.0",
  "fee": "0",
  "status": "completed"
}
```

---

### GET /wallet/transactions

История транзакций.

**Query params:**
- `type` (optional): wallet, exchange, staking, all (default: all)
- `limit` (optional): 1-100 (default: 20)
- `offset` (optional): pagination offset

**Response 200:**
```json
{
  "transactions": [
    {
      "id": "uuid",
      "type": "transfer_out",
      "asset": "OLTIN",
      "amount": "-1.5",
      "fee": "0.015",
      "counterparty": "@friend_123",
      "tx_hash": "0x1234...abcd",
      "status": "completed",
      "created_at": "2026-01-25T10:00:00Z"
    },
    {
      "id": "uuid",
      "type": "transfer_in",
      "asset": "OLTIN",
      "amount": "+5.0",
      "fee": "0",
      "counterparty": "@friend_456",
      "tx_hash": "0x5678...efgh",
      "status": "completed",
      "created_at": "2026-01-24T15:30:00Z"
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

---

### GET /wallet/contacts

Недавние и избранные контакты.

**Response 200:**
```json
{
  "recent": [
    {"oltin_id": "@friend_123", "last_transfer": "2026-01-25T10:00:00Z"},
    {"oltin_id": "@friend_456", "last_transfer": "2026-01-24T15:30:00Z"}
  ],
  "favorites": [
    {"oltin_id": "@mom", "added_at": "2026-01-20T10:00:00Z"}
  ]
}
```

---

### POST /wallet/contacts/favorites

Добавить в избранное.

**Request:**
```json
{
  "oltin_id": "@friend_123"
}
```

---

### DELETE /wallet/contacts/favorites/{oltin_id}

Удалить из избранного.

---

## 4. EXCHANGE

### GET /exchange/price

Текущая цена OLTIN.

**Response 200:**
```json
{
  "bid": "99.50",
  "ask": "100.50",
  "mid": "100.00",
  "spread": "1.00",
  "change_24h": "+2.5%",
  "volume_24h": "1234.56",
  "updated_at": "2026-01-25T10:00:00Z"
}
```

---

### GET /exchange/orderbook

Стакан ордеров.

**Query params:**
- `depth` (optional): 5, 10, 20 (default: 10)

**Response 200:**
```json
{
  "bids": [
    {"price": "99.50", "quantity": "10.5", "total": "1044.75"},
    {"price": "99.00", "quantity": "25.0", "total": "2475.00"}
  ],
  "asks": [
    {"price": "100.50", "quantity": "5.0", "total": "502.50"},
    {"price": "101.00", "quantity": "15.0", "total": "1515.00"}
  ],
  "spread": "1.00",
  "updated_at": "2026-01-25T10:00:00Z"
}
```

---

### POST /exchange/orders

Создать ордер.

**Request (Market Order):**
```json
{
  "side": "buy",
  "type": "market",
  "amount_usd": "100.00"
}
```

**Request (Limit Order):**
```json
{
  "side": "sell",
  "type": "limit",
  "price": "101.50",
  "quantity": "2.5"
}
```

**Response 201:**
```json
{
  "order_id": "uuid",
  "side": "buy",
  "type": "market",
  "status": "filled",
  "requested_amount": "100.00",
  "filled_quantity": "0.995",
  "average_price": "100.50",
  "fee": "0.10",
  "created_at": "2026-01-25T10:00:00Z"
}
```

---

### GET /exchange/orders

Мои ордера.

**Query params:**
- `status` (optional): open, filled, cancelled, all (default: all)
- `limit` (optional): 1-100 (default: 20)

**Response 200:**
```json
{
  "orders": [
    {
      "order_id": "uuid",
      "side": "sell",
      "type": "limit",
      "price": "101.50",
      "quantity": "2.5",
      "filled_quantity": "1.0",
      "status": "partial",
      "created_at": "2026-01-25T09:00:00Z"
    }
  ]
}
```

---

### DELETE /exchange/orders/{order_id}

Отменить лимитный ордер.

**Response 200:**
```json
{
  "order_id": "uuid",
  "status": "cancelled",
  "filled_quantity": "1.0",
  "cancelled_quantity": "1.5"
}
```

---

### GET /exchange/trades

История сделок.

**Query params:**
- `limit` (optional): 1-100 (default: 20)

**Response 200:**
```json
{
  "trades": [
    {
      "trade_id": "uuid",
      "side": "buy",
      "price": "100.50",
      "quantity": "0.995",
      "total": "99.90",
      "fee": "0.10",
      "created_at": "2026-01-25T10:00:00Z"
    }
  ]
}
```

---

## 5. STAKING

### GET /staking/balance

Баланс стейкинга.

**Response 200:**
```json
{
  "staked": "10.00000000",
  "pending_rewards": "0.01920000",
  "total_earned": "0.50000000",
  "apy": "7.00",
  "locked_until": "2026-02-01T10:00:00Z",
  "is_locked": true,
  "days_remaining": 5
}
```

---

### POST /staking/deposit

Внести в стейкинг (из Wallet).

**Request:**
```json
{
  "amount": "5.0"
}
```

**Response 200:**
```json
{
  "transaction_id": "uuid",
  "amount": "5.0",
  "new_staked": "15.0",
  "locked_until": "2026-02-01T10:00:00Z",
  "estimated_daily_reward": "0.00288"
}
```

---

### POST /staking/withdraw

Вывести из стейкинга (в Wallet).

**Request:**
```json
{
  "amount": "5.0"
}
```

**Response 200:**
```json
{
  "transaction_id": "uuid",
  "amount": "5.0",
  "new_staked": "10.0"
}
```

**Response 400:**
```json
{
  "error": "staking_locked",
  "message": "Cannot withdraw while staking is locked",
  "locked_until": "2026-02-01T10:00:00Z",
  "days_remaining": 5
}
```

---

### GET /staking/rewards

История наград.

**Response 200:**
```json
{
  "rewards": [
    {
      "date": "2026-01-25",
      "staked": "10.0",
      "reward": "0.00192",
      "apy": "7.00"
    },
    {
      "date": "2026-01-24",
      "staked": "10.0",
      "reward": "0.00192",
      "apy": "7.00"
    }
  ],
  "total_earned": "0.50000000"
}
```

---

## 6. ASSISTANT (Aylin)

### POST /assistant/chat

Чат с AI помощником.

**Request:**
```json
{
  "message": "Как отправить OLTIN другу?",
  "session_id": "uuid"
}
```

**Response 200:**
```json
{
  "response": "Чтобы отправить OLTIN другу:\n1. Откройте вкладку Wallet\n2. Нажмите Send\n3. Введите @oltin_id получателя\n4. Укажите сумму\n5. Подтвердите перевод",
  "session_id": "uuid"
}
```

---

## Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| unauthorized | 401 | Missing or invalid token |
| forbidden | 403 | No permission for this action |
| not_found | 404 | Resource not found |
| validation_error | 422 | Invalid request data |
| insufficient_balance | 400 | Not enough funds |
| staking_locked | 400 | Staking is locked |
| oltin_id_taken | 409 | OltinPay ID already in use |
| rate_limited | 429 | Too many requests |
| internal_error | 500 | Server error |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| /auth/* | 10/min |
| /wallet/transfer | 20/min |
| /exchange/orders | 60/min |
| Other | 100/min |

---

## WebSocket

### Connection

```
wss://api.oltinpay.com/ws?token={access_token}
```

### Events

**Price update:**
```json
{"event": "price", "data": {"bid": "99.50", "ask": "100.50"}}
```

**Orderbook update:**
```json
{"event": "orderbook", "data": {"bids": [...], "asks": [...]}}
```

**Trade executed:**
```json
{"event": "trade", "data": {"order_id": "uuid", "status": "filled"}}
```

**Transfer received:**
```json
{"event": "transfer", "data": {"from": "@friend", "amount": "1.5"}}
```

---

*API Specification v1.0 — OltinPay*
