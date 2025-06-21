-- ==================================================================
-- Anonymeme Database Initial Migration
-- Version: 001
-- Description: Initial schema creation with all core tables
-- Author: Lead Developer
-- Date: 2024-01-01
-- ==================================================================

-- Включение расширений PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ==================================================================
-- ENUMS
-- ==================================================================

-- Типы бондинг-кривых
CREATE TYPE curve_type AS ENUM (
    'Linear',
    'Exponential', 
    'Logarithmic',
    'Sigmoid',
    'ConstantProduct'
);

-- Типы DEX для листинга
CREATE TYPE dex_type AS ENUM (
    'Raydium',
    'Jupiter',
    'Orca',
    'Serum',
    'Meteora'
);

-- Статусы токена
CREATE TYPE token_status AS ENUM (
    'active',
    'graduated',
    'paused',
    'flagged',
    'burned'
);

-- Типы торговых операций
CREATE TYPE trade_type AS ENUM (
    'buy',
    'sell'
);

-- Роли пользователей
CREATE TYPE user_role AS ENUM (
    'user',
    'moderator',
    'admin',
    'super_admin'
);

-- Статусы пользователей
CREATE TYPE user_status AS ENUM (
    'active',
    'suspended',
    'banned',
    'pending',
    'deleted'
);

-- ==================================================================
-- ОСНОВНЫЕ ТАБЛИЦЫ
-- ==================================================================

-- Таблица пользователей
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Основные поля
    wallet_address VARCHAR(44) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE,
    email VARCHAR(255) UNIQUE,
    
    -- Статус и роль
    role user_role DEFAULT 'user' NOT NULL,
    status user_status DEFAULT 'active' NOT NULL,
    
    -- Профиль
    profile_image_url VARCHAR(500),
    bio TEXT,
    website VARCHAR(255),
    twitter_handle VARCHAR(50),
    telegram_handle VARCHAR(50),
    
    -- Статистика
    tokens_created INTEGER DEFAULT 0,
    total_volume_traded DECIMAL(20, 9) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    profitable_trades INTEGER DEFAULT 0,
    
    -- Репутация и рейтинги
    reputation_score REAL DEFAULT 50.0,
    creator_rating REAL DEFAULT 0.0,
    trader_rating REAL DEFAULT 0.0,
    
    -- Верификация
    is_verified BOOLEAN DEFAULT FALSE,
    kyc_completed BOOLEAN DEFAULT FALSE,
    kyc_completed_at TIMESTAMPTZ,
    
    -- Модерация
    warning_count INTEGER DEFAULT 0,
    ban_reason TEXT,
    banned_until TIMESTAMPTZ,
    banned_by_id UUID REFERENCES users(id),
    
    -- Активность
    last_login_at TIMESTAMPTZ,
    last_trade_at TIMESTAMPTZ,
    last_token_creation_at TIMESTAMPTZ,
    
    -- JSON поля для расширенных данных
    preferences JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    
    -- Временные метки
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    deleted_at TIMESTAMPTZ,
    
    -- Ограничения
    CONSTRAINT check_reputation_range CHECK (reputation_score >= 0 AND reputation_score <= 100),
    CONSTRAINT check_creator_rating_range CHECK (creator_rating >= 0 AND creator_rating <= 5),
    CONSTRAINT check_trader_rating_range CHECK (trader_rating >= 0 AND trader_rating <= 5),
    CONSTRAINT check_wallet_address_length CHECK (LENGTH(wallet_address) = 44)
);

