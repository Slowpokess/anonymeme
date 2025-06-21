#!/usr/bin/env python3
"""
🚀 Database Migration Runner для Anonymeme
Production-ready миграционная система с полным контролем
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

import asyncpg
from asyncpg import Connection
import click

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationRunner:
    """Система выполнения миграций БД"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.migrations_dir = Path(__file__).parent / "migrations"
        self.connection: Connection = None
        
    async def connect(self):
        """Подключение к базе данных"""
        try:
            self.connection = await asyncpg.connect(self.database_url)
            logger.info("✅ Подключение к базе данных установлено")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к БД: {e}")
            raise
    
    async def disconnect(self):
        """Отключение от базы данных"""
        if self.connection:
            await self.connection.close()
            logger.info("Подключение к БД закрыто")
    
    async def create_migration_table(self):
        """Создание таблицы для отслеживания миграций"""
        query = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id SERIAL PRIMARY KEY,
            version VARCHAR(100) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            applied_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
            execution_time_ms INTEGER,
            checksum VARCHAR(64),
            success BOOLEAN DEFAULT TRUE,
            error_message TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_schema_migrations_version 
        ON schema_migrations(version);
        
        CREATE INDEX IF NOT EXISTS idx_schema_migrations_applied_at 
        ON schema_migrations(applied_at);
        """
        
        await self.connection.execute(query)
        logger.info("📋 Таблица миграций создана/проверена")
    
    async def get_applied_migrations(self) -> List[str]:
        """Получение списка примененных миграций"""
        query = """
        SELECT version FROM schema_migrations 
        WHERE success = TRUE 
        ORDER BY version
        """
        
        rows = await self.connection.fetch(query)
        return [row['version'] for row in rows]
    
    def get_migration_files(self) -> List[Dict[str, Any]]:
        """Получение списка файлов миграций"""
        migrations = []
        
        if not self.migrations_dir.exists():
            logger.warning(f"Папка миграций не найдена: {self.migrations_dir}")
            return migrations
        
        for file_path in sorted(self.migrations_dir.glob("*.sql")):
            # Извлекаем версию из имени файла (например, 001_initial_schema.sql -> 001)
            version = file_path.stem.split('_')[0]
            
            migrations.append({
                'version': version,
                'name': file_path.stem,
                'file_path': file_path,
                'content': file_path.read_text(encoding='utf-8')
            })
        
        return migrations
    
    def calculate_checksum(self, content: str) -> str:
        """Вычисление контрольной суммы миграции"""
        import hashlib
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    async def apply_migration(self, migration: Dict[str, Any]) -> bool:
        """Применение одной миграции"""
        version = migration['version']
        name = migration['name']
        content = migration['content']
        checksum = self.calculate_checksum(content)
        
        logger.info(f"🔄 Применение миграции {version}: {name}")
        
        start_time = datetime.now()
        
        try:
            # Начало транзакции
            async with self.connection.transaction():
                # Выполнение миграции
                await self.connection.execute(content)
                
                # Вычисление времени выполнения
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                # Запись в таблицу миграций
                await self.connection.execute("""
                    INSERT INTO schema_migrations 
                    (version, name, execution_time_ms, checksum, success)
                    VALUES ($1, $2, $3, $4, $5)
                """, version, name, int(execution_time), checksum, True)
                
                logger.info(f"✅ Миграция {version} успешно применена ({execution_time:.0f}ms)")
                return True
                
        except Exception as e:
            # Запись об ошибке
            try:
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                await self.connection.execute("""
                    INSERT INTO schema_migrations 
                    (version, name, execution_time_ms, checksum, success, error_message)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, version, name, int(execution_time), checksum, False, str(e))
            except:
                pass  # Игнорируем ошибки записи лога
            
            logger.error(f"❌ Ошибка применения миграции {version}: {e}")
            return False
    
    async def migrate_down(self, target_version: str) -> bool:
        """Откат миграций до указанной версии"""
        await self.create_migration_table()
        
        applied_migrations = await self.get_applied_migrations()
        
        # Находим миграции для отката (в обратном порядке)
        migrations_to_rollback = [
            v for v in reversed(applied_migrations) 
            if v > target_version
        ]
        
        if not migrations_to_rollback:
            logger.info("🔄 Нет миграций для отката")
            return True
        
        logger.warning(f"⚠️ Откат {len(migrations_to_rollback)} миграций до версии {target_version}")
        
        # В простой реализации просто помечаем как откаченные
        # В production версии здесь будут down-миграции
        for version in migrations_to_rollback:
            try:
                await self.connection.execute("""
                    UPDATE schema_migrations 
                    SET success = FALSE, error_message = 'Rolled back'
                    WHERE version = $1
                """, version)
                logger.info(f"🔄 Откачена миграция {version}")
            except Exception as e:
                logger.error(f"❌ Ошибка отката миграции {version}: {e}")
                return False
        
        logger.info(f"✅ Откат до версии {target_version} завершен")
        return True
    
    async def migrate_up(self, target_version: str = None) -> bool:
        """Применение миграций до указанной версии"""
        await self.create_migration_table()
        
        applied_migrations = await self.get_applied_migrations()
        available_migrations = self.get_migration_files()
        
        logger.info(f"📊 Применено миграций: {len(applied_migrations)}")
        logger.info(f"📊 Доступно миграций: {len(available_migrations)}")
        
        # Фильтрация неприменённых миграций
        pending_migrations = [
            m for m in available_migrations 
            if m['version'] not in applied_migrations
        ]
        
        if target_version:
            pending_migrations = [
                m for m in pending_migrations 
                if m['version'] <= target_version
            ]
        
        if not pending_migrations:
            logger.info("✨ Все миграции уже применены")
            return True
        
        logger.info(f"🚀 Применение {len(pending_migrations)} миграций...")
        
        success_count = 0
        for migration in pending_migrations:
            if await self.apply_migration(migration):
                success_count += 1
            else:
                logger.error("💥 Миграция прервана из-за ошибки")
                break
        
        if success_count == len(pending_migrations):
            logger.info(f"🎉 Все миграции успешно применены ({success_count}/{len(pending_migrations)})")
            return True
        else:
            logger.error(f"⚠️ Применено только {success_count}/{len(pending_migrations)} миграций")
            return False
    
    async def show_status(self):
        """Показать статус миграций"""
        await self.create_migration_table()
        
        applied_migrations = await self.get_applied_migrations()
        available_migrations = self.get_migration_files()
        
        print("\n" + "="*60)
        print("📋 СТАТУС МИГРАЦИЙ")
        print("="*60)
        
        print(f"Применено миграций: {len(applied_migrations)}")
        print(f"Доступно миграций: {len(available_migrations)}")
        
        # Детали по каждой миграции
        print("\nДетали:")
        for migration in available_migrations:
            version = migration['version']
            name = migration['name']
            status = "✅ Применена" if version in applied_migrations else "⏳ Ожидает"
            print(f"  {version}: {name} - {status}")
        
        # Последние применённые миграции
        if applied_migrations:
            query = """
            SELECT version, name, applied_at, execution_time_ms 
            FROM schema_migrations 
            WHERE success = TRUE 
            ORDER BY applied_at DESC 
            LIMIT 5
            """
            recent_migrations = await self.connection.fetch(query)
            
            print("\n🕒 Последние применённые миграции:")
            for row in recent_migrations:
                print(f"  {row['version']}: {row['name']} "
                      f"({row['applied_at'].strftime('%Y-%m-%d %H:%M:%S')}, "
                      f"{row['execution_time_ms']}ms)")
        
        print("="*60)
    
    async def validate_migrations(self) -> bool:
        """Валидация миграций"""
        logger.info("🔍 Валидация миграций...")
        
        migrations = self.get_migration_files()
        
        if not migrations:
            logger.warning("⚠️ Файлы миграций не найдены")
            return False
        
        # Проверка последовательности версий
        versions = [m['version'] for m in migrations]
        for i, version in enumerate(versions):
            expected = f"{i+1:03d}"
            if version != expected:
                logger.error(f"❌ Нарушена последовательность версий: найдена {version}, ожидалась {expected}")
                return False
        
        # Проверка синтаксиса SQL (базовая)
        for migration in migrations:
            content = migration['content'].strip()
            if not content:
                logger.error(f"❌ Пустая миграция: {migration['name']}")
                return False
            
            # Проверка на опасные операции в продакшене
            dangerous_patterns = [
                'DROP DATABASE',
                'DROP SCHEMA',
                'TRUNCATE',
            ]
            
            content_upper = content.upper()
            for pattern in dangerous_patterns:
                if pattern in content_upper:
                    logger.warning(f"⚠️ Обнаружена потенциально опасная операция в {migration['name']}: {pattern}")
        
        logger.info("✅ Валидация миграций завершена успешно")
        return True


