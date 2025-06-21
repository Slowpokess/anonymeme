#!/usr/bin/env python3
"""
🔗 Database Connection Management для Anonymeme
Production-ready подключение к PostgreSQL с пулом соединений
"""

import logging
from typing import Optional, AsyncGenerator, Any
from contextlib import asynccontextmanager

try:
    import asyncpg
except ImportError:
    asyncpg = None

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

import sys
import os

# Добавляем путь к backend в sys.path
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from api.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер подключений к базе данных"""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self._pool = None  # asyncpg.Pool если доступен
    
    async def initialize(self):
        """Инициализация подключения к БД"""
        try:
            # Создание SQLAlchemy engine для ORM
            if settings.DEBUG:
                # Для разработки - простая конфигурация
                self.engine = create_async_engine(
                    settings.ASYNC_DATABASE_URL,
                    echo=True,
                    poolclass=NullPool,
                )
            else:
                # Для продакшена - полный пул соединений
                self.engine = create_async_engine(
                    settings.ASYNC_DATABASE_URL,
                    echo=False,
                    pool_size=settings.DB_POOL_SIZE,
                    max_overflow=settings.DB_MAX_OVERFLOW,
                    pool_timeout=30,
                    pool_recycle=3600,  # Пересоздание соединений каждый час
                    pool_pre_ping=True,  # Проверка соединений
                )
            
            # Создание фабрики сессий
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
            
            # Создание asyncpg пула для прямых запросов
            if asyncpg is not None:
                self._pool = await asyncpg.create_pool(
                    settings.DATABASE_URL,
                    min_size=5,
                    max_size=settings.DB_POOL_SIZE,
                    command_timeout=60,
                    server_settings={
                        'jit': 'off',  # Отключение JIT для стабильности
                        'application_name': 'anonymeme_backend'
                    }
                )
            else:
                logger.warning("asyncpg не установлен, пул прямых подключений недоступен")
            
            logger.info("✅ Подключение к базе данных инициализировано")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации БД: {e}")
            raise
    
    async def close(self):
        """Закрытие подключений к БД"""
        try:
            if self.engine:
                await self.engine.dispose()
                logger.info("SQLAlchemy engine закрыт")
            
            if self._pool:
                await self._pool.close()
                logger.info("AsyncPG pool закрыт")
                
        except Exception as e:
            logger.error(f"Ошибка закрытия БД: {e}")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Получение сессии SQLAlchemy"""
        if not self.session_factory:
            raise RuntimeError("Database not initialized")
        
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Получение прямого подключения asyncpg"""
        if not self._pool:
            raise RuntimeError("Database pool not initialized or asyncpg not available")
        
        if asyncpg is None:
            raise RuntimeError("asyncpg не установлен")
        
        async with self._pool.acquire() as connection:
            yield connection
    
    async def health_check(self) -> dict:
        """Проверка состояния БД"""
        try:
            # Проверка SQLAlchemy
            async with self.get_session() as session:
                result = await session.execute("SELECT 1")
                sqlalchemy_ok = bool(result.scalar())
            
            # Проверка asyncpg
            async with self.get_connection() as conn:
                result = await conn.fetchval("SELECT 1")
                asyncpg_ok = result == 1
            
            # Статистика пула
            pool_stats = {
                "size": self._pool.get_size(),
                "min_size": self._pool.get_min_size(), 
                "max_size": self._pool.get_max_size(),
                "idle_connections": self._pool.get_idle_size()
            } if self._pool else {}
            
            return {
                "status": "healthy" if (sqlalchemy_ok and asyncpg_ok) else "unhealthy",
                "sqlalchemy": sqlalchemy_ok,
                "asyncpg": asyncpg_ok,
                "pool_stats": pool_stats
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "sqlalchemy": False,
                "asyncpg": False,
                "pool_stats": {}
            }


# Глобальный экземпляр менеджера БД
db_manager = DatabaseManager()


# Dependency функции для FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для получения сессии БД в FastAPI"""
    async with db_manager.get_session() as session:
        yield session


async def get_db_connection() -> AsyncGenerator[Any, None]:
    """Dependency для получения прямого подключения в FastAPI"""
    async with db_manager.get_connection() as connection:
        yield connection


# События жизненного цикла приложения
async def startup_database():
    """Инициализация БД при старте приложения"""
    await db_manager.initialize()


async def shutdown_database():
    """Закрытие БД при остановке приложения"""
    await db_manager.close()


