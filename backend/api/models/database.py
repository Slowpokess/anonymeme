#!/usr/bin/env python3
"""
🗄️ Модели базы данных для Anonymeme
Production-ready SQLAlchemy модели с полной типизацией
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from decimal import Decimal

from sqlalchemy import (
    Column, String, Integer, BigInteger, Float, Boolean, DateTime, 
    Text, JSON, ForeignKey, Index, UniqueConstraint, CheckConstraint,
    Enum as SQLEnum, DECIMAL, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
import enum


# Базовый класс для всех моделей
Base = declarative_base()


class TimestampMixin:
    """Миксин для автоматических временных меток"""
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        comment="Время создания записи"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False,
        comment="Время последнего обновления"
    )


class UUIDMixin:
    """Миксин для UUID первичного ключа"""
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Уникальный идентификатор"
    )


# === ENUMS ===

class CurveType(enum.Enum):
    """Типы бондинг-кривых"""
    LINEAR = "Linear"
    EXPONENTIAL = "Exponential"
    LOGARITHMIC = "Logarithmic"
    SIGMOID = "Sigmoid"
    CONSTANT_PRODUCT = "ConstantProduct"


class DexType(enum.Enum):
    """Типы DEX для листинга"""
    RAYDIUM = "Raydium"
    JUPITER = "Jupiter"
    ORCA = "Orca"
    SERUM = "Serum"
    METEORA = "Meteora"


class TokenStatus(enum.Enum):
    """Статусы токена"""
    ACTIVE = "active"
    GRADUATED = "graduated"
    PAUSED = "paused"
    FLAGGED = "flagged"
    BURNED = "burned"


class TradeType(enum.Enum):
    """Типы торговых операций"""
    BUY = "buy"
    SELL = "sell"


class UserRole(enum.Enum):
    """Роли пользователей"""
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(enum.Enum):
    """Статусы пользователей"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"
    PENDING = "pending"
    DELETED = "deleted"


# === ОСНОВНЫЕ МОДЕЛИ ===