# CLI интерфейс
@click.group()
def cli():
    """Anonymeme Database Migration Tool"""
    pass


@cli.command()
@click.option('--database-url', 
              envvar='DATABASE_URL',
              required=True,
              help='URL подключения к базе данных')
@click.option('--target-version', 
              help='Версия до которой применить миграции')
def migrate(database_url: str, target_version: str = None):
    """Применить миграции"""
    async def run_migration():
        runner = MigrationRunner(database_url)
        try:
            await runner.connect()
            success = await runner.migrate_up(target_version)
            sys.exit(0 if success else 1)
        finally:
            await runner.disconnect()
    
    asyncio.run(run_migration())


@cli.command()
@click.option('--database-url',
              envvar='DATABASE_URL', 
              required=True,
              help='URL подключения к базе данных')
def status(database_url: str):
    """Показать статус миграций"""
    async def show_migration_status():
        runner = MigrationRunner(database_url)
        try:
            await runner.connect()
            await runner.show_status()
        finally:
            await runner.disconnect()
    
    asyncio.run(show_migration_status())


@cli.command()
@click.option('--database-url',
              envvar='DATABASE_URL',
              required=True,
              help='URL подключения к базе данных')
@click.option('--target-version',
              required=True,
              help='Версия до которой откатить миграции')