-- Таблица токенов
CREATE TABLE tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Основная информация
    mint_address VARCHAR(44) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    description TEXT,
    image_url VARCHAR(500),
    metadata_uri VARCHAR(500),
    
    -- Создатель
    creator_id UUID NOT NULL REFERENCES users(id),
    
    -- Бондинг-кривая
    curve_type curve_type NOT NULL,
    initial_supply DECIMAL(20, 9) NOT NULL,
    current_supply DECIMAL(20, 9) NOT NULL,
    initial_price DECIMAL(20, 9) NOT NULL,
    current_price DECIMAL(20, 9) NOT NULL,
    
    -- Резервы
    sol_reserves DECIMAL(20, 9) DEFAULT 0,
    token_reserves DECIMAL(20, 9) NOT NULL,
    
    -- Рыночные данные
    market_cap DECIMAL(20, 9) DEFAULT 0,
    all_time_high_price DECIMAL(20, 9),
    all_time_high_mc DECIMAL(20, 9),
    
    -- Градация
    graduation_threshold DECIMAL(20, 9) NOT NULL,
    is_graduated BOOLEAN DEFAULT FALSE,
    graduated_at TIMESTAMPTZ,
    graduation_dex dex_type,
    
    -- Статистика торговли
    trade_count INTEGER DEFAULT 0,
    unique_traders INTEGER DEFAULT 0,
    holder_count INTEGER DEFAULT 0,
    volume_24h DECIMAL(20, 9) DEFAULT 0,
    volume_7d DECIMAL(20, 9) DEFAULT 0,
    volume_total DECIMAL(20, 9) DEFAULT 0,
    trades_24h INTEGER DEFAULT 0,
    
    -- Изменения цены
    price_change_1h REAL DEFAULT 0,
    price_change_24h REAL DEFAULT 0,
    price_change_7d REAL DEFAULT 0,
    
    -- Статус и модерация
    status token_status DEFAULT 'active' NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    is_flagged BOOLEAN DEFAULT FALSE,
    flag_reason TEXT,
    
    -- Социальные данные
    telegram_url VARCHAR(255),
    twitter_url VARCHAR(255),
    website_url VARCHAR(255),
    
    -- Безопасность
    security_score REAL DEFAULT 50.0,
    rug_pull_risk REAL DEFAULT 0.0,
    liquidity_locked BOOLEAN DEFAULT FALSE,
    
    -- Дополнительные данные
    tags JSONB DEFAULT '[]',
    bonding_curve_params JSONB,
    metadata JSONB DEFAULT '{}',
    
    -- Временные метки
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    -- Ограничения
    CONSTRAINT check_security_score_range CHECK (security_score >= 0 AND security_score <= 100),
    CONSTRAINT check_rug_pull_risk_range CHECK (rug_pull_risk >= 0 AND rug_pull_risk <= 100),
    CONSTRAINT check_positive_supply CHECK (initial_supply > 0),
    CONSTRAINT check_positive_price CHECK (initial_price > 0),
    CONSTRAINT check_mint_address_length CHECK (LENGTH(mint_address) = 44),
    CONSTRAINT check_symbol_length CHECK (LENGTH(symbol) <= 10 AND LENGTH(symbol) > 0)
);

-- Таблица торговых операций
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Основная информация
    transaction_signature VARCHAR(88) UNIQUE NOT NULL,
    
    -- Участники
    user_id UUID NOT NULL REFERENCES users(id),
    token_id UUID NOT NULL REFERENCES tokens(id),
    
    -- Детали сделки
    trade_type trade_type NOT NULL,
    sol_amount DECIMAL(20, 9) NOT NULL,
    token_amount DECIMAL(20, 9) NOT NULL,
    price_per_token DECIMAL(20, 9) NOT NULL,
    
    -- Slippage и комиссии
    expected_amount DECIMAL(20, 9),
    actual_slippage REAL,
    max_slippage REAL,
    platform_fee DECIMAL(20, 9),
    
    -- Состояние рынка на момент сделки
    market_cap_before DECIMAL(20, 9),
    market_cap_after DECIMAL(20, 9),
    price_impact REAL,
    
    -- P&L для пользователя
    realized_pnl DECIMAL(20, 9) DEFAULT 0,
    
    -- Статус
    is_successful BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    -- Дополнительные данные
    metadata JSONB DEFAULT '{}',
    
    -- Временные метки
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    -- Ограничения
    CONSTRAINT check_positive_sol_amount CHECK (sol_amount > 0),
    CONSTRAINT check_positive_token_amount CHECK (token_amount > 0),
    CONSTRAINT check_positive_price CHECK (price_per_token > 0),
    CONSTRAINT check_transaction_signature_length CHECK (LENGTH(transaction_signature) = 88)
);

