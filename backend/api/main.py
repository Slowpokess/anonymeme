#!/usr/bin/env python3
"""
🚀 Anonymeme Backend API
Production-ready FastAPI приложение для memecoin платформы на Solana

Архитектурные решения:
- FastAPI для высокой производительности и автогенерации документации
- SQLAlchemy с async поддержкой для работы с PostgreSQL
- Redis для кэширования и сессий
- Solana.py для взаимодействия с блокчейном
- Pydantic для валидации данных
- Structured logging для production monitoring
"""

import os
import logging
import uvicorn
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Импорты наших модулей
from .routes import tokens, trading, users, analytics, admin
from .services.blockchain import SolanaService
from .services.cache import CacheService
from .models.database import Base
from .middleware.security import SecurityMiddleware
from .middleware.logging import LoggingMiddleware
from .core.config import settings
from .core.exceptions import (
    CustomHTTPException,
    ValidationException,
    BlockchainException,
    DatabaseException
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальные переменные для зависимостей
engine = None
async_session = None
redis_client = None
solana_service = None
cache_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения
    Инициализация и закрытие ресурсов
    """
    global engine, async_session, redis_client, solana_service, cache_service
    
    logger.info("🚀 Запуск Anonymeme Backend API...")
    
    try:
        # Инициализация базы данных
        logger.info("📊 Подключение к PostgreSQL...")
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        async_session = async_sessionmaker(
            engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        
        # Создание таблиц (в продакшене используем миграции)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Инициализация Redis
        logger.info("🔴 Подключение к Redis...")
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
            socket_keepalive=True,
            socket_keepalive_options={}
        )
        
        # Проверка подключения к Redis
        await redis_client.ping()
        
        # Инициализация сервисов
        logger.info("⛓️ Инициализация Solana сервиса...")
        solana_service = SolanaService(
            rpc_url=settings.SOLANA_RPC_URL,
            program_id=settings.PUMP_CORE_PROGRAM_ID
        )
        await solana_service.initialize()
        
        cache_service = CacheService(redis_client)
        
        # Сохранение сервисов в app.state для доступа в handlers
        app.state.db_session = async_session
        app.state.redis = redis_client
        app.state.solana = solana_service
        app.state.cache = cache_service
        
        logger.info("✅ Все сервисы успешно инициализированы")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации: {e}")
        raise
    
    finally:
        # Закрытие ресурсов
        logger.info("🔄 Закрытие соединений...")
        
        if redis_client:
            await redis_client.close()
        
        if engine:
            await engine.dispose()
        
        logger.info("✅ Ресурсы освобождены")


# Создание FastAPI приложения
app = FastAPI(
    title="Anonymeme API",
    description="""
    🚀 **Anonymeme Platform API**
    
    Production-ready API для decentralized memecoin платформы на Solana
    
    ## Основные возможности:
    
    * **🪙 Token Management** - Создание и управление токенами
    * **💱 Trading** - Торговля по бондинг-кривым
    * **👤 User Profiles** - Система пользователей и репутации
    * **📊 Analytics** - Аналитика и статистика
    * **🛡️ Security** - Комплексная система безопасности
    * **⚡ Real-time** - WebSocket обновления
    
    ## Архитектура:
    
    * FastAPI + SQLAlchemy + PostgreSQL
    * Redis для кэширования
    * Solana blockchain интеграция
    * Production-ready security
    """,
    version="1.0.0",
    contact={
        "name": "Anonymeme Team",
        "url": "https://anonymeme.com",
        "email": "dev@anonymeme.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Middleware настройка
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

app.add_middleware(SecurityMiddleware)
app.add_middleware(LoggingMiddleware)


# Dependency для получения сессии БД
async def get_db_session() -> AsyncSession:
    """Dependency для получения сессии базы данных"""
    async with app.state.db_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_redis() -> redis.Redis:
    """Dependency для получения Redis клиента"""
    return app.state.redis


async def get_solana_service() -> SolanaService:
    """Dependency для получения Solana сервиса"""
    return app.state.solana


async def get_cache_service() -> CacheService:
    """Dependency для получения Cache сервиса"""
    return app.state.cache


# Обработчики ошибок
@app.exception_handler(CustomHTTPException)
async def custom_http_exception_handler(request: Request, exc: CustomHTTPException):
    """Обработчик кастомных HTTP ошибок"""
    logger.error(f"Custom HTTP Exception: {exc.detail} - Path: {request.url.path}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "error_code": exc.error_code,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработчик ошибок валидации"""
    logger.error(f"Validation Error: {exc.errors()} - Path: {request.url.path}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "Validation error",
            "details": exc.errors(),
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Обработчик стандартных HTTP ошибок"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработчик всех остальных ошибок"""
    logger.error(f"Unhandled Exception: {str(exc)} - Path: {request.url.path}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "Internal server error" if not settings.DEBUG else str(exc),
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )


# Базовые endpoints
@app.get("/", tags=["System"])
async def root():
    """Корневой endpoint"""
    return {
        "message": "🚀 Anonymeme API v1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["System"])
async def health_check(
    db: AsyncSession = Depends(get_db_session),
    redis: redis.Redis = Depends(get_redis),
    solana: SolanaService = Depends(get_solana_service)
):
    """
    Комплексная проверка здоровья системы
    Проверяет доступность всех критических сервисов
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {}
        }
        
        # Проверка БД
        try:
            await db.execute("SELECT 1")
            health_status["services"]["database"] = "healthy"
        except Exception as e:
            health_status["services"]["database"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        # Проверка Redis
        try:
            await redis.ping()
            health_status["services"]["redis"] = "healthy"
        except Exception as e:
            health_status["services"]["redis"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        # Проверка Solana RPC
        try:
            await solana.get_health()
            health_status["services"]["solana"] = "healthy"
        except Exception as e:
            health_status["services"]["solana"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        return JSONResponse(content=health_status, status_code=status_code)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=503
        )


@app.get("/metrics", tags=["System"])
async def metrics(
    cache: CacheService = Depends(get_cache_service)
):
    """Метрики для мониторинга (Prometheus compatible)"""
    try:
        metrics = await cache.get_metrics()
        return {
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail="Metrics collection failed")


# Подключение роутеров
app.include_router(tokens.router, prefix="/api/v1/tokens", tags=["Tokens"])
app.include_router(trading.router, prefix="/api/v1/trading", tags=["Trading"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])


if __name__ == "__main__":
    """
    Точка входа для разработки
    В продакшене используем gunicorn или uvicorn напрямую
    """
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else 4,
        log_level="info"
    )