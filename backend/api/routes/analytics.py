#!/usr/bin/env python3
"""
📊 API роутер для аналитики и метрик
Production-ready analytics с real-time данными
"""

import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, asc, func, text
from sqlalchemy.orm import selectinload

from ..models.database import (
    Token, Trade, User, PriceHistory, Analytics, 
    TokenStatus, TradeType, CurveType
)
from ..schemas.requests import PaginationRequest
from ..schemas.responses import (
    AnalyticsResponse, TrendingTokensResponse, MarketStatsResponse,
    VolumeAnalyticsResponse, UserLeaderboardResponse, PriceHistoryResponse,
    TokenPerformanceResponse, PlatformStatsResponse, TokenResponse
)
from ..services.cache import CacheService
from ..core.exceptions import ValidationException, DatabaseException
from ..core.config import settings

logger = logging.getLogger(__name__)

# Создание роутера
router = APIRouter()


# === DEPENDENCY FUNCTIONS ===

async def get_db() -> AsyncSession:
    """Dependency для получения сессии БД"""
    pass


async def get_cache_service() -> CacheService:
    """Dependency для получения Cache сервиса"""
    pass


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def _validate_time_period(period: str) -> timedelta:
    """Валидация и конвертация временного периода"""
    period_mapping = {
        "1h": timedelta(hours=1),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
        "1y": timedelta(days=365)
    }
    
    if period not in period_mapping:
        raise ValidationException(f"Invalid period: {period}. Allowed: {list(period_mapping.keys())}")
    
    return period_mapping[period]


async def _get_market_overview(db: AsyncSession) -> Dict[str, Any]:
    """Получение общего обзора рынка"""
    
    # Общее количество активных токенов
    total_tokens_query = select(func.count(Token.id)).where(
        Token.status == TokenStatus.ACTIVE
    )
    total_tokens = await db.execute(total_tokens_query)
    
    # Общий объем торгов за 24ч
    yesterday = datetime.utcnow() - timedelta(days=1)
    volume_24h_query = select(func.sum(Trade.sol_amount)).where(
        Trade.created_at >= yesterday
    )
    volume_24h = await db.execute(volume_24h_query)
    
    # Общее количество торгов за 24ч
    trades_24h_query = select(func.count(Trade.id)).where(
        Trade.created_at >= yesterday
    )
    trades_24h = await db.execute(trades_24h_query)
    
    # Общее количество пользователей
    total_users_query = select(func.count(User.id))
    total_users = await db.execute(total_users_query)
    
    # Средняя рыночная капитализация
    avg_market_cap_query = select(func.avg(Token.market_cap)).where(
        and_(
            Token.status == TokenStatus.ACTIVE,
            Token.market_cap > 0
        )
    )
    avg_market_cap = await db.execute(avg_market_cap_query)
    
    return {
        "total_tokens": total_tokens.scalar() or 0,
        "volume_24h": float(volume_24h.scalar() or 0),
        "trades_24h": trades_24h.scalar() or 0,
        "total_users": total_users.scalar() or 0,
        "avg_market_cap": float(avg_market_cap.scalar() or 0)
    }


async def _calculate_price_change(
    db: AsyncSession, 
    token_id: str, 
    period: timedelta
) -> Optional[float]:
    """Вычисление изменения цены за период"""
    
    try:
        period_start = datetime.utcnow() - period
        
        # Получение цены в начале периода
        start_price_query = select(PriceHistory.price).where(
            and_(
                PriceHistory.token_id == token_id,
                PriceHistory.timestamp >= period_start
            )
        ).order_by(asc(PriceHistory.timestamp)).limit(1)
        
        start_price_result = await db.execute(start_price_query)
        start_price = start_price_result.scalar()
        
        if not start_price:
            return None
        
        # Получение текущей цены
        current_price_query = select(PriceHistory.price).where(
            PriceHistory.token_id == token_id
        ).order_by(desc(PriceHistory.timestamp)).limit(1)
        
        current_price_result = await db.execute(current_price_query)
        current_price = current_price_result.scalar()
        
        if not current_price:
            return None
        
        # Вычисление процентного изменения
        price_change = ((float(current_price) - float(start_price)) / float(start_price)) * 100
        return price_change
        
    except Exception as e:
        logger.error(f"Failed to calculate price change: {e}")
        return None


