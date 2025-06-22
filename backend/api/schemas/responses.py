#!/usr/bin/env python3
"""
📤 Pydantic схемы для исходящих ответов API
Production-ready сериализация данных
"""

from typing import Optional, List, Dict, Any, Union
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID

# Импорт enum'ов из моделей
from ..models.database import CurveType, DexType, TokenStatus, TradeType, UserRole, UserStatus


class BaseResponse(BaseModel):
    """Базовый класс для всех ответов"""
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class PaginationResponse(BaseModel):
    """Информация о пагинации"""
    page: int = Field(..., description="Текущая страница")
    limit: int = Field(..., description="Элементов на странице")
    total: int = Field(..., description="Общее количество элементов")
    pages: int = Field(..., description="Общее количество страниц")
    has_next: bool = Field(..., description="Есть ли следующая страница")
    has_prev: bool = Field(..., description="Есть ли предыдущая страница")


class ErrorResponse(BaseModel):
    """Стандартный ответ с ошибкой"""
    error: bool = Field(True, description="Флаг ошибки")
    message: str = Field(..., description="Сообщение об ошибке")
    error_code: Optional[str] = Field(None, description="Код ошибки")
    details: Optional[Dict[str, Any]] = Field(None, description="Дополнительные детали")
    timestamp: datetime = Field(..., description="Время ошибки")
    path: str = Field(..., description="Путь запроса")


class SuccessResponse(BaseModel):
    """Стандартный успешный ответ"""
    success: bool = Field(True, description="Флаг успеха")
    message: str = Field(..., description="Сообщение")
    data: Optional[Dict[str, Any]] = Field(None, description="Данные ответа")
    timestamp: datetime = Field(..., description="Время ответа")


# === ПОЛЬЗОВАТЕЛИ ===

class UserResponse(BaseResponse):
    """Ответ с данными пользователя"""
    id: UUID = Field(..., description="Уникальный идентификатор")
    wallet_address: str = Field(..., description="Адрес кошелька")
    username: Optional[str] = Field(None, description="Никнейм")
    email: Optional[str] = Field(None, description="Email (скрыт для других пользователей)")
    
    # Профиль
    avatar_url: Optional[str] = Field(None, description="URL аватара")
    bio: Optional[str] = Field(None, description="Биография")
    website: Optional[str] = Field(None, description="Сайт")
    twitter_handle: Optional[str] = Field(None, description="Twitter")
    telegram_handle: Optional[str] = Field(None, description="Telegram")
    
    # Статус и роль
    role: UserRole = Field(..., description="Роль пользователя")
    status: UserStatus = Field(..., description="Статус пользователя")
    is_verified: bool = Field(..., description="Верифицирован ли")
    
    # Статистика
    tokens_created: int = Field(..., description="Создано токенов")
    total_volume_traded: Decimal = Field(..., description="Общий объем торгов")
    total_trades: int = Field(..., description="Количество сделок")
    
    # Рейтинги
    reputation_score: float = Field(..., description="Репутация (0-100)")
    creator_rating: float = Field(..., description="Рейтинг создателя (0-5)")
    trader_rating: float = Field(..., description="Рейтинг трейдера (0-5)")
    win_rate: float = Field(..., description="Процент выигрышных сделок")
    
    # Временные метки
    created_at: datetime = Field(..., description="Дата регистрации")
    last_login_at: Optional[datetime] = Field(None, description="Последний вход")
    
    
class UserProfileResponse(UserResponse):
    """Расширенный профиль пользователя"""
    # Дополнительная статистика
    profitable_trades: int = Field(..., description="Прибыльные сделки")
    kyc_completed: bool = Field(..., description="Прохождение KYC")
    warning_count: int = Field(..., description="Количество предупреждений")
    
    # Активность
    last_trade_at: Optional[datetime] = Field(None, description="Последняя сделка")
    last_token_creation_at: Optional[datetime] = Field(None, description="Последнее создание токена")


class UsersListResponse(BaseResponse):
    """Список пользователей с пагинацией"""
    users: List[UserResponse] = Field(..., description="Список пользователей")
    pagination: PaginationResponse = Field(..., description="Информация о пагинации")


# === ТОКЕНЫ ===

class BondingCurveResponse(BaseResponse):
    """Данные бондинг-кривой"""
    curve_type: CurveType = Field(..., description="Тип кривой")
    initial_price: Decimal = Field(..., description="Начальная цена")
    current_price: Decimal = Field(..., description="Текущая цена")
    initial_supply: Decimal = Field(..., description="Начальное предложение")
    current_supply: Decimal = Field(..., description="Текущее предложение")
    graduation_threshold: Decimal = Field(..., description="Порог для листинга")
    progress_to_graduation: float = Field(..., description="Прогресс до листинга (0-1)")


