-- ==================================================================
-- Anonymeme Database Migration 002
-- Version: 002
-- Description: Additional optimized indexes for performance
-- Author: Lead Developer
-- Date: 2024-01-01
-- ==================================================================

-- ==================================================================
-- СОСТАВНЫЕ ИНДЕКСЫ ДЛЯ ОПТИМИЗАЦИИ ЗАПРОСОВ
-- ==================================================================

-- Индексы для аналитики и dashboard
CREATE INDEX CONCURRENTLY idx_tokens_status_created_at ON tokens(status, created_at DESC) 
WHERE status = 'active';

CREATE INDEX CONCURRENTLY idx_tokens_market_cap_status ON tokens(market_cap DESC, status) 
WHERE status = 'active' AND market_cap > 0;

CREATE INDEX CONCURRENTLY idx_tokens_volume_24h_status ON tokens(volume_24h DESC, status) 
WHERE status = 'active' AND volume_24h > 0;

-- Индексы для пользовательских запросов
CREATE INDEX CONCURRENTLY idx_trades_user_created_at ON trades(user_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_trades_token_created_at ON trades(token_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_user_tokens_user_balance ON user_tokens(user_id, balance DESC) 
WHERE balance > 0;

-- Индексы для поиска и фильтрации
CREATE INDEX CONCURRENTLY idx_tokens_creator_created_at ON tokens(creator_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_tokens_curve_market_cap ON tokens(curve_type, market_cap DESC);

-- ==================================================================
-- ПАРТИАЛЬНЫЕ ИНДЕКСЫ ДЛЯ АКТИВНЫХ ЗАПИСЕЙ
-- ==================================================================

-- Индексы только для активных пользователей
CREATE INDEX CONCURRENTLY idx_users_active_reputation ON users(reputation_score DESC) 
WHERE status = 'active';

CREATE INDEX CONCURRENTLY idx_users_active_volume ON users(total_volume_traded DESC) 
WHERE status = 'active' AND total_volume_traded > 0;

-- Индексы только для успешных торгов
CREATE INDEX CONCURRENTLY idx_trades_successful_volume ON trades(sol_amount DESC, created_at DESC) 
WHERE is_successful = TRUE;

CREATE INDEX CONCURRENTLY idx_trades_successful_user_token ON trades(user_id, token_id, created_at DESC) 
WHERE is_successful = TRUE;

-- ==================================================================
-- ИНДЕКСЫ ДЛЯ ВРЕМЕННЫХ ЗАПРОСОВ
-- ==================================================================

-- Индексы для запросов "за последние N дней"
CREATE INDEX CONCURRENTLY idx_trades_recent_24h ON trades(created_at DESC) 
WHERE created_at > NOW() - INTERVAL '24 hours';

CREATE INDEX CONCURRENTLY idx_trades_recent_7d ON trades(created_at DESC) 
WHERE created_at > NOW() - INTERVAL '7 days';

CREATE INDEX CONCURRENTLY idx_users_recent_activity ON users(last_login_at DESC) 
WHERE last_login_at > NOW() - INTERVAL '30 days';

-- ==================================================================
-- JSON ИНДЕКСЫ ДЛЯ БЫСТРОГО ПОИСКА
-- ==================================================================

-- Индексы для поиска по тегам токенов
CREATE INDEX CONCURRENTLY idx_tokens_tags_gin ON tokens USING gin(tags);

-- Индексы для пользовательских предпочтений
CREATE INDEX CONCURRENTLY idx_users_preferences_gin ON users USING gin(preferences);

-- Индексы для метаданных
CREATE INDEX CONCURRENTLY idx_tokens_metadata_gin ON tokens USING gin(metadata);
CREATE INDEX CONCURRENTLY idx_trades_metadata_gin ON trades USING gin(metadata);

-- ==================================================================
-- ИНДЕКСЫ ДЛЯ АГРЕГАТНЫХ ЗАПРОСОВ
-- ==================================================================

-- Индексы для группировки по времени
CREATE INDEX CONCURRENTLY idx_trades_date_trunc_day ON trades(date_trunc('day', created_at), trade_type);
CREATE INDEX CONCURRENTLY idx_trades_date_trunc_hour ON trades(date_trunc('hour', created_at), trade_type);

-- Индексы для статистики по токенам
CREATE INDEX CONCURRENTLY idx_price_history_token_interval_time ON price_history(token_id, interval_minutes, period_start DESC);

-- ==================================================================
-- УНИКАЛЬНЫЕ ИНДЕКСЫ ДЛЯ ПРЕДОТВРАЩЕНИЯ ДУБЛИКАТОВ
-- ==================================================================

-- Уникальность email (игнорируя NULL)
CREATE UNIQUE INDEX CONCURRENTLY idx_users_email_unique ON users(email) 
WHERE email IS NOT NULL;

-- Уникальность username (игнорируя NULL)
CREATE UNIQUE INDEX CONCURRENTLY idx_users_username_unique ON users(username) 
WHERE username IS NOT NULL;

-- ==================================================================
-- ИНДЕКСЫ ДЛЯ БЕЗОПАСНОСТИ И МОДЕРАЦИИ
-- ==================================================================

-- Индексы для поиска подозрительной активности
CREATE INDEX CONCURRENTLY idx_users_warning_count ON users(warning_count DESC) 
WHERE warning_count > 0;

CREATE INDEX CONCURRENTLY idx_tokens_flagged ON tokens(is_flagged, flag_reason) 
WHERE is_flagged = TRUE;

CREATE INDEX CONCURRENTLY idx_trades_failed ON trades(created_at DESC, error_message) 
WHERE is_successful = FALSE;

-- ==================================================================
-- ОПТИМИЗИРОВАННЫЕ ПРЕДСТАВЛЕНИЯ
-- ==================================================================

-- Представление для активных токенов с расширенной информацией
CREATE VIEW active_tokens_extended AS
SELECT 
    t.*,
    u.username as creator_username,
    u.reputation_score as creator_reputation,
    CASE 
        WHEN t.graduation_threshold > 0 
        THEN (t.market_cap / t.graduation_threshold) 
        ELSE 0 
    END as graduation_progress,
    CASE 
        WHEN t.total_trades > 0 
        THEN (t.volume_24h / NULLIF(t.volume_total, 0)) * 100 
        ELSE 0 
    END as volume_24h_percent_of_total
FROM tokens t
JOIN users u ON t.creator_id = u.id
WHERE t.status = 'active'
  AND u.status = 'active';

-- Представление для статистики пользователей
CREATE VIEW user_stats_extended AS
SELECT 
    u.*,
    COALESCE(calculate_user_win_rate(u.id), 0) as calculated_win_rate,
    COUNT(DISTINCT ut.token_id) as unique_tokens_held,
    COALESCE(SUM(ut.balance * t.current_price), 0) as portfolio_value_estimate
FROM users u
LEFT JOIN user_tokens ut ON u.id = ut.user_id AND ut.balance > 0
LEFT JOIN tokens t ON ut.token_id = t.id
WHERE u.status = 'active'
GROUP BY u.id;

-- Представление для trending токенов
CREATE VIEW trending_tokens AS
SELECT 
    t.*,
    u.username as creator_username,
    ROW_NUMBER() OVER (ORDER BY t.volume_24h DESC) as volume_rank,
    ROW_NUMBER() OVER (ORDER BY t.market_cap DESC) as market_cap_rank,
    ROW_NUMBER() OVER (ORDER BY t.trades_24h DESC) as trades_rank
FROM tokens t
JOIN users u ON t.creator_id = u.id
WHERE t.status = 'active'
  AND t.volume_24h > 0
  AND u.status = 'active'
ORDER BY t.volume_24h DESC;

-- ==================================================================
-- ФУНКЦИИ ДЛЯ ПОДДЕРЖАНИЯ ПРОИЗВОДИТЕЛЬНОСТИ
-- ==================================================================

-- Функция для очистки старых данных price_history
CREATE OR REPLACE FUNCTION cleanup_old_price_history()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Удаляем данные старше 1 года для 1-минутных интервалов
    DELETE FROM price_history 
    WHERE interval_minutes = 1 
      AND period_start < NOW() - INTERVAL '1 year';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Удаляем данные старше 2 лет для 5-минутных интервалов
    DELETE FROM price_history 
    WHERE interval_minutes = 5 
      AND period_start < NOW() - INTERVAL '2 years';
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Функция для обновления агрегированной статистики
CREATE OR REPLACE FUNCTION update_token_statistics()
RETURNS VOID AS $$
BEGIN
    -- Обновляем статистику торговли за 24 часа
    UPDATE tokens SET
        volume_24h = COALESCE((
            SELECT SUM(sol_amount) 
            FROM trades 
            WHERE token_id = tokens.id 
              AND created_at > NOW() - INTERVAL '24 hours'
              AND is_successful = TRUE
        ), 0),
        trades_24h = COALESCE((
            SELECT COUNT(*) 
            FROM trades 
            WHERE token_id = tokens.id 
              AND created_at > NOW() - INTERVAL '24 hours'
              AND is_successful = TRUE
        ), 0),
        unique_traders = COALESCE((
            SELECT COUNT(DISTINCT user_id) 
            FROM trades 
            WHERE token_id = tokens.id 
              AND is_successful = TRUE
        ), 0),
        holder_count = COALESCE((
            SELECT COUNT(*) 
            FROM user_tokens 
            WHERE token_id = tokens.id 
              AND balance > 0
        ), 0)
    WHERE status = 'active';
    
    -- Обновляем статистику пользователей
    UPDATE users SET
        total_volume_traded = COALESCE((
            SELECT SUM(sol_amount) 
            FROM trades 
            WHERE user_id = users.id 
              AND is_successful = TRUE
        ), 0),
        total_trades = COALESCE((
            SELECT COUNT(*) 
            FROM trades 
            WHERE user_id = users.id 
              AND is_successful = TRUE
        ), 0),
        profitable_trades = COALESCE((
            SELECT COUNT(*) 
            FROM trades 
            WHERE user_id = users.id 
              AND realized_pnl > 0 
              AND is_successful = TRUE
        ), 0)
    WHERE status = 'active';
END;
$$ LANGUAGE plpgsql;

-- ==================================================================
-- ЗАДАНИЯ ДЛЯ АВТОМАТИЧЕСКОГО ОБСЛУЖИВАНИЯ
-- ==================================================================

-- Создание расширения для планировщика задач (если доступно)
-- CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Задание для ежедневной очистки старых данных
-- SELECT cron.schedule('cleanup-old-data', '0 2 * * *', 'SELECT cleanup_old_price_history();');

-- Задание для обновления статистики каждые 10 минут
-- SELECT cron.schedule('update-stats', '*/10 * * * *', 'SELECT update_token_statistics();');

-- ==================================================================
-- ЗАВЕРШЕНИЕ МИГРАЦИИ
-- ==================================================================

-- Анализ таблиц для оптимизации планировщика запросов
ANALYZE users;
ANALYZE tokens;
ANALYZE trades;
ANALYZE price_history;
ANALYZE user_tokens;
ANALYZE analytics;

-- Лог завершения миграции
DO $$
BEGIN
    RAISE NOTICE 'Migration 002_additional_indexes.sql completed successfully at %', NOW();
    RAISE NOTICE 'Total indexes created: 25+';
    RAISE NOTICE 'Views created: 3';
    RAISE NOTICE 'Functions created: 3';
END $$;