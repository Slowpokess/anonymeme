#!/usr/bin/env python3
"""
📥 Pydantic схемы для входящих запросов API
Production-ready валидация и типизация данных
"""

from typing import Optional, List, Dict, Any, Union
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum

# Импорт enum'ов из моделей
from ..models.database import CurveType, DexType, TradeType, UserRole


class PaginationRequest(BaseModel):
    """Базовая схема для пагинации"""
    page: int = Field(1, ge=1, description="Номер страницы")
    limit: int = Field(20, ge=1, le=100, description="Количество элементов на странице")
    sort_by: Optional[str] = Field(None, description="Поле для сортировки")
    sort_order: Optional[str] = Field("desc", regex="^(asc|desc)$", description="Направление сортировки")


# === ПОЛЬЗОВАТЕЛИ ===

class UserCreateRequest(BaseModel):
    """Создание нового пользователя"""
    wallet_address: str = Field(..., min_length=44, max_length=44, description="Адрес кошелька Solana")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Никнейм пользователя")
    email: Optional[str] = Field(None, description="Email адрес")
    
    @validator('wallet_address')
    def validate_wallet_address(cls, v):
        """Валидация адреса кошелька"""
        if not v.isalnum():
            raise ValueError('Wallet address must be alphanumeric')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        """Базовая валидация email"""
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v


class UserUpdateRequest(BaseModel):
    """Обновление профиля пользователя"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[str] = Field(None)
    bio: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=255)
    twitter_handle: Optional[str] = Field(None, max_length=50)
    telegram_handle: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserSearchRequest(BaseModel):
    """Поиск пользователей"""
    query: Optional[str] = Field(None, min_length=2, description="Поисковый запрос")
    role: Optional[UserRole] = Field(None, description="Фильтр по роли")
    min_reputation: Optional[float] = Field(None, ge=0, le=100, description="Минимальная репутация")
    is_verified: Optional[bool] = Field(None, description="Только верифицированные")


# === ТОКЕНЫ ===

class BondingCurveParamsRequest(BaseModel):
    """Параметры бондинг-кривой"""
    curve_type: CurveType = Field(..., description="Тип кривой")
    initial_supply: Decimal = Field(..., gt=0, description="Начальное предложение")
    initial_price: Decimal = Field(..., gt=0, description="Начальная цена в lamports")
    graduation_threshold: Decimal = Field(..., gt=0, description="Порог для листинга на DEX")
    slope: float = Field(..., description="Наклон кривой")
    volatility_damper: Optional[float] = Field(1.0, ge=0.1, le=2.0, description="Демпфер волатильности")
    
    @root_validator
    def validate_curve_params(cls, values):
        """Валидация параметров в зависимости от типа кривой"""
        curve_type = values.get('curve_type')
        slope = values.get('slope')
        initial_price = values.get('initial_price')
        graduation_threshold = values.get('graduation_threshold')
        
        if curve_type == CurveType.LINEAR:
            if slope <= 0 or slope >= 1000:
                raise ValueError('Linear curve slope must be between 0 and 1000')
        elif curve_type == CurveType.EXPONENTIAL:
            if slope <= 0 or slope >= 0.001:
                raise ValueError('Exponential curve slope must be between 0 and 0.001')
        elif curve_type == CurveType.SIGMOID:
            if slope <= 0 or slope >= 100:
                raise ValueError('Sigmoid curve slope must be between 0 and 100')
        
        if graduation_threshold <= initial_price:
            raise ValueError('Graduation threshold must be greater than initial price')
        
        return values


class TokenCreateRequest(BaseModel):
    """Создание нового токена"""
    name: str = Field(..., min_length=1, max_length=50, description="Название токена")
    symbol: str = Field(..., min_length=1, max_length=10, description="Символ токена")
    description: Optional[str] = Field(None, max_length=1000, description="Описание токена")
    image_url: Optional[str] = Field(None, max_length=500, description="URL изображения")
    
    # Социальные ссылки
    telegram_url: Optional[str] = Field(None, max_length=255, description="Ссылка на Telegram")
    twitter_url: Optional[str] = Field(None, max_length=255, description="Ссылка на Twitter")
    website_url: Optional[str] = Field(None, max_length=255, description="Ссылка на сайт")
    
    # Параметры бондинг-кривой
    bonding_curve_params: BondingCurveParamsRequest = Field(..., description="Параметры бондинг-кривой")
    
    # Теги
    tags: Optional[List[str]] = Field([], max_items=10, description="Теги токена")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Валидация символа токена"""
        if not v.isalnum():
            raise ValueError('Token symbol must be alphanumeric')
        return v.upper()
    
    @validator('tags')
    def validate_tags(cls, v):
        """Валидация тегов"""
        if v:
            for tag in v:
                if len(tag) > 20:
                    raise ValueError('Tag length must not exceed 20 characters')
        return v


