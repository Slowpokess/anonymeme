# 🗄️ Database Management для Anonymeme

Полная система управления базой данных с миграциями, подключениями и мониторингом.

## 📋 Структура

```
database/
├── migrations/           # SQL миграции
│   ├── 001_initial_schema.sql
│   ├── 002_additional_indexes.sql
│   └── 003_security_enhancements.sql
├── migrate.py           # Система миграций
├── connection.py        # Управление подключениями
└── README.md           # Эта документация
```

## 🚀 Миграции

### Применение миграций

```bash
# Применить все миграции
python -m backend.database.migrate migrate --database-url postgresql://...

# Применить до определенной версии
python -m backend.database.migrate migrate --database-url postgresql://... --target-version 002

# Откат миграций до версии
python -m backend.database.migrate rollback --database-url postgresql://... --target-version 001

# Проверить статус миграций
python -m backend.database.migrate status --database-url postgresql://...

# Валидация файлов миграций
python -m backend.database.migrate validate

# Создать новую миграцию
python -m backend.database.migrate create --name "add_user_preferences"

# Запустить тесты миграций
python -m pytest backend/database/test_migrations.py -v
```

### Использование переменных окружения

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/anonymeme"
python -m backend.database.migrate migrate
```

## 📊 Схема базы данных

### Основные таблицы

- **users** - Пользователи платформы
- **tokens** - Токены созданные на платформе  
- **trades** - История торговых операций
- **price_history** - История цен с разными интервалами
- **user_tokens** - Балансы токенов у пользователей
- **analytics** - Аналитические данные

### Таблицы безопасности

- **audit_log** - Аудит действий пользователей
- **security_log** - Логи событий безопасности
- **suspicious_activity** - Подозрительная активность
- **rate_limits** - Ограничения скорости запросов
- **blocked_ips** - Заблокированные IP адреса
- **user_sessions** - Активные сессии пользователей

## 🔗 Подключения

### В коде приложения

```python
from backend.database.connection import get_db_session, db_manager

# Dependency для FastAPI
async def some_endpoint(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(User))
    return result.scalars().all()

# Прямое использование
async with db_manager.get_session() as session:
    result = await session.execute(select(Token))
    tokens = result.scalars().all()

# Транзакции
from backend.database.connection import transaction

async with transaction() as session:
    user = User(wallet_address="...", username="...")
    session.add(user)
    # Автоматический commit при выходе из контекста
```

### Инициализация в FastAPI

```python
from fastapi import FastAPI
from backend.database.connection import startup_database, shutdown_database

app = FastAPI()

@app.on_event("startup")
async def startup():
    await startup_database()

@app.on_event("shutdown")
async def shutdown():
    await shutdown_database()
```

## 🛡️ Безопасность

### Функции безопасности

```sql
-- Логирование действий пользователя
SELECT log_user_action(
    user_id, 
    'token_created', 
    'token', 
    token_id,
    old_values, 
    new_values,
    ip_address,
    user_agent
);

-- Проверка rate limit
SELECT check_rate_limit(
    identifier,    -- IP или ID пользователя
    'ip',         -- Тип идентификатора
    '/api/v1/trade', -- Endpoint
    10,           -- Максимум запросов
    60            -- Окно в секундах
);

-- Блокировка IP
SELECT block_ip_address(
    '192.168.1.100',
    'Suspicious activity detected',
    'temporary',  -- Тип блокировки
    24,          -- Часов блокировки
    admin_user_id
);
```

### Роли безопасности

- **anonymeme_readonly** - Только чтение
- **anonymeme_readwrite** - Чтение и запись
- **anonymeme_admin** - Полные права
- **anonymeme_auditor** - Доступ к логам аудита
- **anonymeme_security** - Управление безопасностью

## 📈 Мониторинг и производительность

### Проверка здоровья БД

```python
from backend.database.connection import db_manager

health = await db_manager.health_check()
print(health)
# {
#   "status": "healthy",
#   "sqlalchemy": True,
#   "asyncpg": True,
#   "pool_stats": {...}
# }
```

### Статистика производительности

```python
from backend.database.connection import get_db_stats, IndexManager

# Общая статистика
stats = await get_db_stats()

# Неиспользуемые индексы
unused_indexes = await IndexManager.get_unused_indexes()

