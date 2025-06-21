-- ==================================================================
-- Anonymeme Database Migration 003
-- Version: 003
-- Description: Security enhancements and audit trail
-- Author: Lead Developer
-- Date: 2024-01-01
-- ==================================================================

-- ==================================================================
-- АУДИТ И ЛОГИРОВАНИЕ
-- ==================================================================

-- Таблица для аудита действий пользователей
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Основная информация
    user_id UUID REFERENCES users(id),
    admin_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    
    -- Детали действия
    old_values JSONB,
    new_values JSONB,
    changes JSONB,
    
    -- Контекст
    ip_address INET,
    user_agent TEXT,
    request_id VARCHAR(100),
    session_id VARCHAR(100),
    
    -- Метаданные
    severity VARCHAR(20) DEFAULT 'info',
    status VARCHAR(20) DEFAULT 'success',
    error_message TEXT,
    
    -- Временные метки
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Таблица для логов безопасности
CREATE TABLE security_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Событие безопасности
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL, -- low, medium, high, critical
    
    -- Источник
    source_ip INET,
    source_country VARCHAR(2),
    user_id UUID REFERENCES users(id),
    
    -- Детали события
    details JSONB DEFAULT '{}',
    rule_triggered VARCHAR(100),
    
    -- Обработка
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolved_by_id UUID REFERENCES users(id),
    resolution_notes TEXT,
    
    -- Блокировка
    action_taken VARCHAR(50), -- none, warn, suspend, block_ip, block_user
    blocked_until TIMESTAMPTZ,
    
    -- Временные метки
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Таблица для отслеживания подозрительной активности
CREATE TABLE suspicious_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Субъект
    user_id UUID REFERENCES users(id),
    ip_address INET,
    fingerprint VARCHAR(100),
    
    -- Тип активности
    activity_type VARCHAR(50) NOT NULL,
    risk_score INTEGER DEFAULT 0, -- 0-100
    
    -- Детали
    details JSONB DEFAULT '{}',
    patterns_matched TEXT[],
    
    -- Статус
    status VARCHAR(20) DEFAULT 'pending', -- pending, reviewed, false_positive, confirmed
    reviewed_by_id UUID REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    notes TEXT,
    
    -- Временные метки
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ==================================================================
-- ОГРАНИЧЕНИЯ СКОРОСТИ И ЛИМИТЫ
-- ==================================================================

-- Таблица для rate limiting
CREATE TABLE rate_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Идентификатор (IP, пользователь, API ключ)
    identifier VARCHAR(100) NOT NULL,
    identifier_type VARCHAR(20) NOT NULL, -- ip, user, api_key
    
    -- Endpoint/действие
    endpoint VARCHAR(200) NOT NULL,
    
    -- Лимиты
    requests_count INTEGER DEFAULT 0,
    window_start TIMESTAMPTZ NOT NULL,
    window_duration_seconds INTEGER NOT NULL,
    max_requests INTEGER NOT NULL,
    
    -- Блокировка
    is_blocked BOOLEAN DEFAULT FALSE,
    blocked_until TIMESTAMPTZ,
    
    -- Временные метки
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ==================================================================
-- БЛОКИРОВКА IP И ГЕОЛОКАЦИЯ
-- ==================================================================

-- Таблица заблокированных IP адресов
CREATE TABLE blocked_ips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- IP информация
    ip_address INET NOT NULL UNIQUE,
    ip_range CIDR,
    country VARCHAR(2),
    
    -- Причина блокировки
    reason VARCHAR(200) NOT NULL,
    block_type VARCHAR(20) NOT NULL, -- temporary, permanent, suspicious
    
    -- Детали
    blocked_by_id UUID REFERENCES users(id),
    auto_blocked BOOLEAN DEFAULT FALSE,
    violation_count INTEGER DEFAULT 1,
    
    -- Время блокировки
    blocked_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMPTZ,
    
    -- Разблокировка
    is_active BOOLEAN DEFAULT TRUE,
    unblocked_at TIMESTAMPTZ,
    unblocked_by_id UUID REFERENCES users(id),
    unblock_reason TEXT
);

-- Таблица для whitelist IP адресов
CREATE TABLE whitelisted_ips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    ip_address INET NOT NULL UNIQUE,
    ip_range CIDR,
    
    -- Описание
    description VARCHAR(200),
    added_by_id UUID NOT NULL REFERENCES users(id),
    
    -- Временные метки
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ==================================================================
-- СЕССИИ И АУТЕНТИФИКАЦИЯ
-- ==================================================================

