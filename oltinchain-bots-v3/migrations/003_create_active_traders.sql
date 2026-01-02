-- Create 20 Active Trader bots (10 RED sellers, 10 GREEN buyers)
-- Run once to set up all bots with their balances

-- Get current oracle price (approximate)
DO $$
DECLARE
    oracle_price DECIMAL(20,8) := 530;  -- Will use orderbook if available
    capital_usd DECIMAL(20,8) := 5000;
    oltin_amount DECIMAL(20,8);
    new_user_id UUID;
    new_phone VARCHAR(20);
    new_side VARCHAR(10);
    i INT;
BEGIN
    -- Try to get actual price from last trade
    SELECT price INTO oracle_price FROM trades ORDER BY created_at DESC LIMIT 1;
    IF oracle_price IS NULL THEN oracle_price := 530; END IF;

    oltin_amount := capital_usd / oracle_price;

    RAISE NOTICE 'Creating Active Traders with oracle price: %, OLTIN per bot: %', oracle_price, oltin_amount;

    FOR i IN 0..19 LOOP
        new_user_id := gen_random_uuid();
        new_phone := '+99890123452' || i;

        -- Alternate: 0,2,4,6,8,10,12,14,16,18 = RED (sellers)
        --           1,3,5,7,9,11,13,15,17,19 = GREEN (buyers)
        IF i % 2 = 0 THEN
            new_side := 'red';
        ELSE
            new_side := 'green';
        END IF;

        -- Create user (password: bot123 hashed with bcrypt)
        INSERT INTO users (id, phone, password_hash, kyc_level, is_active, is_bot, created_at, updated_at)
        VALUES (
            new_user_id,
            new_phone,
            '$2b$12$rj4CN2DhFKybhnfDIqY/WuXIpWzx2.hqmnCAmt.wXQOHqNkQUFA.K', -- bot123
            0,
            true,
            true,
            NOW(),
            NOW()
        )
        ON CONFLICT (phone) DO NOTHING;

        -- Create bot_states entry
        INSERT INTO bot_states (user_id, bot_number, level, state, bot_type, created_at, updated_at, state_changed_at)
        VALUES (
            new_user_id,
            21 + i,  -- Bot numbers 21-40
            1,       -- Level (required by constraint, not used)
            'idle',
            'active_trader',
            NOW(),
            NOW(),
            NOW()
        )
        ON CONFLICT (user_id) DO NOTHING;

        -- Create active_bot_queue entry
        INSERT INTO active_bot_queue (bot_id, side, position)
        VALUES (
            new_user_id,
            new_side,
            (i / 2) + 1  -- Position 1-10
        )
        ON CONFLICT (bot_id) DO NOTHING;

        -- Create balances
        IF new_side = 'red' THEN
            -- RED bots get OLTIN to sell
            INSERT INTO balances (id, user_id, asset, available, locked, updated_at)
            VALUES (gen_random_uuid(), new_user_id, 'OLTIN', oltin_amount, 0, NOW())
            ON CONFLICT (user_id, asset) DO NOTHING;

            INSERT INTO balances (id, user_id, asset, available, locked, updated_at)
            VALUES (gen_random_uuid(), new_user_id, 'USD', 0, 0, NOW())
            ON CONFLICT (user_id, asset) DO NOTHING;
        ELSE
            -- GREEN bots get USD to buy
            INSERT INTO balances (id, user_id, asset, available, locked, updated_at)
            VALUES (gen_random_uuid(), new_user_id, 'USD', capital_usd, 0, NOW())
            ON CONFLICT (user_id, asset) DO NOTHING;

            INSERT INTO balances (id, user_id, asset, available, locked, updated_at)
            VALUES (gen_random_uuid(), new_user_id, 'OLTIN', 0, 0, NOW())
            ON CONFLICT (user_id, asset) DO NOTHING;
        END IF;

        RAISE NOTICE 'Created: % (%) pos=%', new_phone, new_side, (i / 2) + 1;
    END LOOP;

    RAISE NOTICE 'Done! Created 20 Active Trader bots';
END $$;

-- Verify
SELECT
    u.phone,
    aq.side,
    aq.position,
    bs.bot_type,
    (SELECT available FROM balances WHERE user_id = u.id AND asset = 'USD') as usd,
    (SELECT available FROM balances WHERE user_id = u.id AND asset = 'OLTIN') as oltin
FROM users u
JOIN bot_states bs ON bs.user_id = u.id
JOIN active_bot_queue aq ON aq.bot_id = u.id
WHERE bs.bot_type = 'active_trader'
ORDER BY aq.position, aq.side;