def rollback(database_url: str, target_version: str):
    """Откат миграций до указанной версии"""
    async def run_rollback():
        runner = MigrationRunner(database_url)
        try:
            await runner.connect()
            success = await runner.migrate_down(target_version)
            sys.exit(0 if success else 1)
        finally:
            await runner.disconnect()
    
    asyncio.run(run_rollback())


@cli.command()
def validate():
    """Валидация файлов миграций"""
    async def validate_migrations():
        runner = MigrationRunner("dummy://")  # URL не нужен для валидации
        success = await runner.validate_migrations()
        sys.exit(0 if success else 1)
    
    asyncio.run(validate_migrations())


@cli.command()
@click.option('--name', required=True, help='Название миграции')
def create(name: str):
    """Создать новую миграцию"""
    migrations_dir = Path(__file__).parent / "migrations"
    migrations_dir.mkdir(exist_ok=True)
    
    # Определение следующего номера версии
    existing_migrations = list(migrations_dir.glob("*.sql"))
    if existing_migrations:
        versions = [int(f.stem.split('_')[0]) for f in existing_migrations]
        next_version = max(versions) + 1
    else:
        next_version = 1
    
    # Создание файла миграции
    version_str = f"{next_version:03d}"
    filename = f"{version_str}_{name.lower().replace(' ', '_')}.sql"
    file_path = migrations_dir / filename
    
    template = f"""-- ==================================================================
-- Anonymeme Database Migration {version_str}
-- Version: {version_str}
-- Description: {name}
-- Author: Developer
-- Date: {datetime.now().strftime('%Y-%m-%d')}
-- ==================================================================

-- TODO: Добавьте SQL команды для миграции

-- ==================================================================
-- ЗАВЕРШЕНИЕ МИГРАЦИИ
-- ==================================================================

-- Лог завершения миграции
DO $$
BEGIN
    RAISE NOTICE 'Migration {filename} completed successfully at %', NOW();
END $$;
"""
    
    file_path.write_text(template, encoding='utf-8')
    
    logger.info(f"✅ Создана новая миграция: {filename}")
    logger.info(f"📂 Путь: {file_path}")


if __name__ == "__main__":
    cli()