-- Таблица активных сессий
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Токен информация
    session_token VARCHAR(255) NOT NULL UNIQUE,
    refresh_token VARCHAR(255),
    
    -- Контекст
    ip_address INET,
    user_agent TEXT,
    device_fingerprint VARCHAR(100),
    
    -- География
    country VARCHAR(2),
    city VARCHAR(100),
    
    -- Статус
    is_active BOOLEAN DEFAULT TRUE,
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    
    -- Время жизни
    expires_at TIMESTAMPTZ NOT NULL,
    
    -- Временные метки
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Таблица неудачных попыток входа
CREATE TABLE login_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Попытка входа
    wallet_address VARCHAR(44),
    ip_address INET,
    user_agent TEXT,
    
    -- Результат
    success BOOLEAN DEFAULT FALSE,
    error_reason VARCHAR(100),
    
    -- Географическая информация
    country VARCHAR(2),
    
    -- Временные метки
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ==================================================================
-- ИНДЕКСЫ ДЛЯ БЕЗОПАСНОСТИ
-- ==================================================================

-- Индексы для audit_log
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_admin_id ON audit_log(admin_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at DESC);
CREATE INDEX idx_audit_log_ip_address ON audit_log(ip_address);

-- Индексы для security_log
CREATE INDEX idx_security_log_event_type ON security_log(event_type);
CREATE INDEX idx_security_log_severity ON security_log(severity);
CREATE INDEX idx_security_log_source_ip ON security_log(source_ip);
CREATE INDEX idx_security_log_user_id ON security_log(user_id);
CREATE INDEX idx_security_log_created_at ON security_log(created_at DESC);
CREATE INDEX idx_security_log_unresolved ON security_log(is_resolved, severity) WHERE is_resolved = FALSE;

-- Индексы для suspicious_activity
CREATE INDEX idx_suspicious_activity_user_id ON suspicious_activity(user_id);
CREATE INDEX idx_suspicious_activity_ip_address ON suspicious_activity(ip_address);
CREATE INDEX idx_suspicious_activity_type ON suspicious_activity(activity_type);
CREATE INDEX idx_suspicious_activity_risk_score ON suspicious_activity(risk_score DESC);
CREATE INDEX idx_suspicious_activity_status ON suspicious_activity(status);
CREATE INDEX idx_suspicious_activity_created_at ON suspicious_activity(created_at DESC);

-- Индексы для rate_limits
CREATE INDEX idx_rate_limits_identifier ON rate_limits(identifier, identifier_type);
CREATE INDEX idx_rate_limits_endpoint ON rate_limits(endpoint);
CREATE INDEX idx_rate_limits_window ON rate_limits(window_start, window_duration_seconds);
CREATE INDEX idx_rate_limits_blocked ON rate_limits(is_blocked, blocked_until) WHERE is_blocked = TRUE;

-- Индексы для blocked_ips
CREATE INDEX idx_blocked_ips_ip_address ON blocked_ips(ip_address);
CREATE INDEX idx_blocked_ips_active ON blocked_ips(is_active, expires_at) WHERE is_active = TRUE;
CREATE INDEX idx_blocked_ips_country ON blocked_ips(country);

-- Индексы для user_sessions
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_user_sessions_active ON user_sessions(is_active, expires_at) WHERE is_active = TRUE;
CREATE INDEX idx_user_sessions_last_activity ON user_sessions(last_activity DESC);
CREATE INDEX idx_user_sessions_ip_address ON user_sessions(ip_address);

-- Индексы для login_attempts
CREATE INDEX idx_login_attempts_wallet_address ON login_attempts(wallet_address);
CREATE INDEX idx_login_attempts_ip_address ON login_attempts(ip_address);
CREATE INDEX idx_login_attempts_success ON login_attempts(success, created_at);
CREATE INDEX idx_login_attempts_failed_recent ON login_attempts(ip_address, created_at) WHERE success = FALSE AND created_at > NOW() - INTERVAL '1 hour';

-- ==================================================================
-- ФУНКЦИИ БЕЗОПАСНОСТИ
-- ==================================================================

-- Функция для логирования действий пользователей
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