class TokenResponse(BaseResponse):
    """Ответ с данными токена"""
    id: UUID = Field(..., description="Уникальный идентификатор")
    mint_address: str = Field(..., description="Mint адрес в Solana")
    name: str = Field(..., description="Название")
    symbol: str = Field(..., description="Символ")
    description: Optional[str] = Field(None, description="Описание")
    image_url: Optional[str] = Field(None, description="URL изображения")
    
    # Создатель
    creator_id: UUID = Field(..., description="ID создателя")
    creator: UserResponse = Field(..., description="Данные создателя")
    
    # Рыночные данные
    market_cap: Decimal = Field(..., description="Рыночная капитализация")
    current_price: Decimal = Field(..., description="Текущая цена")
    price_change_24h: Optional[float] = Field(None, description="Изменение цены за 24ч (%)")
    
    # Резервы
    sol_reserves: Decimal = Field(..., description="Резервы SOL")
    token_reserves: Decimal = Field(..., description="Резервы токенов")
    
    # Статистика
    volume_24h: Decimal = Field(..., description="Объем за 24 часа")
    volume_total: Decimal = Field(..., description="Общий объем")
    trade_count: int = Field(..., description="Количество сделок")
    holder_count: int = Field(..., description="Количество держателей")
    
    # Статус
    status: TokenStatus = Field(..., description="Статус токена")
    is_graduated: bool = Field(..., description="Листингован ли на DEX")
    is_verified: bool = Field(..., description="Верифицирован ли")
    
    # Бондинг-кривая
    bonding_curve: BondingCurveResponse = Field(..., description="Данные бондинг-кривой")
    
    # Социальные ссылки
    telegram_url: Optional[str] = Field(None, description="Telegram")
    twitter_url: Optional[str] = Field(None, description="Twitter")
    website_url: Optional[str] = Field(None, description="Сайт")
    
    # Безопасность
    security_score: float = Field(..., description="Оценка безопасности")
    rug_pull_risk: float = Field(..., description="Риск rug pull")
    
    # Дополнительно
    tags: List[str] = Field(..., description="Теги")
    created_at: datetime = Field(..., description="Дата создания")


class TokenDetailResponse(TokenResponse):
    """Подробная информация о токене"""
    # Расширенная статистика
    all_time_high_price: Optional[Decimal] = Field(None, description="Максимальная цена")
    all_time_high_mc: Optional[Decimal] = Field(None, description="Максимальная капитализация")
    unique_traders: int = Field(..., description="Уникальных трейдеров")
    trades_24h: int = Field(..., description="Сделки за 24 часа")
    
    # Градация
    graduated_at: Optional[datetime] = Field(None, description="Время листинга на DEX")
    graduation_dex: Optional[DexType] = Field(None, description="DEX листинга")
    
    # Расширенные данные
    metadata_uri: Optional[str] = Field(None, description="URI метаданных")
    liquidity_locked: bool = Field(..., description="Заблокирована ли ликвидность")


class TokensListResponse(BaseResponse):
    """Список токенов с пагинацией"""
    tokens: List[TokenResponse] = Field(..., description="Список токенов")
    pagination: PaginationResponse = Field(..., description="Информация о пагинации")


class TokenCreateResponse(BaseResponse):
    """Ответ на создание токена"""
    token: TokenResponse = Field(..., description="Созданный токен")
    transaction_signature: str = Field(..., description="Подпись транзакции")
    estimated_confirmation_time: int = Field(..., description="Ожидаемое время подтверждения (сек)")


# === ТОРГОВЛЯ ===

class TradeResponse(BaseResponse):
    """Ответ с данными сделки"""
    id: UUID = Field(..., description="ID сделки")
    transaction_signature: str = Field(..., description="Подпись транзакции")
    
    # Участники
    user_id: UUID = Field(..., description="ID пользователя")
    token_id: UUID = Field(..., description="ID токена")
    token: TokenResponse = Field(..., description="Данные токена")
    
    # Детали сделки
    trade_type: TradeType = Field(..., description="Тип операции")
    sol_amount: Decimal = Field(..., description="Количество SOL")
    token_amount: Decimal = Field(..., description="Количество токенов")
    price_per_token: Decimal = Field(..., description="Цена за токен")
    
    # Slippage
    expected_amount: Optional[Decimal] = Field(None, description="Ожидаемое количество")
    actual_slippage: Optional[float] = Field(None, description="Фактический slippage")
    max_slippage: Optional[float] = Field(None, description="Максимальный slippage")
    
    # Комиссии
    platform_fee: Optional[Decimal] = Field(None, description="Комиссия платформы")
    
    # Влияние на рынок
    price_impact: Optional[float] = Field(None, description="Влияние на цену")
    market_cap_before: Optional[Decimal] = Field(None, description="Капитализация до")
    market_cap_after: Optional[Decimal] = Field(None, description="Капитализация после")
    
    # Статус
    is_successful: bool = Field(..., description="Успешная ли сделка")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    
    # Время
    created_at: datetime = Field(..., description="Время сделки")


