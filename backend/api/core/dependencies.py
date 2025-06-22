#!/usr/bin/env python3
"""
🔧 Dependency functions для FastAPI
Production-ready зависимости для инъекции в роутеры
"""

import jwt
from typing import Optional, AsyncGenerator
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as redis

from ..models.database import User, UserRole
from ..services.blockchain import SolanaService
from ..services.cache import CacheService
from ..core.config import settings


# Глобальные переменные для dependency injection
_db_session = None
_redis_client = None
_solana_service = None
_cache_service = None

def set_dependencies(db_session, redis_client, solana_service, cache_service):
    """Устанавливает глобальные dependency для использования в роутерах"""
    global _db_session, _redis_client, _solana_service, _cache_service
    _db_session = db_session
    _redis_client = redis_client
    _solana_service = solana_service
    _cache_service = cache_service


# === DATABASE DEPENDENCIES ===

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для получения сессии базы данных"""
    if not _db_session:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not initialized"
        )
    
    async with _db_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# === REDIS DEPENDENCIES ===

async def get_redis() -> redis.Redis:
    """Dependency для получения Redis клиента"""
    if not _redis_client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Redis not initialized"
        )
    return _redis_client


# === SERVICE DEPENDENCIES ===

async def get_solana_service() -> SolanaService:
    """Dependency для получения Solana сервиса"""
    if not _solana_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Solana service not initialized"
        )
    return _solana_service


async def get_cache_service() -> CacheService:
    """Dependency для получения Cache сервиса"""
    if not _cache_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cache service not initialized"
        )
    return _cache_service


# === AUTHENTICATION DEPENDENCIES ===

security = HTTPBearer(auto_error=False)

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Dependency для получения текущего пользователя (опционально)"""
    if not credentials:
        return None
    
    try:
        # Декодирование JWT токена
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
            
    except jwt.PyJWTError:
        return None
    
    # Получение пользователя из БД
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    return user


async def get_current_user(
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    """Dependency для получения текущего пользователя (обязательно)"""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def get_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency для получения активного пользователя"""
    if current_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active"
        )
    return current_user


# === ROLE-BASED DEPENDENCIES ===

async def get_admin_user(
    current_user: User = Depends(get_active_user)
) -> User:
    """Dependency для проверки прав администратора"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def get_super_admin_user(
    current_user: User = Depends(get_active_user)
) -> User:
    """Dependency для проверки прав суперадминистратора"""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )
    return current_user


async def get_moderator_user(
    current_user: User = Depends(get_active_user)
) -> User:
    """Dependency для проверки прав модератора"""
    if current_user.role not in [UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator privileges required"
        )
    return current_user


# === RATE LIMITING DEPENDENCIES ===

async def check_rate_limit(
    request: Request,
    redis: redis.Redis = Depends(get_redis)
) -> None:
    """Dependency для проверки rate limiting"""
    client_ip = request.client.host
    
    # Получение количества запросов за последний час
    key = f"rate_limit:{client_ip}"
    current_requests = await redis.get(key)
    
    if current_requests is None:
        await redis.setex(key, 3600, 1)  # 1 час
    else:
        current_requests = int(current_requests)
        if current_requests >= settings.RATE_LIMIT_REQUESTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        await redis.incr(key)


# === PAGINATION DEPENDENCIES ===

async def get_pagination_params(
    page: int = 1,
    limit: int = 20
) -> dict:
    """Dependency для параметров пагинации"""
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 20
        
    offset = (page - 1) * limit
    
    return {
        "page": page,
        "limit": limit,
        "offset": offset
    }


# === VALIDATION DEPENDENCIES ===

async def validate_wallet_signature(
    wallet_address: str,
    signature: str,
    message: str = None
) -> bool:
    """Dependency для валидации подписи кошелька"""
    try:
        # В реальной реализации здесь будет проверка подписи
        # используя библиотеки для работы с Solana
        
        # Заглушка для разработки
        return len(wallet_address) == 44 and len(signature) > 0
        
    except Exception:
        return False


# === SECURITY DEPENDENCIES ===

async def check_suspicious_activity(
    request: Request,
    redis: redis.Redis = Depends(get_redis)
) -> None:
    """Dependency для проверки подозрительной активности"""
    client_ip = request.client.host
    
    # Проверка блокировки IP
    blocked_key = f"blocked_ip:{client_ip}"
    if await redis.get(blocked_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="IP address is blocked"
        )


# === EXPORT ===

__all__ = [
    "get_db",
    "get_redis", 
    "get_solana_service",
    "get_cache_service",
    "get_current_user_optional",
    "get_current_user",
    "get_active_user",
    "get_admin_user",
    "get_super_admin_user",
    "get_moderator_user",
    "check_rate_limit",
    "get_pagination_params",
    "validate_wallet_signature",
    "check_suspicious_activity",
    "set_dependencies"
]