-- Функция для логирования событий безопасности
CREATE OR REPLACE FUNCTION log_security_event(
    p_event_type VARCHAR(50),
    p_severity VARCHAR(20),
    p_source_ip INET,
    p_user_id UUID DEFAULT NULL,
    p_details JSONB DEFAULT '{}',
    p_action_taken VARCHAR(50) DEFAULT 'none'
)
RETURNS UUID AS $$
DECLARE
    log_id UUID;
BEGIN
    INSERT INTO security_log (
        event_type, severity, source_ip, user_id, details, action_taken
    ) VALUES (
        p_event_type, p_severity, p_source_ip, p_user_id, p_details, p_action_taken
    ) RETURNING id INTO log_id;
    
    RETURN log_id;
END;
$$ LANGUAGE plpgsql;

-- Функция для проверки rate limit
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
    current_requests INTEGER;
    is_blocked BOOLEAN;
BEGIN
    -- Вычисляем начало текущего окна
    current_window_start := date_trunc('second', NOW()) - 
                           (EXTRACT(EPOCH FROM date_trunc('second', NOW()))::INTEGER % p_window_seconds) * INTERVAL '1 second';
    
    -- Проверяем существующий лимит
    SELECT requests_count, is_blocked INTO current_requests, is_blocked
    FROM rate_limits
    WHERE identifier = p_identifier
      AND identifier_type = p_identifier_type
      AND endpoint = p_endpoint
      AND window_start = current_window_start;
    
    -- Если записи нет, создаем новую
    IF NOT FOUND THEN
        INSERT INTO rate_limits (
            identifier, identifier_type, endpoint,
            requests_count, window_start, window_duration_seconds, max_requests
        ) VALUES (
            p_identifier, p_identifier_type, p_endpoint,
            1, current_window_start, p_window_seconds, p_max_requests
        );
        RETURN TRUE;
    END IF;
    
    -- Проверяем блокировку
    IF is_blocked AND NOW() < blocked_until THEN
        RETURN FALSE;
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
            blocked_until = current_window_start + (p_window_seconds || ' seconds')::INTERVAL
        WHERE identifier = p_identifier
          AND identifier_type = p_identifier_type
          AND endpoint = p_endpoint
          AND window_start = current_window_start;
        
        RETURN FALSE;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Функция для блокировки IP адреса