class TradeEstimateResponse(BaseResponse):
    """Оценка торговой операции"""
    expected_output: Decimal = Field(..., description="Ожидаемый результат")
    price_impact: float = Field(..., description="Влияние на цену (%)")
    estimated_slippage: float = Field(..., description="Ожидаемый slippage (%)")
    platform_fee: Decimal = Field(..., description="Комиссия платформы")
    minimum_output: Decimal = Field(..., description="Минимальный результат")
    price_per_token: Decimal = Field(..., description="Цена за токен")
    market_cap_after: Decimal = Field(..., description="Капитализация после сделки")


class TradesListResponse(BaseResponse):
    """Список сделок с пагинацией"""
    trades: List[TradeResponse] = Field(..., description="Список сделок")
    pagination: PaginationResponse = Field(..., description="Информация о пагинации")


class UserPortfolioResponse(BaseResponse):
    """Портфель пользователя"""
    user_id: UUID = Field(..., description="ID пользователя")
    total_value_sol: Decimal = Field(..., description="Общая стоимость в SOL")
    total_value_usd: Optional[Decimal] = Field(None, description="Общая стоимость в USD")
    total_pnl: Decimal = Field(..., description="Общий P&L")
    total_pnl_percent: float = Field(..., description="Общий P&L в процентах")
    
    positions: List[Dict[str, Any]] = Field(..., description="Позиции по токенам")


# === АНАЛИТИКА ===

class PricePointResponse(BaseResponse):
    """Точка цены для графика"""
    timestamp: datetime = Field(..., description="Время")
    open_price: Decimal = Field(..., description="Цена открытия")
    high_price: Decimal = Field(..., description="Максимальная цена")
    low_price: Decimal = Field(..., description="Минимальная цена")
    close_price: Decimal = Field(..., description="Цена закрытия")
    volume_sol: Decimal = Field(..., description="Объем в SOL")
    volume_tokens: Decimal = Field(..., description="Объем в токенах")
    trade_count: int = Field(..., description="Количество сделок")
    market_cap: Optional[Decimal] = Field(None, description="Рыночная капитализация")


class PriceHistoryResponse(BaseResponse):
    """История цен токена"""
    token_address: str = Field(..., description="Адрес токена")
    interval_minutes: int = Field(..., description="Интервал в минутах")
    data: List[PricePointResponse] = Field(..., description="Данные цен")
    summary: Dict[str, Any] = Field(..., description="Сводная статистика")


class MarketStatsResponse(BaseResponse):
    """Рыночная статистика"""
    total_tokens: int = Field(..., description="Общее количество токенов")
    active_tokens: int = Field(..., description="Активные токены")
    graduated_tokens: int = Field(..., description="Токены на DEX")
    
    total_volume_24h: Decimal = Field(..., description="Общий объем за 24ч")
    total_trades_24h: int = Field(..., description="Сделки за 24ч")
    total_users: int = Field(..., description="Общее количество пользователей")
    active_users_24h: int = Field(..., description="Активные пользователи за 24ч")
    
    total_market_cap: Decimal = Field(..., description="Общая капитализация")
    platform_fees_24h: Decimal = Field(..., description="Комиссии платформы за 24ч")
    
    top_tokens_by_volume: List[TokenResponse] = Field(..., description="Топ токенов по объему")
    top_tokens_by_market_cap: List[TokenResponse] = Field(..., description="Топ токенов по капитализации")


class TrendingTokensResponse(BaseResponse):
    """Трендинговые токены"""
    trending_by_volume: List[TokenResponse] = Field(..., description="Топ по объему")
    trending_by_trades: List[TokenResponse] = Field(..., description="Топ по сделкам")
    trending_by_holders: List[TokenResponse] = Field(..., description="Топ по держателям")
    new_tokens: List[TokenResponse] = Field(..., description="Новые токены")
    recently_graduated: List[TokenResponse] = Field(..., description="Недавно выпущенные на DEX")


