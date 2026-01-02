-- Migration: Create Active Traders tables
-- Date: 2026-01-02

-- Active bot queue for trade coordination
CREATE TABLE IF NOT EXISTS active_bot_queue (
    id SERIAL PRIMARY KEY,
    bot_id UUID NOT NULL REFERENCES bot_states(user_id),
    side VARCHAR(10) NOT NULL CHECK (side IN ('red', 'green')),
    position INT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_trade_at TIMESTAMP,
    trades_count INT DEFAULT 0,
    total_volume DECIMAL(20,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(bot_id)
);

CREATE INDEX IF NOT EXISTS idx_active_queue_side ON active_bot_queue(side);
CREATE INDEX IF NOT EXISTS idx_active_queue_position ON active_bot_queue(position);

-- Add bot_type to bot_states to distinguish MM from Active
ALTER TABLE bot_states ADD COLUMN IF NOT EXISTS bot_type VARCHAR(20) DEFAULT 'market_maker';

-- Update existing bots as market_makers
UPDATE bot_states SET bot_type = 'market_maker' WHERE bot_type IS NULL;

COMMENT ON TABLE active_bot_queue IS 'Queue coordination for Active Trader bots';