CREATE OR REPLACE FUNCTION block_ip_address(
    p_ip_address INET,
    p_reason VARCHAR(200),
    p_block_type VARCHAR(20) DEFAULT 'temporary',
    p_duration_hours INTEGER DEFAULT 24,
    p_blocked_by_id UUID DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    block_id UUID;
    expires_at TIMESTAMPTZ;
BEGIN
    -- Вычисляем время истечения
    IF p_block_type = 'permanent' THEN
        expires_at := NULL;
    ELSE
        expires_at := NOW() + (p_duration_hours || ' hours')::INTERVAL;
    END IF;
    
    -- Создаем или обновляем блокировку
    INSERT INTO blocked_ips (
        ip_address, reason, block_type, blocked_by_id, expires_at
    ) VALUES (
        p_ip_address, p_reason, p_block_type, p_blocked_by_id, expires_at
    )
    ON CONFLICT (ip_address) DO UPDATE SET
        reason = p_reason,
        block_type = p_block_type,
        blocked_by_id = p_blocked_by_id,
        expires_at = expires_at,
        is_active = TRUE,
        blocked_at = NOW(),
        violation_count = blocked_ips.violation_count + 1
    RETURNING id INTO block_id;
    
    -- Логируем событие безопасности
    PERFORM log_security_event(
        'ip_blocked',
        'medium',
        p_ip_address,
        NULL,
        json_build_object('reason', p_reason, 'duration_hours', p_duration_hours)::JSONB,
        'block_ip'
    );
    
    RETURN block_id;
END;
$$ LANGUAGE plpgsql;

-- Функция для проверки блокировки IP
CREATE OR REPLACE FUNCTION is_ip_blocked(p_ip_address INET)
RETURNS BOOLEAN AS $$
DECLARE
    is_blocked BOOLEAN DEFAULT FALSE;
BEGIN
    SELECT TRUE INTO is_blocked
    FROM blocked_ips
    WHERE ip_address = p_ip_address
      AND is_active = TRUE
      AND (expires_at IS NULL OR expires_at > NOW())
    LIMIT 1;
    
    RETURN COALESCE(is_blocked, FALSE);
END;
$$ LANGUAGE plpgsql;

-- ==================================================================
-- ТРИГГЕРЫ ДЛЯ АВТОМАТИЧЕСКОГО ЛОГИРОВАНИЯ
-- ==================================================================

-- Триггер для логирования изменений пользователей
CREATE OR REPLACE FUNCTION trigger_log_user_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        -- Логируем только значимые изменения
        IF OLD.status != NEW.status OR OLD.role != NEW.role OR OLD.is_verified != NEW.is_verified THEN
            PERFORM log_user_action(
                NEW.id,
                'user_updated',
                'user',
                NEW.id,
                row_to_json(OLD)::JSONB,
                row_to_json(NEW)::JSONB
            );
        END IF;
    ELSIF TG_OP = 'INSERT' THEN
        PERFORM log_user_action(
            NEW.id,
            'user_created',
            'user',
            NEW.id,
            NULL,
            row_to_json(NEW)::JSONB
        );
    END IF;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Триггер для логирования изменений токенов
CREATE OR REPLACE FUNCTION trigger_log_token_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF OLD.status != NEW.status OR OLD.is_flagged != NEW.is_flagged THEN
            PERFORM log_user_action(
                NEW.creator_id,
                'token_updated',
                'token',
                NEW.id,
                row_to_json(OLD)::JSONB,
                row_to_json(NEW)::JSONB
            );
        END IF;
    ELSIF TG_OP = 'INSERT' THEN
        PERFORM log_user_action(
            NEW.creator_id,
            'token_created',
            'token',
            NEW.id,
            NULL,
            row_to_json(NEW)::JSONB
        );
    END IF;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Установка триггеров
CREATE TRIGGER trigger_users_audit
    AFTER INSERT OR UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION trigger_log_user_changes();

CREATE TRIGGER trigger_tokens_audit
    AFTER INSERT OR UPDATE ON tokens
    FOR EACH ROW EXECUTE FUNCTION trigger_log_token_changes();

-- ==================================================================
-- АВТОМАТИЧЕСКАЯ ОЧИСТКА ЛОГОВ
-- ==================================================================

-- Функция для очистки старых логов
CREATE OR REPLACE FUNCTION cleanup_security_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Удаляем audit_log старше 2 лет
    DELETE FROM audit_log WHERE created_at < NOW() - INTERVAL '2 years';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Удаляем security_log старше 1 года (кроме критических)
    DELETE FROM security_log 
    WHERE created_at < NOW() - INTERVAL '1 year' 
      AND severity != 'critical';
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    -- Удаляем login_attempts старше 6 месяцев
    DELETE FROM login_attempts WHERE created_at < NOW() - INTERVAL '6 months';
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    -- Удаляем неактивные сессии старше 30 дней
    DELETE FROM user_sessions 
    WHERE is_active = FALSE 
      AND updated_at < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    -- Удаляем истекшие rate_limits старше 7 дней
    DELETE FROM rate_limits 
    WHERE window_start < NOW() - INTERVAL '7 days';
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ==================================================================
-- РОЛИ БЕЗОПАСНОСТИ
-- ==================================================================

-- Роль для аудиторов (только чтение логов)
CREATE ROLE anonymeme_auditor;
GRANT SELECT ON audit_log, security_log, suspicious_activity TO anonymeme_auditor;

-- Роль для службы безопасности
CREATE ROLE anonymeme_security;
GRANT SELECT, INSERT, UPDATE ON security_log, suspicious_activity, blocked_ips TO anonymeme_security;
GRANT EXECUTE ON FUNCTION log_security_event, block_ip_address, is_ip_blocked TO anonymeme_security;

-- ==================================================================
-- ЗАВЕРШЕНИЕ МИГРАЦИИ
-- ==================================================================

-- Создание начальных записей для мониторинга
INSERT INTO security_log (event_type, severity, source_ip, details) 
VALUES ('system_init', 'info', '127.0.0.1', '{"message": "Security system initialized"}'::JSONB);

-- Лог завершения миграции
DO $$
BEGIN
    RAISE NOTICE 'Migration 003_security_enhancements.sql completed successfully at %', NOW();
    RAISE NOTICE 'Security tables created: 7';
    RAISE NOTICE 'Security functions created: 6';
    RAISE NOTICE 'Security triggers created: 2';
END $$;