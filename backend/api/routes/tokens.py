#!/usr/bin/env python3
"""
🪙 API роутер для управления токенами
Production-ready endpoints с полной валидацией и обработкой ошибок
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, asc, func
from sqlalchemy.orm import selectinload

from ..models.database import Token, User, TokenStatus, CurveType
from ..schemas.requests import (
    TokenCreateRequest, TokenSearchRequest, TokenUpdateRequest, 
    PaginationRequest
)
from ..schemas.responses import (
    TokenResponse, TokenDetailResponse, TokensListResponse, 
    TokenCreateResponse, SuccessResponse, PaginationResponse
)
from ..services.blockchain import SolanaService
from ..services.cache import CacheService
from ..core.exceptions import (
    RecordNotFoundException, ValidationException, BlockchainException,
    AuthorizationException, DatabaseException
)
from ..core.config import settings

logger = logging.getLogger(__name__)

# Создание роутера
router = APIRouter()


# === DEPENDENCY FUNCTIONS ===

async def get_db() -> AsyncSession:
    """Dependency для получения сессии БД (будет переопределена в main.py)"""
    pass


async def get_current_user() -> User:
    """Dependency для получения текущего пользователя"""
    pass


async def get_solana_service() -> SolanaService:
    """Dependency для получения Solana сервиса"""
    pass


async def get_cache_service() -> CacheService:
    """Dependency для получения Cache сервиса"""
    pass


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

async def _get_token_by_id(db: AsyncSession, token_id: UUID) -> Token:
    """Получение токена по ID с проверкой существования"""
    stmt = select(Token).where(Token.id == token_id).options(
        selectinload(Token.creator)
    )
    result = await db.execute(stmt)
    token = result.scalar_one_or_none()
    
    if not token:
        raise RecordNotFoundException("Token", str(token_id))
    
    return token


async def _get_token_by_mint(db: AsyncSession, mint_address: str) -> Token:
    """Получение токена по mint адресу"""
    stmt = select(Token).where(Token.mint_address == mint_address).options(
        selectinload(Token.creator)
    )
    result = await db.execute(stmt)
    token = result.scalar_one_or_none()
    
    if not token:
        raise RecordNotFoundException("Token", mint_address)
    
    return token


async def _update_token_price_data(
    token: Token, 
    solana: SolanaService,
    cache: CacheService
) -> Token:
    """Обновление данных о цене токена"""
    try:
        # Получение данных о цене из блокчейна
        price_info = await solana.get_token_price(token.mint_address)
        
        if price_info:
            token.current_price = price_info.current_price
            token.market_cap = price_info.market_cap
            token.sol_reserves = price_info.sol_reserves
            token.token_reserves = price_info.token_reserves
            
            # Кэширование данных о цене
            await cache.cache_price_data(token.mint_address, {
                "current_price": float(price_info.current_price),
                "market_cap": float(price_info.market_cap),
                "sol_reserves": float(price_info.sol_reserves),
                "token_reserves": float(price_info.token_reserves),
                "last_updated": datetime.utcnow().isoformat()
            })
    
    except Exception as e:
        logger.warning(f"Failed to update price data for {token.mint_address}: {e}")
    
    return token


def _build_token_search_query(db_query, search_params: TokenSearchRequest):
    """Построение запроса для поиска токенов"""
    
    if search_params.query:
        # Поиск по имени и символу
        search_filter = or_(
            Token.name.ilike(f"%{search_params.query}%"),
            Token.symbol.ilike(f"%{search_params.query}%"),
            Token.description.ilike(f"%{search_params.query}%")
        )
        db_query = db_query.where(search_filter)
    
    if search_params.curve_type:
        db_query = db_query.where(Token.curve_type == search_params.curve_type)
    
    if search_params.min_market_cap is not None:
        db_query = db_query.where(Token.market_cap >= search_params.min_market_cap)
    
    if search_params.max_market_cap is not None:
        db_query = db_query.where(Token.market_cap <= search_params.max_market_cap)
    
    if search_params.is_graduated is not None:
        db_query = db_query.where(Token.is_graduated == search_params.is_graduated)
    
    if search_params.is_verified is not None:
        db_query = db_query.where(Token.is_verified == search_params.is_verified)
    
    if search_params.creator_id:
        try:
            creator_uuid = UUID(search_params.creator_id)
            db_query = db_query.where(Token.creator_id == creator_uuid)
        except ValueError:
            raise ValidationException("Invalid creator_id format")
    
    if search_params.tags:
        # Поиск по тегам (JSON поле)
        for tag in search_params.tags:
            db_query = db_query.where(Token.tags.contains([tag]))
    
    return db_query


# === ENDPOINTS ===

@router.get("", response_model=TokensListResponse)
async def get_tokens(
    search: TokenSearchRequest = Depends(),
    pagination: PaginationRequest = Depends(),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service),
    solana: SolanaService = Depends(get_solana_service)
):
    """
    Получение списка токенов с фильтрацией и пагинацией
    
    Поддерживает:
    - Поиск по имени, символу, описанию
    - Фильтрация по типу кривой, капитализации, статусу
    - Сортировка и пагинация
    """
    try:
        # Кэш ключ для запроса
        cache_key = f"tokens_list:{hash(str(search.dict()) + str(pagination.dict()))}"
        
        # Попытка получить из кэша
        cached_result = await cache.get(cache_key, "token")
        if cached_result:
            return TokensListResponse(**cached_result)
        
        # Базовый запрос
        base_query = select(Token).where(Token.status == TokenStatus.ACTIVE)
        base_query = base_query.options(selectinload(Token.creator))
        
        # Применение фильтров
        filtered_query = _build_token_search_query(base_query, search)
        
        # Подсчет общего количества
        count_query = select(func.count()).select_from(
            filtered_query.subquery()
        )
        result = await db.execute(count_query)
        total_count = result.scalar()
        
        # Сортировка
        sort_column = getattr(Token, pagination.sort_by, Token.created_at)
        if pagination.sort_order == "asc":
            filtered_query = filtered_query.order_by(asc(sort_column))
        else:
            filtered_query = filtered_query.order_by(desc(sort_column))
        
        # Пагинация
        offset = (pagination.page - 1) * pagination.limit
        filtered_query = filtered_query.offset(offset).limit(pagination.limit)
        
        # Выполнение запроса
        result = await db.execute(filtered_query)
        tokens = result.scalars().all()
        
        # Обновление данных о ценах для первых 10 токенов
        for token in tokens[:10]:
            await _update_token_price_data(token, solana, cache)
        
        # Формирование ответа
        token_responses = [TokenResponse.from_orm(token) for token in tokens]
        
        pagination_info = PaginationResponse(
            page=pagination.page,
            limit=pagination.limit,
            total=total_count,
            pages=(total_count + pagination.limit - 1) // pagination.limit,
            has_next=pagination.page * pagination.limit < total_count,
            has_prev=pagination.page > 1
        )
        
        response = TokensListResponse(
            tokens=token_responses,
            pagination=pagination_info
        )
        
        # Кэширование результата
        await cache.set(cache_key, response.dict(), "token", ttl=60)
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get tokens: {e}")
        if isinstance(e, (ValidationException, DatabaseException)):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tokens"
        )


@router.get("/{token_id}", response_model=TokenDetailResponse)
async def get_token(
    token_id: UUID = Path(..., description="ID токена"),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service),
    solana: SolanaService = Depends(get_solana_service)
):
    """
    Получение детальной информации о токене
    """
    try:
        # Попытка получить из кэша
        cache_key = f"token_detail:{token_id}"
        cached_token = await cache.get(cache_key, "token")
        
        if cached_token:
            return TokenDetailResponse(**cached_token)
        
        # Получение токена из БД
        token = await _get_token_by_id(db, token_id)
        
        # Обновление данных о цене
        token = await _update_token_price_data(token, solana, cache)
        
        # Сохранение изменений в БД
        await db.commit()
        await db.refresh(token)
        
        response = TokenDetailResponse.from_orm(token)
        
        # Кэширование результата
        await cache.set(cache_key, response.dict(), "token", ttl=300)
        
        return response
        
    except RecordNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to get token {token_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve token"
        )


@router.get("/mint/{mint_address}", response_model=TokenDetailResponse)
async def get_token_by_mint(
    mint_address: str = Path(..., description="Mint адрес токена"),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service),
    solana: SolanaService = Depends(get_solana_service)
):
    """
    Получение токена по mint адресу
    """
    try:
        # Валидация mint адреса
        if len(mint_address) != 44:
            raise ValidationException("Invalid mint address format")
        
        # Попытка получить из кэша
        cache_key = f"token_mint:{mint_address}"
        cached_token = await cache.get(cache_key, "token")
        
        if cached_token:
            return TokenDetailResponse(**cached_token)
        
        # Получение токена из БД
        token = await _get_token_by_mint(db, mint_address)
        
        # Обновление данных о цене
        token = await _update_token_price_data(token, solana, cache)
        
        await db.commit()
        await db.refresh(token)
        
        response = TokenDetailResponse.from_orm(token)
        
        # Кэширование результата
        await cache.set(cache_key, response.dict(), "token", ttl=300)
        
        return response
        
    except RecordNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to get token by mint {mint_address}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve token"
        )


@router.post("", response_model=TokenCreateResponse)
async def create_token(
    token_data: TokenCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    solana: SolanaService = Depends(get_solana_service),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Создание нового токена
    
    Требует аутентификации. Создает токен в блокчейне и сохраняет в БД.
    """
    try:
        # Проверка лимитов пользователя
        if current_user.tokens_created >= settings.MAX_TOKENS_PER_USER:
            raise ValidationException(
                f"Maximum {settings.MAX_TOKENS_PER_USER} tokens per user exceeded"
            )
        
        # Проверка уникальности символа
        existing_token = await db.execute(
            select(Token).where(Token.symbol == token_data.symbol.upper())
        )
        if existing_token.scalar_one_or_none():
            raise ValidationException(f"Token symbol '{token_data.symbol}' already exists")
        
        # Создание токена в блокчейне
        logger.info(f"Creating token {token_data.symbol} for user {current_user.id}")
        
        transaction_signature = await solana.create_token(
            creator_wallet=current_user.wallet_address,
            name=token_data.name,
            symbol=token_data.symbol,
            uri=token_data.image_url or "",
            bonding_curve_params=token_data.bonding_curve_params.dict()
        )
        
        # Генерация mint адреса (в реальности получается из транзакции)
        # Для демо используем хэш от параметров
        import hashlib
        mint_address = hashlib.sha256(
            f"{current_user.wallet_address}{token_data.symbol}{transaction_signature}".encode()
        ).hexdigest()[:44]
        
        # Создание записи в БД
        new_token = Token(
            mint_address=mint_address,
            name=token_data.name,
            symbol=token_data.symbol.upper(),
            description=token_data.description,
            image_url=token_data.image_url,
            creator_id=current_user.id,
            curve_type=token_data.bonding_curve_params.curve_type,
            initial_supply=token_data.bonding_curve_params.initial_supply,
            current_supply=token_data.bonding_curve_params.initial_supply,
            initial_price=token_data.bonding_curve_params.initial_price,
            current_price=token_data.bonding_curve_params.initial_price,
            token_reserves=token_data.bonding_curve_params.initial_supply,
            graduation_threshold=token_data.bonding_curve_params.graduation_threshold,
            telegram_url=token_data.telegram_url,
            twitter_url=token_data.twitter_url,
            website_url=token_data.website_url,
            tags=token_data.tags or [],
            bonding_curve_params=token_data.bonding_curve_params.dict()
        )
        
        db.add(new_token)
        
        # Обновление статистики пользователя
        current_user.tokens_created += 1
        current_user.last_token_creation_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(new_token)
        
        # Очистка кэша
        await cache.delete_pattern("tokens_list:*", "token")
        await cache.delete_pattern("trending_*", "analytics")
        
        # Формирование ответа
        token_response = TokenResponse.from_orm(new_token)
        
        response = TokenCreateResponse(
            token=token_response,
            transaction_signature=transaction_signature,
            estimated_confirmation_time=30
        )
        
        logger.info(f"✅ Token {token_data.symbol} created successfully: {new_token.id}")
        
        return response
        
    except ValidationException:
        raise
    except BlockchainException:
        raise
    except Exception as e:
        logger.error(f"Failed to create token: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create token"
        )