class TokenSearchRequest(BaseModel):
    """Поиск токенов"""
    query: Optional[str] = Field(None, min_length=1, description="Поисковый запрос")
    curve_type: Optional[CurveType] = Field(None, description="Фильтр по типу кривой")
    min_market_cap: Optional[Decimal] = Field(None, ge=0, description="Минимальная капитализация")
    max_market_cap: Optional[Decimal] = Field(None, ge=0, description="Максимальная капитализация")
    is_graduated: Optional[bool] = Field(None, description="Только токены на DEX")
    is_verified: Optional[bool] = Field(None, description="Только верифицированные")
    creator_id: Optional[str] = Field(None, description="ID создателя")
    tags: Optional[List[str]] = Field(None, description="Фильтр по тегам")
    
    @root_validator
    def validate_market_cap_range(cls, values):
        """Валидация диапазона капитализации"""
        min_cap = values.get('min_market_cap')
        max_cap = values.get('max_market_cap')
        
        if min_cap and max_cap and min_cap > max_cap:
            raise ValueError('min_market_cap must be less than max_market_cap')
        
        return values


class TokenUpdateRequest(BaseModel):
    """Обновление токена (только владелец)"""
    description: Optional[str] = Field(None, max_length=1000)
    telegram_url: Optional[str] = Field(None, max_length=255)
    twitter_url: Optional[str] = Field(None, max_length=255)
    website_url: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = Field(None, max_items=10)


# === ТОРГОВЛЯ ===

class TradeRequest(BaseModel):
    """Базовый запрос на торговлю"""
    token_address: str = Field(..., min_length=44, max_length=44, description="Mint адрес токена")
    slippage_tolerance: float = Field(..., ge=0.1, le=50.0, description="Максимальный slippage в %")
    
    @validator('token_address')
    def validate_token_address(cls, v):
        if not v.isalnum():
            raise ValueError('Token address must be alphanumeric')
        return v


class BuyTokensRequest(TradeRequest):
    """Покупка токенов"""
    sol_amount: Decimal = Field(..., gt=0, description="Количество SOL для покупки")
    min_tokens_out: Decimal = Field(..., gt=0, description="Минимальное количество токенов")
    
    @validator('sol_amount')
    def validate_sol_amount(cls, v):
        # Максимум 100 SOL за одну сделку
        if v > 100:
            raise ValueError('Maximum trade size is 100 SOL')
        return v


class SellTokensRequest(TradeRequest):
    """Продажа токенов"""
    token_amount: Decimal = Field(..., gt=0, description="Количество токенов для продажи")
    min_sol_out: Decimal = Field(..., gt=0, description="Минимальное количество SOL")


class TradeHistoryRequest(PaginationRequest):
    """Запрос истории торгов"""
    user_id: Optional[str] = Field(None, description="ID пользователя")
    token_id: Optional[str] = Field(None, description="ID токена")
    trade_type: Optional[TradeType] = Field(None, description="Тип операции")
    min_amount: Optional[Decimal] = Field(None, ge=0, description="Минимальная сумма")
    date_from: Optional[datetime] = Field(None, description="Дата начала")
    date_to: Optional[datetime] = Field(None, description="Дата окончания")
    
    @root_validator
    def validate_date_range(cls, values):
        """Валидация диапазона дат"""
        date_from = values.get('date_from')
        date_to = values.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValueError('date_from must be less than date_to')
        
        return values


# === АНАЛИТИКА ===

class PriceHistoryRequest(BaseModel):
    """Запрос истории цен"""
    token_address: str = Field(..., min_length=44, max_length=44)
    interval: int = Field(..., description="Интервал в минутах (1, 5, 15, 60, 240, 1440)")
    date_from: Optional[datetime] = Field(None, description="Дата начала")
    date_to: Optional[datetime] = Field(None, description="Дата окончания")
    limit: int = Field(1000, ge=1, le=5000, description="Максимальное количество точек")
    
    @validator('interval')
    def validate_interval(cls, v):
        allowed_intervals = [1, 5, 15, 60, 240, 1440]
        if v not in allowed_intervals:
            raise ValueError(f'Interval must be one of {allowed_intervals}')
        return v
    
    @root_validator
    def validate_date_range(cls, values):
        date_from = values.get('date_from')
        date_to = values.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValueError('date_from must be less than date_to')
        
        return values


