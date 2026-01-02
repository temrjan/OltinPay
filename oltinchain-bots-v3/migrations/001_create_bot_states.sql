-- Migration: Create bot_states table for State Machine bots
-- Date: 2026-01-02

-- Add is_bot column to users
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_bot BOOLEAN DEFAULT FALSE;

-- Mark existing bot users
UPDATE users SET is_bot = TRUE WHERE phone LIKE '+998900%' OR phone LIKE '+998901%' OR phone LIKE '+998902%' OR phone LIKE '+998903%';

-- Create bot_states table
CREATE TABLE IF NOT EXISTS bot_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bot_number INT NOT NULL,
    level INT NOT NULL CHECK (level >= 1 AND level <= 10),

    -- State machine
    state VARCHAR(20) NOT NULL DEFAULT 'idle',

    -- Current order reference
    pending_order_id UUID REFERENCES limit_orders(id) ON DELETE SET NULL,

    -- Tracking
    total_trades INT NOT NULL DEFAULT 0,
    last_trade_at TIMESTAMP,
    state_changed_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE(bot_number),
    UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_bot_states_state ON bot_states(state);
CREATE INDEX IF NOT EXISTS idx_bot_states_level ON bot_states(level);

-- Create bot_pnl table
CREATE TABLE IF NOT EXISTS bot_pnl (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id UUID NOT NULL REFERENCES bot_states(id) ON DELETE CASCADE,
    initial_usd NUMERIC(20, 8) NOT NULL,
    initial_oltin NUMERIC(20, 8) NOT NULL,
    initial_oltin_price NUMERIC(20, 8) NOT NULL,
    initial_value NUMERIC(20, 8) NOT NULL,
    total_volume_usd NUMERIC(20, 8) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(bot_id)
);

-- Create rebalance_history table
CREATE TABLE IF NOT EXISTS rebalance_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id UUID NOT NULL REFERENCES bot_states(id) ON DELETE CASCADE,
    imbalance_pct NUMERIC(10, 4) NOT NULL,
    usd_before NUMERIC(20, 8) NOT NULL,
    oltin_before NUMERIC(20, 8) NOT NULL,
    action_type VARCHAR(20) NOT NULL,
    market_order_side VARCHAR(10),
    market_order_value NUMERIC(20, 8),
    usd_after NUMERIC(20, 8) NOT NULL,
    oltin_after NUMERIC(20, 8) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rebalance_history_bot ON rebalance_history(bot_id);

-- Create oracle_prices table
CREATE TABLE IF NOT EXISTS oracle_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    price NUMERIC(20, 8) NOT NULL,
    source VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_oracle_prices_time ON oracle_prices(created_at DESC);

-- Add bot_id to limit_orders
ALTER TABLE limit_orders ADD COLUMN IF NOT EXISTS bot_id UUID REFERENCES bot_states(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_limit_orders_bot ON limit_orders(bot_id);