# === ENDPOINTS ===

@router.get("/overview", response_model=MarketStatsResponse)
async def get_market_overview(
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Получение общего обзора рынка
    
    Включает основные метрики: количество токенов, объемы, пользователи.
    """
    try:
        # Попытка получить из кэша
        cache_key = "market_overview"
        cached_data = await cache.get(cache_key, 'analytics')
        
        if cached_data:
            return MarketStatsResponse(**cached_data)
        
        # Получение данных
        overview_data = await _get_market_overview(db)
        
        response = MarketStatsResponse(
            **overview_data,
            last_updated=datetime.utcnow()
        )
        
        # Кэширование на 5 минут
        await cache.set(cache_key, response.dict(), 'analytics', ttl=300)
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get market overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve market overview"
        )


@router.get("/trending/tokens", response_model=TrendingTokensResponse)
async def get_trending_tokens(
    period: str = Query("24h", regex="^(1h|24h|7d)$", description="Временной период"),
    limit: int = Query(20, ge=1, le=100, description="Количество токенов"),
    sort_by: str = Query("volume", regex="^(volume|price_change|trades|market_cap)$"),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Получение трендинговых токенов
    
    Сортировка по объему, изменению цены, количеству торгов или капитализации.
    """
    try:
        # Попытка получить из кэша
        cache_key = f"trending_tokens:{period}:{limit}:{sort_by}"
        cached_data = await cache.get(cache_key, 'analytics')
        
        if cached_data:
            return TrendingTokensResponse(**cached_data)
        
        # Валидация периода
        time_delta = _validate_time_period(period)
        period_start = datetime.utcnow() - time_delta
        
        # Базовый запрос
        query = select(Token).where(
            and_(
                Token.status == TokenStatus.ACTIVE,
                Token.market_cap > 0
            )
        ).options(selectinload(Token.creator))
        
        # Сортировка в зависимости от параметра
        if sort_by == "volume":
            if period == "1h":
                query = query.order_by(desc(Token.volume_1h))
            elif period == "24h":
                query = query.order_by(desc(Token.volume_24h))
            else:
                query = query.order_by(desc(Token.volume_7d))
        elif sort_by == "market_cap":
            query = query.order_by(desc(Token.market_cap))
        elif sort_by == "price_change":
            # Для изменения цены нужен более сложный запрос
            query = query.order_by(desc(Token.price_change_24h))
        else:  # trades
            query = query.order_by(desc(Token.trades_count))
        
        query = query.limit(limit)
        
        # Выполнение запроса
        result = await db.execute(query)
        tokens = result.scalars().all()
        
        # Обогащение данными об изменении цены
        trending_tokens = []
        for token in tokens:
            price_change = await _calculate_price_change(db, str(token.id), time_delta)
            
            token_data = {
                "token": TokenResponse.from_orm(token),
                "price_change_percent": price_change,
                "volume_period": getattr(token, f"volume_{period.replace('h', 'h').replace('d', 'd')}", 0),
                "rank": len(trending_tokens) + 1
            }
            trending_tokens.append(token_data)
        
        response = TrendingTokensResponse(
            period=period,
            tokens=trending_tokens,
            last_updated=datetime.utcnow()
        )
        
        # Кэширование на 2 минуты
        await cache.set(cache_key, response.dict(), 'analytics', ttl=120)
        
        return response
        
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trending tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trending tokens"
        )