# Медленные запросы
slow_queries = await IndexManager.get_slow_queries()
```

### Автоматическая очистка

```sql
-- Очистка старых логов (автоматически)
SELECT cleanup_security_logs();

-- Очистка старой истории цен
SELECT cleanup_old_price_history();

-- Обновление статистики токенов
SELECT update_token_statistics();
```

## 🔧 Настройка

### Переменные окружения

```bash
# Основные настройки БД
DATABASE_URL="postgresql://user:password@localhost:5432/anonymeme"
ASYNC_DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/anonymeme"

# Пул соединений
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Логирование
DEBUG=False
```

### Конфигурация PostgreSQL

```sql
-- Рекомендуемые настройки для продакшена
shared_preload_libraries = 'pg_stat_statements'
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

## 🧪 Тестирование

### Тестовая база данных

```python
# Создание тестовой БД
pytest_plugins = ["backend.tests.database_fixtures"]

async def test_user_creation(test_db):
    async with test_db.get_session() as session:
        user = User(wallet_address="test123", username="testuser")
        session.add(user)
        await session.commit()
        
        assert user.id is not None
```

## 📚 Дополнительные функции

### Работа с JSON полями

```sql
-- Поиск по тегам токенов
SELECT * FROM tokens WHERE tags @> '["meme"]';

-- Обновление настроек пользователя
UPDATE users SET preferences = preferences || '{"theme": "dark"}' 
WHERE id = $1;
```

### Полнотекстовый поиск

```sql
-- Поиск токенов по имени и символу
SELECT * FROM tokens 
WHERE name % 'bitcoin' OR symbol % 'btc'
ORDER BY similarity(name, 'bitcoin') DESC;
```

### Временные ряды

```sql
-- История цен за день с 1-часовыми интервалами
SELECT period_start, close_price, volume_sol
FROM price_history 
WHERE token_id = $1 
  AND interval_minutes = 60
  AND period_start >= NOW() - INTERVAL '1 day'
ORDER BY period_start;
```

## 🔧 Исправленные проблемы после аудита

### Критические исправления
- ✅ **Синхронизация схемы**: Исправлены несоответствия между SQL и SQLAlchemy моделями
- ✅ **Пул соединений**: Исправлена конфигурация для development/production режимов  
- ✅ **Rate limiting**: Переписана функция с улучшенной логикой и безопасностью
- ✅ **Индексы**: Добавлены критически важные индексы для производительности
- ✅ **Типы данных**: Финансовые поля переведены на DECIMAL для точности

### Безопасность
- ✅ **Автоблокировка**: Добавлена автоматическая блокировка при неудачных попытках входа
- ✅ **Валидация**: Усилена валидация входных параметров в функциях
- ✅ **Шифрование**: Добавлены функции шифрования для чувствительных данных

### Производительность  
- ✅ **Материализованные представления**: Добавлены для часто используемых запросов
- ✅ **Автоочистка**: Реализована автоматическая очистка старых данных
- ✅ **Мониторинг**: Добавлены функции мониторинга производительности

### Функциональность
- ✅ **Откат миграций**: Добавлена возможность отката миграций
- ✅ **Тестирование**: Создан полный набор тестов для системы
- ✅ **Документация**: Обновлена документация с новой функциональностью

## 🚨 Устранение неполадок

### Частые проблемы

1. **Ошибка подключения к БД**
   ```bash
   # Проверить доступность БД
   pg_isready -h localhost -p 5432
   
   # Проверить настройки
   python -c "from backend.core.config import settings; print(settings.DATABASE_URL)"
   ```

2. **Медленные запросы**
   ```sql
   -- Включить логирование медленных запросов
   ALTER SYSTEM SET log_min_duration_statement = 1000;
   SELECT pg_reload_conf();
   ```

3. **Блокировки**
   ```sql
   -- Просмотр активных блокировок
   SELECT * FROM pg_locks WHERE NOT granted;
   
   -- Просмотр активных запросов
   SELECT pid, query, state FROM pg_stat_activity WHERE state = 'active';
   ```

### Восстановление

```bash
# Бэкап
pg_dump anonymeme > backup.sql

# Восстановление
psql anonymeme < backup.sql

# Восстановление схемы
python -m backend.database.migrate migrate --database-url postgresql://...
```