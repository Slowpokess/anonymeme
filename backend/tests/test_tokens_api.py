"""
🪙 Integration тесты для Tokens API
Comprehensive тестирование всех endpoint'ов для работы с токенами
"""

import pytest
import json
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from fastapi.testclient import TestClient

from .conftest import DatabaseTestHelper, sample_token_data, auth_headers


@pytest.mark.integration
@pytest.mark.requires_db
class TestTokensAPI:
    """Тесты API для управления токенами"""

    async def test_create_token_success(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict,
        auth_headers: dict,
        mock_solana_client
    ):
        """Тест успешного создания токена"""
        # Создаем тестового пользователя
        user_data = {
            "wallet_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
            "username": "testcreator",
            "email": "creator@test.com",
            "reputation_score": 75.0
        }
        user_id = await db_helper.create_test_user(user_data)

        # Мокаем blockchain операции
        with patch("api.services.blockchain.SolanaService") as mock_service:
            mock_service.return_value.create_token_mint = AsyncMock(
                return_value={
                    "mint_address": "test_mint_address_123",
                    "transaction_signature": "test_tx_signature_123"
                }
            )

            # Отправляем запрос на создание токена
            response = await async_client.post(
                "/api/v1/tokens/create",
                json=sample_token_data,
                headers=auth_headers
            )

        # Проверяем успешный ответ
        assert response.status_code == 201
        response_data = response.json()
        
        assert "mint_address" in response_data
        assert response_data["name"] == sample_token_data["name"]
        assert response_data["symbol"] == sample_token_data["symbol"]
        assert response_data["creator"]["id"] == user_id
        assert "bonding_curve" in response_data
        assert response_data["status"] == "active"

        # Проверяем, что токен сохранен в БД
        token_in_db = await db_helper.conn.fetchrow(
            "SELECT * FROM tokens WHERE mint_address = $1",
            response_data["mint_address"]
        )
        assert token_in_db is not None
        assert token_in_db["name"] == sample_token_data["name"]

    async def test_create_token_validation_error(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Тест создания токена с невалидными данными"""
        invalid_data = {
            "name": "",  # Пустое имя
            "symbol": "TOOLONGNAME",  # Слишком длинный символ
            "initial_supply": -1,  # Негативный supply
        }

        response = await async_client.post(
            "/api/v1/tokens/create",
            json=invalid_data,
            headers=auth_headers
        )

        assert response.status_code == 422
        response_data = response.json()
        assert "detail" in response_data
        assert len(response_data["detail"]) > 0  # Должны быть ошибки валидации

    async def test_create_token_insufficient_reputation(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict,
        auth_headers: dict
    ):
        """Тест создания токена пользователем с низкой репутацией"""
        # Создаем пользователя с низкой репутацией
        low_rep_user_data = {
            "wallet_address": "LowRepUser123456789",
            "username": "lowrepuser",
            "email": "lowrep@test.com",
            "reputation_score": 10.0  # Очень низкая репутация
        }
        await db_helper.create_test_user(low_rep_user_data)

        response = await async_client.post(
            "/api/v1/tokens/create",
            json=sample_token_data,
            headers=auth_headers
        )

        assert response.status_code == 403
        response_data = response.json()
        assert "insufficient reputation" in response_data["detail"].lower()

    async def test_get_token_by_mint(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict
    ):
        """Тест получения токена по mint адресу"""
        # Создаем тестового пользователя и токен
        user_data = {
            "wallet_address": "TokenOwner123456789",
            "username": "tokenowner",
            "email": "owner@test.com",
            "reputation_score": 60.0
        }
        user_id = await db_helper.create_test_user(user_data)
        mint_address = await db_helper.create_test_token(sample_token_data, user_id)

        # Запрашиваем токен
        response = await async_client.get(f"/api/v1/tokens/{mint_address}")

        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["mint_address"] == mint_address
        assert response_data["name"] == sample_token_data["name"]
        assert response_data["symbol"] == sample_token_data["symbol"]
        assert "creator" in response_data
        assert "bonding_curve" in response_data
        assert "market_data" in response_data

    async def test_get_token_not_found(
        self,
        async_client: AsyncClient
    ):
        """Тест получения несуществующего токена"""
        response = await async_client.get("/api/v1/tokens/nonexistent_mint")

        assert response.status_code == 404
        response_data = response.json()
        assert "not found" in response_data["detail"].lower()

    async def test_list_tokens_with_pagination(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict
    ):
        """Тест получения списка токенов с пагинацией"""
        # Создаем несколько тестовых токенов
        user_data = {
            "wallet_address": "TokenCreator123456789",
            "username": "tokencreator",
            "email": "creator@test.com",
            "reputation_score": 80.0
        }
        user_id = await db_helper.create_test_user(user_data)

        # Создаем 5 токенов
        token_mints = []
        for i in range(5):
            token_data = sample_token_data.copy()
            token_data["name"] = f"Test Token {i}"
            token_data["symbol"] = f"TT{i}"
            mint_address = await db_helper.create_test_token(token_data, user_id)
            token_mints.append(mint_address)

        # Запрашиваем первую страницу (2 токена)
        response = await async_client.get("/api/v1/tokens?page=1&limit=2")

        assert response.status_code == 200
        response_data = response.json()
        
        assert "tokens" in response_data
        assert "pagination" in response_data
        assert len(response_data["tokens"]) == 2
        assert response_data["pagination"]["page"] == 1
        assert response_data["pagination"]["limit"] == 2
        assert response_data["pagination"]["total"] >= 5

    async def test_list_tokens_with_filters(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict
    ):
        """Тест получения токенов с фильтрами"""
        # Создаем токены с разными типами кривых
        user_data = {
            "wallet_address": "FilterTestUser123456789",
            "username": "filteruser",
            "email": "filter@test.com",
            "reputation_score": 70.0
        }
        user_id = await db_helper.create_test_user(user_data)

        # Создаем токены с разными параметрами
        linear_token = sample_token_data.copy()
        linear_token["bonding_curve_type"] = "linear"
        await db_helper.create_test_token(linear_token, user_id)

        exponential_token = sample_token_data.copy()
        exponential_token["bonding_curve_type"] = "exponential"
        exponential_token["name"] = "Exponential Token"
        await db_helper.create_test_token(exponential_token, user_id)

        # Фильтруем по типу кривой
        response = await async_client.get("/api/v1/tokens?curve_type=linear")

        assert response.status_code == 200
        response_data = response.json()
        
        assert "tokens" in response_data
        # Все возвращенные токены должны иметь linear кривую
        for token in response_data["tokens"]:
            assert token["bonding_curve"]["curve_type"] == "linear"

    async def test_get_token_price(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict
    ):
        """Тест получения текущей цены токена"""
        # Создаем токен
        user_data = {
            "wallet_address": "PriceTestUser123456789",
            "username": "priceuser",
            "email": "price@test.com",
            "reputation_score": 60.0
        }
        user_id = await db_helper.create_test_user(user_data)
        mint_address = await db_helper.create_test_token(sample_token_data, user_id)

        # Мокаем price calculation
        with patch("api.services.blockchain.calculate_token_price") as mock_price:
            mock_price.return_value = {
                "current_price": 1500000,  # 0.0015 SOL
                "price_change_24h": 15.5,
                "market_cap": 1500000000000000,
                "volume_24h": 5000000000
            }

            response = await async_client.get(f"/api/v1/tokens/{mint_address}/price")

        assert response.status_code == 200
        response_data = response.json()
        
        assert "current_price" in response_data
        assert "price_change_24h" in response_data
        assert "market_cap" in response_data
        assert "volume_24h" in response_data
        assert response_data["current_price"] == 1500000

    async def test_get_token_holders(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict
    ):
        """Тест получения списка держателей токена"""
        # Создаем токен
        user_data = {
            "wallet_address": "HolderTestUser123456789",
            "username": "holderuser",
            "email": "holder@test.com",
            "reputation_score": 60.0
        }
        user_id = await db_helper.create_test_user(user_data)
        mint_address = await db_helper.create_test_token(sample_token_data, user_id)

        # Создаем несколько держателей (через сделки)
        holders_data = [
            {"wallet": "Holder1", "amount": 1000000},
            {"wallet": "Holder2", "amount": 500000},
            {"wallet": "Holder3", "amount": 750000},
        ]

        for holder in holders_data:
            trade_data = {
                "token_mint": mint_address,
                "trader_address": holder["wallet"],
                "trade_type": "buy",
                "sol_amount": 1000000000,
                "token_amount": holder["amount"]
            }
            await db_helper.create_test_trade(trade_data)

        response = await async_client.get(f"/api/v1/tokens/{mint_address}/holders")

        assert response.status_code == 200
        response_data = response.json()
        
        assert "holders" in response_data
        assert "total_holders" in response_data
        assert len(response_data["holders"]) >= 3
        
        # Проверяем, что холдеры отсортированы по количеству токенов
        amounts = [holder["token_amount"] for holder in response_data["holders"]]
        assert amounts == sorted(amounts, reverse=True)

    async def test_update_token_metadata(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict,
        auth_headers: dict
    ):
        """Тест обновления метаданных токена (только создателем)"""
        # Создаем токен
        user_data = {
            "wallet_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
            "username": "updateuser",
            "email": "update@test.com",
            "reputation_score": 70.0
        }
        user_id = await db_helper.create_test_user(user_data)
        mint_address = await db_helper.create_test_token(sample_token_data, user_id)

        # Обновляем метаданные
        update_data = {
            "description": "Updated description for test token",
            "website_url": "https://updated.example.com",
            "telegram_url": "https://t.me/updated_channel"
        }

        response = await async_client.patch(
            f"/api/v1/tokens/{mint_address}/metadata",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["description"] == update_data["description"]
        assert response_data["website_url"] == update_data["website_url"]
        assert response_data["telegram_url"] == update_data["telegram_url"]

    async def test_update_token_metadata_unauthorized(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict,
        auth_headers: dict
    ):
        """Тест обновления метаданных токена не создателем"""
        # Создаем токен под одним пользователем
        creator_data = {
            "wallet_address": "TokenCreator123456789",
            "username": "creator",
            "email": "creator@test.com",
            "reputation_score": 70.0
        }
        creator_id = await db_helper.create_test_user(creator_data)
        mint_address = await db_helper.create_test_token(sample_token_data, creator_id)

        # Пытаемся обновить под другим пользователем
        update_data = {
            "description": "Unauthorized update attempt"
        }

        response = await async_client.patch(
            f"/api/v1/tokens/{mint_address}/metadata",
            json=update_data,
            headers=auth_headers  # Заголовки от другого пользователя
        )

        assert response.status_code == 403
        response_data = response.json()
        assert "not authorized" in response_data["detail"].lower()

    async def test_search_tokens(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict
    ):
        """Тест поиска токенов по названию и символу"""
        # Создаем несколько токенов
        user_data = {
            "wallet_address": "SearchTestUser123456789",
            "username": "searchuser",
            "email": "search@test.com",
            "reputation_score": 60.0
        }
        user_id = await db_helper.create_test_user(user_data)

        # Создаем токены с разными именами
        test_tokens = [
            {"name": "Bitcoin Meme", "symbol": "BTCM"},
            {"name": "Ethereum Fun", "symbol": "ETHF"},
            {"name": "Solana Power", "symbol": "SOLP"},
            {"name": "Moon Token", "symbol": "MOON"},
        ]

        for token_data in test_tokens:
            token = sample_token_data.copy()
            token.update(token_data)
            await db_helper.create_test_token(token, user_id)

        # Поиск по названию
        response = await async_client.get("/api/v1/tokens/search?q=bitcoin")

        assert response.status_code == 200
        response_data = response.json()
        
        assert "tokens" in response_data
        assert len(response_data["tokens"]) >= 1
        
        # Проверяем, что найден токен с "Bitcoin" в названии
        bitcoin_token = next(
            (token for token in response_data["tokens"] 
             if "bitcoin" in token["name"].lower()), 
            None
        )
        assert bitcoin_token is not None

    async def test_get_trending_tokens(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict
    ):
        """Тест получения трендовых токенов"""
        # Создаем токены с разной активностью
        user_data = {
            "wallet_address": "TrendingTestUser123456789",
            "username": "trendinguser",
            "email": "trending@test.com",
            "reputation_score": 60.0
        }
        user_id = await db_helper.create_test_user(user_data)

        # Создаем токены
        trending_tokens = []
        for i in range(3):
            token = sample_token_data.copy()
            token["name"] = f"Trending Token {i}"
            token["symbol"] = f"TREND{i}"
            mint_address = await db_helper.create_test_token(token, user_id)
            trending_tokens.append(mint_address)

            # Создаем активность (сделки) для токенов
            for j in range((i + 1) * 5):  # Больше активности для токенов с большим индексом
                trade_data = {
                    "token_mint": mint_address,
                    "trader_address": f"Trader{j}",
                    "trade_type": "buy" if j % 2 == 0 else "sell",
                    "sol_amount": 100000000,  # 0.1 SOL
                    "token_amount": 10000
                }
                await db_helper.create_test_trade(trade_data)

        response = await async_client.get("/api/v1/tokens/trending?limit=5")

        assert response.status_code == 200
        response_data = response.json()
        
        assert "tokens" in response_data
        assert len(response_data["tokens"]) >= 3
        
        # Проверяем, что токены отсортированы по активности
        volumes = [token.get("volume_24h", 0) for token in response_data["tokens"]]
        assert volumes == sorted(volumes, reverse=True)

    @pytest.mark.slow
    async def test_token_graduation_process(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict,
        auth_headers: dict,
        mock_solana_client
    ):
        """Тест процесса листинга токена на DEX"""
        # Создаем токен близкий к листингу
        user_data = {
            "wallet_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
            "username": "graduationuser",
            "email": "graduation@test.com",
            "reputation_score": 80.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        # Создаем токен с высокой market cap (близкой к threshold)
        graduation_token = sample_token_data.copy()
        graduation_token["current_market_cap"] = 45000000000000000  # 45 SOL (близко к 50 SOL threshold)
        mint_address = await db_helper.create_test_token(graduation_token, user_id)

        # Мокаем DEX листинг
        with patch("api.services.blockchain.SolanaService") as mock_service:
            mock_service.return_value.create_raydium_pool = AsyncMock(
                return_value={
                    "pool_address": "test_pool_address",
                    "transaction_signature": "test_graduation_tx"
                }
            )

            # Инициируем листинг
            graduation_data = {
                "dex_type": "raydium",
                "initial_liquidity_sol": 10000000000,  # 10 SOL
                "liquidity_lock_duration": 86400 * 30  # 30 дней
            }

            response = await async_client.post(
                f"/api/v1/tokens/{mint_address}/graduate",
                json=graduation_data,
                headers=auth_headers
            )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "pool_address" in response_data
        assert "transaction_signature" in response_data
        assert response_data["status"] == "graduated"
        assert response_data["dex_type"] == "raydium"

        # Проверяем, что в БД обновился статус
        token_in_db = await db_helper.conn.fetchrow(
            "SELECT graduated, graduation_timestamp FROM tokens WHERE mint_address = $1",
            mint_address
        )
        assert token_in_db["graduated"] is True
        assert token_in_db["graduation_timestamp"] is not None