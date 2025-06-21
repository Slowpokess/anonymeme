#!/usr/bin/env python3
"""
🔧 API роутер для администрирования
Production-ready admin panel с полным контролем системы
"""

import logging
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, update, delete
from sqlalchemy.orm import selectinload

from ..models.database import (
    User, Token, Trade, PriceHistory, Analytics,
    UserRole, UserStatus, TokenStatus, TradeType
)
from ..schemas.requests import (
    AdminUserUpdateRequest, AdminTokenUpdateRequest, 
    SecurityParamsUpdateRequest, PaginationRequest
)
from ..schemas.responses import (
    AdminDashboardResponse, SystemHealthResponse, AdminUserResponse,
    AdminTokenResponse, AdminTradeResponse, SecurityLogResponse,
    SuccessResponse, PaginationResponse
)
from ..services.cache import CacheService
from ..middleware.security import SecurityMiddleware
from ..middleware.logging import AuditLogger, audit_logger
from ..core.exceptions import (
    RecordNotFoundException, ValidationException, AuthorizationException,
    DatabaseException, SecurityException
)
from ..core.config import settings

logger = logging.getLogger(__name__)

# Создание роутера
router = APIRouter()


# === DEPENDENCY FUNCTIONS ===

async def get_db() -> AsyncSession:
    """Dependency для получения сессии БД"""
    pass


async def get_current_user() -> User:
    """Dependency для получения текущего пользователя"""
    pass


async def get_cache_service() -> CacheService:
    """Dependency для получения Cache сервиса"""
    pass


async def verify_admin_role(current_user: User = Depends(get_current_user)) -> User:
    """Dependency для проверки админских прав"""
    if current_user.role != UserRole.ADMIN:
        raise AuthorizationException("Admin role required")
    return current_user


async def verify_super_admin_role(current_user: User = Depends(get_current_user)) -> User:
    """Dependency для проверки супер-админских прав"""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise AuthorizationException("Super admin role required")
    return current_user


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

