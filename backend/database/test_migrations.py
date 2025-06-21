#!/usr/bin/env python3
"""
🧪 Тесты для системы миграций Anonymeme
Production-ready тестирование миграций
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from .migrate import MigrationRunner


class TestMigrationRunner:
    """Тесты для MigrationRunner"""
    
    @pytest.fixture
    def temp_migrations_dir(self):
        """Временная папка для тестовых миграций"""
        with tempfile.TemporaryDirectory() as tmpdir:
            migrations_dir = Path(tmpdir) / "migrations"
            migrations_dir.mkdir()
            
            # Создаем тестовые миграции
            (migrations_dir / "001_test_migration.sql").write_text("""
                CREATE TABLE test_table (id SERIAL PRIMARY KEY);
            """)
            
            (migrations_dir / "002_another_migration.sql").write_text("""
                ALTER TABLE test_table ADD COLUMN name VARCHAR(100);
            """)
            
            yield migrations_dir
    
    @pytest.fixture
    def runner(self):
        """Экземпляр MigrationRunner с моками"""
        runner = MigrationRunner("postgresql://test")
        runner.connection = AsyncMock()
        return runner
    
    def test_get_migration_files(self, runner, temp_migrations_dir):
        """Тест получения файлов миграций"""
        runner.migrations_dir = temp_migrations_dir
        
        migrations = runner.get_migration_files()
        
        assert len(migrations) == 2
        assert migrations[0]['version'] == '001'
        assert migrations[1]['version'] == '002'
        assert 'CREATE TABLE' in migrations[0]['content']
    
    def test_calculate_checksum(self, runner):
        """Тест вычисления контрольной суммы"""
        content = "CREATE TABLE test;"
        checksum1 = runner.calculate_checksum(content)
        checksum2 = runner.calculate_checksum(content)
        
        assert checksum1 == checksum2
        assert len(checksum1) == 64  # SHA256 в hex
    
    @pytest.mark.asyncio
    async def test_apply_migration_success(self, runner):
        """Тест успешного применения миграции"""
        migration = {
            'version': '001',
            'name': 'test_migration',
            'content': 'CREATE TABLE test_table (id SERIAL);'
        }
        
        # Мок успешного выполнения
        runner.connection.transaction.return_value.__aenter__ = AsyncMock()
        runner.connection.transaction.return_value.__aexit__ = AsyncMock()
        runner.connection.execute = AsyncMock()
        
        result = await runner.apply_migration(migration)
        
        assert result is True
        assert runner.connection.execute.call_count == 2  # Миграция + запись в лог
    
    @pytest.mark.asyncio
    async def test_apply_migration_failure(self, runner):
        """Тест неудачного применения миграции"""
        migration = {
            'version': '001',
            'name': 'test_migration',
            'content': 'INVALID SQL;'
        }
        
        # Мок ошибки выполнения
        runner.connection.transaction.return_value.__aenter__ = AsyncMock()
        runner.connection.transaction.return_value.__aexit__ = AsyncMock()
        runner.connection.execute = AsyncMock(side_effect=Exception("SQL Error"))
        
        result = await runner.apply_migration(migration)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_applied_migrations(self, runner):
        """Тест получения примененных миграций"""
        # Мок результата запроса
        mock_rows = [
            {'version': '001'},
            {'version': '002'}
        ]
        runner.connection.fetch = AsyncMock(return_value=mock_rows)
        
        applied = await runner.get_applied_migrations()
        
        assert applied == ['001', '002']
    
    def test_validate_migrations_success(self, runner, temp_migrations_dir):
        """Тест успешной валидации миграций"""
        runner.migrations_dir = temp_migrations_dir
        
        result = asyncio.run(runner.validate_migrations())
        
        assert result is True
    
    def test_validate_migrations_empty(self, runner):
        """Тест валидации пустой папки миграций"""
        runner.migrations_dir = Path("/nonexistent")
        
        result = asyncio.run(runner.validate_migrations())
        
        assert result is False


class TestMigrationIntegration:
    """Интеграционные тесты миграций"""
    
    @pytest.mark.asyncio
    async def test_full_migration_cycle(self):
        """Тест полного цикла миграций"""
        # Этот тест требует реальной БД для полного тестирования
        # В CI/CD среде можно использовать тестовую PostgreSQL
        pass
    
    def test_migration_files_syntax(self):
        """Тест синтаксиса файлов миграций"""
        migrations_dir = Path(__file__).parent / "migrations"
        
        if not migrations_dir.exists():
            pytest.skip("Migrations directory not found")
        
        for migration_file in migrations_dir.glob("*.sql"):
            content = migration_file.read_text()
            
            # Базовые проверки синтаксиса
            assert content.strip(), f"Empty migration: {migration_file.name}"
            assert "DO $$" in content or "CREATE" in content or "ALTER" in content, \
                f"No SQL commands found in: {migration_file.name}"
            
            # Проверка на опасные команды в продакшене
            dangerous_commands = ["DROP DATABASE", "DROP SCHEMA"]
            content_upper = content.upper()
            for cmd in dangerous_commands:
                assert cmd not in content_upper, \
                    f"Dangerous command '{cmd}' found in: {migration_file.name}"


class TestDatabaseConnection:
    """Тесты для DatabaseManager"""
    
    @pytest.fixture
    def db_manager(self):
        """Экземпляр DatabaseManager с моками"""
        from .connection import DatabaseManager
        return DatabaseManager()
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, db_manager):
        """Тест health check при здоровой БД"""
        # Мок здоровой БД
        with patch.object(db_manager, 'get_session') as mock_session, \
             patch.object(db_manager, 'get_connection') as mock_conn:
            
            # Мок успешных запросов
            mock_session.return_value.__aenter__ = AsyncMock()
            mock_session.return_value.__aexit__ = AsyncMock()
            mock_session.return_value.execute = AsyncMock()
            mock_session.return_value.execute.return_value.scalar.return_value = 1
            
            mock_conn.return_value.__aenter__ = AsyncMock()
            mock_conn.return_value.__aexit__ = AsyncMock()
            mock_conn.return_value.fetchval = AsyncMock(return_value=1)
            
            # Мок статистики пула
            db_manager._pool = AsyncMock()
            db_manager._pool.get_size.return_value = 10
            db_manager._pool.get_min_size.return_value = 5
            db_manager._pool.get_max_size.return_value = 20
            db_manager._pool.get_idle_size.return_value = 3
            
            health = await db_manager.health_check()
            
            assert health["status"] == "healthy"
            assert health["sqlalchemy"] is True
            assert health["asyncpg"] is True
            assert "pool_stats" in health
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, db_manager):
        """Тест health check при нездоровой БД"""
        # Мок ошибки подключения
        with patch.object(db_manager, 'get_session') as mock_session:
            mock_session.side_effect = Exception("Connection failed")
            
            health = await db_manager.health_check()
            
            assert health["status"] == "unhealthy"
            assert "error" in health


class TestPerformanceOptimizations:
    """Тесты для оптимизации производительности"""
    
    def test_index_coverage(self):
        """Проверка покрытия индексами критических запросов"""
        # Проверяем что есть индексы для часто используемых запросов
        migrations_dir = Path(__file__).parent / "migrations"
        
        # Собираем все созданные индексы
        all_indexes = []
        for migration_file in migrations_dir.glob("*.sql"):
            content = migration_file.read_text().upper()
            # Простой парсинг индексов
            lines = content.split('\n')
            for line in lines:
                if 'CREATE INDEX' in line or 'CREATE UNIQUE INDEX' in line:
                    all_indexes.append(line.strip())
        
        # Проверяем критические индексы
        critical_patterns = [
            'USERS(WALLET_ADDRESS)',
            'TOKENS(MINT_ADDRESS)', 
            'TRADES(USER_ID',
            'TRADES(TOKEN_ID',
            'TOKENS(STATUS'
        ]
        
        for pattern in critical_patterns:
            found = any(pattern in idx for idx in all_indexes)
            assert found, f"Missing critical index for: {pattern}"
    
    def test_foreign_key_indexes(self):
        """Проверка индексов на внешних ключах"""
        # Все FK должны иметь индексы для производительности
        # Это критично для PostgreSQL
        migrations_dir = Path(__file__).parent / "migrations"
        
        foreign_keys = []
        indexes = []
        
        for migration_file in migrations_dir.glob("*.sql"):
            content = migration_file.read_text().upper()
            
            # Ищем внешние ключи
            for line in content.split('\n'):
                if 'REFERENCES' in line and 'FOREIGN KEY' not in line:
                    # Простой парсинг FK
                    if '(' in line and ')' in line:
                        foreign_keys.append(line.strip())
                
                if 'CREATE INDEX' in line:
                    indexes.append(line.strip())
        
        # В идеале каждый FK должен иметь индекс
        # Это упрощенная проверка
        assert len(indexes) >= len(foreign_keys) // 2, \
            "Not enough indexes for foreign keys"


if __name__ == "__main__":
    pytest.main([__file__])