class User(Base, UUIDMixin, TimestampMixin):
    """Модель пользователя"""
    __tablename__ = "users"
    
    # Основные поля
    wallet_address = Column(
        String(44), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="Адрес кошелька Solana"
    )
    username = Column(
        String(50), 
        unique=True, 
        nullable=True,
        comment="Никнейм пользователя"
    )
    email = Column(
        String(255), 
        unique=True, 
        nullable=True,
        comment="Email адрес"
    )
    
    # Статус и роль
    role = Column(
        SQLEnum(UserRole), 
        default=UserRole.USER,
        nullable=False,
        comment="Роль пользователя"
    )
    status = Column(
        SQLEnum(UserStatus), 
        default=UserStatus.ACTIVE,
        nullable=False,
        comment="Статус пользователя"
    )
    
    # Профиль
    profile_image_url = Column(String(500), comment="URL изображения профиля")
    bio = Column(Text, comment="Биография пользователя")
    website = Column(String(255), comment="Личный сайт")
    twitter_handle = Column(String(50), comment="Twitter handle")
    telegram_handle = Column(String(50), comment="Telegram handle")
    
    # Статистика
    tokens_created = Column(Integer, default=0, comment="Количество созданных токенов")
    total_volume_traded = Column(DECIMAL(20, 9), default=0, comment="Общий объем торгов в SOL")
    total_trades = Column(Integer, default=0, comment="Общее количество сделок")
    profitable_trades = Column(Integer, default=0, comment="Прибыльные сделки")
    
    # Репутация и рейтинги
    reputation_score = Column(Float, default=50.0, comment="Репутация (0-100)")
    creator_rating = Column(Float, default=0.0, comment="Рейтинг как создателя (0-5)")
    trader_rating = Column(Float, default=0.0, comment="Рейтинг как трейдера (0-5)")
    
    # Верификация
    is_verified = Column(Boolean, default=False, comment="Верифицирован ли")
    kyc_completed = Column(Boolean, default=False, comment="Прошел ли KYC")
    kyc_completed_at = Column(DateTime(timezone=True), comment="Время прохождения KYC")
    
    # Модерация
    warning_count = Column(Integer, default=0, comment="Количество предупреждений")
    ban_reason = Column(Text, comment="Причина блокировки")
    banned_until = Column(DateTime(timezone=True), comment="Заблокирован до")
    banned_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), comment="Кем заблокирован")
    
    # Активность
    last_login_at = Column(DateTime(timezone=True), comment="Последний вход")
    last_trade_at = Column(DateTime(timezone=True), comment="Последняя сделка")
    last_token_creation_at = Column(DateTime(timezone=True), comment="Последнее создание токена")
    
    # JSON поля для расширенных данных
    preferences = Column(JSONB, default=dict, comment="Пользовательские настройки")
    meta_data = Column(JSONB, default=dict, comment="Дополнительные метаданные")
    
    # Связи
    tokens = relationship("Token", back_populates="creator", foreign_keys="Token.creator_id")
    trades = relationship("Trade", back_populates="user")
    banned_by = relationship("User", remote_side=[id])
    
    # Индексы
    __table_args__ = (
        Index("idx_users_wallet_address", "wallet_address"),
        Index("idx_users_username", "username"),
        Index("idx_users_status", "status"),
        Index("idx_users_role", "role"),
        Index("idx_users_reputation", "reputation_score"),
        CheckConstraint("reputation_score >= 0 AND reputation_score <= 100", name="check_reputation_range"),
        CheckConstraint("creator_rating >= 0 AND creator_rating <= 5", name="check_creator_rating_range"),
        CheckConstraint("trader_rating >= 0 AND trader_rating <= 5", name="check_trader_rating_range"),
    )
    
    @validates('wallet_address')
    def validate_wallet_address(self, key, address):
        """Валидация адреса кошелька Solana"""
        if len(address) != 44:
            raise ValueError("Wallet address must be 44 characters long")
        return address
    
    @validates('email')
    def validate_email(self, key, email):
        """Базовая валидация email"""
        if email and '@' not in email:
            raise ValueError("Invalid email format")
        return email
    
    @hybrid_property
    def is_banned(self) -> bool:
        """Проверка заблокирован ли пользователь"""
        if self.status == UserStatus.BANNED:
            if self.banned_until is None:
                return True
            return datetime.now(timezone.utc) < self.banned_until
        return False
    
    @hybrid_property
    def win_rate(self) -> float:
        """Процент выигрышных сделок"""
        if self.total_trades == 0:
            return 0.0
        return (self.profitable_trades / self.total_trades) * 100


