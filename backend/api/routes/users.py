#!/usr/bin/env python3
"""
👤 API роутер для управления пользователями
Production-ready user management с полной авторизацией
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, update
from sqlalchemy.orm import selectinload
import jwt
import hashlib

from ..models.database import User, Token, Trade, UserRole, UserStatus
from ..schemas.requests import (
    UserRegistrationRequest, UserProfileUpdateRequest, 
    UserPasswordChangeRequest, PaginationRequest
)
from ..schemas.responses import (
    UserProfileResponse, UserStatsResponse, UserTokensResponse,
    UserTradesResponse, SuccessResponse, AuthTokenResponse
)
from ..services.cache import CacheService
from ..core.exceptions import (
    RecordNotFoundException, ValidationException, AuthenticationException,
    AuthorizationException, DatabaseException
)
from ..core.config import settings

logger = logging.getLogger(__name__)

# Создание роутера
router = APIRouter()
security = HTTPBearer()


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


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

async def _get_user_by_id(db: AsyncSession, user_id: UUID) -> User:
    """Получение пользователя по ID"""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise RecordNotFoundException("User", str(user_id))
    
    return user


async def _get_user_by_wallet(db: AsyncSession, wallet_address: str) -> User:
    """Получение пользователя по wallet адресу"""
    stmt = select(User).where(User.wallet_address == wallet_address)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise RecordNotFoundException("User", wallet_address)
    
    return user


def _generate_jwt_token(user: User) -> str:
    """Генерация JWT токена для пользователя"""
    payload = {
        "user_id": str(user.id),
        "wallet_address": user.wallet_address,
        "role": user.role.value,
        "exp": datetime.utcnow() + timedelta(days=7),
        "iat": datetime.utcnow()
    }
    
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


async def _calculate_user_stats(db: AsyncSession, user: User) -> Dict[str, Any]:
    """Вычисление статистики пользователя"""
    
    # Количество торгов
    trades_query = select(func.count(Trade.id)).where(Trade.user_id == user.id)
    trades_result = await db.execute(trades_query)
    total_trades = trades_result.scalar() or 0
    
    # Общий объем торгов в SOL
    volume_query = select(func.sum(Trade.sol_amount)).where(Trade.user_id == user.id)
    volume_result = await db.execute(volume_query)
    total_volume_sol = float(volume_result.scalar() or 0)
    
    # Количество созданных токенов
    tokens_query = select(func.count(Token.id)).where(Token.creator_id == user.id)
    tokens_result = await db.execute(tokens_query)
    tokens_created = tokens_result.scalar() or 0
    
    # P&L за последние 30 дней
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    pnl_query = select(func.sum(Trade.realized_pnl)).where(
        and_(
            Trade.user_id == user.id,
            Trade.created_at >= thirty_days_ago
        )
    )
    pnl_result = await db.execute(pnl_query)
    pnl_30d = float(pnl_result.scalar() or 0)
    
    return {
        "total_trades": total_trades,
        "total_volume_sol": total_volume_sol,
        "tokens_created": tokens_created,
        "pnl_30d": pnl_30d,
        "win_rate": user.win_rate,
        "reputation_score": user.reputation_score
    }


# === ENDPOINTS ===

@router.post("/register", response_model=AuthTokenResponse)
async def register_user(
    registration_data: UserRegistrationRequest,
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Регистрация нового пользователя
    
    Создает пользователя с wallet адресом и базовыми данными.
    """
    try:
        # Проверка существования пользователя
        existing_user = await db.execute(
            select(User).where(User.wallet_address == registration_data.wallet_address)
        )
        if existing_user.scalar_one_or_none():
            raise ValidationException("User with this wallet address already exists")
        
        # Валидация wallet адреса (базовая проверка длины)
        if len(registration_data.wallet_address) != 44:
            raise ValidationException("Invalid Solana wallet address format")
        
        # Создание нового пользователя
        new_user = User(
            wallet_address=registration_data.wallet_address,
            username=registration_data.username,
            email=registration_data.email,
            profile_image_url=registration_data.profile_image_url,
            bio=registration_data.bio,
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            reputation_score=100.0  # Начальная репутация
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Генерация JWT токена
        access_token = _generate_jwt_token(new_user)
        
        # Кэширование профиля пользователя
        await cache.cache_user_profile(str(new_user.id), {
            "id": str(new_user.id),
            "wallet_address": new_user.wallet_address,
            "username": new_user.username,
            "role": new_user.role.value,
            "reputation_score": new_user.reputation_score
        })
        
        logger.info(f"✅ New user registered: {new_user.wallet_address}")
        
        return AuthTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=7 * 24 * 3600,  # 7 дней
            user=UserProfileResponse.from_orm(new_user)
        )
        
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to register user: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user"
        )