# Утилиты для работы с транзакциями
@asynccontextmanager
async def transaction() -> AsyncGenerator[AsyncSession, None]:
    """Контекстный менеджер для транзакций"""
    async with db_manager.get_session() as session:
        async with session.begin():
            yield session


class TransactionManager:
    """Менеджер транзакций для сложных операций"""
    
    def __init__(self):
        self.session: Optional[AsyncSession] = None
        self.in_transaction = False
    
    async def __aenter__(self) -> AsyncSession:
        self.session = db_manager.session_factory()
        await self.session.begin()
        self.in_transaction = True
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Подавляем предупреждения о неиспользуемых параметрах
        _ = exc_val, exc_tb
        
        if self.session:
            try:
                if exc_type is None and self.in_transaction:
                    await self.session.commit()
                else:
                    await self.session.rollback()
            finally:
                await self.session.close()
                self.session = None
                self.in_transaction = False
        
        # Возвращаем False чтобы не подавлять исключения
        return False


# Декоратор для автоматических транзакций
def with_transaction(func):
    """Декоратор для выполнения async функции в транзакции"""
    import functools
    import asyncio
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not asyncio.iscoroutinefunction(func):
            raise TypeError("with_transaction can only be used with async functions")
        
        async with TransactionManager() as session:
            # Добавляем сессию в аргументы если её нет
            if 'db' not in kwargs and 'session' not in kwargs:
                kwargs['db'] = session
            return await func(*args, **kwargs)
    return wrapper


# Утилиты для миграций
async def run_migration_query(query: str) -> None:
    """Выполнение SQL запроса для миграций"""
    async with db_manager.get_connection() as conn:
        await conn.execute(query)


async def check_table_exists(table_name: str) -> bool:
    """Проверка существования таблицы"""
    query = """
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = $1
    )
    """
    async with db_manager.get_connection() as conn:
        return await conn.fetchval(query, table_name)


async def get_table_schema(table_name: str) -> list:
    """Получение схемы таблицы"""
    query = """
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = $1
    ORDER BY ordinal_position
    """
    async with db_manager.get_connection() as conn:
        return await conn.fetch(query, table_name)


# Утилиты для мониторинга производительности
async def get_db_stats() -> dict:
    """Получение статистики базы данных"""
    queries = {
        "active_connections": "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'",
        "idle_connections": "SELECT count(*) FROM pg_stat_activity WHERE state = 'idle'",
        "database_size": "SELECT pg_size_pretty(pg_database_size(current_database()))",
        "total_queries": "SELECT sum(calls) FROM pg_stat_statements",
        "cache_hit_ratio": """
            SELECT round(
                100.0 * sum(blks_hit) / (sum(blks_hit) + sum(blks_read)), 2
            ) FROM pg_stat_database WHERE datname = current_database()
        """
    }
    
    stats = {}
    async with db_manager.get_connection() as conn:
        for stat_name, query in queries.items():
            try:
                stats[stat_name] = await conn.fetchval(query)
            except Exception as e:
                stats[stat_name] = f"Error: {e}"
    
    return stats


# Класс для работы с индексами
class IndexManager:
    """Менеджер индексов для оптимизации производительности"""
    
    @staticmethod
    async def get_unused_indexes() -> list:
        """Получение неиспользуемых индексов"""
        query = """
        SELECT
            schemaname,
            tablename,
            indexname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch,
            pg_size_pretty(pg_relation_size(indexname::regclass)) as size
        FROM pg_stat_user_indexes
        WHERE idx_scan = 0
        ORDER BY pg_relation_size(indexname::regclass) DESC
        """
        
        async with db_manager.get_connection() as conn:
            return await conn.fetch(query)
    
    @staticmethod
    async def get_slow_queries() -> list:
        """Получение медленных запросов"""
        query = """
        SELECT
            query,
            calls,
            total_time,
            mean_time,
            rows
        FROM pg_stat_statements
        WHERE calls > 100
        ORDER BY mean_time DESC
        LIMIT 10
        """
        
        async with db_manager.get_connection() as conn:
            return await conn.fetch(query)


# Экспорт основных компонентов
__all__ = [
    'db_manager',
    'get_db_session',
    'get_db_connection', 
    'startup_database',
    'shutdown_database',
    'transaction',
    'TransactionManager',
    'with_transaction',
    'run_migration_query',
    'check_table_exists',
    'get_table_schema',
    'get_db_stats',
    'IndexManager'
]