class Token(Base, UUIDMixin, TimestampMixin):
    """Модель токена"""
    __tablename__ = "tokens"
    
    # Основная информация
    mint_address = Column(
        String(44), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="Mint адрес токена в Solana"
    )
    name = Column(String(50), nullable=False, comment="Название токена")
    symbol = Column(String(10), nullable=False, comment="Символ токена")
    description = Column(Text, comment="Описание токена")
    image_url = Column(String(500), comment="URL изображения")
    metadata_uri = Column(String(500), comment="URI метаданных")
    
    # Создатель
    creator_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id"), 
        nullable=False,
        comment="ID создателя токена"
    )
    
    # Бондинг-кривая
    curve_type = Column(
        SQLEnum(CurveType), 
        nullable=False,
        comment="Тип бондинг-кривой"
    )
    initial_supply = Column(DECIMAL(20, 9), nullable=False, comment="Начальное предложение")
    current_supply = Column(DECIMAL(20, 9), nullable=False, comment="Текущее предложение")
    initial_price = Column(DECIMAL(20, 9), nullable=False, comment="Начальная цена в lamports")
    current_price = Column(DECIMAL(20, 9), nullable=False, comment="Текущая цена в lamports")
    
    # Резервы
    sol_reserves = Column(DECIMAL(20, 9), default=0, comment="Резервы SOL в lamports")
    token_reserves = Column(DECIMAL(20, 9), nullable=False, comment="Резервы токенов")
    
    # Рыночные данные
    market_cap = Column(DECIMAL(20, 9), default=0, comment="Рыночная капитализация")
    all_time_high_price = Column(DECIMAL(20, 9), comment="Максимальная цена за всё время")
    all_time_high_mc = Column(DECIMAL(20, 9), comment="Максимальная капитализация")
    
    # Градация
    graduation_threshold = Column(DECIMAL(20, 9), nullable=False, comment="Порог для листинга на DEX")
    is_graduated = Column(Boolean, default=False, comment="Листингован ли на DEX")
    graduated_at = Column(DateTime(timezone=True), comment="Время листинга")
    graduation_dex = Column(SQLEnum(DexType), comment="DEX на котором листингован")
    
    # Статистика торговли
    trade_count = Column(Integer, default=0, comment="Количество сделок")
    unique_traders = Column(Integer, default=0, comment="Уникальных трейдеров")
    holder_count = Column(Integer, default=0, comment="Количество держателей")
    volume_24h = Column(DECIMAL(20, 9), default=0, comment="Объем за 24 часа")
    volume_total = Column(DECIMAL(20, 9), default=0, comment="Общий объем")
    trades_24h = Column(Integer, default=0, comment="Сделки за 24 часа")
    
    # Статус и модерация
    status = Column(
        SQLEnum(TokenStatus), 
        default=TokenStatus.ACTIVE,
        nullable=False,
        comment="Статус токена"
    )
    is_verified = Column(Boolean, default=False, comment="Верифицирован ли")
    is_flagged = Column(Boolean, default=False, comment="Помечен как подозрительный")
    flag_reason = Column(Text, comment="Причина пометки")
    
    # Социальные данные
    telegram_url = Column(String(255), comment="Ссылка на Telegram")
    twitter_url = Column(String(255), comment="Ссылка на Twitter")
    website_url = Column(String(255), comment="Ссылка на сайт")
    
    # Безопасность
    security_score = Column(Float, default=50.0, comment="Оценка безопасности (0-100)")
    rug_pull_risk = Column(Float, default=0.0, comment="Риск rug pull (0-100)")
    liquidity_locked = Column(Boolean, default=False, comment="Заблокирована ли ликвидность")
    
    # Дополнительные данные
    tags = Column(JSONB, default=list, comment="Теги токена")
    bonding_curve_params = Column(JSONB, comment="Параметры бондинг-кривой")
    metadata = Column(JSONB, default=dict, comment="Дополнительные метаданные")
    
    # Связи
    creator = relationship("User", back_populates="tokens", foreign_keys=[creator_id])
    trades = relationship("Trade", back_populates="token")
    price_history = relationship("PriceHistory", back_populates="token")
    
    # Индексы
    __table_args__ = (
        Index("idx_tokens_mint_address", "mint_address"),
        Index("idx_tokens_creator_id", "creator_id"),
        Index("idx_tokens_symbol", "symbol"),
        Index("idx_tokens_status", "status"),
        Index("idx_tokens_market_cap", "market_cap"),
        Index("idx_tokens_volume_24h", "volume_24h"),
        Index("idx_tokens_created_at", "created_at"),
        Index("idx_tokens_curve_type", "curve_type"),
        CheckConstraint("security_score >= 0 AND security_score <= 100", name="check_security_score_range"),
        CheckConstraint("rug_pull_risk >= 0 AND rug_pull_risk <= 100", name="check_rug_pull_risk_range"),
        CheckConstraint("initial_supply > 0", name="check_positive_supply"),
        CheckConstraint("initial_price > 0", name="check_positive_price"),
    )
    
    @hybrid_property
    def progress_to_graduation(self) -> float:
        """Прогресс до листинга на DEX (0-1)"""
        if self.graduation_threshold <= 0:
            return 0.0
        return min(float(self.market_cap) / float(self.graduation_threshold), 1.0)
    
    @hybrid_property
    def is_graduation_eligible(self) -> bool:
        """Готов ли к листингу на DEX"""
        return self.market_cap >= self.graduation_threshold and not self.is_graduated