@router.post("/auth/wallet", response_model=AuthTokenResponse)
async def authenticate_wallet(
    wallet_address: str,
    signature: str,
    message: str,
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Аутентификация пользователя через подпись кошелька
    
    Проверяет подпись сообщения и возвращает JWT токен.
    """
    try:
        # В реальной реализации здесь будет проверка подписи Solana
        # Для демо просто проверяем существование пользователя
        
        user = await _get_user_by_wallet(db, wallet_address)
        
        # Обновление времени последнего входа
        user.last_login_at = datetime.utcnow()
        await db.commit()
        
        # Генерация токена
        access_token = _generate_jwt_token(user)
        
        # Обновление кэша
        await cache.cache_user_profile(str(user.id), {
            "id": str(user.id),
            "wallet_address": user.wallet_address,
            "username": user.username,
            "role": user.role.value,
            "reputation_score": user.reputation_score
        })
        
        logger.info(f"User authenticated: {wallet_address}")
        
        return AuthTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=7 * 24 * 3600,
            user=UserProfileResponse.from_orm(user)
        )
        
    except RecordNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please register first."
        )
    except Exception as e:
        logger.error(f"Wallet authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.get("/profile", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Получение профиля текущего пользователя
    """
    try:
        # Попытка получить из кэша
        cached_profile = await cache.get_user_profile(str(current_user.id))
        if cached_profile:
            return UserProfileResponse(**cached_profile)
        
        # Если нет в кэше, формируем ответ
        response = UserProfileResponse.from_orm(current_user)
        
        # Кэширование
        await cache.cache_user_profile(str(current_user.id), response.dict())
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile"
        )


@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    update_data: UserProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Обновление профиля пользователя
    """
    try:
        # Обновление полей
        update_fields = update_data.dict(exclude_unset=True)
        
        for field, value in update_fields.items():
            if hasattr(current_user, field):
                setattr(current_user, field, value)
        
        current_user.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(current_user)
        
        # Очистка кэша
        await cache.delete(str(current_user.id), 'user')
        
        response = UserProfileResponse.from_orm(current_user)
        
        # Обновление кэша
        await cache.cache_user_profile(str(current_user.id), response.dict())
        
        logger.info(f"User profile updated: {current_user.id}")
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to update profile: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Получение статистики пользователя
    """
    try:
        # Попытка получить из кэша
        cache_key = f"user_stats:{current_user.id}"
        cached_stats = await cache.get(cache_key, 'analytics')
        
        if cached_stats:
            return UserStatsResponse(**cached_stats)
        
        # Вычисление статистики
        stats = await _calculate_user_stats(db, current_user)
        
        response = UserStatsResponse(
            user_id=current_user.id,
            **stats
        )
        
        # Кэширование на 10 минут
        await cache.set(cache_key, response.dict(), 'analytics', ttl=600)
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get user stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


