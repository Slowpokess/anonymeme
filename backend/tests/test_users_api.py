"""
👤 Integration тесты для Users API
Comprehensive тестирование пользовательских операций и профилей
"""

import pytest
import json
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from .conftest import DatabaseTestHelper, sample_user_data, auth_headers


@pytest.mark.integration
@pytest.mark.requires_db
class TestUsersAPI:
    """Тесты API для управления пользователями"""

    async def test_create_user_profile_success(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict
    ):
        """Тест успешного создания профиля пользователя"""
        response = await async_client.post(
            "/api/v1/users/profile",
            json=sample_user_data
        )

        assert response.status_code == 201
        response_data = response.json()
        
        assert "id" in response_data
        assert response_data["wallet_address"] == sample_user_data["wallet_address"]
        assert response_data["username"] == sample_user_data["username"]
        assert response_data["email"] == sample_user_data["email"]
        assert response_data["reputation_score"] == sample_user_data["reputation_score"]
        assert "created_at" in response_data

        # Проверяем, что пользователь сохранен в БД
        user_in_db = await db_helper.conn.fetchrow(
            "SELECT * FROM users WHERE wallet_address = $1",
            sample_user_data["wallet_address"]
        )
        assert user_in_db is not None
        assert user_in_db["username"] == sample_user_data["username"]

    async def test_create_user_duplicate_wallet(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict
    ):
        """Тест создания пользователя с уже существующим wallet"""
        # Создаем пользователя первый раз
        await db_helper.create_test_user(sample_user_data)

        # Пытаемся создать еще раз с тем же wallet
        response = await async_client.post(
            "/api/v1/users/profile",
            json=sample_user_data
        )

        assert response.status_code == 409  # Conflict
        response_data = response.json()
        assert "already exists" in response_data["detail"].lower()

    async def test_create_user_duplicate_username(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict
    ):
        """Тест создания пользователя с уже существующим username"""
        # Создаем первого пользователя
        await db_helper.create_test_user(sample_user_data)

        # Пытаемся создать второго с тем же username но другим wallet
        duplicate_user = sample_user_data.copy()
        duplicate_user["wallet_address"] = "DifferentWalletAddress123456789"
        
        response = await async_client.post(
            "/api/v1/users/profile",
            json=duplicate_user
        )

        assert response.status_code == 409
        response_data = response.json()
        assert "username" in response_data["detail"].lower()

    async def test_get_user_profile_by_wallet(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict
    ):
        """Тест получения профиля пользователя по wallet адресу"""
        # Создаем пользователя
        user_id = await db_helper.create_test_user(sample_user_data)

        response = await async_client.get(
            f"/api/v1/users/profile/{sample_user_data['wallet_address']}"
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["id"] == user_id
        assert response_data["wallet_address"] == sample_user_data["wallet_address"]
        assert response_data["username"] == sample_user_data["username"]
        assert response_data["reputation_score"] == sample_user_data["reputation_score"]

    async def test_get_user_profile_not_found(
        self,
        async_client: AsyncClient
    ):
        """Тест получения несуществующего профиля"""
        response = await async_client.get(
            "/api/v1/users/profile/NonExistentWallet123456789"
        )

        assert response.status_code == 404
        response_data = response.json()
        assert "not found" in response_data["detail"].lower()

    async def test_update_user_profile_success(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict,
        auth_headers: dict
    ):
        """Тест успешного обновления профиля пользователя"""
        # Создаем пользователя
        await db_helper.create_test_user(sample_user_data)

        # Обновляем профиль
        update_data = {
            "username": "updatedusername",
            "email": "updated@test.com",
            "bio": "Updated bio information",
            "twitter_handle": "updated_twitter",
            "discord_handle": "updated_discord"
        }

        response = await async_client.patch(
            f"/api/v1/users/profile/{sample_user_data['wallet_address']}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["username"] == update_data["username"]
        assert response_data["email"] == update_data["email"]
        assert response_data["bio"] == update_data["bio"]
        assert response_data["twitter_handle"] == update_data["twitter_handle"]
        assert response_data["discord_handle"] == update_data["discord_handle"]

    async def test_update_user_profile_unauthorized(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict,
        auth_headers: dict
    ):
        """Тест обновления профиля другого пользователя (неавторизовано)"""
        # Создаем пользователя
        await db_helper.create_test_user(sample_user_data)

        # Пытаемся обновить профиль другого пользователя
        other_wallet = "AnotherUserWallet123456789"
        update_data = {"username": "hackAttempt"}

        response = await async_client.patch(
            f"/api/v1/users/profile/{other_wallet}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 403
        response_data = response.json()
        assert "not authorized" in response_data["detail"].lower()

    async def test_get_user_trading_stats(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict,
        auth_headers: dict
    ):
        """Тест получения торговой статистики пользователя"""
        # Создаем пользователя и токен
        user_id = await db_helper.create_test_user(sample_user_data)
        
        token_data = {
            "name": "Stats Test Token",
            "symbol": "STT",
            "description": "Token for testing stats",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Создаем несколько торговых операций
        trades_data = [
            {
                "token_mint": mint_address,
                "trader_address": sample_user_data["wallet_address"],
                "trade_type": "buy",
                "sol_amount": 1000000000,  # 1 SOL
                "token_amount": 1000000
            },
            {
                "token_mint": mint_address,
                "trader_address": sample_user_data["wallet_address"],
                "trade_type": "sell",
                "sol_amount": 1200000000,  # 1.2 SOL (прибыль)
                "token_amount": 1000000
            },
            {
                "token_mint": mint_address,
                "trader_address": sample_user_data["wallet_address"],
                "trade_type": "buy",
                "sol_amount": 2000000000,  # 2 SOL
                "token_amount": 1500000
            }
        ]

        for trade_data in trades_data:
            await db_helper.create_test_trade(trade_data)

        response = await async_client.get(
            f"/api/v1/users/{sample_user_data['wallet_address']}/stats",
            headers=auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "total_trades" in response_data
        assert "total_volume_sol" in response_data
        assert "total_pnl_sol" in response_data
        assert "win_rate" in response_data
        assert "tokens_created" in response_data
        assert "reputation_score" in response_data
        
        assert response_data["total_trades"] == 3
        assert response_data["total_volume_sol"] > 0

    async def test_get_user_created_tokens(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict
    ):
        """Тест получения токенов, созданных пользователем"""
        # Создаем пользователя
        user_id = await db_helper.create_test_user(sample_user_data)

        # Создаем несколько токенов
        token_names = ["Token A", "Token B", "Token C"]
        created_tokens = []
        
        for i, name in enumerate(token_names):
            token_data = {
                "name": name,
                "symbol": f"T{i}",
                "description": f"Test token {i}",
                "initial_supply": 1000000000000000000,
                "initial_price": 1000000
            }
            mint_address = await db_helper.create_test_token(token_data, user_id)
            created_tokens.append(mint_address)

        response = await async_client.get(
            f"/api/v1/users/{sample_user_data['wallet_address']}/tokens"
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "tokens" in response_data
        assert "pagination" in response_data
        assert len(response_data["tokens"]) == 3
        
        # Проверяем, что все токены принадлежат правильному создателю
        for token in response_data["tokens"]:
            assert token["creator"]["wallet_address"] == sample_user_data["wallet_address"]

    async def test_get_user_portfolio(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict
    ):
        """Тест получения портфолио пользователя"""
        # Создаем пользователя и токены
        user_id = await db_helper.create_test_user(sample_user_data)
        
        token_data = {
            "name": "Portfolio Token",
            "symbol": "PORT",
            "description": "Token for portfolio testing",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Создаем торговые позиции
        trade_data = {
            "token_mint": mint_address,
            "trader_address": sample_user_data["wallet_address"],
            "trade_type": "buy",
            "sol_amount": 5000000000,  # 5 SOL
            "token_amount": 5000000    # 5M токенов
        }
        await db_helper.create_test_trade(trade_data)

        response = await async_client.get(
            f"/api/v1/users/{sample_user_data['wallet_address']}/portfolio"
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "holdings" in response_data
        assert "total_value_sol" in response_data
        assert "total_pnl_sol" in response_data
        assert "total_pnl_percentage" in response_data
        assert len(response_data["holdings"]) >= 1
        
        # Проверяем структуру holdings
        holding = response_data["holdings"][0]
        assert "token" in holding
        assert "amount" in holding
        assert "current_value_sol" in holding
        assert "pnl_sol" in holding

    async def test_follow_unfollow_user(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict,
        auth_headers: dict
    ):
        """Тест подписки и отписки от пользователя"""
        # Создаем двух пользователей
        user1_id = await db_helper.create_test_user(sample_user_data)
        
        user2_data = {
            "wallet_address": "FollowTargetUser123456789",
            "username": "followtarget",
            "email": "target@test.com",
            "reputation_score": 70.0
        }
        user2_id = await db_helper.create_test_user(user2_data)

        # Подписываемся на пользователя
        response = await async_client.post(
            f"/api/v1/users/{user2_data['wallet_address']}/follow",
            headers=auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["following"] is True

        # Проверяем, что подписка сохранена
        # (предполагается наличие таблицы user_follows)
        
        # Отписываемся
        response = await async_client.delete(
            f"/api/v1/users/{user2_data['wallet_address']}/follow",
            headers=auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["following"] is False

    async def test_get_user_followers_following(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict
    ):
        """Тест получения списка подписчиков и подписок"""
        # Создаем пользователя
        user_id = await db_helper.create_test_user(sample_user_data)

        # Тест получения подписчиков
        response = await async_client.get(
            f"/api/v1/users/{sample_user_data['wallet_address']}/followers"
        )

        assert response.status_code == 200
        response_data = response.json()
        assert "followers" in response_data
        assert "total_count" in response_data

        # Тест получения подписок
        response = await async_client.get(
            f"/api/v1/users/{sample_user_data['wallet_address']}/following"
        )

        assert response.status_code == 200
        response_data = response.json()
        assert "following" in response_data
        assert "total_count" in response_data

    async def test_update_user_reputation(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict,
        admin_auth_headers: dict
    ):
        """Тест обновления репутации пользователя (только админ)"""
        # Создаем пользователя
        user_id = await db_helper.create_test_user(sample_user_data)

        # Обновляем репутацию
        reputation_update = {
            "reputation_score": 85.0,
            "reason": "Successful token launches"
        }

        response = await async_client.patch(
            f"/api/v1/users/{sample_user_data['wallet_address']}/reputation",
            json=reputation_update,
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["reputation_score"] == 85.0

        # Проверяем, что изменение сохранено в БД
        user_in_db = await db_helper.conn.fetchrow(
            "SELECT reputation_score FROM users WHERE id = $1",
            user_id
        )
        assert user_in_db["reputation_score"] == 85.0

    async def test_update_reputation_unauthorized(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict,
        auth_headers: dict  # Обычные заголовки, не админские
    ):
        """Тест обновления репутации обычным пользователем (должно быть запрещено)"""
        user_id = await db_helper.create_test_user(sample_user_data)

        reputation_update = {
            "reputation_score": 95.0,
            "reason": "Hack attempt"
        }

        response = await async_client.patch(
            f"/api/v1/users/{sample_user_data['wallet_address']}/reputation",
            json=reputation_update,
            headers=auth_headers
        )

        assert response.status_code == 403
        response_data = response.json()
        assert "admin" in response_data["detail"].lower()

    async def test_get_user_notifications(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict,
        auth_headers: dict
    ):
        """Тест получения уведомлений пользователя"""
        # Создаем пользователя
        user_id = await db_helper.create_test_user(sample_user_data)

        response = await async_client.get(
            f"/api/v1/users/{sample_user_data['wallet_address']}/notifications",
            headers=auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "notifications" in response_data
        assert "unread_count" in response_data
        assert "pagination" in response_data

    async def test_mark_notifications_read(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict,
        auth_headers: dict
    ):
        """Тест отметки уведомлений как прочитанных"""
        # Создаем пользователя
        user_id = await db_helper.create_test_user(sample_user_data)

        # Отмечаем все уведомления как прочитанные
        response = await async_client.patch(
            f"/api/v1/users/{sample_user_data['wallet_address']}/notifications/read",
            headers=auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        assert "marked_read" in response_data

    async def test_user_search(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper
    ):
        """Тест поиска пользователей"""
        # Создаем несколько пользователей
        users_data = [
            {
                "wallet_address": "SearchUser1",
                "username": "bitcoinfan",
                "email": "bitcoin@test.com",
                "reputation_score": 60.0
            },
            {
                "wallet_address": "SearchUser2", 
                "username": "ethereumtrader",
                "email": "ethereum@test.com",
                "reputation_score": 70.0
            },
            {
                "wallet_address": "SearchUser3",
                "username": "solanabuilder",
                "email": "solana@test.com",
                "reputation_score": 80.0
            }
        ]

        for user_data in users_data:
            await db_helper.create_test_user(user_data)

        # Поиск по username
        response = await async_client.get("/api/v1/users/search?q=bitcoin")

        assert response.status_code == 200
        response_data = response.json()
        
        assert "users" in response_data
        assert len(response_data["users"]) >= 1
        
        # Проверяем, что найден правильный пользователь
        bitcoin_user = next(
            (user for user in response_data["users"] 
             if "bitcoin" in user["username"].lower()),
            None
        )
        assert bitcoin_user is not None

    async def test_get_leaderboard(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper
    ):
        """Тест получения leaderboard пользователей"""
        # Создаем пользователей с разной репутацией
        users_data = [
            {"wallet_address": "Leader1", "username": "leader1", "email": "l1@test.com", "reputation_score": 95.0},
            {"wallet_address": "Leader2", "username": "leader2", "email": "l2@test.com", "reputation_score": 85.0},
            {"wallet_address": "Leader3", "username": "leader3", "email": "l3@test.com", "reputation_score": 75.0},
        ]

        for user_data in users_data:
            await db_helper.create_test_user(user_data)

        response = await async_client.get("/api/v1/users/leaderboard?limit=10")

        assert response.status_code == 200
        response_data = response.json()
        
        assert "users" in response_data
        assert len(response_data["users"]) >= 3
        
        # Проверяем, что пользователи отсортированы по репутации
        reputation_scores = [user["reputation_score"] for user in response_data["users"]]
        assert reputation_scores == sorted(reputation_scores, reverse=True)

    @pytest.mark.slow
    async def test_user_activity_feed(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict,
        auth_headers: dict
    ):
        """Тест получения ленты активности пользователя"""
        # Создаем пользователя
        user_id = await db_helper.create_test_user(sample_user_data)

        # Создаем токен и торговую активность
        token_data = {
            "name": "Activity Token",
            "symbol": "ACT",
            "description": "Token for activity testing",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Создаем торговую активность
        trade_data = {
            "token_mint": mint_address,
            "trader_address": sample_user_data["wallet_address"],
            "trade_type": "buy",
            "sol_amount": 1000000000,
            "token_amount": 1000000
        }
        await db_helper.create_test_trade(trade_data)

        response = await async_client.get(
            f"/api/v1/users/{sample_user_data['wallet_address']}/activity",
            headers=auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "activities" in response_data
        assert "pagination" in response_data
        
        # Проверяем наличие активности
        if response_data["activities"]:
            activity = response_data["activities"][0]
            assert "type" in activity
            assert "timestamp" in activity
            assert "data" in activity