-- Таблица истории цен
CREATE TABLE price_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    token_id UUID NOT NULL REFERENCES tokens(id),
    
    -- Данные свечи
    open_price DECIMAL(20, 9) NOT NULL,
    high_price DECIMAL(20, 9) NOT NULL,
    low_price DECIMAL(20, 9) NOT NULL,
    close_price DECIMAL(20, 9) NOT NULL,
    
    -- Объемы
    volume_sol DECIMAL(20, 9) DEFAULT 0,
    volume_tokens DECIMAL(20, 9) DEFAULT 0,
    trade_count INTEGER DEFAULT 0,
    
    -- Капитализация
    market_cap DECIMAL(20, 9),
    
    -- Временной интервал (в минутах: 1, 5, 15, 60, 240, 1440)
    interval_minutes INTEGER NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    
    -- Временные метки
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    -- Ограничения
    CONSTRAINT check_high_low_price CHECK (high_price >= low_price),
    CONSTRAINT check_positive_prices CHECK (open_price > 0 AND close_price > 0),
    CONSTRAINT check_valid_interval CHECK (interval_minutes IN (1, 5, 15, 60, 240, 1440)),
    CONSTRAINT uq_price_history_period UNIQUE (token_id, interval_minutes, period_start)
);

-- Таблица балансов пользователей
CREATE TABLE user_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    user_id UUID NOT NULL REFERENCES users(id),
    token_id UUID NOT NULL REFERENCES tokens(id),
    
    -- Баланс
    balance DECIMAL(20, 9) DEFAULT 0,
    
    -- Статистика
    total_bought DECIMAL(20, 9) DEFAULT 0,
    total_sold DECIMAL(20, 9) DEFAULT 0,
    avg_buy_price DECIMAL(20, 9),
    realized_pnl DECIMAL(20, 9) DEFAULT 0,
    
    -- Первая и последняя операция
    first_trade_at TIMESTAMPTZ,
    last_trade_at TIMESTAMPTZ,
    
    -- Временные метки
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    -- Ограничения
    CONSTRAINT check_non_negative_balance CHECK (balance >= 0),
    CONSTRAINT uq_user_token UNIQUE (user_id, token_id)
);

-- Таблица аналитических данных
CREATE TABLE analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Временной период
    date TIMESTAMPTZ NOT NULL,
    period_type VARCHAR(10) NOT NULL, -- 'day', 'hour'
    
    -- Общая статистика
    total_users INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    
    total_tokens INTEGER DEFAULT 0,
    new_tokens INTEGER DEFAULT 0,
    graduated_tokens INTEGER DEFAULT 0,
    
    total_trades INTEGER DEFAULT 0,
    total_volume DECIMAL(20, 9) DEFAULT 0,
    platform_fees DECIMAL(20, 9) DEFAULT 0,
    
    -- Временные метки
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    -- Ограничения
    CONSTRAINT check_period_type CHECK (period_type IN ('day', 'hour')),
    CONSTRAINT uq_analytics_period UNIQUE (date, period_type)
);

-- ==================================================================
-- ИНДЕКСЫ
-- ==================================================================

-- Индексы для users
CREATE INDEX idx_users_wallet_address ON users(wallet_address);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_reputation ON users(reputation_score);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_users_last_login ON users(last_login_at);

-- Индексы для tokens
CREATE INDEX idx_tokens_mint_address ON tokens(mint_address);
CREATE INDEX idx_tokens_creator_id ON tokens(creator_id);
CREATE INDEX idx_tokens_symbol ON tokens(symbol);
CREATE INDEX idx_tokens_status ON tokens(status);
CREATE INDEX idx_tokens_market_cap ON tokens(market_cap);
CREATE INDEX idx_tokens_volume_24h ON tokens(volume_24h);
CREATE INDEX idx_tokens_created_at ON tokens(created_at);
CREATE INDEX idx_tokens_curve_type ON tokens(curve_type);
CREATE INDEX idx_tokens_is_graduated ON tokens(is_graduated);
CREATE INDEX idx_tokens_name_trgm ON tokens USING gin(name gin_trgm_ops);
CREATE INDEX idx_tokens_symbol_trgm ON tokens USING gin(symbol gin_trgm_ops);

-- Индексы для trades
CREATE INDEX idx_trades_transaction_signature ON trades(transaction_signature);
CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_token_id ON trades(token_id);
CREATE INDEX idx_trades_trade_type ON trades(trade_type);
CREATE INDEX idx_trades_created_at ON trades(created_at);
CREATE INDEX idx_trades_sol_amount ON trades(sol_amount);
CREATE INDEX idx_trades_user_token ON trades(user_id, token_id);
CREATE INDEX idx_trades_token_created ON trades(token_id, created_at);

-- Индексы для price_history
CREATE INDEX idx_price_history_token_id ON price_history(token_id);
CREATE INDEX idx_price_history_period ON price_history(token_id, interval_minutes, period_start);
CREATE INDEX idx_price_history_time ON price_history(period_start);