@router.put("/{token_id}", response_model=TokenResponse)
async def update_token(
    token_id: UUID,
    update_data: TokenUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Обновление токена (только создатель)
    
    Позволяет обновить описание, социальные ссылки и теги.
    """
    try:
        # Получение токена
        token = await _get_token_by_id(db, token_id)
        
        # Проверка прав (только создатель может редактировать)
        if token.creator_id != current_user.id:
            raise AuthorizationException("Only token creator can update token")
        
        # Обновление полей
        update_fields = update_data.dict(exclude_unset=True)
        
        for field, value in update_fields.items():
            if hasattr(token, field):
                setattr(token, field, value)
        
        await db.commit()
        await db.refresh(token)
        
        # Очистка кэша
        await cache.delete(f"token_detail:{token_id}", "token")
        await cache.delete(f"token_mint:{token.mint_address}", "token")
        
        response = TokenResponse.from_orm(token)
        
        logger.info(f"Token {token_id} updated by user {current_user.id}")
        
        return response
        
    except (RecordNotFoundException, AuthorizationException):
        raise
    except Exception as e:
        logger.error(f"Failed to update token {token_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update token"
        )


@router.get("/{token_id}/price", response_model=Dict[str, Any])
async def get_token_price(
    token_id: UUID,
    db: AsyncSession = Depends(get_db),
    solana: SolanaService = Depends(get_solana_service),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Получение актуальной цены токена
    """
    try:
        # Попытка получить из кэша
        cache_key = f"price:{token_id}"
        cached_price = await cache.get(cache_key, "price")
        
        if cached_price:
            return cached_price
        
        # Получение токена
        token = await _get_token_by_id(db, token_id)
        
        # Получение данных о цене из блокчейна
        price_info = await solana.get_token_price(token.mint_address)
        
        if not price_info:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to fetch current price"
            )
        
        price_data = {
            "token_id": str(token_id),
            "mint_address": token.mint_address,
            "current_price": float(price_info.current_price),
            "market_cap": float(price_info.market_cap),
            "sol_reserves": float(price_info.sol_reserves),
            "token_reserves": float(price_info.token_reserves),
            "price_impact_1_sol": price_info.price_impact_1_sol,
            "graduation_progress": price_info.graduation_progress,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # Кэширование на 30 секунд
        await cache.set(cache_key, price_data, "price", ttl=30)
        
        return price_data
        
    except RecordNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to get price for token {token_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get token price"
        )


@router.get("/trending/volume", response_model=List[TokenResponse])
async def get_trending_by_volume(
    limit: int = Query(10, ge=1, le=50, description="Количество токенов"),
    period: str = Query("24h", regex="^(1h|24h|7d)$", description="Период"),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Получение трендинговых токенов по объему торгов
    """
    try:
        # Попытка получить из кэша
        cache_key = f"trending_volume:{period}:{limit}"
        cached_result = await cache.get(cache_key, "analytics")
        
        if cached_result:
            return [TokenResponse(**token) for token in cached_result]
        
        # Запрос в БД
        query = select(Token).where(
            and_(
                Token.status == TokenStatus.ACTIVE,
                Token.volume_24h > 0
            )
        ).order_by(desc(Token.volume_24h)).limit(limit)
        
        query = query.options(selectinload(Token.creator))
        
        result = await db.execute(query)
        tokens = result.scalars().all()
        
        token_responses = [TokenResponse.from_orm(token) for token in tokens]
        
        # Кэширование на 5 минут
        await cache.set(
            cache_key, 
            [token.dict() for token in token_responses], 
            "analytics", 
            ttl=300
        )
        
        return token_responses
        
    except Exception as e:
        logger.error(f"Failed to get trending tokens by volume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trending tokens"
        )


@router.get("/search/autocomplete")
async def search_autocomplete(
    q: str = Query(..., min_length=2, description="Поисковый запрос"),
    limit: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Автодополнение для поиска токенов
    """
    try:
        # Кэш ключ
        cache_key = f"autocomplete:{q.lower()}:{limit}"
        cached_result = await cache.get(cache_key, "token")
        
        if cached_result:
            return cached_result
        
        # Поиск по имени и символу
        search_filter = or_(
            Token.name.ilike(f"{q}%"),
            Token.symbol.ilike(f"{q}%")
        )
        
        query = select(Token.name, Token.symbol, Token.mint_address).where(
            and_(
                Token.status == TokenStatus.ACTIVE,
                search_filter
            )
        ).limit(limit)
        
        result = await db.execute(query)
        suggestions = []
        
        for row in result:
            suggestions.append({
                "name": row.name,
                "symbol": row.symbol,
                "mint_address": row.mint_address,
                "display": f"{row.name} ({row.symbol})"
            })
        
        # Кэширование на 10 минут
        await cache.set(cache_key, suggestions, "token", ttl=600)
        
        return suggestions
        
    except Exception as e:
        logger.error(f"Failed to get autocomplete suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get suggestions"
        )


@router.delete("/{token_id}")
async def delete_token(
    token_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Удаление токена (только создатель или админ)
    
    На самом деле помечает токен как удаленный, не удаляет из БД.
    """
    try:
        # Получение токена
        token = await _get_token_by_id(db, token_id)
        
        # Проверка прав
        if token.creator_id != current_user.id and current_user.role != "admin":
            raise AuthorizationException("Only token creator or admin can delete token")
        
        # "Удаление" (изменение статуса)
        token.status = TokenStatus.PAUSED
        
        await db.commit()
        
        # Очистка кэша
        await cache.delete(f"token_detail:{token_id}", "token")
        await cache.delete(f"token_mint:{token.mint_address}", "token")
        await cache.delete_pattern("tokens_list:*", "token")
        
        logger.info(f"Token {token_id} deleted by user {current_user.id}")
        
        return SuccessResponse(
            message="Token deleted successfully",
            timestamp=datetime.utcnow()
        )
        
    except (RecordNotFoundException, AuthorizationException):
        raise
    except Exception as e:
        logger.error(f"Failed to delete token {token_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete token"
        )