class Trade(Base, UUIDMixin, TimestampMixin):
    """Модель торговой операции"""
    __tablename__ = "trades"
    
    # Основная информация
    transaction_signature = Column(
        String(88), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="Подпись транзакции Solana"
    )
    
    # Участники
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id"), 
        nullable=False,
        comment="ID пользователя"
    )
    token_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("tokens.id"), 
        nullable=False,
        comment="ID токена"
    )
    
    # Детали сделки
    trade_type = Column(
        SQLEnum(TradeType), 
        nullable=False,
        comment="Тип операции (покупка/продажа)"
    )
    sol_amount = Column(DECIMAL(20, 9), nullable=False, comment="Количество SOL")
    token_amount = Column(DECIMAL(20, 9), nullable=False, comment="Количество токенов")
    price_per_token = Column(DECIMAL(20, 9), nullable=False, comment="Цена за токен")
    
    # Slippage и комиссии
    expected_amount = Column(DECIMAL(20, 9), comment="Ожидаемое количество")
    actual_slippage = Column(Float, comment="Фактический slippage в %")
    max_slippage = Column(Float, comment="Максимальный slippage в %")
    platform_fee = Column(DECIMAL(20, 9), comment="Комиссия платформы")
    
    # Состояние рынка на момент сделки
    market_cap_before = Column(DECIMAL(20, 9), comment="Капитализация до сделки")
    market_cap_after = Column(DECIMAL(20, 9), comment="Капитализация после сделки")
    price_impact = Column(Float, comment="Влияние на цену в %")
    
    # Статус
    is_successful = Column(Boolean, default=True, comment="Успешная ли сделка")
    error_message = Column(Text, comment="Сообщение об ошибке")
    
    # Дополнительные данные
    metadata = Column(JSONB, default=dict, comment="Дополнительные данные")
    
    # Связи
    user = relationship("User", back_populates="trades")
    token = relationship("Token", back_populates="trades")
    
    # Индексы
    __table_args__ = (
        Index("idx_trades_transaction_signature", "transaction_signature"),
        Index("idx_trades_user_id", "user_id"),
        Index("idx_trades_token_id", "token_id"),
        Index("idx_trades_trade_type", "trade_type"),
        Index("idx_trades_created_at", "created_at"),
        Index("idx_trades_sol_amount", "sol_amount"),
        Index("idx_trades_user_token", "user_id", "token_id"),
        CheckConstraint("sol_amount > 0", name="check_positive_sol_amount"),
        CheckConstraint("token_amount > 0", name="check_positive_token_amount"),
        CheckConstraint("price_per_token > 0", name="check_positive_price"),
    )


class PriceHistory(Base, UUIDMixin, TimestampMixin):
    """История цен токенов"""
    __tablename__ = "price_history"
    
    token_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("tokens.id"), 
        nullable=False,
        comment="ID токена"
    )
    
    # Данные свечи
    open_price = Column(DECIMAL(20, 9), nullable=False, comment="Цена открытия")
    high_price = Column(DECIMAL(20, 9), nullable=False, comment="Максимальная цена")
    low_price = Column(DECIMAL(20, 9), nullable=False, comment="Минимальная цена")
    close_price = Column(DECIMAL(20, 9), nullable=False, comment="Цена закрытия")
    
    # Объемы
    volume_sol = Column(DECIMAL(20, 9), default=0, comment="Объем в SOL")
    volume_tokens = Column(DECIMAL(20, 9), default=0, comment="Объем в токенах")
    trade_count = Column(Integer, default=0, comment="Количество сделок")
    
    # Капитализация
    market_cap = Column(DECIMAL(20, 9), comment="Рыночная капитализация")
    
    # Временной интервал (в минутах: 1, 5, 15, 60, 240, 1440)
    interval_minutes = Column(Integer, nullable=False, comment="Интервал в минутах")
    period_start = Column(DateTime(timezone=True), nullable=False, comment="Начало периода")
    period_end = Column(DateTime(timezone=True), nullable=False, comment="Конец периода")
    
    # Связи
    token = relationship("Token", back_populates="price_history")
    
    # Индексы
    __table_args__ = (
        Index("idx_price_history_token_id", "token_id"),
        Index("idx_price_history_period", "token_id", "interval_minutes", "period_start"),
        Index("idx_price_history_time", "period_start"),
        UniqueConstraint("token_id", "interval_minutes", "period_start", name="uq_price_history_period"),
        CheckConstraint("high_price >= low_price", name="check_high_low_price"),
        CheckConstraint("open_price > 0 AND close_price > 0", name="check_positive_prices"),
    )


