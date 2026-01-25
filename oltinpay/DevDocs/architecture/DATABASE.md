# OltinPay — Database Schema

> **Version:** 1.0 | **Date:** 2026-01-25

## Overview

PostgreSQL 16 with SQLAlchemy 2.0 ORM.

---

## Tables

### users

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    oltin_id VARCHAR(32) UNIQUE NOT NULL,
    language VARCHAR(2) DEFAULT 'uz',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_oltin_id ON users(oltin_id);
```

### balances

```sql
CREATE TABLE balances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    account VARCHAR(10) NOT NULL,  -- 'wallet', 'exchange', 'staking'
    currency VARCHAR(10) NOT NULL, -- 'USD', 'OLTIN'
    amount DECIMAL(20,8) DEFAULT 0 CHECK (amount >= 0),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, account, currency)
);

CREATE INDEX idx_balances_user ON balances(user_id);
```

### staking_deposits

```sql
CREATE TABLE staking_deposits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    amount DECIMAL(20,8) NOT NULL CHECK (amount > 0),
    deposited_at TIMESTAMP DEFAULT NOW(),
    unlocked_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_staking_user ON staking_deposits(user_id);
CREATE INDEX idx_staking_unlock ON staking_deposits(unlocked_at);
```

### staking_rewards

```sql
CREATE TABLE staking_rewards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    amount DECIMAL(20,8) NOT NULL,
    balance_snapshot DECIMAL(20,8) NOT NULL,
    reward_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rewards_user ON staking_rewards(user_id);
CREATE INDEX idx_rewards_date ON staking_rewards(reward_date);
```

### transfers (blockchain)

```sql
CREATE TABLE transfers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_user_id UUID NOT NULL REFERENCES users(id),
    to_user_id UUID NOT NULL REFERENCES users(id),
    amount DECIMAL(20,8) NOT NULL CHECK (amount > 0),
    fee DECIMAL(20,8) NOT NULL CHECK (fee >= 0),
    tx_hash VARCHAR(66),
    status VARCHAR(20) DEFAULT 'pending', -- pending, confirmed, failed
    created_at TIMESTAMP DEFAULT NOW(),
    confirmed_at TIMESTAMP
);

CREATE INDEX idx_transfers_from ON transfers(from_user_id);
CREATE INDEX idx_transfers_to ON transfers(to_user_id);
CREATE INDEX idx_transfers_status ON transfers(status);
```

### internal_transfers

```sql
CREATE TABLE internal_transfers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    from_account VARCHAR(10) NOT NULL,
    to_account VARCHAR(10) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    amount DECIMAL(20,8) NOT NULL CHECK (amount > 0),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_internal_user ON internal_transfers(user_id);
```

### favorite_contacts

```sql
CREATE TABLE favorite_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    contact_user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, contact_user_id)
);

CREATE INDEX idx_favorites_user ON favorite_contacts(user_id);
```

### system_pools

```sql
CREATE TABLE system_pools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(20) UNIQUE NOT NULL, -- 'treasury', 'liquidity', 'reserve'
    currency VARCHAR(10) NOT NULL,
    amount DECIMAL(20,8) DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Initial data
INSERT INTO system_pools (name, currency, amount) VALUES
    ('treasury', 'OLTIN', 200000),
    ('liquidity', 'OLTIN', 500000),
    ('reserve', 'OLTIN', 300000);
```

### orders (exchange)

```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    side VARCHAR(4) NOT NULL, -- 'buy', 'sell'
    order_type VARCHAR(10) NOT NULL, -- 'market', 'limit'
    price DECIMAL(20,2),
    quantity DECIMAL(20,8) NOT NULL,
    filled_quantity DECIMAL(20,8) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'open', -- open, partial, filled, cancelled
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_side_price ON orders(side, price);
```

### trades

```sql
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buy_order_id UUID NOT NULL REFERENCES orders(id),
    sell_order_id UUID NOT NULL REFERENCES orders(id),
    buyer_id UUID NOT NULL REFERENCES users(id),
    seller_id UUID NOT NULL REFERENCES users(id),
    price DECIMAL(20,2) NOT NULL,
    quantity DECIMAL(20,8) NOT NULL,
    buyer_fee DECIMAL(20,8) NOT NULL,
    seller_fee DECIMAL(20,8) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trades_buyer ON trades(buyer_id);
CREATE INDEX idx_trades_seller ON trades(seller_id);
CREATE INDEX idx_trades_time ON trades(created_at);
```

---

## ERD Summary

```
users 1──────M balances
users 1──────M staking_deposits
users 1──────M staking_rewards
users 1──────M transfers (from)
users 1──────M transfers (to)
users 1──────M internal_transfers
users 1──────M favorite_contacts
users 1──────M orders
users 1──────M trades (buyer/seller)
orders 1─────M trades
```

---

## Initial User Setup

При регистрации создаём 6 записей в balances:

```sql
INSERT INTO balances (user_id, account, currency, amount) VALUES
    (user_id, 'wallet', 'USD', 1000),    -- Demo $1000
    (user_id, 'wallet', 'OLTIN', 0),
    (user_id, 'exchange', 'USD', 0),
    (user_id, 'exchange', 'OLTIN', 0),
    (user_id, 'staking', 'OLTIN', 0);
    -- Note: staking only has OLTIN, no USD
```