@router.get("/volume", response_model=VolumeAnalyticsResponse)
async def get_volume_analytics(
    period: str = Query("24h", regex="^(1h|24h|7d|30d)$"),
    interval: str = Query("1h", regex="^(5m|15m|1h|4h|1d)$", description="Интервал группировки"),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Получение аналитики по объемам торгов
    
    Возвращает временной ряд объемов торгов с заданным интервалом.
    """
    try:
        # Попытка получить из кэша
        cache_key = f"volume_analytics:{period}:{interval}"
        cached_data = await cache.get(cache_key, 'analytics')
        
        if cached_data:
            return VolumeAnalyticsResponse(**cached_data)
        
        # Валидация периода
        time_delta = _validate_time_period(period)
        period_start = datetime.utcnow() - time_delta
        
        # Определение интервала группировки в PostgreSQL формате
        interval_mapping = {
            "5m": "5 minutes",
            "15m": "15 minutes", 
            "1h": "1 hour",
            "4h": "4 hours",
            "1d": "1 day"
        }
        
        pg_interval = interval_mapping.get(interval, "1 hour")
        
        # SQL запрос для группировки по времени
        volume_query = text("""
            SELECT 
                date_trunc(:interval, created_at) as time_bucket,
                SUM(sol_amount) as volume,
                COUNT(*) as trades_count
            FROM trades 
            WHERE created_at >= :start_time
            GROUP BY time_bucket
            ORDER BY time_bucket
        """)
        
        result = await db.execute(volume_query, {
            "interval": pg_interval,
            "start_time": period_start
        })
        
        volume_data = []
        total_volume = 0
        total_trades = 0
        
        for row in result:
            volume = float(row.volume or 0)
            trades = int(row.trades_count or 0)
            
            volume_data.append({
                "timestamp": row.time_bucket,
                "volume": volume,
                "trades_count": trades
            })
            
            total_volume += volume
            total_trades += trades
        
        # Вычисление средних значений
        data_points = len(volume_data)
        avg_volume = total_volume / data_points if data_points > 0 else 0
        avg_trades = total_trades / data_points if data_points > 0 else 0
        
        response = VolumeAnalyticsResponse(
            period=period,
            interval=interval,
            data=volume_data,
            total_volume=total_volume,
            total_trades=total_trades,
            avg_volume_per_interval=avg_volume,
            avg_trades_per_interval=avg_trades,
            last_updated=datetime.utcnow()
        )
        
        # Кэширование в зависимости от интервала
        ttl = 60 if interval in ["5m", "15m"] else 300  # 1-5 минут
        await cache.set(cache_key, response.dict(), 'analytics', ttl=ttl)
        
        return response
        
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to get volume analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve volume analytics"
        )


@router.get("/leaderboard/users", response_model=UserLeaderboardResponse)
async def get_user_leaderboard(
    metric: str = Query("volume", regex="^(volume|pnl|trades|win_rate)$"),
    period: str = Query("30d", regex="^(7d|30d|90d|all)$"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Получение лидерборда пользователей
    
    Ранжирование по объему торгов, P&L, количеству сделок или win rate.
    """
    try:
        # Попытка получить из кэша
        cache_key = f"user_leaderboard:{metric}:{period}:{limit}"
        cached_data = await cache.get(cache_key, 'analytics')
        
        if cached_data:
            return UserLeaderboardResponse(**cached_data)
        
        # Определение временного фильтра
        if period != "all":
            time_delta = _validate_time_period(period)
            period_start = datetime.utcnow() - time_delta
            time_filter = Trade.created_at >= period_start
        else:
            time_filter = True
        
        # Запрос в зависимости от метрики
        if metric == "volume":
            query = select(
                User.id,
                User.username,
                User.wallet_address,
                User.profile_image_url,
                func.sum(Trade.sol_amount).label('total_volume'),
                func.count(Trade.id).label('trades_count')
            ).join(Trade).where(time_filter).group_by(
                User.id, User.username, User.wallet_address, User.profile_image_url
            ).order_by(desc('total_volume')).limit(limit)
            
        elif metric == "pnl":
            query = select(
                User.id,
                User.username, 
                User.wallet_address,
                User.profile_image_url,
                func.sum(Trade.realized_pnl).label('total_pnl'),
                func.count(Trade.id).label('trades_count')
            ).join(Trade).where(time_filter).group_by(
                User.id, User.username, User.wallet_address, User.profile_image_url
            ).order_by(desc('total_pnl')).limit(limit)
            
        elif metric == "trades":
            query = select(
                User.id,
                User.username,
                User.wallet_address, 
                User.profile_image_url,
                func.count(Trade.id).label('trades_count'),
                func.sum(Trade.sol_amount).label('total_volume')
            ).join(Trade).where(time_filter).group_by(
                User.id, User.username, User.wallet_address, User.profile_image_url
            ).order_by(desc('trades_count')).limit(limit)
            
        else:  # win_rate
            query = select(
                User.id,
                User.username,
                User.wallet_address,
                User.profile_image_url,
                User.win_rate,
                func.count(Trade.id).label('trades_count')
            ).join(Trade).where(time_filter).group_by(
                User.id, User.username, User.wallet_address, User.profile_image_url, User.win_rate
            ).having(func.count(Trade.id) >= 5).order_by(desc(User.win_rate)).limit(limit)
        
        result = await db.execute(query)
        
        leaderboard_data = []
        for i, row in enumerate(result, 1):
            user_data = {
                "rank": i,
                "user_id": str(row.id),
                "username": row.username,
                "wallet_address": row.wallet_address,
                "profile_image_url": row.profile_image_url,
                "metric_value": 0,
                "trades_count": row.trades_count if hasattr(row, 'trades_count') else 0
            }
            
            if metric == "volume":
                user_data["metric_value"] = float(row.total_volume or 0)
            elif metric == "pnl":
                user_data["metric_value"] = float(row.total_pnl or 0)
            elif metric == "trades":
                user_data["metric_value"] = int(row.trades_count or 0)
            else:  # win_rate
                user_data["metric_value"] = float(row.win_rate or 0)
            
            leaderboard_data.append(user_data)
        
        response = UserLeaderboardResponse(
            metric=metric,
            period=period,
            leaderboard=leaderboard_data,
            last_updated=datetime.utcnow()
        )
        
        # Кэширование на 10 минут
        await cache.set(cache_key, response.dict(), 'analytics', ttl=600)
        
        return response
        
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user leaderboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user leaderboard"
        )