class UserToken(Base, UUIDMixin, TimestampMixin):
    """Связь пользователей и токенов (балансы)"""
    __tablename__ = "user_tokens"
    
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id"), 
        nullable=False,
        comment="ID пользователя"
    )
    token_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("tokens.id"), 
        nullable=False,
        comment="ID токена"
    )
    
    # Баланс
    balance = Column(DECIMAL(20, 9), default=0, comment="Баланс токенов")
    
    # Статистика
    total_bought = Column(DECIMAL(20, 9), default=0, comment="Всего куплено")
    total_sold = Column(DECIMAL(20, 9), default=0, comment="Всего продано")
    avg_buy_price = Column(DECIMAL(20, 9), comment="Средняя цена покупки")
    realized_pnl = Column(DECIMAL(20, 9), default=0, comment="Реализованная прибыль/убыток")
    
    # Первая и последняя операция
    first_trade_at = Column(DateTime(timezone=True), comment="Первая сделка")
    last_trade_at = Column(DateTime(timezone=True), comment="Последняя сделка")
    
    # Связи
    user = relationship("User")
    token = relationship("Token")
    
    # Индексы
    __table_args__ = (
        Index("idx_user_tokens_user_id", "user_id"),
        Index("idx_user_tokens_token_id", "token_id"),
        Index("idx_user_tokens_balance", "balance"),
        UniqueConstraint("user_id", "token_id", name="uq_user_token"),
        CheckConstraint("balance >= 0", name="check_non_negative_balance"),
    )
    
    @hybrid_property
    def unrealized_pnl(self) -> Optional[Decimal]:
        """Нереализованная прибыль/убыток"""
        if self.balance <= 0 or not self.avg_buy_price:
            return Decimal('0')
        
        # Нужно получить текущую цену токена
        # Это будет вычисляться в сервисном слое
        return None


# === ВСПОМОГАТЕЛЬНЫЕ ТАБЛИЦЫ ===

class Analytics(Base, UUIDMixin, TimestampMixin):
    """Аналитические данные"""
    __tablename__ = "analytics"
    
    # Временной период
    date = Column(DateTime(timezone=True), nullable=False, comment="Дата")
    period_type = Column(String(10), nullable=False, comment="Тип периода (day, hour)")
    
    # Общая статистика
    total_users = Column(Integer, default=0, comment="Общее количество пользователей")
    active_users = Column(Integer, default=0, comment="Активные пользователи")
    new_users = Column(Integer, default=0, comment="Новые пользователи")
    
    total_tokens = Column(Integer, default=0, comment="Общее количество токенов")
    new_tokens = Column(Integer, default=0, comment="Новые токены")
    graduated_tokens = Column(Integer, default=0, comment="Токены на DEX")
    
    total_trades = Column(Integer, default=0, comment="Общее количество сделок")
    total_volume = Column(DECIMAL(20, 9), default=0, comment="Общий объем торгов")
    platform_fees = Column(DECIMAL(20, 9), default=0, comment="Собранные комиссии")
    
    # Индексы
    __table_args__ = (
        Index("idx_analytics_date", "date"),
        Index("idx_analytics_period", "period_type", "date"),
        UniqueConstraint("date", "period_type", name="uq_analytics_period"),
    )


# === ФУНКЦИИ-ХЕЛПЕРЫ ===

def get_current_utc_time() -> datetime:
    """Получение текущего времени в UTC"""
    return datetime.now(timezone.utc)