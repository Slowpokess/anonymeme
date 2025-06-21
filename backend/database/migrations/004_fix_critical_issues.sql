-- ==================================================================
-- Anonymeme Database Migration 004
-- Version: 004
-- Description: Исправление критических проблем после аудита
-- Author: Lead Developer
-- Date: 2024-01-01
-- ==================================================================

-- ==================================================================
-- ИСПРАВЛЕНИЕ ФУНКЦИИ RATE LIMITING
-- ==================================================================

-- Удаление старой некорректной функции
DROP FUNCTION IF EXISTS check_rate_limit(VARCHAR(100), VARCHAR(20), VARCHAR(200), INTEGER, INTEGER);

-- Новая исправленная функция rate limiting
CREATE OR REPLACE FUNCTION check_rate_limit(
    p_identifier VARCHAR(100),
    p_identifier_type VARCHAR(20),
    p_endpoint VARCHAR(200),
    p_max_requests INTEGER,
    p_window_seconds INTEGER
)
RETURNS BOOLEAN AS $$
DECLARE
    current_window_start TIMESTAMPTZ;
    current_requests INTEGER := 0;
    is_blocked BOOLEAN := FALSE;
    blocked_until_time TIMESTAMPTZ;
BEGIN
    -- Безопасное вычисление начала окна
    current_window_start := date_trunc('minute', NOW()) - 
                           (EXTRACT(EPOCH FROM date_trunc('minute', NOW()))::INTEGER / 60 % (p_window_seconds / 60)) * INTERVAL '1 minute';
    
    -- Проверяем существующий лимит с блокировкой строки
    SELECT 
        COALESCE(requests_count, 0), 
        COALESCE(is_blocked, FALSE),
        blocked_until
    INTO current_requests, is_blocked, blocked_until_time
    FROM rate_limits
    WHERE identifier = p_identifier
      AND identifier_type = p_identifier_type
      AND endpoint = p_endpoint
      AND window_start = current_window_start
    FOR UPDATE;
    
    -- Проверяем активную блокировку
    IF is_blocked AND (blocked_until_time IS NULL OR blocked_until_time > NOW()) THEN
        RETURN FALSE;
    END IF;
    
    -- Если записи нет, создаем новую
    IF NOT FOUND THEN
        INSERT INTO rate_limits (
            identifier, identifier_type, endpoint,
            requests_count, window_start, window_duration_seconds, max_requests,
            is_blocked, blocked_until
        ) VALUES (
            p_identifier, p_identifier_type, p_endpoint,
            1, current_window_start, p_window_seconds, p_max_requests,
            FALSE, NULL
        );
        RETURN TRUE;
    END IF;
    
    -- Сброс блокировки если истекла
    IF is_blocked AND blocked_until_time IS NOT NULL AND blocked_until_time <= NOW() THEN
        UPDATE rate_limits
        SET is_blocked = FALSE,
            blocked_until = NULL,
            requests_count = 0
        WHERE identifier = p_identifier
          AND identifier_type = p_identifier_type
          AND endpoint = p_endpoint
          AND window_start = current_window_start;
        current_requests := 0;
        is_blocked := FALSE;
    END IF;
    
    -- Увеличиваем счетчик
    UPDATE rate_limits
    SET requests_count = requests_count + 1,
        updated_at = NOW()
    WHERE identifier = p_identifier
      AND identifier_type = p_identifier_type
      AND endpoint = p_endpoint
      AND window_start = current_window_start;
    
    -- Проверяем превышение лимита
    IF current_requests + 1 > p_max_requests THEN
        -- Блокируем на время окна
        UPDATE rate_limits
        SET is_blocked = TRUE,
            blocked_until = NOW() + (p_window_seconds || ' seconds')::INTERVAL
        WHERE identifier = p_identifier
          AND identifier_type = p_identifier_type
          AND endpoint = p_endpoint
          AND window_start = current_window_start;
        
        RETURN FALSE;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- ==================================================================
-- ДОБАВЛЕНИЕ НЕДОСТАЮЩИХ ИНДЕКСОВ
-- ==================================================================

-- Индекс для JSON поиска по тегам токенов
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tokens_tags_gin 
ON tokens USING gin(tags) WHERE tags IS NOT NULL;

-- Составной индекс для истории торгов пользователя
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_user_created_desc 
ON trades(user_id, created_at DESC) WHERE is_successful = TRUE;

-- Индекс для быстрого поиска активных токенов по капитализации
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tokens_active_market_cap 
ON tokens(market_cap DESC) WHERE status = 'active' AND market_cap > 0;

-- Индекс для поиска подозрительной активности
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_suspicious_activity_unresolved 
ON suspicious_activity(created_at DESC) WHERE status = 'pending';

-- ==================================================================
-- УЛУЧШЕНИЕ БЕЗОПАСНОСТИ
-- ==================================================================