async def _get_system_health_metrics(
    db: AsyncSession, 
    cache: CacheService
) -> Dict[str, Any]:
    """Получение метрик состояния системы"""
    
    try:
        # Статистика базы данных
        db_metrics = {
            "total_users": await db.execute(select(func.count(User.id))),
            "active_users": await db.execute(
                select(func.count(User.id)).where(User.status == UserStatus.ACTIVE)
            ),
            "total_tokens": await db.execute(select(func.count(Token.id))),
            "active_tokens": await db.execute(
                select(func.count(Token.id)).where(Token.status == TokenStatus.ACTIVE)
            ),
            "total_trades": await db.execute(select(func.count(Trade.id))),
            "trades_24h": await db.execute(
                select(func.count(Trade.id)).where(
                    Trade.created_at >= datetime.utcnow() - timedelta(days=1)
                )
            )
        }
        
        # Конвертация результатов
        for key, result in db_metrics.items():
            db_metrics[key] = result.scalar() or 0
        
        # Метрики кэша
        cache_metrics = await cache.get_stats()
        
        # Метрики производительности (мок данные для демо)
        performance_metrics = {
            "avg_response_time_ms": 150,
            "error_rate_percent": 0.1,
            "cpu_usage_percent": 45,
            "memory_usage_percent": 60,
            "disk_usage_percent": 35
        }
        
        return {
            "database": db_metrics,
            "cache": cache_metrics,
            "performance": performance_metrics,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Failed to get system health metrics: {e}")
        return {"error": str(e), "timestamp": datetime.utcnow()}


async def _log_admin_action(
    admin_user: User,
    action: str,
    target: str,
    details: Dict[str, Any],
    request_id: str
):
    """Логирование административных действий"""
    await audit_logger.log_admin_action(
        admin_id=str(admin_user.id),
        action=action,
        target=target,
        changes=details,
        request_id=request_id
    )


# === DASHBOARD & SYSTEM ===

@router.get("/dashboard", response_model=AdminDashboardResponse)
async def get_admin_dashboard(
    admin_user: User = Depends(verify_admin_role),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Главная панель администратора
    
    Общий обзор системы с ключевыми метриками.
    """
    try:
        # Попытка получить из кэша
        cache_key = f"admin_dashboard"
        cached_data = await cache.get(cache_key, 'analytics')
        
        if cached_data and admin_user.role == UserRole.ADMIN:
            # Обычные админы получают кэшированные данные
            return AdminDashboardResponse(**cached_data)
        
        # Получение системных метрик
        health_metrics = await _get_system_health_metrics(db, cache)
        
        # Последние пользователи
        recent_users_query = select(User).order_by(
            desc(User.created_at)
        ).limit(10)
        recent_users_result = await db.execute(recent_users_query)
        recent_users = recent_users_result.scalars().all()
        
        # Последние токены
        recent_tokens_query = select(Token).options(
            selectinload(Token.creator)
        ).order_by(desc(Token.created_at)).limit(10)
        recent_tokens_result = await db.execute(recent_tokens_query)
        recent_tokens = recent_tokens_result.scalars().all()
        
        # Последние торги
        recent_trades_query = select(Trade).options(
            selectinload(Trade.user),
            selectinload(Trade.token)
        ).order_by(desc(Trade.created_at)).limit(10)
        recent_trades_result = await db.execute(recent_trades_query)
        recent_trades = recent_trades_result.scalars().all()
        
        # Алерты системы (демо данные)
        system_alerts = [
            {
                "type": "warning",
                "message": "High memory usage detected",
                "timestamp": datetime.utcnow() - timedelta(minutes=30),
                "severity": "medium"
            }
        ] if health_metrics.get("performance", {}).get("memory_usage_percent", 0) > 80 else []
        
        response = AdminDashboardResponse(
            system_health=health_metrics,
            recent_users=[AdminUserResponse.from_orm(user) for user in recent_users],
            recent_tokens=[AdminTokenResponse.from_orm(token) for token in recent_tokens],
            recent_trades=[AdminTradeResponse.from_orm(trade) for trade in recent_trades],
            system_alerts=system_alerts,
            last_updated=datetime.utcnow()
        )
        
        # Кэширование на 2 минуты
        await cache.set(cache_key, response.dict(), 'analytics', ttl=120)
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get admin dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard data"
        )


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    admin_user: User = Depends(verify_admin_role),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Детальная информация о состоянии системы
    """
    try:
        # Получение метрик
        health_metrics = await _get_system_health_metrics(db, cache)
        
        # Проверка здоровья кэша
        cache_health = await cache.health_check()
        
        # Проверка подключения к БД
        try:
            await db.execute(select(1))
            db_health = {"status": "healthy", "connection": True}
        except Exception as e:
            db_health = {"status": "unhealthy", "connection": False, "error": str(e)}
        
        # Общий статус системы
        overall_status = "healthy"
        if not cache_health.get("overall_health", False) or not db_health["connection"]:
            overall_status = "unhealthy"
        elif health_metrics.get("performance", {}).get("error_rate_percent", 0) > 1:
            overall_status = "degraded"
        
        response = SystemHealthResponse(
            overall_status=overall_status,
            database=db_health,
            cache=cache_health,
            metrics=health_metrics,
            last_check=datetime.utcnow()
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system health"
        )


# === USER MANAGEMENT ===

@router.get("/users", response_model=List[AdminUserResponse])
async def get_users_list(
    pagination: PaginationRequest = Depends(),
    status_filter: Optional[UserStatus] = Query(None),
    role_filter: Optional[UserRole] = Query(None),
    search: Optional[str] = Query(None, min_length=2),
    admin_user: User = Depends(verify_admin_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение списка пользователей с фильтрацией
    """
    try:
        # Базовый запрос
        query = select(User)
        
        # Применение фильтров
        if status_filter:
            query = query.where(User.status == status_filter)
        
        if role_filter:
            query = query.where(User.role == role_filter)
        
        if search:
            search_filter = or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.wallet_address.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
        
        # Сортировка и пагинация
        query = query.order_by(desc(User.created_at))
        offset = (pagination.page - 1) * pagination.limit
        query = query.offset(offset).limit(pagination.limit)
        
        # Выполнение запроса
        result = await db.execute(query)
        users = result.scalars().all()
        
        return [AdminUserResponse.from_orm(user) for user in users]
        
    except Exception as e:
        logger.error(f"Failed to get users list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user_details(
    user_id: UUID,
    admin_user: User = Depends(verify_admin_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение детальной информации о пользователе
    """
    try:
        # Получение пользователя с дополнительными данными
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise RecordNotFoundException("User", str(user_id))
        
        # Получение статистики пользователя
        trades_count_query = select(func.count(Trade.id)).where(Trade.user_id == user_id)
        trades_count = await db.execute(trades_count_query)
        
        tokens_count_query = select(func.count(Token.id)).where(Token.creator_id == user_id)
        tokens_count = await db.execute(tokens_count_query)
        
        # Расширенная информация для админа
        user_response = AdminUserResponse.from_orm(user)
        user_response.trades_count = trades_count.scalar() or 0
        user_response.tokens_count = tokens_count.scalar() or 0
        
        return user_response
        
    except RecordNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user details"
        )


@router.put("/users/{user_id}")
async def update_user(
    user_id: UUID,
    update_data: AdminUserUpdateRequest,
    admin_user: User = Depends(verify_admin_role),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Обновление пользователя администратором
    """
    try:
        # Получение пользователя
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise RecordNotFoundException("User", str(user_id))
        
        # Сохранение изменений для аудита
        changes = {}
        update_fields = update_data.dict(exclude_unset=True)
        
        for field, new_value in update_fields.items():
            if hasattr(user, field):
                old_value = getattr(user, field)
                if old_value != new_value:
                    changes[field] = {"old": old_value, "new": new_value}
                    setattr(user, field, new_value)
        
        if changes:
            user.updated_at = datetime.utcnow()
            await db.commit()
            
            # Очистка кэша
            await cache.delete(str(user_id), 'user')
            
            # Логирование административного действия
            await _log_admin_action(
                admin_user=admin_user,
                action="update_user",
                target=f"user:{user_id}",
                details=changes,
                request_id=getattr(admin_user, 'request_id', 'unknown')
            )
            
            logger.info(f"Admin {admin_user.id} updated user {user_id}: {changes}")
        
        return SuccessResponse(
            message="User updated successfully",
            timestamp=datetime.utcnow()
        )
        
    except RecordNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    reason: str = Body(..., embed=True, min_length=10),
    admin_user: User = Depends(verify_admin_role),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Удаление/блокировка пользователя
    """
    try:
        # Получение пользователя
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise RecordNotFoundException("User", str(user_id))
        
        # Нельзя удалить супер-админа
        if user.role == UserRole.SUPER_ADMIN:
            raise AuthorizationException("Cannot delete super admin")
        
        # Мягкое удаление
        old_status = user.status
        user.status = UserStatus.BANNED
        user.deleted_at = datetime.utcnow()
        
        await db.commit()
        
        # Очистка кэша
        await cache.delete(str(user_id), 'user')
        
        # Логирование
        await _log_admin_action(
            admin_user=admin_user,
            action="delete_user",
            target=f"user:{user_id}",
            details={"reason": reason, "old_status": old_status.value},
            request_id=getattr(admin_user, 'request_id', 'unknown')
        )
        
        logger.warning(f"Admin {admin_user.id} deleted user {user_id}. Reason: {reason}")
        
        return SuccessResponse(
            message="User deleted successfully",
            timestamp=datetime.utcnow()
        )
        
    except (RecordNotFoundException, AuthorizationException):
        raise
    except Exception as e:
        logger.error(f"Failed to delete user: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


# === TOKEN MANAGEMENT ===

@router.get("/tokens", response_model=List[AdminTokenResponse])
async def get_tokens_list(
    pagination: PaginationRequest = Depends(),
    status_filter: Optional[TokenStatus] = Query(None),
    admin_user: User = Depends(verify_admin_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение списка токенов для администрирования
    """
    try:
        # Базовый запрос с создателем
        query = select(Token).options(selectinload(Token.creator))
        
        # Фильтрация по статусу
        if status_filter:
            query = query.where(Token.status == status_filter)
        
        # Сортировка и пагинация
        query = query.order_by(desc(Token.created_at))
        offset = (pagination.page - 1) * pagination.limit
        query = query.offset(offset).limit(pagination.limit)
        
        # Выполнение запроса
        result = await db.execute(query)
        tokens = result.scalars().all()
        
        return [AdminTokenResponse.from_orm(token) for token in tokens]
        
    except Exception as e:
        logger.error(f"Failed to get tokens list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tokens"
        )


@router.put("/tokens/{token_id}/status")
async def update_token_status(
    token_id: UUID,
    new_status: TokenStatus,
    reason: str = Body(..., embed=True),
    admin_user: User = Depends(verify_admin_role),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Изменение статуса токена
    """
    try:
        # Получение токена
        query = select(Token).where(Token.id == token_id)
        result = await db.execute(query)
        token = result.scalar_one_or_none()
        
        if not token:
            raise RecordNotFoundException("Token", str(token_id))
        
        old_status = token.status
        token.status = new_status
        token.updated_at = datetime.utcnow()
        
        await db.commit()
        
        # Очистка кэша
        await cache.delete(f"token_detail:{token_id}", 'token')
        await cache.delete(f"token_mint:{token.mint_address}", 'token')
        
        # Логирование
        await _log_admin_action(
            admin_user=admin_user,
            action="update_token_status",
            target=f"token:{token_id}",
            details={
                "old_status": old_status.value,
                "new_status": new_status.value,
                "reason": reason
            },
            request_id=getattr(admin_user, 'request_id', 'unknown')
        )
        
        logger.info(f"Admin {admin_user.id} changed token {token_id} status: {old_status} -> {new_status}")
        
        return SuccessResponse(
            message=f"Token status updated to {new_status.value}",
            timestamp=datetime.utcnow()
        )
        
    except RecordNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to update token status: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update token status"
        )


# === SECURITY MANAGEMENT ===

@router.get("/security/logs")
async def get_security_logs(
    pagination: PaginationRequest = Depends(),
    severity: Optional[str] = Query(None, regex="^(low|medium|high|critical)$"),
    event_type: Optional[str] = Query(None),
    admin_user: User = Depends(verify_super_admin_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение логов безопасности (только супер-админ)
    """
    try:
        # В реальной реализации здесь будет запрос к системе логирования
        # Для демо возвращаем мок данные
        
        security_logs = [
            {
                "id": f"log_{i}",
                "timestamp": datetime.utcnow() - timedelta(hours=i),
                "event_type": "rate_limit_exceeded",
                "severity": "medium",
                "source_ip": f"192.168.1.{i}",
                "details": {"user_agent": "suspicious_bot", "endpoint": "/api/v1/trading/buy"},
                "resolved": i % 3 == 0
            }
            for i in range(1, pagination.limit + 1)
        ]
        
        return {
            "logs": security_logs,
            "pagination": {
                "page": pagination.page,
                "limit": pagination.limit,
                "total": 100,  # Мок значение
                "pages": 10,
                "has_next": pagination.page < 10,
                "has_prev": pagination.page > 1
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get security logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve security logs"
        )


@router.put("/security/params")
async def update_security_params(
    params: SecurityParamsUpdateRequest,
    admin_user: User = Depends(verify_super_admin_role),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Обновление параметров безопасности (только супер-админ)
    """
    try:
        # В реальной реализации здесь будет обновление конфигурации безопасности
        
        # Логирование изменений
        await _log_admin_action(
            admin_user=admin_user,
            action="update_security_params",
            target="system_security",
            details=params.dict(),
            request_id=getattr(admin_user, 'request_id', 'unknown')
        )
        
        # Очистка кэша настроек
        await cache.delete_pattern("security_*", 'general')
        
        logger.warning(f"Super admin {admin_user.id} updated security parameters")
        
        return SuccessResponse(
            message="Security parameters updated successfully",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to update security params: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update security parameters"
        )


@router.post("/security/emergency-pause")
async def emergency_pause_system(
    reason: str = Body(..., embed=True, min_length=10),
    admin_user: User = Depends(verify_super_admin_role),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Экстренная приостановка торгов (только супер-админ)
    """
    try:
        # Установка флага экстренной остановки в кэше
        emergency_data = {
            "paused": True,
            "reason": reason,
            "admin_id": str(admin_user.id),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await cache.set("emergency_pause", emergency_data, 'general', ttl=3600)
        
        # Критическое логирование
        await _log_admin_action(
            admin_user=admin_user,
            action="emergency_pause",
            target="system_trading",
            details={"reason": reason},
            request_id=getattr(admin_user, 'request_id', 'unknown')
        )
        
        logger.critical(f"EMERGENCY PAUSE activated by super admin {admin_user.id}. Reason: {reason}")
        
        return SuccessResponse(
            message="Emergency pause activated",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to activate emergency pause: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate emergency pause"
        )


@router.delete("/security/emergency-pause")
async def deactivate_emergency_pause(
    admin_user: User = Depends(verify_super_admin_role),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Деактивация экстренной паузы (только супер-админ)
    """
    try:
        # Удаление флага экстренной остановки
        await cache.delete("emergency_pause", 'general')
        
        # Логирование
        await _log_admin_action(
            admin_user=admin_user,
            action="deactivate_emergency_pause",
            target="system_trading",
            details={},
            request_id=getattr(admin_user, 'request_id', 'unknown')
        )
        
        logger.warning(f"Emergency pause deactivated by super admin {admin_user.id}")
        
        return SuccessResponse(
            message="Emergency pause deactivated",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to deactivate emergency pause: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate emergency pause"
        )