#!/usr/bin/env python3
"""
💱 API роутер для торговых операций
Production-ready endpoints для покупки/продажи токенов
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import selectinload

from ..models.database import (
    Token, Trade, User, UserToken, TradeType, TokenStatus
)
from ..schemas.requests import (
    BuyTokensRequest, SellTokensRequest, TradeHistoryRequest,
    BatchTradeRequest
)
from ..schemas.responses import (
    TradeResponse, TradeEstimateResponse, TradesListResponse,
    UserPortfolioResponse, BatchTradeResponse, SuccessResponse,
    TokenResponse, PaginationResponse
)
from ..services.blockchain import SolanaService, TradeResult
from ..services.cache import CacheService
from ..core.exceptions import (
    ValidationException, InsufficientBalanceException, TradingPausedException,
    MaxTradeSizeExceededException, InsufficientLiquidityException,
    TokenGraduatedException, RecordNotFoundException, BlockchainException
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


async def get_solana_service() -> SolanaService:
    """Dependency для получения Solana сервиса"""
    pass


async def get_cache_service() -> CacheService:
    """Dependency для получения Cache сервиса"""
    pass


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

async def _validate_trading_conditions(
    token: Token,
    sol_amount: Optional[Decimal] = None,
    token_amount: Optional[Decimal] = None
):
    """Валидация условий для торговли"""
    
    # Проверка статуса токена
    if token.status != TokenStatus.ACTIVE:
        raise TradingPausedException("Token trading is paused")
    
    # Проверка что токен не выпущен на DEX
    if token.is_graduated:
        raise TokenGraduatedException(token.mint_address)
    
    # Проверка размера сделки
    if sol_amount and sol_amount > settings.MAX_TRADE_SIZE_SOL:
        raise MaxTradeSizeExceededException(
            float(sol_amount), 
            settings.MAX_TRADE_SIZE_SOL
        )
    
    # Проверка ликвидности
    if sol_amount and token.sol_reserves < sol_amount:
        raise InsufficientLiquidityException(
            float(sol_amount),
            float(token.sol_reserves)
        )
    
    if token_amount and token.token_reserves < token_amount:
        raise InsufficientLiquidityException(
            float(token_amount),
            float(token.token_reserves)
        )


async def _get_user_token_balance(
    db: AsyncSession,
    user_id: UUID,
    token_id: UUID
) -> Decimal:
    """Получение баланса токена у пользователя"""
    
    stmt = select(UserToken).where(
        and_(
            UserToken.user_id == user_id,
            UserToken.token_id == token_id
        )
    )
    result = await db.execute(stmt)
    user_token = result.scalar_one_or_none()
    
    return user_token.balance if user_token else Decimal('0')


async def _update_user_token_balance(
    db: AsyncSession,
    user_id: UUID,
    token_id: UUID,
    amount_delta: Decimal,
    avg_price: Optional[Decimal] = None
):
    """Обновление баланса токена у пользователя"""
    
    stmt = select(UserToken).where(
        and_(
            UserToken.user_id == user_id,
            UserToken.token_id == token_id
        )
    )
    result = await db.execute(stmt)
    user_token = result.scalar_one_or_none()
    
    if not user_token:
        # Создание новой записи
        user_token = UserToken(
            user_id=user_id,
            token_id=token_id,
            balance=max(amount_delta, Decimal('0')),
            avg_buy_price=avg_price,
            first_trade_at=datetime.utcnow(),
            last_trade_at=datetime.utcnow()
        )
        
        if amount_delta > 0:
            user_token.total_bought = amount_delta
        else:
            user_token.total_sold = abs(amount_delta)
        
        db.add(user_token)
    else:
        # Обновление существующей записи
        user_token.balance += amount_delta
        user_token.last_trade_at = datetime.utcnow()
        
        if amount_delta > 0:
            # Покупка - обновляем средню цену покупки
            user_token.total_bought += amount_delta
            if avg_price and user_token.avg_buy_price:
                # Взвешенная средняя цена
                total_value = (user_token.balance * user_token.avg_buy_price) + (amount_delta * avg_price)
                user_token.avg_buy_price = total_value / user_token.balance
            elif avg_price:
                user_token.avg_buy_price = avg_price
        else:
            # Продажа
            user_token.total_sold += abs(amount_delta)
            
            # Расчет реализованной прибыли/убытка
            if user_token.avg_buy_price and avg_price:
                realized_pnl = abs(amount_delta) * (avg_price - user_token.avg_buy_price)
                user_token.realized_pnl += realized_pnl
        
        # Устанавливаем first_trade_at если не было
        if not user_token.first_trade_at:
            user_token.first_trade_at = datetime.utcnow()


async def _record_trade(
    db: AsyncSession,
    user_id: UUID,
    token_id: UUID,
    trade_result: TradeResult,
    trade_type: TradeType,
    market_cap_before: Decimal,
    market_cap_after: Decimal,
    expected_amount: Optional[Decimal] = None,
    max_slippage: Optional[float] = None
) -> Trade:
    """Запись торговой операции в БД"""
    
    trade = Trade(
        transaction_signature=trade_result.transaction_signature,
        user_id=user_id,
        token_id=token_id,
        trade_type=trade_type,
        sol_amount=trade_result.sol_amount,
        token_amount=trade_result.tokens_amount,
        price_per_token=trade_result.price_per_token,
        expected_amount=expected_amount,
        actual_slippage=trade_result.slippage,
        max_slippage=max_slippage,
        platform_fee=trade_result.fees_paid,
        market_cap_before=market_cap_before,
        market_cap_after=market_cap_after,
        price_impact=None,  # Будет рассчитан
        is_successful=trade_result.success,
        error_message=trade_result.error_message
    )
    
    # Расчет влияния на цену
    if market_cap_before > 0:
        trade.price_impact = float((market_cap_after - market_cap_before) / market_cap_before * 100)
    
    db.add(trade)
    return trade


async def _update_token_stats(
    db: AsyncSession,
    token: Token,
    trade_amount_sol: Decimal,
    trade_amount_tokens: Decimal,
    new_price: Decimal,
    new_market_cap: Decimal
):
    """Обновление статистики токена после торговли"""
    
    token.current_price = new_price
    token.market_cap = new_market_cap
    token.trade_count += 1
    token.volume_total += trade_amount_sol
    token.volume_24h += trade_amount_sol  # В реальности нужна логика для 24h
    token.trades_24h += 1
    
    # Обновление ATH
    if new_price > (token.all_time_high_price or Decimal('0')):
        token.all_time_high_price = new_price
    
    if new_market_cap > (token.all_time_high_mc or Decimal('0')):
        token.all_time_high_mc = new_market_cap


async def _update_user_stats(
    db: AsyncSession,
    user: User,
    trade_amount_sol: Decimal,
    is_profitable: bool
):
    """Обновление статистики пользователя"""
    
    user.total_trades += 1
    user.total_volume_traded += trade_amount_sol
    user.last_trade_at = datetime.utcnow()
    
    if is_profitable:
        user.profitable_trades += 1


# === ENDPOINTS ===

@router.post("/estimate", response_model=TradeEstimateResponse)
async def estimate_trade(
    token_address: str,
    sol_amount: Optional[Decimal] = Query(None, description="Количество SOL для покупки"),
    token_amount: Optional[Decimal] = Query(None, description="Количество токенов для продажи"),
    db: AsyncSession = Depends(get_db),
    solana: SolanaService = Depends(get_solana_service),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Оценка торговой операции без выполнения
    
    Возвращает ожидаемое количество, slippage, комиссии и влияние на цену
    """
    try:
        # Валидация входных параметров
        if not sol_amount and not token_amount:
            raise ValidationException("Either sol_amount or token_amount must be specified")
        
        if sol_amount and token_amount:
            raise ValidationException("Only one of sol_amount or token_amount should be specified")
        
        # Проверка кэша
        cache_key = f"estimate:{token_address}:{sol_amount or token_amount}"
        cached_estimate = await cache.get(cache_key, "trade")
        
        if cached_estimate:
            return TradeEstimateResponse(**cached_estimate)
        
        # Получение токена
        stmt = select(Token).where(Token.mint_address == token_address)
        result = await db.execute(stmt)
        token = result.scalar_one_or_none()
        
        if not token:
            raise RecordNotFoundException("Token", token_address)
        
        # Валидация условий торговли
        await _validate_trading_conditions(token, sol_amount, token_amount)
        
        # Получение оценки из блокчейна
        if sol_amount:
            # Покупка токенов
            estimate_data = await solana.estimate_trade(
                token_address, sol_amount, is_buy=True
            )
            input_amount = sol_amount
            is_buy = True
        else:
            # Продажа токенов
            estimate_data = await solana.estimate_trade(
                token_address, token_amount, is_buy=False
            )
            input_amount = token_amount
            is_buy = False
        
        # Формирование ответа
        response = TradeEstimateResponse(
            expected_output=estimate_data["expected_output"],
            price_impact=estimate_data["price_impact"],
            estimated_slippage=estimate_data["estimated_slippage"],
            platform_fee=estimate_data["platform_fee"],
            minimum_output=estimate_data["minimum_output"],
            price_per_token=estimate_data["price_per_token"],
            market_cap_after=token.market_cap + (
                input_amount if is_buy else -input_amount
            )  # Упрощенный расчет
        )
        
        # Кэширование на 30 секунд
        await cache.set(cache_key, response.dict(), "trade", ttl=30)
        
        return response
        
    except (ValidationException, RecordNotFoundException):
        raise
    except Exception as e:
        logger.error(f"Failed to estimate trade: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to estimate trade"
        )


