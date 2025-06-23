"""
📊 Integration тесты для Analytics API
Comprehensive тестирование аналитических endpoint'ов и метрик
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from .conftest import DatabaseTestHelper, sample_token_data, sample_user_data, auth_headers


@pytest.mark.integration
@pytest.mark.requires_db
class TestAnalyticsAPI:
    """Тесты API для аналитики и метрик"""

    async def test_get_platform_overview(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper
    ):
        """Тест получения общей статистики платформы"""
        # Создаем тестовые данные
        user_data = {
            "wallet_address": "AnalyticsUser123456789",
            "username": "analyticsuser",
            "email": "analytics@test.com",
            "reputation_score": 70.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        # Создаем несколько токенов
        for i in range(3):
            token_data = {
                "name": f"Analytics Token {i}",
                "symbol": f"AT{i}",
                "description": f"Token for analytics test {i}",
                "initial_supply": 1000000000000000000,
                "initial_price": 1000000
            }
            mint_address = await db_helper.create_test_token(token_data, user_id)
            
            # Создаем торговую активность
            for j in range(5):
                trade_data = {
                    "token_mint": mint_address,
                    "trader_address": f"Trader{j}",
                    "trade_type": "buy" if j % 2 == 0 else "sell",
                    "sol_amount": (j + 1) * 100000000,  # 0.1-0.5 SOL
                    "token_amount": (j + 1) * 100000
                }
                await db_helper.create_test_trade(trade_data)

        response = await async_client.get("/api/v1/analytics/overview")

        assert response.status_code == 200
        response_data = response.json()
        
        assert "total_tokens" in response_data
        assert "total_users" in response_data
        assert "total_trades" in response_data
        assert "total_volume_sol" in response_data
        assert "total_volume_usd" in response_data
        assert "active_users_24h" in response_data
        assert "new_tokens_24h" in response_data
        assert "platform_fees_collected" in response_data
        
        assert response_data["total_tokens"] >= 3
        assert response_data["total_users"] >= 1
        assert response_data["total_trades"] >= 15

    async def test_get_trading_metrics(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper
    ):
        """Тест получения торговых метрик"""
        # Создаем пользователя и токен
        user_data = {
            "wallet_address": "TradingMetricsUser123456789",
            "username": "tradinguser",
            "email": "trading@test.com",
            "reputation_score": 65.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "Trading Metrics Token",
            "symbol": "TMT",
            "description": "Token for trading metrics",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Создаем различные типы сделок
        trades_data = [
            {"sol_amount": 1000000000, "token_amount": 1000000, "type": "buy"},   # 1 SOL
            {"sol_amount": 2000000000, "token_amount": 1800000, "type": "buy"},  # 2 SOL
            {"sol_amount": 1500000000, "token_amount": 1000000, "type": "sell"}, # 1.5 SOL (прибыль)
            {"sol_amount": 3000000000, "token_amount": 2500000, "type": "buy"},  # 3 SOL
            {"sol_amount": 2800000000, "token_amount": 2500000, "type": "sell"}, # 2.8 SOL (убыток)
        ]

        for trade in trades_data:
            trade_data = {
                "token_mint": mint_address,
                "trader_address": "MetricsTrader123456789",
                "trade_type": trade["type"],
                "sol_amount": trade["sol_amount"],
                "token_amount": trade["token_amount"]
            }
            await db_helper.create_test_trade(trade_data)

        # Запрашиваем метрики за последние 24 часа
        response = await async_client.get("/api/v1/analytics/trading/metrics?period=24h")

        assert response.status_code == 200
        response_data = response.json()
        
        assert "total_volume_sol" in response_data
        assert "total_trades" in response_data
        assert "buy_volume" in response_data
        assert "sell_volume" in response_data
        assert "average_trade_size" in response_data
        assert "largest_trade" in response_data
        assert "unique_traders" in response_data
        assert "price_impact_avg" in response_data
        
        assert response_data["total_trades"] == 5
        assert response_data["buy_volume"] + response_data["sell_volume"] == response_data["total_volume_sol"]

    async def test_get_volume_chart_data(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper
    ):
        """Тест получения данных для графика объемов"""
        # Создаем данные для разных периодов
        user_data = {
            "wallet_address": "VolumeChartUser123456789",
            "username": "volumeuser",
            "email": "volume@test.com",
            "reputation_score": 60.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "Volume Chart Token",
            "symbol": "VCT",
            "description": "Token for volume chart",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Создаем сделки
        for i in range(10):
            trade_data = {
                "token_mint": mint_address,
                "trader_address": f"VolumeTrader{i}",
                "trade_type": "buy" if i % 2 == 0 else "sell",
                "sol_amount": (i + 1) * 500000000,  # 0.5-5 SOL
                "token_amount": (i + 1) * 500000
            }
            await db_helper.create_test_trade(trade_data)

        # Запрашиваем данные для графика
        response = await async_client.get("/api/v1/analytics/volume/chart?period=7d&interval=1d")

        assert response.status_code == 200
        response_data = response.json()
        
        assert "data" in response_data
        assert "metadata" in response_data
        assert isinstance(response_data["data"], list)
        
        # Проверяем структуру данных
        if response_data["data"]:
            data_point = response_data["data"][0]
            assert "timestamp" in data_point
            assert "volume_sol" in data_point
            assert "volume_usd" in data_point
            assert "trades_count" in data_point

    async def test_get_token_analytics(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict
    ):
        """Тест получения аналитики по конкретному токену"""
        # Создаем токен с активностью
        user_data = {
            "wallet_address": "TokenAnalyticsUser123456789",
            "username": "tokenuser",
            "email": "token@test.com",
            "reputation_score": 75.0
        }
        user_id = await db_helper.create_test_user(user_data)
        mint_address = await db_helper.create_test_token(sample_token_data, user_id)

        # Создаем активность
        traders = ["Trader1", "Trader2", "Trader3", "Trader4", "Trader5"]
        for i, trader in enumerate(traders):
            # Каждый трейдер делает покупку и продажу
            buy_trade = {
                "token_mint": mint_address,
                "trader_address": trader,
                "trade_type": "buy",
                "sol_amount": (i + 1) * 1000000000,  # 1-5 SOL
                "token_amount": (i + 1) * 1000000
            }
            await db_helper.create_test_trade(buy_trade)
            
            sell_trade = {
                "token_mint": mint_address,
                "trader_address": trader,
                "trade_type": "sell",
                "sol_amount": (i + 1) * 900000000,  # 0.9-4.5 SOL (убыток)
                "token_amount": (i + 1) * 1000000
            }
            await db_helper.create_test_trade(sell_trade)

        response = await async_client.get(f"/api/v1/analytics/tokens/{mint_address}")

        assert response.status_code == 200
        response_data = response.json()
        
        assert "token_info" in response_data
        assert "trading_metrics" in response_data
        assert "holder_metrics" in response_data
        assert "price_history" in response_data
        
        # Проверяем торговые метрики
        trading_metrics = response_data["trading_metrics"]
        assert "total_volume_sol" in trading_metrics
        assert "total_trades" in trading_metrics
        assert "unique_traders" in trading_metrics
        assert "buy_sell_ratio" in trading_metrics
        assert "average_trade_size" in trading_metrics
        
        # Проверяем метрики держателей
        holder_metrics = response_data["holder_metrics"]
        assert "total_holders" in holder_metrics
        assert "concentration_percentage" in holder_metrics
        assert "top_holders" in holder_metrics

    async def test_get_price_history(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict
    ):
        """Тест получения истории цен токена"""
        user_data = {
            "wallet_address": "PriceHistoryUser123456789",
            "username": "priceuser",
            "email": "price@test.com",
            "reputation_score": 65.0
        }
        user_id = await db_helper.create_test_user(user_data)
        mint_address = await db_helper.create_test_token(sample_token_data, user_id)

        # Мокаем расчет исторических цен
        with patch("api.services.analytics.calculate_historical_prices") as mock_prices:
            mock_prices.return_value = [
                {"timestamp": "2024-01-01T00:00:00Z", "price": 1000000, "volume": 5000000000},
                {"timestamp": "2024-01-01T01:00:00Z", "price": 1050000, "volume": 3000000000},
                {"timestamp": "2024-01-01T02:00:00Z", "price": 1100000, "volume": 4000000000},
            ]

            response = await async_client.get(
                f"/api/v1/analytics/tokens/{mint_address}/price-history?period=24h&interval=1h"
            )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "data" in response_data
        assert "metadata" in response_data
        assert len(response_data["data"]) == 3
        
        # Проверяем структуру данных
        price_point = response_data["data"][0]
        assert "timestamp" in price_point
        assert "price" in price_point
        assert "volume" in price_point

    async def test_get_top_performers(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper
    ):
        """Тест получения топ токенов по различным метрикам"""
        # Создаем несколько токенов с разной производительностью
        user_data = {
            "wallet_address": "TopPerformersUser123456789",
            "username": "topuser",
            "email": "top@test.com",
            "reputation_score": 80.0
        }
        user_id = await db_helper.create_test_user(user_data)

        # Создаем токены с разным объемом торгов
        tokens_data = [
            {"name": "High Volume Token", "symbol": "HVT", "volume_multiplier": 10},
            {"name": "Medium Volume Token", "symbol": "MVT", "volume_multiplier": 5},
            {"name": "Low Volume Token", "symbol": "LVT", "volume_multiplier": 1},
        ]

        for token_info in tokens_data:
            token_data = {
                "name": token_info["name"],
                "symbol": token_info["symbol"],
                "description": f"Token with {token_info['volume_multiplier']}x volume",
                "initial_supply": 1000000000000000000,
                "initial_price": 1000000
            }
            mint_address = await db_helper.create_test_token(token_data, user_id)
            
            # Создаем торговую активность пропорциональную multiplier
            for i in range(token_info["volume_multiplier"]):
                trade_data = {
                    "token_mint": mint_address,
                    "trader_address": f"TopTrader{i}",
                    "trade_type": "buy" if i % 2 == 0 else "sell",
                    "sol_amount": 1000000000,  # 1 SOL
                    "token_amount": 1000000
                }
                await db_helper.create_test_trade(trade_data)

        # Запрашиваем топ по объему
        response = await async_client.get("/api/v1/analytics/top-performers?metric=volume&limit=5")

        assert response.status_code == 200
        response_data = response.json()
        
        assert "tokens" in response_data
        assert "metadata" in response_data
        assert len(response_data["tokens"]) >= 3
        
        # Проверяем, что токены отсортированы по объему
        volumes = [token["volume_24h"] for token in response_data["tokens"]]
        assert volumes == sorted(volumes, reverse=True)

    async def test_get_user_analytics(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict,
        auth_headers: dict
    ):
        """Тест получения аналитики пользователя"""
        # Создаем пользователя с торговой активностью
        user_id = await db_helper.create_test_user(sample_user_data)
        
        token_data = {
            "name": "User Analytics Token",
            "symbol": "UAT",
            "description": "Token for user analytics",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Создаем торговую историю
        trades_data = [
            {"sol_amount": 2000000000, "token_amount": 2000000, "type": "buy"},   # 2 SOL
            {"sol_amount": 1000000000, "token_amount": 1000000, "type": "sell"},  # 1 SOL
            {"sol_amount": 3000000000, "token_amount": 2800000, "type": "buy"},   # 3 SOL
            {"sol_amount": 4000000000, "token_amount": 2800000, "type": "sell"},  # 4 SOL (прибыль)
        ]

        for trade in trades_data:
            trade_data = {
                "token_mint": mint_address,
                "trader_address": sample_user_data["wallet_address"],
                "trade_type": trade["type"],
                "sol_amount": trade["sol_amount"],
                "token_amount": trade["token_amount"]
            }
            await db_helper.create_test_trade(trade_data)

        response = await async_client.get(
            f"/api/v1/analytics/users/{sample_user_data['wallet_address']}",
            headers=auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "trading_performance" in response_data
        assert "portfolio_metrics" in response_data
        assert "reputation_history" in response_data
        assert "created_tokens_performance" in response_data
        
        # Проверяем торговую производительность
        trading_perf = response_data["trading_performance"]
        assert "total_pnl_sol" in trading_perf
        assert "win_rate" in trading_perf
        assert "total_trades" in trading_perf
        assert "average_trade_size" in trading_perf
        assert "best_trade" in trading_perf
        assert "worst_trade" in trading_perf

    async def test_get_market_trends(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper
    ):
        """Тест получения рыночных трендов"""
        # Создаем данные для анализа трендов
        user_data = {
            "wallet_address": "TrendsUser123456789",
            "username": "trendsuser",
            "email": "trends@test.com",
            "reputation_score": 70.0
        }
        user_id = await db_helper.create_test_user(user_data)

        # Создаем токены с разными трендами
        trend_tokens = [
            {"name": "Uptrend Token", "symbol": "UP", "trend": "up"},
            {"name": "Downtrend Token", "symbol": "DOWN", "trend": "down"},
            {"name": "Sideways Token", "symbol": "SIDE", "trend": "sideways"},
        ]

        for token_info in trend_tokens:
            token_data = {
                "name": token_info["name"],
                "symbol": token_info["symbol"],
                "description": f"Token with {token_info['trend']} trend",
                "initial_supply": 1000000000000000000,
                "initial_price": 1000000
            }
            mint_address = await db_helper.create_test_token(token_data, user_id)

        response = await async_client.get("/api/v1/analytics/market/trends?period=24h")

        assert response.status_code == 200
        response_data = response.json()
        
        assert "trending_up" in response_data
        assert "trending_down" in response_data
        assert "highest_volume" in response_data
        assert "most_active" in response_data
        assert "new_listings" in response_data
        assert "market_sentiment" in response_data
        
        # Проверяем структуру трендов
        if response_data["trending_up"]:
            trending_token = response_data["trending_up"][0]
            assert "token" in trending_token
            assert "price_change_24h" in trending_token
            assert "volume_change_24h" in trending_token

    async def test_get_platform_health_metrics(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict
    ):
        """Тест получения метрик здоровья платформы (только для админов)"""
        response = await async_client.get(
            "/api/v1/analytics/platform/health",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "system_status" in response_data
        assert "database_health" in response_data
        assert "blockchain_sync_status" in response_data
        assert "api_response_times" in response_data
        assert "error_rates" in response_data
        assert "active_connections" in response_data
        assert "memory_usage" in response_data
        assert "cpu_usage" in response_data

    async def test_get_platform_health_unauthorized(
        self,
        async_client: AsyncClient,
        auth_headers: dict  # Обычные заголовки
    ):
        """Тест доступа к метрикам здоровья обычным пользователем"""
        response = await async_client.get(
            "/api/v1/analytics/platform/health",
            headers=auth_headers
        )

        assert response.status_code == 403
        response_data = response.json()
        assert "admin" in response_data["detail"].lower()

    async def test_get_revenue_analytics(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        admin_auth_headers: dict
    ):
        """Тест получения аналитики доходов платформы"""
        # Создаем торговые данные для расчета комиссий
        user_data = {
            "wallet_address": "RevenueUser123456789",
            "username": "revenueuser",
            "email": "revenue@test.com",
            "reputation_score": 60.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "Revenue Token",
            "symbol": "REV",
            "description": "Token for revenue analytics",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Создаем сделки для генерации комиссий
        for i in range(10):
            trade_data = {
                "token_mint": mint_address,
                "trader_address": f"RevenueTrader{i}",
                "trade_type": "buy" if i % 2 == 0 else "sell",
                "sol_amount": (i + 1) * 1000000000,  # 1-10 SOL
                "token_amount": (i + 1) * 1000000
            }
            await db_helper.create_test_trade(trade_data)

        response = await async_client.get(
            "/api/v1/analytics/revenue?period=30d",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "total_fees_collected" in response_data
        assert "trading_fees" in response_data
        assert "creation_fees" in response_data
        assert "graduation_fees" in response_data
        assert "daily_breakdown" in response_data
        assert "top_revenue_tokens" in response_data
        assert "fee_statistics" in response_data

    @pytest.mark.slow
    async def test_comprehensive_analytics_export(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        admin_auth_headers: dict
    ):
        """Тест экспорта comprehensive аналитических данных"""
        # Создаем комплексные тестовые данные
        user_data = {
            "wallet_address": "ExportUser123456789",
            "username": "exportuser",
            "email": "export@test.com",
            "reputation_score": 85.0
        }
        user_id = await db_helper.create_test_user(user_data)

        # Создаем токены и торговую активность
        for i in range(5):
            token_data = {
                "name": f"Export Token {i}",
                "symbol": f"EXP{i}",
                "description": f"Export test token {i}",
                "initial_supply": 1000000000000000000,
                "initial_price": 1000000
            }
            mint_address = await db_helper.create_test_token(token_data, user_id)
            
            # Создаем торговую активность
            for j in range(10):
                trade_data = {
                    "token_mint": mint_address,
                    "trader_address": f"ExportTrader{j}",
                    "trade_type": "buy" if j % 2 == 0 else "sell",
                    "sol_amount": (j + 1) * 500000000,
                    "token_amount": (j + 1) * 500000
                }
                await db_helper.create_test_trade(trade_data)

        # Запрашиваем экспорт данных
        export_params = {
            "format": "json",
            "period": "7d",
            "include_users": True,
            "include_tokens": True,
            "include_trades": True,
            "include_analytics": True
        }

        response = await async_client.post(
            "/api/v1/analytics/export",
            json=export_params,
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "export_id" in response_data
        assert "status" in response_data
        assert "estimated_completion" in response_data
        assert response_data["status"] in ["processing", "completed"]

        # Если экспорт завершен, проверяем структуру данных
        if response_data["status"] == "completed":
            assert "download_url" in response_data
            assert "file_size" in response_data
            assert "records_count" in response_data

    async def test_analytics_caching_behavior(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper
    ):
        """Тест кэширования аналитических данных"""
        # Создаем базовые данные
        user_data = {
            "wallet_address": "CacheTestUser123456789",
            "username": "cacheuser",
            "email": "cache@test.com",
            "reputation_score": 60.0
        }
        user_id = await db_helper.create_test_user(user_data)

        # Первый запрос (должен быть медленнее)
        response1 = await async_client.get("/api/v1/analytics/overview")
        assert response1.status_code == 200
        
        # Второй запрос (должен использовать кэш)
        response2 = await async_client.get("/api/v1/analytics/overview")
        assert response2.status_code == 200
        
        # Данные должны быть идентичными
        assert response1.json() == response2.json()
        
        # Проверяем наличие заголовков кэширования
        assert "Cache-Control" in response2.headers or "X-Cache-Status" in response2.headers