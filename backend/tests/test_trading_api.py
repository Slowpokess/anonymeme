"""
💹 Integration тесты для Trading API
Comprehensive тестирование торговых операций и связанных endpoint'ов
"""

import pytest
import json
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from .conftest import DatabaseTestHelper, sample_trade_data, auth_headers


@pytest.mark.integration
@pytest.mark.requires_db
class TestTradingAPI:
    """Тесты API для торговых операций"""

    async def test_buy_tokens_success(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_trade_data: dict,
        auth_headers: dict,
        mock_solana_client
    ):
        """Тест успешной покупки токенов"""
        # Создаем тестового пользователя и токен
        user_data = {
            "wallet_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
            "username": "trader1",
            "email": "trader1@test.com",
            "reputation_score": 60.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "Test Trade Token",
            "symbol": "TTT",
            "description": "Token for trading tests",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Мокаем blockchain операции
        with patch("api.services.blockchain.SolanaService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.calculate_buy_amount = AsyncMock(
                return_value={
                    "token_amount": 950000,  # После slippage
                    "actual_sol_amount": 1000000000,
                    "price_impact": 2.5,
                    "new_price": 1025000,
                    "fees": 25000000  # 0.025 SOL fee
                }
            )
            mock_instance.execute_buy_trade = AsyncMock(
                return_value={
                    "transaction_signature": "buy_tx_signature_123",
                    "success": True
                }
            )

            # Отправляем запрос на покупку
            buy_data = {
                "token_mint": mint_address,
                "sol_amount": 1000000000,  # 1 SOL
                "min_tokens_out": 900000,  # Минимум токенов к получению
                "slippage_tolerance": 500  # 5%
            }

            response = await async_client.post(
                "/api/v1/trading/buy",
                json=buy_data,
                headers=auth_headers
            )

        # Проверяем успешный ответ
        assert response.status_code == 200
        response_data = response.json()
        
        assert "transaction_signature" in response_data
        assert "token_amount" in response_data
        assert "actual_sol_amount" in response_data
        assert "price_impact" in response_data
        assert response_data["success"] is True
        assert response_data["token_amount"] == 950000

        # Проверяем, что сделка сохранена в БД
        trade_in_db = await db_helper.conn.fetchrow(
            "SELECT * FROM trades WHERE transaction_signature = $1",
            response_data["transaction_signature"]
        )
        assert trade_in_db is not None
        assert trade_in_db["trade_type"] == "buy"
        assert trade_in_db["token_mint"] == mint_address

    async def test_buy_tokens_insufficient_balance(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        auth_headers: dict,
        mock_solana_client
    ):
        """Тест покупки токенов при недостаточном балансе"""
        # Создаем токен
        user_data = {
            "wallet_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
            "username": "poortrader",
            "email": "poor@test.com",
            "reputation_score": 50.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "Expensive Token",
            "symbol": "EXP",
            "description": "Very expensive token",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Мокаем low balance
        with patch("api.services.blockchain.SolanaService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.get_wallet_balance = AsyncMock(return_value=100000000)  # 0.1 SOL
            mock_instance.calculate_buy_amount = AsyncMock(
                side_effect=Exception("Insufficient balance")
            )

            buy_data = {
                "token_mint": mint_address,
                "sol_amount": 10000000000,  # 10 SOL (больше чем на балансе)
                "min_tokens_out": 900000,
                "slippage_tolerance": 500
            }

            response = await async_client.post(
                "/api/v1/trading/buy",
                json=buy_data,
                headers=auth_headers
            )

        assert response.status_code == 400
        response_data = response.json()
        assert "insufficient" in response_data["detail"].lower()

    async def test_buy_tokens_slippage_exceeded(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        auth_headers: dict,
        mock_solana_client
    ):
        """Тест покупки с превышением slippage tolerance"""
        # Создаем токен
        user_data = {
            "wallet_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
            "username": "slippagetrader",
            "email": "slippage@test.com",
            "reputation_score": 55.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "Volatile Token",
            "symbol": "VOL",
            "description": "Highly volatile token",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Мокаем high slippage
        with patch("api.services.blockchain.SolanaService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.calculate_buy_amount = AsyncMock(
                return_value={
                    "token_amount": 800000,  # Намного меньше ожидаемого
                    "actual_sol_amount": 1000000000,
                    "price_impact": 15.0,  # Высокий price impact
                    "new_price": 1150000,
                    "fees": 25000000
                }
            )

            buy_data = {
                "token_mint": mint_address,
                "sol_amount": 1000000000,
                "min_tokens_out": 950000,  # Больше чем мы получим
                "slippage_tolerance": 200  # 2% (меньше фактического impact)
            }

            response = await async_client.post(
                "/api/v1/trading/buy",
                json=buy_data,
                headers=auth_headers
            )

        assert response.status_code == 400
        response_data = response.json()
        assert "slippage" in response_data["detail"].lower()

    async def test_sell_tokens_success(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        auth_headers: dict,
        mock_solana_client
    ):
        """Тест успешной продажи токенов"""
        # Создаем пользователя и токен
        user_data = {
            "wallet_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
            "username": "seller1",
            "email": "seller1@test.com",
            "reputation_score": 65.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "Sellable Token",
            "symbol": "SELL",
            "description": "Token for selling tests",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Сначала создаем покупку (чтобы у пользователя были токены)
        buy_trade_data = {
            "token_mint": mint_address,
            "trader_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
            "trade_type": "buy",
            "sol_amount": 2000000000,  # 2 SOL
            "token_amount": 2000000    # 2M токенов
        }
        await db_helper.create_test_trade(buy_trade_data)

        # Мокаем blockchain операции для продажи
        with patch("api.services.blockchain.SolanaService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.get_token_balance = AsyncMock(return_value=2000000)
            mock_instance.calculate_sell_amount = AsyncMock(
                return_value={
                    "sol_amount": 950000000,  # 0.95 SOL после fees и slippage
                    "actual_token_amount": 1000000,
                    "price_impact": 3.0,
                    "new_price": 970000,
                    "fees": 50000000  # 0.05 SOL fee
                }
            )
            mock_instance.execute_sell_trade = AsyncMock(
                return_value={
                    "transaction_signature": "sell_tx_signature_123",
                    "success": True
                }
            )

            # Отправляем запрос на продажу
            sell_data = {
                "token_mint": mint_address,
                "token_amount": 1000000,  # 1M токенов
                "min_sol_out": 900000000,  # Минимум 0.9 SOL
                "slippage_tolerance": 500  # 5%
            }

            response = await async_client.post(
                "/api/v1/trading/sell",
                json=sell_data,
                headers=auth_headers
            )

        # Проверяем успешный ответ
        assert response.status_code == 200
        response_data = response.json()
        
        assert "transaction_signature" in response_data
        assert "sol_amount" in response_data
        assert "actual_token_amount" in response_data
        assert "price_impact" in response_data
        assert response_data["success"] is True
        assert response_data["sol_amount"] == 950000000

    async def test_sell_tokens_insufficient_tokens(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        auth_headers: dict,
        mock_solana_client
    ):
        """Тест продажи при недостаточном количестве токенов"""
        # Создаем токен без покупки токенов пользователем
        user_data = {
            "wallet_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
            "username": "notoken_trader",
            "email": "notoken@test.com",
            "reputation_score": 50.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "No Balance Token",
            "symbol": "NBT",
            "description": "Token user doesn't own",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Мокаем zero token balance
        with patch("api.services.blockchain.SolanaService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.get_token_balance = AsyncMock(return_value=0)

            sell_data = {
                "token_mint": mint_address,
                "token_amount": 1000000,  # Пытаемся продать токены которых нет
                "min_sol_out": 900000000,
                "slippage_tolerance": 500
            }

            response = await async_client.post(
                "/api/v1/trading/sell",
                json=sell_data,
                headers=auth_headers
            )

        assert response.status_code == 400
        response_data = response.json()
        assert "insufficient" in response_data["detail"].lower()

    async def test_get_trade_estimate_buy(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        mock_solana_client
    ):
        """Тест получения оценки для покупки"""
        # Создаем токен
        user_data = {
            "wallet_address": "EstimateUser123456789",
            "username": "estimateuser",
            "email": "estimate@test.com",
            "reputation_score": 60.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "Estimate Token",
            "symbol": "EST",
            "description": "Token for estimate tests",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Мокаем calculation
        with patch("api.services.blockchain.calculate_trade_estimate") as mock_calc:
            mock_calc.return_value = {
                "token_amount": 990000,
                "price_impact": 1.5,
                "estimated_price": 1015000,
                "fees": 15000000,
                "minimum_received": 940500  # С учетом slippage
            }

            response = await async_client.get(
                f"/api/v1/trading/estimate/buy?token_mint={mint_address}&sol_amount=1000000000&slippage_tolerance=500"
            )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "token_amount" in response_data
        assert "price_impact" in response_data
        assert "estimated_price" in response_data
        assert "fees" in response_data
        assert "minimum_received" in response_data
        assert response_data["token_amount"] == 990000

    async def test_get_trade_estimate_sell(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        mock_solana_client
    ):
        """Тест получения оценки для продажи"""
        # Создаем токен
        user_data = {
            "wallet_address": "SellEstimateUser123456789",
            "username": "sellestimateuser",
            "email": "sellestimate@test.com",
            "reputation_score": 60.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "Sell Estimate Token",
            "symbol": "SET",
            "description": "Token for sell estimate tests",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Мокаем calculation
        with patch("api.services.blockchain.calculate_trade_estimate") as mock_calc:
            mock_calc.return_value = {
                "sol_amount": 980000000,
                "price_impact": 2.0,
                "estimated_price": 980000,
                "fees": 20000000,
                "minimum_received": 931000000  # С учетом slippage
            }

            response = await async_client.get(
                f"/api/v1/trading/estimate/sell?token_mint={mint_address}&token_amount=1000000&slippage_tolerance=500"
            )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "sol_amount" in response_data
        assert "price_impact" in response_data
        assert "estimated_price" in response_data
        assert "fees" in response_data
        assert "minimum_received" in response_data
        assert response_data["sol_amount"] == 980000000

    async def test_get_user_trades_history(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        auth_headers: dict
    ):
        """Тест получения истории сделок пользователя"""
        # Создаем пользователя и токен
        user_data = {
            "wallet_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
            "username": "historyuser",
            "email": "history@test.com",
            "reputation_score": 70.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "History Token",
            "symbol": "HIST",
            "description": "Token for history tests",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Создаем несколько сделок
        trades_data = [
            {
                "token_mint": mint_address,
                "trader_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
                "trade_type": "buy",
                "sol_amount": 1000000000,
                "token_amount": 1000000
            },
            {
                "token_mint": mint_address,
                "trader_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
                "trade_type": "sell",
                "sol_amount": 500000000,
                "token_amount": 500000
            },
            {
                "token_mint": mint_address,
                "trader_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
                "trade_type": "buy",
                "sol_amount": 2000000000,
                "token_amount": 1800000
            }
        ]

        for trade_data in trades_data:
            await db_helper.create_test_trade(trade_data)

        response = await async_client.get(
            "/api/v1/trading/history",
            headers=auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "trades" in response_data
        assert "pagination" in response_data
        assert len(response_data["trades"]) == 3
        
        # Проверяем, что сделки отсортированы по времени (новые первыми)
        timestamps = [trade["created_at"] for trade in response_data["trades"]]
        assert timestamps == sorted(timestamps, reverse=True)

    async def test_get_token_trades_history(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper
    ):
        """Тест получения истории сделок по токену"""
        # Создаем токен
        user_data = {
            "wallet_address": "TokenHistoryUser123456789",
            "username": "tokenhistoryuser",
            "email": "tokenhistory@test.com",
            "reputation_score": 60.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "Token History Test",
            "symbol": "THT",
            "description": "Token for testing trade history",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Создаем сделки от разных пользователей
        traders = ["Trader1", "Trader2", "Trader3"]
        for i, trader in enumerate(traders):
            trade_data = {
                "token_mint": mint_address,
                "trader_address": trader,
                "trade_type": "buy" if i % 2 == 0 else "sell",
                "sol_amount": (i + 1) * 500000000,
                "token_amount": (i + 1) * 500000
            }
            await db_helper.create_test_trade(trade_data)

        response = await async_client.get(f"/api/v1/trading/tokens/{mint_address}/history")

        assert response.status_code == 200
        response_data = response.json()
        
        assert "trades" in response_data
        assert "pagination" in response_data
        assert len(response_data["trades"]) == 3
        
        # Все сделки должны быть для этого токена
        for trade in response_data["trades"]:
            assert trade["token_mint"] == mint_address

    async def test_trading_cooldown_protection(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        auth_headers: dict,
        mock_solana_client
    ):
        """Тест защиты от частых сделок (cooldown)"""
        # Создаем пользователя и токен
        user_data = {
            "wallet_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
            "username": "cooldownuser",
            "email": "cooldown@test.com",
            "reputation_score": 60.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "Cooldown Token",
            "symbol": "COOL",
            "description": "Token for cooldown tests",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Создаем недавнюю сделку
        recent_trade_data = {
            "token_mint": mint_address,
            "trader_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
            "trade_type": "buy",
            "sol_amount": 1000000000,
            "token_amount": 1000000
        }
        await db_helper.create_test_trade(recent_trade_data)

        # Мокаем blockchain операции
        with patch("api.services.blockchain.SolanaService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.calculate_buy_amount = AsyncMock(
                return_value={
                    "token_amount": 950000,
                    "actual_sol_amount": 1000000000,
                    "price_impact": 2.5,
                    "new_price": 1025000,
                    "fees": 25000000
                }
            )

            # Пытаемся сделать еще одну сделку сразу
            buy_data = {
                "token_mint": mint_address,
                "sol_amount": 500000000,
                "min_tokens_out": 450000,
                "slippage_tolerance": 500
            }

            response = await async_client.post(
                "/api/v1/trading/buy",
                json=buy_data,
                headers=auth_headers
            )

        assert response.status_code == 429  # Too Many Requests
        response_data = response.json()
        assert "cooldown" in response_data["detail"].lower()

    async def test_whale_protection_trigger(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        auth_headers: dict,
        mock_solana_client
    ):
        """Тест срабатывания защиты от китов"""
        # Создаем токен
        user_data = {
            "wallet_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
            "username": "whaleuser",
            "email": "whale@test.com",
            "reputation_score": 60.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "Whale Protected Token",
            "symbol": "WPT",
            "description": "Token with whale protection",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Мокаем большую покупку (превышающую лимиты)
        with patch("api.services.blockchain.SolanaService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.check_whale_limits = AsyncMock(
                side_effect=Exception("Whale protection triggered: purchase would exceed 5% of total supply")
            )

            # Пытаемся купить слишком много токенов
            whale_buy_data = {
                "token_mint": mint_address,
                "sol_amount": 100000000000,  # 100 SOL - очень большая покупка
                "min_tokens_out": 50000000000000,  # Огромное количество токенов
                "slippage_tolerance": 1000
            }

            response = await async_client.post(
                "/api/v1/trading/buy",
                json=whale_buy_data,
                headers=auth_headers
            )

        assert response.status_code == 400
        response_data = response.json()
        assert "whale protection" in response_data["detail"].lower()

    async def test_get_trading_statistics(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        auth_headers: dict
    ):
        """Тест получения торговой статистики пользователя"""
        # Создаем пользователя и токен
        user_data = {
            "wallet_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
            "username": "statsuser",
            "email": "stats@test.com",
            "reputation_score": 70.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "Stats Token",
            "symbol": "STAT",
            "description": "Token for stats tests",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Создаем микс прибыльных и убыточных сделок
        profitable_trades = [
            {"sol_amount": 1000000000, "token_amount": 1000000, "type": "buy"},
            {"sol_amount": 1200000000, "token_amount": 1000000, "type": "sell"},  # Прибыль 0.2 SOL
        ]
        
        losing_trades = [
            {"sol_amount": 2000000000, "token_amount": 2000000, "type": "buy"},
            {"sol_amount": 1500000000, "token_amount": 2000000, "type": "sell"},  # Убыток 0.5 SOL
        ]

        all_trades = profitable_trades + losing_trades
        for trade in all_trades:
            trade_data = {
                "token_mint": mint_address,
                "trader_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
                "trade_type": trade["type"],
                "sol_amount": trade["sol_amount"],
                "token_amount": trade["token_amount"]
            }
            await db_helper.create_test_trade(trade_data)

        response = await async_client.get(
            "/api/v1/trading/statistics",
            headers=auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "total_trades" in response_data
        assert "total_volume_sol" in response_data
        assert "profitable_trades" in response_data
        assert "total_pnl_sol" in response_data
        assert "win_rate" in response_data
        assert "average_trade_size" in response_data
        
        assert response_data["total_trades"] == 4
        assert response_data["profitable_trades"] == 1  # Только одна пара buy-sell была прибыльной
        assert response_data["win_rate"] == 25.0  # 1/4 = 25%

    @pytest.mark.slow
    async def test_concurrent_trading_stress(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        mock_solana_client
    ):
        """Стресс-тест конкурентных торговых операций"""
        import asyncio
        
        # Создаем токен
        user_data = {
            "wallet_address": "StressTestUser123456789",
            "username": "stressuser",
            "email": "stress@test.com",
            "reputation_score": 80.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "Stress Test Token",
            "symbol": "STRESS",
            "description": "Token for stress testing",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Мокаем blockchain операции
        with patch("api.services.blockchain.SolanaService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.calculate_buy_amount = AsyncMock(
                return_value={
                    "token_amount": 100000,
                    "actual_sol_amount": 100000000,
                    "price_impact": 1.0,
                    "new_price": 1010000,
                    "fees": 2000000
                }
            )
            mock_instance.execute_buy_trade = AsyncMock(
                return_value={
                    "transaction_signature": "stress_tx_123",
                    "success": True
                }
            )

            # Создаем множественные конкурентные запросы
            async def make_trade_request(trader_id: int):
                auth_headers_trader = {
                    "Authorization": f"Bearer trader_{trader_id}_token",
                    "Content-Type": "application/json"
                }
                
                buy_data = {
                    "token_mint": mint_address,
                    "sol_amount": 100000000,  # 0.1 SOL
                    "min_tokens_out": 95000,
                    "slippage_tolerance": 500
                }

                return await async_client.post(
                    "/api/v1/trading/buy",
                    json=buy_data,
                    headers=auth_headers_trader
                )

            # Запускаем 10 конкурентных запросов
            tasks = [make_trade_request(i) for i in range(10)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Проверяем, что большинство запросов обработалось успешно
            successful_responses = [
                r for r in responses 
                if not isinstance(r, Exception) and r.status_code == 200
            ]
            
            # Ожидаем что хотя бы половина запросов прошла успешно
            assert len(successful_responses) >= 5
            
            # Проверяем, что нет критических ошибок (500)
            error_responses = [
                r for r in responses 
                if not isinstance(r, Exception) and r.status_code >= 500
            ]
            assert len(error_responses) == 0