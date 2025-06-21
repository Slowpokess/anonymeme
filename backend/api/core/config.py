#!/usr/bin/env python3
"""
🔧 Конфигурация Anonymeme Backend
Production-ready настройки с поддержкой различных окружений
"""

import os
from typing import List, Optional, Union
from pydantic import BaseSettings, validator, Field
from functools import lru_cache


class Settings(BaseSettings):
    """
    Настройки приложения с автоматической загрузкой из переменных окружения
    Используем Pydantic для валидации и типизации
    """
    
    # === ОСНОВНЫЕ НАСТРОЙКИ ===
    APP_NAME: str = "Anonymeme API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(False, env="DEBUG")
    ENVIRONMENT: str = Field("production", env="ENVIRONMENT")
    
    # === БАЗА ДАННЫХ ===
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://devuser:devpass@localhost:5432/crypto_pump_anon",
        env="DATABASE_URL"
    )
    
    # === REDIS ===
    REDIS_URL: str = Field(
        "redis://localhost:6379",
        env="REDIS_URL"
    )
    
    # === SOLANA BLOCKCHAIN ===
    SOLANA_RPC_URL: str = Field(
        "https://api.devnet.solana.com",
        env="SOLANA_RPC_URL"
    )
    
    PUMP_CORE_PROGRAM_ID: str = Field(
        "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
        env="PUMP_CORE_PROGRAM_ID"
    )
    
    # === БЕЗОПАСНОСТЬ ===
    SECRET_KEY: str = Field(
        "your-super-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Разрешенные домены для CORS
    ALLOWED_ORIGINS: List[str] = Field(
        ["http://localhost:3000", "http://localhost:8000"],
        env="ALLOWED_ORIGINS"
    )
    
    # Доверенные хосты
    ALLOWED_HOSTS: List[str] = Field(
        ["localhost", "127.0.0.1", "0.0.0.0"],
        env="ALLOWED_HOSTS"
    )
    
    # === API RATE LIMITING ===
    RATE_LIMIT_REQUESTS: int = Field(100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(3600, env="RATE_LIMIT_WINDOW")  # в секундах
    
    # === ТОРГОВЛЯ ===
    # Максимальный размер сделки в SOL
    MAX_TRADE_SIZE_SOL: float = Field(10.0, env="MAX_TRADE_SIZE_SOL")
    
    # Максимальный slippage (в процентах)
    MAX_SLIPPAGE_PERCENT: float = Field(50.0, env="MAX_SLIPPAGE_PERCENT")
    
    # Комиссия платформы (в процентах)
    PLATFORM_FEE_PERCENT: float = Field(1.0, env="PLATFORM_FEE_PERCENT")
    
    # === МОНИТОРИНГ И ЛОГИРОВАНИЕ ===
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    SENTRY_DSN: Optional[str] = Field(None, env="SENTRY_DSN")
    
    # === CELERY ===
    CELERY_BROKER_URL: str = Field(
        "redis://localhost:6379/0",
        env="CELERY_BROKER_URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        "redis://localhost:6379/0",
        env="CELERY_RESULT_BACKEND"
    )
    
    # === WEBSOCKET ===
    WEBSOCKET_PORT: int = Field(8001, env="WEBSOCKET_PORT")
    WEBSOCKET_MAX_CONNECTIONS: int = Field(1000, env="WEBSOCKET_MAX_CONNECTIONS")
    
    # === EMAIL (для уведомлений) ===
    SMTP_SERVER: Optional[str] = Field(None, env="SMTP_SERVER")
    SMTP_PORT: int = Field(587, env="SMTP_PORT")
    SMTP_USERNAME: Optional[str] = Field(None, env="SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = Field(None, env="SMTP_PASSWORD")
    EMAIL_FROM: str = Field("noreply@anonymeme.com", env="EMAIL_FROM")
    
    # === ANALYTICS ===
    ANALYTICS_RETENTION_DAYS: int = Field(365, env="ANALYTICS_RETENTION_DAYS")
    
    # === АДМИНКА ===
    ADMIN_EMAILS: List[str] = Field(
        ["admin@anonymeme.com"],
        env="ADMIN_EMAILS"
    )
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_allowed_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Парсинг разрешенных origins из строки или списка"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        """Парсинг доверенных хостов из строки или списка"""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    @validator("ADMIN_EMAILS", pre=True)
    def parse_admin_emails(cls, v: Union[str, List[str]]) -> List[str]:
        """Парсинг email адресов админов"""
        if isinstance(v, str):
            return [email.strip() for email in v.split(",")]
        return v
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v: str) -> str:
        """Валидация секретного ключа"""
        if len(v) < 32:
            raise ValueError("SECRET_KEY должен быть не менее 32 символов")
        return v
    
    @validator("PUMP_CORE_PROGRAM_ID")
    def validate_program_id(cls, v: str) -> str:
        """Валидация Program ID для Solana"""
        if len(v) != 44:  # Стандартная длина base58 encoded pubkey
            raise ValueError("PUMP_CORE_PROGRAM_ID должен быть валидным Solana pubkey")
        return v
    
    @property
    def is_development(self) -> bool:
        """Проверка на development окружение"""
        return self.ENVIRONMENT.lower() in ["development", "dev", "local"]
    
    @property
    def is_production(self) -> bool:
        """Проверка на production окружение"""
        return self.ENVIRONMENT.lower() in ["production", "prod"]
    
    @property
    def is_testing(self) -> bool:
        """Проверка на testing окружение"""
        return self.ENVIRONMENT.lower() in ["testing", "test"]
    
    @property
    def database_url_sync(self) -> str:
        """Синхронный URL для базы данных (для миграций)"""
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class DevelopmentSettings(Settings):
    """Настройки для разработки"""
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "DEBUG"
    
    # Более мягкие лимиты для разработки
    RATE_LIMIT_REQUESTS: int = 1000
    MAX_TRADE_SIZE_SOL: float = 100.0


class ProductionSettings(Settings):
    """Настройки для продакшена"""
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "WARNING"
    
    # Строгие лимиты для продакшена
    RATE_LIMIT_REQUESTS: int = 60
    MAX_TRADE_SIZE_SOL: float = 10.0
    
    # Production-specific security
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    
    @validator("SECRET_KEY")
    def validate_production_secret_key(cls, v: str) -> str:
        """Дополнительная валидация секретного ключа для продакшена"""
        if v == "your-super-secret-key-change-in-production":
            raise ValueError("Необходимо изменить SECRET_KEY для продакшена!")
        return super().validate_secret_key(v)


class TestingSettings(Settings):
    """Настройки для тестирования"""
    DEBUG: bool = True
    ENVIRONMENT: str = "testing"
    LOG_LEVEL: str = "DEBUG"
    
    # Тестовая база данных
    DATABASE_URL: str = "postgresql+asyncpg://test:test@localhost:5432/test_crypto_pump_anon"
    
    # Отключение внешних сервисов
    SOLANA_RPC_URL: str = "http://localhost:8899"  # Локальный validator
    
    # Быстрые лимиты для тестов
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 5
    RATE_LIMIT_REQUESTS: int = 10000


@lru_cache()
def get_settings() -> Settings:
    """
    Получение настроек с кэшированием
    Автоматически выбирает правильный класс настроек в зависимости от окружения
    """
    environment = os.getenv("ENVIRONMENT", "production").lower()
    
    if environment in ["development", "dev", "local"]:
        return DevelopmentSettings()
    elif environment in ["testing", "test"]:
        return TestingSettings()
    else:
        return ProductionSettings()


# Глобальный объект настроек
settings = get_settings()


def reload_settings():
    """Перезагрузка настроек (полезно для тестов)"""
    get_settings.cache_clear()
    global settings
    settings = get_settings()


# Дополнительные константы
SOLANA_LAMPORTS_PER_SOL = 1_000_000_000
SOLANA_DECIMALS = 9

# Константы для бондинг-кривых
BONDING_CURVE_TYPES = [
    "Linear",
    "Exponential", 
    "Logarithmic",
    "Sigmoid",
    "ConstantProduct"
]

# Константы для типов DEX
DEX_TYPES = [
    "Raydium",
    "Jupiter",
    "Orca",
    "Serum",
    "Meteora"
]

# HTTP status codes для кастомных ошибок
ERROR_CODES = {
    "INSUFFICIENT_BALANCE": 4001,
    "SLIPPAGE_EXCEEDED": 4002,
    "TRADING_PAUSED": 4003,
    "INVALID_TOKEN": 4004,
    "RATE_LIMITED": 4005,
    "UNAUTHORIZED_ACCESS": 4006,
    "BLOCKCHAIN_ERROR": 5001,
    "DATABASE_ERROR": 5002,
    "CACHE_ERROR": 5003,
}