-- Индексы для user_tokens
CREATE INDEX idx_user_tokens_user_id ON user_tokens(user_id);
CREATE INDEX idx_user_tokens_token_id ON user_tokens(token_id);
CREATE INDEX idx_user_tokens_balance ON user_tokens(balance);

-- Индексы для analytics
CREATE INDEX idx_analytics_date ON analytics(date);
CREATE INDEX idx_analytics_period ON analytics(period_type, date);

-- ==================================================================
-- ТРИГГЕРЫ ДЛЯ АВТОМАТИЧЕСКОГО ОБНОВЛЕНИЯ updated_at
-- ==================================================================

-- Функция для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггеры для всех таблиц
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tokens_updated_at BEFORE UPDATE ON tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trades_updated_at BEFORE UPDATE ON trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_price_history_updated_at BEFORE UPDATE ON price_history
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_tokens_updated_at BEFORE UPDATE ON user_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analytics_updated_at BEFORE UPDATE ON analytics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==================================================================
-- ФУНКЦИИ ДЛЯ РАСЧЕТА МЕТРИК
-- ==================================================================

-- Функция для расчета винрейта пользователя
CREATE OR REPLACE FUNCTION calculate_user_win_rate(user_uuid UUID)
RETURNS REAL AS $$
DECLARE
    total_trades_count INTEGER;
    profitable_trades_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_trades_count
    FROM trades 
    WHERE user_id = user_uuid AND is_successful = TRUE;
    
    IF total_trades_count = 0 THEN
        RETURN 0.0;
    END IF;
    
    SELECT COUNT(*) INTO profitable_trades_count
    FROM trades 
    WHERE user_id = user_uuid AND realized_pnl > 0 AND is_successful = TRUE;
    
    RETURN (profitable_trades_count::REAL / total_trades_count::REAL) * 100.0;
END;
$$ LANGUAGE plpgsql;

-- Функция для расчета прогресса токена до градации
CREATE OR REPLACE FUNCTION calculate_graduation_progress(token_uuid UUID)
RETURNS REAL AS $$
DECLARE
    current_mc DECIMAL(20, 9);
    graduation_threshold DECIMAL(20, 9);
BEGIN
    SELECT market_cap, tokens.graduation_threshold 
    INTO current_mc, graduation_threshold
    FROM tokens 
    WHERE id = token_uuid;
    
    IF graduation_threshold <= 0 THEN
        RETURN 0.0;
    END IF;
    
    RETURN LEAST((current_mc / graduation_threshold), 1.0);
END;
$$ LANGUAGE plpgsql;

-- ==================================================================
-- ПРЕДУСТАНОВЛЕННЫЕ ДАННЫЕ
-- ==================================================================

-- Создание супер-админа по умолчанию
INSERT INTO users (
    id,
    wallet_address,
    username,
    role,
    status,
    reputation_score,
    is_verified
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    '11111111111111111111111111111111111111111111',
    'system_admin',
    'super_admin',
    'active',
    100.0,
    TRUE
) ON CONFLICT (wallet_address) DO NOTHING;

-- ==================================================================
-- КОММЕНТАРИИ К ТАБЛИЦАМ
-- ==================================================================

COMMENT ON TABLE users IS 'Пользователи платформы';
COMMENT ON TABLE tokens IS 'Токены созданные на платформе';
COMMENT ON TABLE trades IS 'История торговых операций';
COMMENT ON TABLE price_history IS 'История цен токенов с разными интервалами';
COMMENT ON TABLE user_tokens IS 'Балансы токенов у пользователей';
COMMENT ON TABLE analytics IS 'Аналитические данные платформы';

-- ==================================================================
-- РАЗРЕШЕНИЯ
-- ==================================================================

-- Создание ролей для разных уровней доступа
CREATE ROLE anonymeme_readonly;
CREATE ROLE anonymeme_readwrite;
CREATE ROLE anonymeme_admin;

-- Права только на чтение
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anonymeme_readonly;

-- Права на чтение и запись
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO anonymeme_readwrite;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anonymeme_readwrite;

-- Админские права
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO anonymeme_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO anonymeme_admin;

-- ==================================================================
-- ЗАВЕРШЕНИЕ МИГРАЦИИ
-- ==================================================================

-- Лог успешного выполнения миграции
DO $$
BEGIN
    RAISE NOTICE 'Migration 001_initial_schema.sql completed successfully at %', NOW();
END $$;