-- Функция для автоматической блокировки при неудачных попытках входа
CREATE OR REPLACE FUNCTION auto_block_failed_logins()
RETURNS TRIGGER AS $$
DECLARE
    failed_attempts INTEGER;
    block_duration INTERVAL := INTERVAL '1 hour';
BEGIN
    -- Подсчитываем неудачные попытки за последний час
    IF NEW.success = FALSE THEN
        SELECT COUNT(*) INTO failed_attempts
        FROM login_attempts
        WHERE ip_address = NEW.ip_address
          AND success = FALSE
          AND created_at > NOW() - INTERVAL '1 hour';
        
        -- Блокируем IP после 5 неудачных попыток
        IF failed_attempts >= 5 THEN
            PERFORM block_ip_address(
                NEW.ip_address,
                'Automated block: too many failed login attempts',
                'temporary',
                1, -- 1 час
                NULL -- системная блокировка
            );
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер для автоматической блокировки
DROP TRIGGER IF EXISTS trigger_auto_block_failed_logins ON login_attempts;
CREATE TRIGGER trigger_auto_block_failed_logins
    AFTER INSERT ON login_attempts
    FOR EACH ROW EXECUTE FUNCTION auto_block_failed_logins();

-- ==================================================================
-- УЛУЧШЕНИЕ ФУНКЦИЙ ВАЛИДАЦИИ
-- ==================================================================