class MarketStatsRequest(BaseModel):
    """Запрос рыночной статистики"""
    period: str = Field("24h", regex="^(1h|24h|7d|30d)$", description="Период для статистики")
    include_graduated: bool = Field(True, description="Включать токены на DEX")


class TopTokensRequest(PaginationRequest):
    """Запрос топ токенов"""
    sort_by: str = Field("market_cap", regex="^(market_cap|volume_24h|trade_count|created_at)$")
    period: str = Field("24h", regex="^(24h|7d|30d|all)$", description="Период для фильтра")
    include_graduated: bool = Field(True, description="Включать токены на DEX")


# === АДМИН ===

class AdminUserUpdateRequest(BaseModel):
    """Административное обновление пользователя"""
    role: Optional[UserRole] = Field(None)
    is_verified: Optional[bool] = Field(None)
    reputation_score: Optional[float] = Field(None, ge=0, le=100)
    ban_reason: Optional[str] = Field(None, max_length=500)
    banned_until: Optional[datetime] = Field(None)


class AdminTokenUpdateRequest(BaseModel):
    """Административное обновление токена"""
    is_verified: Optional[bool] = Field(None)
    is_flagged: Optional[bool] = Field(None)
    flag_reason: Optional[str] = Field(None, max_length=500)
    security_score: Optional[float] = Field(None, ge=0, le=100)


class PlatformConfigUpdateRequest(BaseModel):
    """Обновление конфигурации платформы"""
    trading_paused: Optional[bool] = Field(None, description="Приостановить торговлю")
    max_trade_size: Optional[Decimal] = Field(None, gt=0, description="Максимальный размер сделки")
    platform_fee_percent: Optional[float] = Field(None, ge=0, le=10, description="Комиссия платформы в %")
    max_slippage_percent: Optional[float] = Field(None, ge=0, le=100, description="Максимальный slippage в %")


# === WEBSOCKET ===

class WebSocketSubscribeRequest(BaseModel):
    """Подписка на WebSocket события"""
    event_types: List[str] = Field(..., min_items=1, description="Типы событий")
    token_addresses: Optional[List[str]] = Field(None, description="Адреса токенов для подписки")
    user_id: Optional[str] = Field(None, description="ID пользователя")
    
    @validator('event_types')
    def validate_event_types(cls, v):
        allowed_events = [
            'trade', 'token_created', 'token_graduated', 
            'price_update', 'user_update', 'platform_update'
        ]
        for event in v:
            if event not in allowed_events:
                raise ValueError(f'Invalid event type: {event}')
        return v


# === BATCH ОПЕРАЦИИ ===

class BatchTradeRequest(BaseModel):
    """Пакетная торговая операция"""
    trades: List[Union[BuyTokensRequest, SellTokensRequest]] = Field(
        ..., 
        min_items=1, 
        max_items=10,
        description="Список торговых операций"
    )
    execute_all_or_none: bool = Field(
        True, 
        description="Выполнить все операции или ни одной"
    )


class BatchTokenCreateRequest(BaseModel):
    """Пакетное создание токенов"""
    tokens: List[TokenCreateRequest] = Field(
        ..., 
        min_items=1, 
        max_items=5,
        description="Список токенов для создания"
    )


# === ДОПОЛНИТЕЛЬНЫЕ СХЕМЫ ===

class ReportRequest(BaseModel):
    """Жалоба на пользователя или токен"""
    target_type: str = Field(..., regex="^(user|token)$", description="Тип объекта жалобы")
    target_id: str = Field(..., description="ID объекта")
    reason: str = Field(..., max_length=50, description="Причина жалобы")
    description: str = Field(..., max_length=1000, description="Подробное описание")


class FeedbackRequest(BaseModel):
    """Обратная связь"""
    category: str = Field(..., regex="^(bug|feature|general)$", description="Категория")
    subject: str = Field(..., min_length=5, max_length=100, description="Тема")
    message: str = Field(..., min_length=10, max_length=2000, description="Сообщение")
    contact_email: Optional[str] = Field(None, description="Email для связи")


class HealthCheckRequest(BaseModel):
    """Запрос проверки здоровья системы"""
    detailed: bool = Field(False, description="Подробная информация")
    check_external: bool = Field(False, description="Проверять внешние сервисы")