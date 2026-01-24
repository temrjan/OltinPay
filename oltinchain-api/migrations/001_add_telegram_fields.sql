-- Migration: Add Telegram fields to users table
-- Date: 2026-01-24
-- Description: Support Telegram Mini App authentication

-- Add Telegram fields
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS telegram_id BIGINT UNIQUE,
ADD COLUMN IF NOT EXISTS telegram_username VARCHAR(32),
ADD COLUMN IF NOT EXISTS telegram_first_name VARCHAR(64),
ADD COLUMN IF NOT EXISTS telegram_photo_url TEXT;

-- Index for fast lookup by telegram_username (case-insensitive search)
CREATE INDEX IF NOT EXISTS idx_users_telegram_username 
ON users(LOWER(telegram_username));

-- Index for lookup by telegram_id
CREATE INDEX IF NOT EXISTS idx_users_telegram_id 
ON users(telegram_id) WHERE telegram_id IS NOT NULL;

-- Comment
COMMENT ON COLUMN users.telegram_id IS 'Telegram user ID for Mini App auth';
COMMENT ON COLUMN users.telegram_username IS 'Telegram @username for transfers';