# === СИСТЕМА ===

class HealthCheckResponse(BaseResponse):
    """Проверка здоровья системы"""
    status: str = Field(..., description="Общий статус (healthy/degraded/unhealthy)")
    timestamp: datetime = Field(..., description="Время проверки")
    services: Dict[str, str] = Field(..., description="Статус сервисов")
    version: str = Field(..., description="Версия API")
    uptime: str = Field(..., description="Время работы")


class MetricsResponse(BaseResponse):
    """Метрики системы"""
    api_requests_total: int = Field(..., description="Общее количество запросов")
    api_requests_per_minute: float = Field(..., description="Запросов в минуту")
    active_connections: int = Field(..., description="Активные соединения")
    database_connections: int = Field(..., description="Соединения с БД")
    redis_connections: int = Field(..., description="Соединения с Redis")
    memory_usage_mb: float = Field(..., description="Использование памяти (МБ)")
    cpu_usage_percent: float = Field(..., description="Использование CPU (%)")


class WebSocketEventResponse(BaseResponse):
    """WebSocket событие"""
    event_type: str = Field(..., description="Тип события")
    data: Dict[str, Any] = Field(..., description="Данные события")
    timestamp: datetime = Field(..., description="Время события")
    token_address: Optional[str] = Field(None, description="Адрес токена (если применимо)")
    user_id: Optional[UUID] = Field(None, description="ID пользователя (если применимо)")


# === BATCH ОТВЕТЫ ===

class BatchOperationResponse(BaseResponse):
    """Результат пакетной операции"""
    total_operations: int = Field(..., description="Общее количество операций")
    successful_operations: int = Field(..., description="Успешные операции")
    failed_operations: int = Field(..., description="Неудачные операции")
    results: List[Dict[str, Any]] = Field(..., description="Результаты операций")
    errors: List[Dict[str, Any]] = Field(..., description="Ошибки")


class BatchTradeResponse(BatchOperationResponse):
    """Результат пакетной торговли"""
    total_volume: Decimal = Field(..., description="Общий объем торгов")
    total_fees: Decimal = Field(..., description="Общие комиссии")
    successful_trades: List[TradeResponse] = Field(..., description="Успешные сделки")


# === АДМИНИСТРАТИВНЫЕ ОТВЕТЫ ===

class AdminStatsResponse(BaseResponse):
    """Административная статистика"""
    # Пользователи
    total_users: int = Field(..., description="Общее количество пользователей")
    verified_users: int = Field(..., description="Верифицированные пользователи")
    banned_users: int = Field(..., description="Заблокированные пользователи")
    
    # Токены
    total_tokens: int = Field(..., description="Общее количество токенов")
    flagged_tokens: int = Field(..., description="Помеченные токены")
    verified_tokens: int = Field(..., description="Верифицированные токены")
    
    # Финансы
    total_volume: Decimal = Field(..., description="Общий объем торгов")
    platform_revenue: Decimal = Field(..., description="Доходы платформы")
    
    # Активность за период
    new_users_24h: int = Field(..., description="Новые пользователи за 24ч")
    new_tokens_24h: int = Field(..., description="Новые токены за 24ч")
    volume_24h: Decimal = Field(..., description="Объем за 24ч")


class PlatformConfigResponse(BaseResponse):
    """Конфигурация платформы"""
    trading_paused: bool = Field(..., description="Торговля приостановлена")
    max_trade_size_sol: Decimal = Field(..., description="Максимальный размер сделки")
    platform_fee_percent: float = Field(..., description="Комиссия платформы")
    max_slippage_percent: float = Field(..., description="Максимальный slippage")
    rate_limit_requests: int = Field(..., description="Лимит запросов")
    rate_limit_window: int = Field(..., description="Окно лимитирования")
    version: str = Field(..., description="Версия конфигурации")
    last_updated: datetime = Field(..., description="Последнее обновление")


# === ДОПОЛНИТЕЛЬНЫЕ ОТВЕТЫ ===

class SearchResponse(BaseResponse):
    """Результаты поиска"""
    query: str = Field(..., description="Поисковый запрос")
    total_results: int = Field(..., description="Общее количество результатов")
    tokens: List[TokenResponse] = Field(..., description="Найденные токены")
    users: List[UserResponse] = Field(..., description="Найденные пользователи")
    execution_time_ms: float = Field(..., description="Время выполнения поиска")