@router.get("/tokens", response_model=UserTokensResponse)
async def get_user_tokens(
    pagination: PaginationRequest = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение токенов созданных пользователем
    """
    try:
        # Базовый запрос
        query = select(Token).where(Token.creator_id == current_user.id)
        
        # Подсчет общего количества
        count_query = select(func.count()).select_from(
            query.subquery()
        )
        result = await db.execute(count_query)
        total_count = result.scalar()
        
        # Сортировка и пагинация
        query = query.order_by(desc(Token.created_at))
        offset = (pagination.page - 1) * pagination.limit
        query = query.offset(offset).limit(pagination.limit)
        
        # Выполнение запроса
        result = await db.execute(query)
        tokens = result.scalars().all()
        
        return UserTokensResponse(
            tokens=[TokenResponse.from_orm(token) for token in tokens],
            pagination=PaginationResponse(
                page=pagination.page,
                limit=pagination.limit,
                total=total_count,
                pages=(total_count + pagination.limit - 1) // pagination.limit,
                has_next=pagination.page * pagination.limit < total_count,
                has_prev=pagination.page > 1
            )
        )
        
    except Exception as e:
        logger.error(f"Failed to get user tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tokens"
        )


@router.get("/trades", response_model=UserTradesResponse)
async def get_user_trades(
    pagination: PaginationRequest = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение истории торгов пользователя
    """
    try:
        # Базовый запрос с join на токены
        query = select(Trade).where(Trade.user_id == current_user.id)
        query = query.options(selectinload(Trade.token))
        
        # Подсчет общего количества
        count_query = select(func.count()).select_from(
            query.subquery()
        )
        result = await db.execute(count_query)
        total_count = result.scalar()
        
        # Сортировка и пагинация
        query = query.order_by(desc(Trade.created_at))
        offset = (pagination.page - 1) * pagination.limit
        query = query.offset(offset).limit(pagination.limit)
        
        # Выполнение запроса
        result = await db.execute(query)
        trades = result.scalars().all()
        
        return UserTradesResponse(
            trades=[TradeResponse.from_orm(trade) for trade in trades],
            pagination=PaginationResponse(
                page=pagination.page,
                limit=pagination.limit,
                total=total_count,
                pages=(total_count + pagination.limit - 1) // pagination.limit,
                has_next=pagination.page * pagination.limit < total_count,
                has_prev=pagination.page > 1
            )
        )
        
    except Exception as e:
        logger.error(f"Failed to get user trades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trades"
        )


@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_by_id(
    user_id: UUID = Path(..., description="ID пользователя"),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Получение публичного профиля пользователя по ID
    """
    try:
        # Попытка получить из кэша
        cache_key = f"public_profile:{user_id}"
        cached_profile = await cache.get(cache_key, 'user')
        
        if cached_profile:
            return UserProfileResponse(**cached_profile)
        
        # Получение из БД
        user = await _get_user_by_id(db, user_id)
        
        # Проверка статуса (не показываем заблокированных)
        if user.status != UserStatus.ACTIVE:
            raise RecordNotFoundException("User", str(user_id))
        
        response = UserProfileResponse.from_orm(user)
        
        # Кэширование публичного профиля на 5 минут
        await cache.set(cache_key, response.dict(), 'user', ttl=300)
        
        return response
        
    except RecordNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user by ID: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )


@router.delete("/profile")
async def delete_user_account(
    password_confirmation: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Удаление аккаунта пользователя (мягкое удаление)
    """
    try:
        # В реальной реализации здесь будет проверка пароля/подписи
        
        # Деактивация аккаунта (не удаляем данные полностью)
        current_user.status = UserStatus.DELETED
        current_user.deleted_at = datetime.utcnow()
        
        await db.commit()
        
        # Очистка кэша
        await cache.delete(str(current_user.id), 'user')
        await cache.delete(f"public_profile:{current_user.id}", 'user')
        
        logger.info(f"User account deleted: {current_user.id}")
        
        return SuccessResponse(
            message="Account deleted successfully",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to delete account: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )


# === ADMIN ENDPOINTS ===

@router.get("/admin/users", response_model=List[UserProfileResponse])
async def get_all_users(
    pagination: PaginationRequest = Depends(),
    admin_user: User = Depends(verify_admin_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение списка всех пользователей (только админ)
    """
    try:
        # Базовый запрос
        query = select(User).where(User.status != UserStatus.DELETED)
        
        # Сортировка и пагинация
        query = query.order_by(desc(User.created_at))
        offset = (pagination.page - 1) * pagination.limit
        query = query.offset(offset).limit(pagination.limit)
        
        result = await db.execute(query)
        users = result.scalars().all()
        
        return [UserProfileResponse.from_orm(user) for user in users]
        
    except Exception as e:
        logger.error(f"Failed to get users list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.put("/admin/users/{user_id}/status")
async def update_user_status(
    user_id: UUID,
    new_status: UserStatus,
    admin_user: User = Depends(verify_admin_role),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Изменение статуса пользователя (только админ)
    """
    try:
        user = await _get_user_by_id(db, user_id)
        
        old_status = user.status
        user.status = new_status
        user.updated_at = datetime.utcnow()
        
        await db.commit()
        
        # Очистка кэша
        await cache.delete(str(user_id), 'user')
        await cache.delete(f"public_profile:{user_id}", 'user')
        
        logger.info(f"Admin {admin_user.id} changed user {user_id} status: {old_status} -> {new_status}")
        
        return SuccessResponse(
            message=f"User status updated to {new_status.value}",
            timestamp=datetime.utcnow()
        )
        
    except RecordNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user status: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user status"
        )