@router.get("/tokens/{token_id}/performance", response_model=TokenPerformanceResponse)
async def get_token_performance(
    token_id: str,
    period: str = Query("7d", regex="^(1d|7d|30d|90d)$"),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Получение детальной аналитики производительности токена
    """
    try:
        # Попытка получить из кэша
        cache_key = f"token_performance:{token_id}:{period}"
        cached_data = await cache.get(cache_key, 'analytics')
        
        if cached_data:
            return TokenPerformanceResponse(**cached_data)
        
        # Валидация периода
        time_delta = _validate_time_period(period)
        period_start = datetime.utcnow() - time_delta
        
        # Получение базовой информации о токене
        token_query = select(Token).where(Token.id == token_id)
        token_result = await db.execute(token_query)
        token = token_result.scalar_one_or_none()
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token not found"
            )
        
        # Статистика торгов за период
        trades_stats_query = select(
            func.count(Trade.id).label('total_trades'),
            func.sum(Trade.sol_amount).label('total_volume'),
            func.sum(
                func.case([(Trade.trade_type == TradeType.BUY, Trade.sol_amount)], else_=0)
            ).label('buy_volume'),
            func.sum(
                func.case([(Trade.trade_type == TradeType.SELL, Trade.sol_amount)], else_=0)
            ).label('sell_volume'),
            func.count(func.distinct(Trade.user_id)).label('unique_traders')
        ).where(
            and_(
                Trade.token_id == token_id,
                Trade.created_at >= period_start
            )
        )
        
        trades_stats = await db.execute(trades_stats_query)
        stats_row = trades_stats.first()
        
        # История цен
        price_history_query = select(PriceHistory).where(
            and_(
                PriceHistory.token_id == token_id,
                PriceHistory.timestamp >= period_start
            )
        ).order_by(PriceHistory.timestamp)
        
        price_history_result = await db.execute(price_history_query)
        price_history = price_history_result.scalars().all()
        
        # Вычисление метрик производительности
        price_data = [{"timestamp": ph.timestamp, "price": float(ph.price)} for ph in price_history]
        
        if price_data:
            start_price = price_data[0]["price"]
            current_price = price_data[-1]["price"]
            price_change_percent = ((current_price - start_price) / start_price) * 100
            
            # Максимальная и минимальная цена
            prices = [p["price"] for p in price_data]
            high_price = max(prices)
            low_price = min(prices)
        else:
            price_change_percent = 0
            high_price = float(token.current_price)
            low_price = float(token.current_price)
        
        response = TokenPerformanceResponse(
            token_id=token_id,
            token_symbol=token.symbol,
            token_name=token.name,
            period=period,
            current_price=float(token.current_price),
            price_change_percent=price_change_percent,
            high_price=high_price,
            low_price=low_price,
            total_trades=stats_row.total_trades or 0,
            total_volume=float(stats_row.total_volume or 0),
            buy_volume=float(stats_row.buy_volume or 0),
            sell_volume=float(stats_row.sell_volume or 0),
            unique_traders=stats_row.unique_traders or 0,
            price_history=price_data,
            last_updated=datetime.utcnow()
        )
        
        # Кэширование на 5 минут
        await cache.set(cache_key, response.dict(), 'analytics', ttl=300)
        
        return response
        
    except ValidationException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get token performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve token performance"
        )


@router.get("/platform/stats", response_model=PlatformStatsResponse)
async def get_platform_statistics(
    period: str = Query("30d", regex="^(7d|30d|90d|all)$"),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Получение общей статистики платформы
    """
    try:
        # Попытка получить из кэша
        cache_key = f"platform_stats:{period}"
        cached_data = await cache.get(cache_key, 'analytics')
        
        if cached_data:
            return PlatformStatsResponse(**cached_data)
        
        # Определение временного фильтра
        if period != "all":
            time_delta = _validate_time_period(period)
            period_start = datetime.utcnow() - time_delta
            time_filter = lambda table: table.created_at >= period_start
        else:
            time_filter = lambda table: True
        
        # Общая статистика токенов
        tokens_stats_query = select(
            func.count(Token.id).label('total_tokens'),
            func.count(
                func.case([(Token.is_graduated, 1)], else_=None)
            ).label('graduated_tokens'),
            func.sum(Token.market_cap).label('total_market_cap'),
            func.avg(Token.market_cap).label('avg_market_cap')
        ).where(time_filter(Token))
        
        tokens_stats = await db.execute(tokens_stats_query)
        tokens_row = tokens_stats.first()
        
        # Статистика пользователей
        users_stats_query = select(
            func.count(User.id).label('total_users'),
            func.count(
                func.case([(User.tokens_created > 0, 1)], else_=None)
            ).label('token_creators'),
            func.avg(User.reputation_score).label('avg_reputation')
        ).where(time_filter(User))
        
        users_stats = await db.execute(users_stats_query)
        users_row = users_stats.first()
        
        # Статистика торгов
        trades_stats_query = select(
            func.count(Trade.id).label('total_trades'),
            func.sum(Trade.sol_amount).label('total_volume'),
            func.avg(Trade.sol_amount).label('avg_trade_size'),
            func.count(func.distinct(Trade.user_id)).label('active_traders')
        ).where(time_filter(Trade))
        
        trades_stats = await db.execute(trades_stats_query)
        trades_row = trades_stats.first()
        
        # Распределение по типам кривых
        curve_distribution_query = select(
            Token.curve_type,
            func.count(Token.id).label('count')
        ).where(time_filter(Token)).group_by(Token.curve_type)
        
        curve_distribution = await db.execute(curve_distribution_query)
        curve_stats = {row.curve_type.value: row.count for row in curve_distribution}
        
        response = PlatformStatsResponse(
            period=period,
            # Токены
            total_tokens=tokens_row.total_tokens or 0,
            graduated_tokens=tokens_row.graduated_tokens or 0,
            total_market_cap=float(tokens_row.total_market_cap or 0),
            avg_market_cap=float(tokens_row.avg_market_cap or 0),
            # Пользователи
            total_users=users_row.total_users or 0,
            token_creators=users_row.token_creators or 0,
            avg_reputation=float(users_row.avg_reputation or 0),
            # Торги
            total_trades=trades_row.total_trades or 0,
            total_volume=float(trades_row.total_volume or 0),
            avg_trade_size=float(trades_row.avg_trade_size or 0),
            active_traders=trades_row.active_traders or 0,
            # Распределения
            curve_type_distribution=curve_stats,
            last_updated=datetime.utcnow()
        )
        
        # Кэширование на 15 минут
        await cache.set(cache_key, response.dict(), 'analytics', ttl=900)
        
        return response
        
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to get platform statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve platform statistics"
        )