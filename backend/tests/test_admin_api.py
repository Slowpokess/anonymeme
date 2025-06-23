"""
🔐 Integration тесты для Admin API
Comprehensive тестирование административных операций и управления
"""

import pytest
import json
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from .conftest import DatabaseTestHelper, sample_token_data, sample_user_data, admin_auth_headers, auth_headers


@pytest.mark.integration
@pytest.mark.requires_db
class TestAdminAPI:
    """Тесты API для административного управления"""

    async def test_get_admin_dashboard(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        admin_auth_headers: dict
    ):
        """Тест получения административной панели"""
        # Создаем тестовые данные
        user_data = {
            "wallet_address": "AdminDashboardUser123456789",
            "username": "dashboarduser",
            "email": "dashboard@test.com",
            "reputation_score": 70.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "Admin Dashboard Token",
            "symbol": "ADT",
            "description": "Token for admin dashboard",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        response = await async_client.get(
            "/api/v1/admin/dashboard",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "statistics" in response_data
        assert "recent_activity" in response_data
        assert "pending_actions" in response_data
        assert "system_health" in response_data
        assert "alerts" in response_data
        
        # Проверяем статистику
        stats = response_data["statistics"]
        assert "total_users" in stats
        assert "total_tokens" in stats
        assert "total_trades" in stats
        assert "total_volume" in stats
        assert "platform_fees" in stats

    async def test_get_admin_dashboard_unauthorized(
        self,
        async_client: AsyncClient,
        auth_headers: dict  # Обычные заголовки
    ):
        """Тест доступа к админ панели обычным пользователем"""
        response = await async_client.get(
            "/api/v1/admin/dashboard",
            headers=auth_headers
        )

        assert response.status_code == 403
        response_data = response.json()
        assert "admin" in response_data["detail"].lower()

    async def test_manage_user_status(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_user_data: dict,
        admin_auth_headers: dict
    ):
        """Тест управления статусом пользователя"""
        # Создаем пользователя
        user_id = await db_helper.create_test_user(sample_user_data)

        # Блокируем пользователя
        ban_data = {
            "action": "ban",
            "reason": "Violation of terms of service",
            "duration_hours": 168  # 7 дней
        }

        response = await async_client.post(
            f"/api/v1/admin/users/{sample_user_data['wallet_address']}/status",
            json=ban_data,
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "banned"
        assert response_data["reason"] == ban_data["reason"]

        # Проверяем, что статус сохранен в БД
        user_in_db = await db_helper.conn.fetchrow(
            "SELECT status, ban_reason FROM users WHERE id = $1",
            user_id
        )
        assert user_in_db["status"] == "banned"
        assert user_in_db["ban_reason"] == ban_data["reason"]

        # Разблокируем пользователя
        unban_data = {
            "action": "unban",
            "reason": "Appeal approved"
        }

        response = await async_client.post(
            f"/api/v1/admin/users/{sample_user_data['wallet_address']}/status",
            json=unban_data,
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "active"

    async def test_moderate_token_content(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict,
        admin_auth_headers: dict
    ):
        """Тест модерации контента токенов"""
        # Создаем пользователя и токен
        user_data = {
            "wallet_address": "ModerationUser123456789",
            "username": "moderationuser",
            "email": "moderation@test.com",
            "reputation_score": 60.0
        }
        user_id = await db_helper.create_test_user(user_data)
        mint_address = await db_helper.create_test_token(sample_token_data, user_id)

        # Помечаем токен как неподходящий
        moderation_data = {
            "action": "flag",
            "reason": "Inappropriate content",
            "severity": "high",
            "requires_review": True
        }

        response = await async_client.post(
            f"/api/v1/admin/tokens/{mint_address}/moderate",
            json=moderation_data,
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "flagged"
        assert response_data["moderation_reason"] == moderation_data["reason"]

        # Проверяем, что модерация сохранена в БД
        token_in_db = await db_helper.conn.fetchrow(
            "SELECT status, moderation_status FROM tokens WHERE mint_address = $1",
            mint_address
        )
        assert token_in_db["moderation_status"] == "flagged"

    async def test_approve_reject_token(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict,
        admin_auth_headers: dict
    ):
        """Тест одобрения/отклонения токенов"""
        # Создаем токен в статусе pending
        user_data = {
            "wallet_address": "ApprovalUser123456789",
            "username": "approvaluser",
            "email": "approval@test.com",
            "reputation_score": 65.0
        }
        user_id = await db_helper.create_test_user(user_data)
        mint_address = await db_helper.create_test_token(sample_token_data, user_id)

        # Одобряем токен
        approval_data = {
            "action": "approve",
            "notes": "Token meets all requirements"
        }

        response = await async_client.post(
            f"/api/v1/admin/tokens/{mint_address}/review",
            json=approval_data,
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "approved"
        assert response_data["admin_notes"] == approval_data["notes"]

        # Проверяем статус в БД
        token_in_db = await db_helper.conn.fetchrow(
            "SELECT status FROM tokens WHERE mint_address = $1",
            mint_address
        )
        assert token_in_db["status"] == "active"

    async def test_get_pending_reviews(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        admin_auth_headers: dict
    ):
        """Тест получения списка токенов на рассмотрении"""
        # Создаем несколько токенов требующих review
        user_data = {
            "wallet_address": "PendingUser123456789",
            "username": "pendinguser",
            "email": "pending@test.com",
            "reputation_score": 50.0
        }
        user_id = await db_helper.create_test_user(user_data)

        # Создаем токены
        for i in range(3):
            token_data = {
                "name": f"Pending Token {i}",
                "symbol": f"PEND{i}",
                "description": f"Token requiring review {i}",
                "initial_supply": 1000000000000000000,
                "initial_price": 1000000
            }
            await db_helper.create_test_token(token_data, user_id)

        response = await async_client.get(
            "/api/v1/admin/tokens/pending-review",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "tokens" in response_data
        assert "pagination" in response_data
        assert "summary" in response_data
        
        # Проверяем summary
        summary = response_data["summary"]
        assert "total_pending" in summary
        assert "high_priority" in summary
        assert "flagged_content" in summary

    async def test_emergency_pause_system(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict
    ):
        """Тест экстренной остановки системы"""
        # Включаем emergency pause
        pause_data = {
            "action": "pause",
            "reason": "Security incident detected",
            "affected_modules": ["trading", "token_creation"],
            "estimated_duration": "2h"
        }

        response = await async_client.post(
            "/api/v1/admin/system/emergency-pause",
            json=pause_data,
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "paused"
        assert response_data["reason"] == pause_data["reason"]
        assert "affected_modules" in response_data

        # Снимаем pause
        resume_data = {
            "action": "resume",
            "reason": "Security issue resolved"
        }

        response = await async_client.post(
            "/api/v1/admin/system/emergency-pause",
            json=resume_data,
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "active"

    async def test_manage_platform_settings(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict
    ):
        """Тест управления настройками платформы"""
        # Получаем текущие настройки
        response = await async_client.get(
            "/api/v1/admin/settings",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        current_settings = response.json()
        assert "trading_settings" in current_settings
        assert "fee_settings" in current_settings
        assert "moderation_settings" in current_settings

        # Обновляем настройки
        new_settings = {
            "trading_settings": {
                "max_slippage_percentage": 15.0,
                "min_trade_amount": 100000000,  # 0.1 SOL
                "whale_protection_threshold": 5.0
            },
            "fee_settings": {
                "trading_fee_percentage": 0.25,
                "creation_fee_sol": 1000000000,  # 1 SOL
                "graduation_fee_percentage": 1.0
            }
        }

        response = await async_client.patch(
            "/api/v1/admin/settings",
            json=new_settings,
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["trading_settings"]["max_slippage_percentage"] == 15.0
        assert response_data["fee_settings"]["trading_fee_percentage"] == 0.25

    async def test_view_audit_logs(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        admin_auth_headers: dict
    ):
        """Тест просмотра audit логов"""
        # Выполняем несколько действий для создания логов
        user_data = {
            "wallet_address": "AuditLogUser123456789",
            "username": "audituser",
            "email": "audit@test.com",
            "reputation_score": 60.0
        }
        user_id = await db_helper.create_test_user(user_data)

        # Запрашиваем audit logs
        response = await async_client.get(
            "/api/v1/admin/audit-logs?limit=50&action_type=user_management",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "logs" in response_data
        assert "pagination" in response_data
        assert "filters" in response_data
        
        # Проверяем структуру лога
        if response_data["logs"]:
            log_entry = response_data["logs"][0]
            assert "timestamp" in log_entry
            assert "admin_user" in log_entry
            assert "action_type" in log_entry
            assert "target_entity" in log_entry
            assert "details" in log_entry

    async def test_generate_admin_reports(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        admin_auth_headers: dict
    ):
        """Тест генерации административных отчетов"""
        # Создаем данные для отчета
        user_data = {
            "wallet_address": "ReportUser123456789",
            "username": "reportuser",
            "email": "report@test.com",
            "reputation_score": 75.0
        }
        user_id = await db_helper.create_test_user(user_data)

        # Запрашиваем генерацию отчета
        report_request = {
            "report_type": "user_activity",
            "period": "30d",
            "format": "pdf",
            "include_charts": True,
            "filters": {
                "min_reputation": 50.0,
                "include_banned": False
            }
        }

        response = await async_client.post(
            "/api/v1/admin/reports/generate",
            json=report_request,
            headers=admin_auth_headers
        )

        assert response.status_code == 202  # Accepted
        response_data = response.json()
        assert "report_id" in response_data
        assert "status" in response_data
        assert "estimated_completion" in response_data

        # Проверяем статус генерации
        report_id = response_data["report_id"]
        response = await async_client.get(
            f"/api/v1/admin/reports/{report_id}/status",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        status_data = response.json()
        assert "status" in status_data
        assert status_data["status"] in ["pending", "processing", "completed", "failed"]

    async def test_manage_featured_tokens(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        sample_token_data: dict,
        admin_auth_headers: dict
    ):
        """Тест управления featured токенами"""
        # Создаем токен
        user_data = {
            "wallet_address": "FeaturedUser123456789",
            "username": "featureduser",
            "email": "featured@test.com",
            "reputation_score": 80.0
        }
        user_id = await db_helper.create_test_user(user_data)
        mint_address = await db_helper.create_test_token(sample_token_data, user_id)

        # Добавляем токен в featured
        feature_data = {
            "action": "add",
            "priority": 1,
            "duration_hours": 168,  # 1 неделя
            "reason": "Exceptional community engagement"
        }

        response = await async_client.post(
            f"/api/v1/admin/tokens/{mint_address}/featured",
            json=feature_data,
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["featured"] is True
        assert response_data["priority"] == 1

        # Получаем список featured токенов
        response = await async_client.get(
            "/api/v1/admin/tokens/featured",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        assert "tokens" in response_data
        assert len(response_data["tokens"]) >= 1
        
        # Проверяем, что наш токен в списке
        featured_token = next(
            (token for token in response_data["tokens"] 
             if token["mint_address"] == mint_address),
            None
        )
        assert featured_token is not None

    async def test_financial_reconciliation(
        self,
        async_client: AsyncClient,
        db_helper: DatabaseTestHelper,
        admin_auth_headers: dict
    ):
        """Тест финансовой сверки"""
        # Создаем торговые данные
        user_data = {
            "wallet_address": "FinanceUser123456789",
            "username": "financeuser",
            "email": "finance@test.com",
            "reputation_score": 70.0
        }
        user_id = await db_helper.create_test_user(user_data)
        
        token_data = {
            "name": "Finance Token",
            "symbol": "FIN",
            "description": "Token for financial reconciliation",
            "initial_supply": 1000000000000000000,
            "initial_price": 1000000
        }
        mint_address = await db_helper.create_test_token(token_data, user_id)

        # Создаем сделки
        for i in range(5):
            trade_data = {
                "token_mint": mint_address,
                "trader_address": f"FinanceTrader{i}",
                "trade_type": "buy" if i % 2 == 0 else "sell",
                "sol_amount": (i + 1) * 1000000000,
                "token_amount": (i + 1) * 1000000
            }
            await db_helper.create_test_trade(trade_data)

        # Запрашиваем финансовую сверку
        reconciliation_request = {
            "period_start": "2024-01-01T00:00:00Z",
            "period_end": "2024-12-31T23:59:59Z",
            "include_details": True
        }

        response = await async_client.post(
            "/api/v1/admin/finance/reconciliation",
            json=reconciliation_request,
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "summary" in response_data
        assert "discrepancies" in response_data
        assert "fee_breakdown" in response_data
        assert "blockchain_verification" in response_data
        
        # Проверяем summary
        summary = response_data["summary"]
        assert "total_fees_collected" in summary
        assert "total_volume_processed" in summary
        assert "transaction_count" in summary
        assert "reconciliation_status" in summary

    async def test_security_alerts_management(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict
    ):
        """Тест управления security alerts"""
        # Получаем текущие alerts
        response = await async_client.get(
            "/api/v1/admin/security/alerts",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        assert "alerts" in response_data
        assert "statistics" in response_data

        # Создаем новый alert
        alert_data = {
            "type": "suspicious_activity",
            "severity": "high",
            "title": "Multiple failed login attempts",
            "description": "User attempting brute force attack",
            "affected_entity": "UserAccount123456789",
            "recommended_action": "temporary_ban"
        }

        response = await async_client.post(
            "/api/v1/admin/security/alerts",
            json=alert_data,
            headers=admin_auth_headers
        )

        assert response.status_code == 201
        response_data = response.json()
        assert "alert_id" in response_data
        assert response_data["severity"] == "high"
        assert response_data["status"] == "active"

        # Закрываем alert
        alert_id = response_data["alert_id"]
        resolution_data = {
            "action": "resolve",
            "resolution": "User temporarily banned for 24 hours",
            "follow_up_required": False
        }

        response = await async_client.patch(
            f"/api/v1/admin/security/alerts/{alert_id}",
            json=resolution_data,
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "resolved"

    @pytest.mark.slow
    async def test_database_maintenance_operations(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict
    ):
        """Тест операций обслуживания базы данных"""
        # Запускаем анализ производительности БД
        response = await async_client.post(
            "/api/v1/admin/database/analyze",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        assert "analysis_id" in response_data
        assert "status" in response_data

        # Получаем статистику БД
        response = await async_client.get(
            "/api/v1/admin/database/statistics",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        
        assert "table_sizes" in response_data
        assert "index_usage" in response_data
        assert "query_performance" in response_data
        assert "connection_stats" in response_data
        assert "disk_usage" in response_data

    async def test_backup_restore_operations(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict
    ):
        """Тест операций backup и restore"""
        # Создаем backup
        backup_request = {
            "backup_type": "incremental",
            "include_user_data": True,
            "include_trade_history": True,
            "compression": True
        }

        response = await async_client.post(
            "/api/v1/admin/backup/create",
            json=backup_request,
            headers=admin_auth_headers
        )

        assert response.status_code == 202  # Accepted
        response_data = response.json()
        assert "backup_id" in response_data
        assert "status" in response_data

        # Получаем список backups
        response = await async_client.get(
            "/api/v1/admin/backup/list",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        assert "backups" in response_data
        
        # Проверяем структуру backup info
        if response_data["backups"]:
            backup = response_data["backups"][0]
            assert "backup_id" in backup
            assert "created_at" in backup
            assert "size" in backup
            assert "status" in backup
            assert "backup_type" in backup