-- Исправленная функция логирования с валидацией
CREATE OR REPLACE FUNCTION log_user_action(
    p_user_id UUID,
    p_action VARCHAR(100),
    p_resource_type VARCHAR(50),
    p_resource_id UUID DEFAULT NULL,
    p_old_values JSONB DEFAULT NULL,
    p_new_values JSONB DEFAULT NULL,
    p_ip_address INET DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    log_id UUID;
BEGIN
    -- Валидация входных параметров
    IF p_user_id IS NULL OR p_action IS NULL OR p_resource_type IS NULL THEN
        RAISE EXCEPTION 'Required parameters cannot be NULL';
    END IF;
    
    -- Валидация длины строк
    IF LENGTH(p_action) > 100 OR LENGTH(p_resource_type) > 50 THEN
        RAISE EXCEPTION 'String parameters exceed maximum length';
    END IF;
    
    -- Санитизация user_agent
    IF p_user_agent IS NOT NULL AND LENGTH(p_user_agent) > 1000 THEN
        p_user_agent := LEFT(p_user_agent, 1000);
    END IF;
    
    INSERT INTO audit_log (
        user_id, action, resource_type, resource_id,
        old_values, new_values, ip_address, user_agent
    ) VALUES (
        p_user_id, p_action, p_resource_type, p_resource_id,
        p_old_values, p_new_values, p_ip_address, p_user_agent
    ) RETURNING id INTO log_id;
    
    RETURN log_id;
END;
$$ LANGUAGE plpgsql;

-- ==================================================================
-- ДОБАВЛЕНИЕ АВТОМАТИЧЕСКОЙ ОЧИСТКИ
-- ==================================================================

-- Функция для очистки старых записей rate_limits
CREATE OR REPLACE FUNCTION cleanup_rate_limits()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Удаляем записи старше 7 дней
    DELETE FROM rate_limits 
    WHERE window_start < NOW() - INTERVAL '7 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Сбрасываем старые блокировки
    UPDATE rate_limits 
    SET is_blocked = FALSE, blocked_until = NULL
    WHERE is_blocked = TRUE 
      AND blocked_until IS NOT NULL 
      AND blocked_until < NOW();
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ==================================================================
-- МАТЕРИАЛИЗОВАННЫЕ ПРЕДСТАВЛЕНИЯ ДЛЯ ПРОИЗВОДИТЕЛЬНОСТИ
-- ==================================================================

-- Материализованное представление для статистики токенов
CREATE MATERIALIZED VIEW mv_token_stats AS
SELECT 
    t.id,
    t.symbol,
    t.name,
    t.market_cap,
    t.volume_24h,
    t.trades_24h,
    COUNT(DISTINCT tr.user_id) as unique_traders_24h,
    COUNT(DISTINCT ut.user_id) as current_holders,
    COALESCE(AVG(tr.price_per_token), 0) as avg_price_24h
FROM tokens t
LEFT JOIN trades tr ON t.id = tr.token_id 
    AND tr.created_at > NOW() - INTERVAL '24 hours'
    AND tr.is_successful = TRUE
LEFT JOIN user_tokens ut ON t.id = ut.token_id 
    AND ut.balance > 0
WHERE t.status = 'active'
GROUP BY t.id, t.symbol, t.name, t.market_cap, t.volume_24h, t.trades_24h;

-- Индекс для материализованного представления
CREATE UNIQUE INDEX idx_mv_token_stats_id ON mv_token_stats(id);
CREATE INDEX idx_mv_token_stats_market_cap ON mv_token_stats(market_cap DESC);
CREATE INDEX idx_mv_token_stats_volume ON mv_token_stats(volume_24h DESC);

-- Функция для обновления материализованного представления
CREATE OR REPLACE FUNCTION refresh_token_stats()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_token_stats;
END;
$$ LANGUAGE plpgsql;

-- ==================================================================
-- ИСПРАВЛЕНИЕ ТИПОВ ДАННЫХ ДЛЯ ФИНАНСОВЫХ ПОЛЕЙ
-- ==================================================================

-- Изменение типов для более точного хранения финансовых данных
ALTER TABLE users 
    ALTER COLUMN reputation_score TYPE DECIMAL(5,2),
    ALTER COLUMN creator_rating TYPE DECIMAL(3,2),
    ALTER COLUMN trader_rating TYPE DECIMAL(3,2);

-- Обновляем ограничения
ALTER TABLE users DROP CONSTRAINT IF EXISTS check_reputation_range;
ALTER TABLE users ADD CONSTRAINT check_reputation_range 
    CHECK (reputation_score >= 0 AND reputation_score <= 100);

ALTER TABLE users DROP CONSTRAINT IF EXISTS check_creator_rating_range;
ALTER TABLE users ADD CONSTRAINT check_creator_rating_range 
    CHECK (creator_rating >= 0 AND creator_rating <= 5);

ALTER TABLE users DROP CONSTRAINT IF EXISTS check_trader_rating_range;
ALTER TABLE users ADD CONSTRAINT check_trader_rating_range 
    CHECK (trader_rating >= 0 AND trader_rating <= 5);

-- ==================================================================
-- ДОБАВЛЕНИЕ ШИФРОВАНИЯ ДЛЯ ЧУВСТВИТЕЛЬНЫХ ДАННЫХ
-- ==================================================================

-- Включение расширения для шифрования
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Функция для шифрования email
CREATE OR REPLACE FUNCTION encrypt_email(email_text TEXT)
RETURNS TEXT AS $$
BEGIN
    IF email_text IS NULL OR email_text = '' THEN
        RETURN NULL;
    END IF;
    RETURN encode(encrypt(email_text::bytea, 'anonymeme_secret_key', 'aes'), 'base64');
END;
$$ LANGUAGE plpgsql;

-- Функция для расшифровки email
CREATE OR REPLACE FUNCTION decrypt_email(encrypted_email TEXT)
RETURNS TEXT AS $$
BEGIN
    IF encrypted_email IS NULL OR encrypted_email = '' THEN
        RETURN NULL;
    END IF;
    RETURN convert_from(decrypt(decode(encrypted_email, 'base64'), 'anonymeme_secret_key', 'aes'), 'UTF8');
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- ==================================================================
-- ДОБАВЛЕНИЕ МОНИТОРИНГА ПРОИЗВОДИТЕЛЬНОСТИ
-- ==================================================================

-- Функция для получения статистики производительности
CREATE OR REPLACE FUNCTION get_performance_stats()
RETURNS TABLE(
    active_connections INTEGER,
    idle_connections INTEGER,
    total_queries BIGINT,
    cache_hit_ratio NUMERIC,
    avg_query_time NUMERIC,
    slowest_queries TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT count(*)::INTEGER FROM pg_stat_activity WHERE state = 'active'),
        (SELECT count(*)::INTEGER FROM pg_stat_activity WHERE state = 'idle'),
        (SELECT COALESCE(sum(calls), 0) FROM pg_stat_statements),
        (SELECT ROUND(100.0 * sum(blks_hit) / NULLIF(sum(blks_hit) + sum(blks_read), 0), 2)
         FROM pg_stat_database WHERE datname = current_database()),
        (SELECT ROUND(COALESCE(avg(mean_time), 0), 2) FROM pg_stat_statements),
        (SELECT array_agg(substring(query, 1, 100) || '...') 
         FROM pg_stat_statements 
         WHERE calls > 10 
         ORDER BY mean_time DESC 
         LIMIT 5);
END;
$$ LANGUAGE plpgsql;

-- ==================================================================
-- ЗАВЕРШЕНИЕ МИГРАЦИИ
-- ==================================================================

-- Обновление статистики после изменений
ANALYZE;

-- Лог завершения миграции
DO $$
BEGIN
    RAISE NOTICE 'Migration 004_fix_critical_issues.sql completed successfully at %', NOW();
    RAISE NOTICE 'Fixed critical issues:';
    RAISE NOTICE '- Rate limiting function improved';
    RAISE NOTICE '- Missing indexes added';
    RAISE NOTICE '- Security enhancements implemented';
    RAISE NOTICE '- Data types optimized';
    RAISE NOTICE '- Performance monitoring added';
END $$;