@router.post("/buy", response_model=TradeResponse)
async def buy_tokens(
    buy_request: BuyTokensRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    solana: SolanaService = Depends(get_solana_service),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Покупка токенов за SOL
    
    Выполняет торговую операцию через смарт-контракт
    """
    try:
        logger.info(f"User {current_user.id} buying tokens: {buy_request.dict()}")
        
        # Получение токена
        stmt = select(Token).where(Token.mint_address == buy_request.token_address)
        result = await db.execute(stmt)
        token = result.scalar_one_or_none()
        
        if not token:
            raise RecordNotFoundException("Token", buy_request.token_address)
        
        # Валидация условий торговли
        await _validate_trading_conditions(token, buy_request.sol_amount)
        
        # Проверка баланса SOL пользователя
        user_sol_balance = await solana.get_sol_balance(current_user.wallet_address)
        if user_sol_balance < buy_request.sol_amount:
            raise InsufficientBalanceException(
                float(buy_request.sol_amount),
                float(user_sol_balance)
            )
        
        # Сохранение состояния до торговли
        market_cap_before = token.market_cap
        
        # Выполнение торговой операции в блокчейне
        trade_result = await solana.buy_tokens(
            buyer_wallet=current_user.wallet_address,
            token_mint=buy_request.token_address,
            sol_amount=buy_request.sol_amount,
            min_tokens_out=buy_request.min_tokens_out,
            slippage_tolerance=buy_request.slippage_tolerance
        )
        
        if not trade_result.success:
            raise BlockchainException(
                f"Trade failed: {trade_result.error_message}",
                transaction_signature=trade_result.transaction_signature
            )
        
        # Расчет нового market cap (упрощенно)
        market_cap_after = token.market_cap + buy_request.sol_amount
        
        # Запись торговой операции
        trade = await _record_trade(
            db=db,
            user_id=current_user.id,
            token_id=token.id,
            trade_result=trade_result,
            trade_type=TradeType.BUY,
            market_cap_before=market_cap_before,
            market_cap_after=market_cap_after,
            expected_amount=buy_request.min_tokens_out,
            max_slippage=buy_request.slippage_tolerance
        )
        
        # Обновление баланса пользователя
        await _update_user_token_balance(
            db=db,
            user_id=current_user.id,
            token_id=token.id,
            amount_delta=trade_result.tokens_amount,
            avg_price=trade_result.price_per_token
        )
        
        # Обновление статистики токена
        await _update_token_stats(
            db=db,
            token=token,
            trade_amount_sol=trade_result.sol_amount,
            trade_amount_tokens=trade_result.tokens_amount,
            new_price=trade_result.price_per_token,
            new_market_cap=market_cap_after
        )
        
        # Обновление статистики пользователя
        await _update_user_stats(
            db=db,
            user=current_user,
            trade_amount_sol=trade_result.sol_amount,
            is_profitable=True  # При покупке всегда считаем успешной
        )
        
        await db.commit()
        await db.refresh(trade)
        
        # Очистка кэша
        await cache.delete_pattern(f"*{token.mint_address}*", "price")
        await cache.delete_pattern(f"*{current_user.id}*", "user")
        
        # Формирование ответа
        response = TradeResponse.from_orm(trade)
        response.token = TokenResponse.from_orm(token)
        
        logger.info(f"✅ Buy trade completed: {trade.transaction_signature}")
        
        return response
        
    except (
        ValidationException, RecordNotFoundException, InsufficientBalanceException,
        TradingPausedException, BlockchainException
    ):
        raise
    except Exception as e:
        logger.error(f"Failed to buy tokens: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute buy order"
        )


@router.post("/sell", response_model=TradeResponse)
async def sell_tokens(
    sell_request: SellTokensRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    solana: SolanaService = Depends(get_solana_service),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Продажа токенов за SOL
    """
    try:
        logger.info(f"User {current_user.id} selling tokens: {sell_request.dict()}")
        
        # Получение токена
        stmt = select(Token).where(Token.mint_address == sell_request.token_address)
        result = await db.execute(stmt)
        token = result.scalar_one_or_none()
        
        if not token:
            raise RecordNotFoundException("Token", sell_request.token_address)
        
        # Валидация условий торговли
        await _validate_trading_conditions(token, token_amount=sell_request.token_amount)
        
        # Проверка баланса токенов пользователя
        user_token_balance = await _get_user_token_balance(
            db, current_user.id, token.id
        )
        
        if user_token_balance < sell_request.token_amount:
            raise InsufficientBalanceException(
                float(sell_request.token_amount),
                float(user_token_balance)
            )
        
        # Сохранение состояния до торговли
        market_cap_before = token.market_cap
        
        # Выполнение торговой операции в блокчейне
        trade_result = await solana.sell_tokens(
            seller_wallet=current_user.wallet_address,
            token_mint=sell_request.token_address,
            token_amount=sell_request.token_amount,
            min_sol_out=sell_request.min_sol_out,
            slippage_tolerance=sell_request.slippage_tolerance
        )
        
        if not trade_result.success:
            raise BlockchainException(
                f"Trade failed: {trade_result.error_message}",
                transaction_signature=trade_result.transaction_signature
            )
        
        # Расчет нового market cap
        market_cap_after = token.market_cap - trade_result.sol_amount
        
        # Запись торговой операции
        trade = await _record_trade(
            db=db,
            user_id=current_user.id,
            token_id=token.id,
            trade_result=trade_result,
            trade_type=TradeType.SELL,
            market_cap_before=market_cap_before,
            market_cap_after=market_cap_after,
            expected_amount=sell_request.min_sol_out,
            max_slippage=sell_request.slippage_tolerance
        )
        
        # Обновление баланса пользователя
        await _update_user_token_balance(
            db=db,
            user_id=current_user.id,
            token_id=token.id,
            amount_delta=-sell_request.token_amount,
            avg_price=trade_result.price_per_token
        )
        
        # Обновление статистики токена
        await _update_token_stats(
            db=db,
            token=token,
            trade_amount_sol=trade_result.sol_amount,
            trade_amount_tokens=sell_request.token_amount,
            new_price=trade_result.price_per_token,
            new_market_cap=market_cap_after
        )
        
        # Определение прибыльности (упрощенно)
        # В реальности нужно сравнить с средней ценой покупки
        is_profitable = True  # Заглушка
        
        # Обновление статистики пользователя
        await _update_user_stats(
            db=db,
            user=current_user,
            trade_amount_sol=trade_result.sol_amount,
            is_profitable=is_profitable
        )
        
        await db.commit()
        await db.refresh(trade)
        
        # Очистка кэша
        await cache.delete_pattern(f"*{token.mint_address}*", "price")
        await cache.delete_pattern(f"*{current_user.id}*", "user")
        
        # Формирование ответа
        response = TradeResponse.from_orm(trade)
        response.token = TokenResponse.from_orm(token)
        
        logger.info(f"✅ Sell trade completed: {trade.transaction_signature}")
        
        return response
        
    except (
        ValidationException, RecordNotFoundException, InsufficientBalanceException,
        TradingPausedException, BlockchainException
    ):
        raise
    except Exception as e:
        logger.error(f"Failed to sell tokens: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute sell order"
        )


@router.get("/history", response_model=TradesListResponse)
async def get_trade_history(
    history_request: TradeHistoryRequest = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Получение истории торговых операций
    
    Возвращает историю торгов с фильтрацией и пагинацией
    """
    try:
        # Базовый запрос
        query = select(Trade).options(
            selectinload(Trade.token).selectinload(Token.creator)
        )
        
        # Фильтр по пользователю (если не админ, показываем только свои)
        if history_request.user_id:
            if current_user.role != "admin":
                # Обычный пользователь может видеть только свои сделки
                query = query.where(Trade.user_id == current_user.id)
            else:
                # Админ может просматривать сделки любого пользователя
                query = query.where(Trade.user_id == UUID(history_request.user_id))
        else:
            # Если пользователь не указан, показываем сделки текущего пользователя
            query = query.where(Trade.user_id == current_user.id)
        
        # Применение фильтров
        if history_request.token_id:
            query = query.where(Trade.token_id == UUID(history_request.token_id))
        
        if history_request.trade_type:
            query = query.where(Trade.trade_type == history_request.trade_type)
        
        if history_request.min_amount:
            query = query.where(Trade.sol_amount >= history_request.min_amount)
        
        if history_request.date_from:
            query = query.where(Trade.created_at >= history_request.date_from)
        
        if history_request.date_to:
            query = query.where(Trade.created_at <= history_request.date_to)
        
        # Подсчет общего количества
        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        total_count = result.scalar()
        
        # Сортировка и пагинация
        query = query.order_by(desc(Trade.created_at))
        offset = (history_request.page - 1) * history_request.limit
        query = query.offset(offset).limit(history_request.limit)
        
        # Выполнение запроса
        result = await db.execute(query)
        trades = result.scalars().all()
        
        # Формирование ответа
        trade_responses = [TradeResponse.from_orm(trade) for trade in trades]
        
        pagination = PaginationResponse(
            page=history_request.page,
            limit=history_request.limit,
            total=total_count,
            pages=(total_count + history_request.limit - 1) // history_request.limit,
            has_next=history_request.page * history_request.limit < total_count,
            has_prev=history_request.page > 1
        )
        
        return TradesListResponse(
            trades=trade_responses,
            pagination=pagination
        )
        
    except Exception as e:
        logger.error(f"Failed to get trade history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trade history"
        )


@router.get("/portfolio", response_model=UserPortfolioResponse)
async def get_user_portfolio(
    user_id: Optional[UUID] = Query(None, description="ID пользователя (только админ)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    solana: SolanaService = Depends(get_solana_service),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Получение портфеля пользователя
    
    Показывает все позиции, общую стоимость и P&L
    """
    try:
        # Определение пользователя для портфеля
        target_user_id = user_id if user_id and current_user.role == "admin" else current_user.id
        
        # Кэш ключ
        cache_key = f"portfolio:{target_user_id}"
        cached_portfolio = await cache.get(cache_key, "user")
        
        if cached_portfolio:
            return UserPortfolioResponse(**cached_portfolio)
        
        # Получение всех позиций пользователя
        stmt = select(UserToken).where(
            and_(
                UserToken.user_id == target_user_id,
                UserToken.balance > 0
            )
        ).options(
            selectinload(UserToken.token).selectinload(Token.creator)
        )
        
        result = await db.execute(stmt)
        positions = result.scalars().all()
        
        total_value_sol = Decimal('0')
        total_pnl = Decimal('0')
        position_data = []
        
        for position in positions:
            # Получение текущей цены токена
            price_info = await solana.get_token_price(position.token.mint_address)
            
            if price_info:
                current_value = position.balance * price_info.current_price
                total_value_sol += current_value
                
                # Расчет P&L
                if position.avg_buy_price:
                    cost_basis = position.balance * position.avg_buy_price
                    unrealized_pnl = current_value - cost_basis
                    total_pnl += unrealized_pnl + position.realized_pnl
                else:
                    unrealized_pnl = Decimal('0')
                
                position_data.append({
                    "token": TokenResponse.from_orm(position.token).dict(),
                    "balance": float(position.balance),
                    "avg_buy_price": float(position.avg_buy_price) if position.avg_buy_price else None,
                    "current_price": float(price_info.current_price),
                    "current_value_sol": float(current_value),
                    "unrealized_pnl": float(unrealized_pnl),
                    "realized_pnl": float(position.realized_pnl),
                    "total_pnl": float(unrealized_pnl + position.realized_pnl),
                    "total_bought": float(position.total_bought),
                    "total_sold": float(position.total_sold),
                    "first_trade_at": position.first_trade_at,
                    "last_trade_at": position.last_trade_at
                })
        
        # Расчет процентного P&L
        total_pnl_percent = 0.0
        if total_value_sol > 0:
            cost_basis_total = total_value_sol - total_pnl
            if cost_basis_total > 0:
                total_pnl_percent = float(total_pnl / cost_basis_total * 100)
        
        response = UserPortfolioResponse(
            user_id=target_user_id,
            total_value_sol=total_value_sol,
            total_value_usd=None,  # Можно добавить конвертацию через API
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            positions=position_data
        )
        
        # Кэширование на 2 минуты
        await cache.set(cache_key, response.dict(), "user", ttl=120)
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get user portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve portfolio"
        )


@router.post("/batch", response_model=BatchTradeResponse)
async def execute_batch_trades(
    batch_request: BatchTradeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    solana: SolanaService = Depends(get_solana_service)
):
    """
    Выполнение пакета торговых операций
    
    Поддерживает режим "все или ничего"
    """
    try:
        logger.info(f"User {current_user.id} executing batch trades: {len(batch_request.trades)} operations")
        
        results = []
        errors = []
        successful_trades = []
        total_volume = Decimal('0')
        total_fees = Decimal('0')
        
        # Если режим "все или ничего", используем точку сохранения
        if batch_request.execute_all_or_none:
            savepoint = await db.begin_nested()
        
        try:
            for i, trade_request in enumerate(batch_request.trades):
                try:
                    if isinstance(trade_request, BuyTokensRequest):
                        # Выполнение покупки
                        trade_response = await buy_tokens(
                            trade_request, db, current_user, solana, None
                        )
                        successful_trades.append(trade_response)
                        total_volume += trade_request.sol_amount
                        
                    elif isinstance(trade_request, SellTokensRequest):
                        # Выполнение продажи
                        trade_response = await sell_tokens(
                            trade_request, db, current_user, solana, None
                        )
                        successful_trades.append(trade_response)
                        # Для продажи берем SOL из результата
                        total_volume += trade_response.sol_amount
                    
                    results.append({
                        "index": i,
                        "success": True,
                        "trade": trade_response.dict()
                    })
                    
                except Exception as e:
                    error_info = {
                        "index": i,
                        "success": False,
                        "error": str(e),
                        "trade_request": trade_request.dict()
                    }
                    
                    errors.append(error_info)
                    results.append(error_info)
                    
                    # В режиме "все или ничего" прерываем при первой ошибке
                    if batch_request.execute_all_or_none:
                        raise e
            
            # Если дошли до сюда в режиме "все или ничего", коммитим savepoint
            if batch_request.execute_all_or_none:
                await savepoint.commit()
            
        except Exception as e:
            # Откат в режиме "все или ничего"
            if batch_request.execute_all_or_none:
                await savepoint.rollback()
                raise e
        
        # Подсчет статистики
        for trade in successful_trades:
            if hasattr(trade, 'platform_fee') and trade.platform_fee:
                total_fees += trade.platform_fee
        
        # Финальный коммит
        await db.commit()
        
        response = BatchTradeResponse(
            total_operations=len(batch_request.trades),
            successful_operations=len(successful_trades),
            failed_operations=len(errors),
            results=results,
            errors=errors,
            total_volume=total_volume,
            total_fees=total_fees,
            successful_trades=successful_trades
        )
        
        logger.info(f"✅ Batch trades completed: {len(successful_trades)}/{len(batch_request.trades)} successful")
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to execute batch trades: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute batch trades"
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_trading_stats(
    period: str = Query("24h", regex="^(1h|24h|7d|30d)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Получение статистики торговли пользователя
    """
    try:
        # Кэш ключ
        cache_key = f"trading_stats:{current_user.id}:{period}"
        cached_stats = await cache.get(cache_key, "analytics")
        
        if cached_stats:
            return cached_stats
        
        # Определение временного диапазона
        now = datetime.utcnow()
        if period == "1h":
            start_time = now - timedelta(hours=1)
        elif period == "24h":
            start_time = now - timedelta(days=1)
        elif period == "7d":
            start_time = now - timedelta(days=7)
        else:  # 30d
            start_time = now - timedelta(days=30)
        
        # Запрос статистики
        stmt = select(
            func.count(Trade.id).label('total_trades'),
            func.sum(Trade.sol_amount).label('total_volume'),
            func.sum(Trade.platform_fee).label('total_fees'),
            func.count(Trade.id).filter(Trade.trade_type == TradeType.BUY).label('buy_count'),
            func.count(Trade.id).filter(Trade.trade_type == TradeType.SELL).label('sell_count'),
            func.avg(Trade.actual_slippage).label('avg_slippage'),
            func.max(Trade.sol_amount).label('largest_trade')
        ).where(
            and_(
                Trade.user_id == current_user.id,
                Trade.created_at >= start_time,
                Trade.is_successful == True
            )
        )
        
        result = await db.execute(stmt)
        stats_row = result.one()
        
        stats = {
            "period": period,
            "total_trades": stats_row.total_trades or 0,
            "total_volume_sol": float(stats_row.total_volume or 0),
            "total_fees_paid": float(stats_row.total_fees or 0),
            "buy_trades": stats_row.buy_count or 0,
            "sell_trades": stats_row.sell_count or 0,
            "average_slippage": float(stats_row.avg_slippage or 0),
            "largest_trade_sol": float(stats_row.largest_trade or 0),
            "trades_per_day": (stats_row.total_trades or 0) / max(1, (now - start_time).days or 1)
        }
        
        # Кэширование на 5 минут
        await cache.set(cache_key, stats, "analytics", ttl=300)
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get trading stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trading statistics"
        )