class NotificationResponse(BaseResponse):
    """Уведомление"""
    id: UUID = Field(..., description="ID уведомления")
    user_id: UUID = Field(..., description="ID пользователя")
    type: str = Field(..., description="Тип уведомления")
    title: str = Field(..., description="Заголовок")
    message: str = Field(..., description="Сообщение")
    data: Optional[Dict[str, Any]] = Field(None, description="Дополнительные данные")
    is_read: bool = Field(..., description="Прочитано ли")
    created_at: datetime = Field(..., description="Время создания")


class ApiInfoResponse(BaseResponse):
    """Информация об API"""
    name: str = Field(..., description="Название API")
    version: str = Field(..., description="Версия")
    description: str = Field(..., description="Описание")
    documentation_url: str = Field(..., description="URL документации")
    support_email: str = Field(..., description="Email поддержки")
    rate_limits: Dict[str, Any] = Field(..., description="Лимиты API")
    features: List[str] = Field(..., description="Доступные функции")


# === ОТСУТСТВУЮЩИЕ СХЕМЫ ИЗ АУДИТА ===

class AuthTokenResponse(BaseResponse):
    """Ответ с токеном авторизации"""
    access_token: str = Field(..., description="JWT токен доступа")
    token_type: str = Field(default="Bearer", description="Тип токена")
    expires_in: int = Field(..., description="Время жизни токена в секундах")
    user: UserResponse = Field(..., description="Данные пользователя")

class UserStatsResponse(BaseResponse):
    """Статистика пользователя"""
    total_trades: int = Field(..., description="Общее количество сделок")
    total_volume: Decimal = Field(..., description="Общий объем торгов")
    tokens_created: int = Field(..., description="Создано токенов")
    portfolio_value: Decimal = Field(..., description="Стоимость портфеля")
    pnl_24h: Decimal = Field(..., description="PnL за 24 часа")

class UserTokensResponse(BaseResponse):
    """Токены пользователя"""
    tokens: List[TokenResponse] = Field(..., description="Список токенов")
    total_count: int = Field(..., description="Общее количество")
    total_value: Decimal = Field(..., description="Общая стоимость")

class UserTradesResponse(BaseResponse):
    """Сделки пользователя"""
    trades: List[TradeResponse] = Field(..., description="Список сделок")
    pagination: PaginationResponse = Field(..., description="Пагинация")

class AdminDashboardResponse(BaseResponse):
    """Данные админской панели"""
    total_users: int = Field(..., description="Общее количество пользователей")
    total_tokens: int = Field(..., description="Общее количество токенов")
    total_volume_24h: Decimal = Field(..., description="Объем за 24 часа")
    active_users_24h: int = Field(..., description="Активные пользователи за 24 часа")
    platform_fees_24h: Decimal = Field(..., description="Комиссии платформы за 24 часа")

class SystemHealthResponse(BaseResponse):
    """Здоровье системы"""
    status: str = Field(..., description="Статус системы")
    database_status: str = Field(..., description="Статус базы данных")
    blockchain_status: str = Field(..., description="Статус блокчейна")
    cache_status: str = Field(..., description="Статус кэша")
    uptime: int = Field(..., description="Время работы в секундах")

class AdminUserResponse(UserResponse):
    """Расширенные данные пользователя для админов"""
    email: str = Field(..., description="Email пользователя")
    ip_address: Optional[str] = Field(None, description="IP адрес")
    warning_count: int = Field(..., description="Количество предупреждений")
    last_login_ip: Optional[str] = Field(None, description="IP последнего входа")

class AdminTokenResponse(TokenResponse):
    """Расширенные данные токена для админов"""
    security_flags: List[str] = Field(..., description="Флаги безопасности")
    reported_count: int = Field(..., description="Количество жалоб")
    admin_notes: Optional[str] = Field(None, description="Заметки администратора")

class AdminTradeResponse(TradeResponse):
    """Расширенные данные сделки для админов"""
    ip_address: Optional[str] = Field(None, description="IP адрес трейдера")
    risk_score: float = Field(..., description="Оценка риска")
    flags: List[str] = Field(..., description="Флаги подозрительной активности")

class SecurityLogResponse(BaseResponse):
    """Запись в логе безопасности"""
    id: UUID = Field(..., description="ID записи")
    event_type: str = Field(..., description="Тип события")
    severity: str = Field(..., description="Серьезность")
    user_id: Optional[UUID] = Field(None, description="ID пользователя")
    ip_address: Optional[str] = Field(None, description="IP адрес")
    details: Dict[str, Any] = Field(..., description="Детали события")
    created_at: datetime = Field(..., description="Время события")