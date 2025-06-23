"""
🧪 Pytest конфигурация для integration тестов API
Comprehensive test setup для production-ready тестирования
"""

import pytest
import asyncio
import tempfile
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock

import asyncpg
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Предполагаем, что API использует FastAPI
# from api.main import app
# from api.core.config import get_settings
# from api.models.database import get_database


class TestConfig:
    """Конфигурация для тестовой среды"""
    DATABASE_URL = "postgresql://test_user:test_pass@localhost:5432/test_anonymeme"
    REDIS_URL = "redis://localhost:6379/1"
    SECRET_KEY = "test-secret-key-for-testing-only"
    ENVIRONMENT = "testing"
    DEBUG = True
    TESTING = True
    
    # Solana test configuration
    SOLANA_RPC_URL = "https://api.devnet.solana.com"
    SOLANA_CLUSTER = "devnet"
    
    # WebSocket test configuration
    WEBSOCKET_HOST = "localhost"
    WEBSOCKET_PORT = 8001
    
    # Disable external services in tests
    ENABLE_EXTERNAL_APIS = False
    ENABLE_WEBSOCKETS = False


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Создание event loop для async тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db() -> AsyncGenerator[str, None]:
    """Создание тестовой базы данных"""
    # Создаем временную тестовую БД
    temp_db_name = f"test_anonymeme_{os.getpid()}"
    
    # Подключение к PostgreSQL для создания тестовой БД
    try:
        conn = await asyncpg.connect("postgresql://postgres@localhost:5432/postgres")
        await conn.execute(f'CREATE DATABASE "{temp_db_name}"')
        await conn.close()
        
        test_db_url = f"postgresql://postgres@localhost:5432/{temp_db_name}"
        
        # Запуск миграций
        # await run_migrations(test_db_url)
        
        yield test_db_url
        
    finally:
        # Удаление тестовой БД
        try:
            conn = await asyncpg.connect("postgresql://postgres@localhost:5432/postgres")
            await conn.execute(f'DROP DATABASE IF EXISTS "{temp_db_name}"')
            await conn.close()
        except Exception as e:
            print(f"Warning: Could not cleanup test database: {e}")


@pytest.fixture
async def db_connection(test_db: str) -> AsyncGenerator[asyncpg.Connection, None]:
    """Подключение к тестовой БД для отдельного теста"""
    conn = await asyncpg.connect(test_db)
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture
async def clean_db(db_connection: asyncpg.Connection) -> AsyncGenerator[asyncpg.Connection, None]:
    """Очистка БД между тестами"""
    # Начинаем транзакцию
    async with db_connection.transaction():
        yield db_connection
        # Транзакция автоматически откатится после теста


# @pytest.fixture
# def test_app() -> FastAPI:
#     """Тестовое приложение FastAPI с тестовой конфигурацией"""
#     app.dependency_overrides[get_settings] = lambda: TestConfig()
#     return app


@pytest.fixture
def client() -> TestClient:
    """Синхронный test client для простых API тестов"""
    # return TestClient(test_app)
    # Заглушка для примера
    return Mock()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Асинхронный HTTP client для complex API тестов"""
    # async with AsyncClient(app=test_app, base_url="http://test") as ac:
    #     yield ac
    # Заглушка для примера
    yield AsyncMock()


@pytest.fixture
def mock_solana_client() -> Mock:
    """Mock Solana client для тестирования blockchain операций"""
    mock = Mock()
    
    # Мокаем основные методы
    mock.get_balance = AsyncMock(return_value=1000000000)  # 1 SOL
    mock.get_transaction = AsyncMock(return_value={
        "slot": 123456,
        "transaction": {
            "signatures": ["test_signature"],
            "message": {
                "accountKeys": [],
                "instructions": []
            }
        }
    })
    mock.send_transaction = AsyncMock(return_value="test_transaction_signature")
    mock.confirm_transaction = AsyncMock(return_value={"value": {"confirmationStatus": "finalized"}})
    
    return mock


@pytest.fixture
def mock_redis_client() -> Mock:
    """Mock Redis client для тестирования cache операций"""
    mock = Mock()
    
    # Внутренний store для имитации Redis
    store = {}
    
    async def mock_get(key):
        return store.get(key)
    
    async def mock_set(key, value, ex=None):
        store[key] = value
        return True
    
    async def mock_delete(key):
        return store.pop(key, None) is not None
    
    async def mock_exists(key):
        return key in store
    
    mock.get = AsyncMock(side_effect=mock_get)
    mock.set = AsyncMock(side_effect=mock_set)
    mock.delete = AsyncMock(side_effect=mock_delete)
    mock.exists = AsyncMock(side_effect=mock_exists)
    
    return mock


@pytest.fixture
def sample_token_data() -> dict:
    """Тестовые данные токена"""
    return {
        "name": "Test Meme Token",
        "symbol": "TMT",
        "description": "A test token for integration testing",
        "image_url": "https://example.com/token.png",
        "initial_supply": 1000000000000000000,  # 1 млрд
        "initial_price": 1000000,  # 0.001 SOL
        "bonding_curve_type": "linear",
        "graduation_threshold": 50000000000000000,  # 50 SOL market cap
    }


@pytest.fixture
def sample_user_data() -> dict:
    """Тестовые данные пользователя"""
    return {
        "wallet_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
        "username": "testuser",
        "email": "test@example.com",
        "reputation_score": 50.0,
    }


@pytest.fixture
def sample_trade_data() -> dict:
    """Тестовые данные сделки"""
    return {
        "token_mint": "TokenMintAddress123456789",
        "trader_address": "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb",
        "trade_type": "buy",
        "sol_amount": 1000000000,  # 1 SOL
        "token_amount": 1000000,
        "slippage_tolerance": 100,  # 1%
    }


@pytest.fixture
def auth_headers() -> dict:
    """Заголовки авторизации для тестовых запросов"""
    return {
        "Authorization": "Bearer test_jwt_token",
        "Content-Type": "application/json"
    }


@pytest.fixture
def admin_auth_headers() -> dict:
    """Заголовки авторизации для админских запросов"""
    return {
        "Authorization": "Bearer admin_jwt_token",
        "Content-Type": "application/json",
        "X-Admin-Key": "test_admin_key"
    }


class DatabaseTestHelper:
    """Хелпер для работы с БД в тестах"""
    
    def __init__(self, connection: asyncpg.Connection):
        self.conn = connection
    
    async def create_test_user(self, user_data: dict) -> int:
        """Создание тестового пользователя"""
        query = """
            INSERT INTO users (wallet_address, username, email, reputation_score)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """
        return await self.conn.fetchval(
            query,
            user_data["wallet_address"],
            user_data["username"],
            user_data["email"],
            user_data["reputation_score"]
        )
    
    async def create_test_token(self, token_data: dict, creator_id: int) -> str:
        """Создание тестового токена"""
        query = """
            INSERT INTO tokens (
                mint_address, name, symbol, description, 
                creator_id, initial_supply, current_price
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING mint_address
        """
        return await self.conn.fetchval(
            query,
            f"test_mint_{creator_id}",
            token_data["name"],
            token_data["symbol"],
            token_data["description"],
            creator_id,
            token_data["initial_supply"],
            token_data["initial_price"]
        )
    
    async def create_test_trade(self, trade_data: dict) -> int:
        """Создание тестовой сделки"""
        query = """
            INSERT INTO trades (
                token_mint, trader_address, trade_type,
                sol_amount, token_amount, created_at
            )
            VALUES ($1, $2, $3, $4, $5, NOW())
            RETURNING id
        """
        return await self.conn.fetchval(
            query,
            trade_data["token_mint"],
            trade_data["trader_address"],
            trade_data["trade_type"],
            trade_data["sol_amount"],
            trade_data["token_amount"]
        )


@pytest.fixture
def db_helper(clean_db: asyncpg.Connection) -> DatabaseTestHelper:
    """Хелпер для работы с БД"""
    return DatabaseTestHelper(clean_db)


class WebSocketTestHelper:
    """Хелпер для тестирования WebSocket соединений"""
    
    def __init__(self):
        self.connections = []
        self.messages = []
    
    async def connect(self, uri: str):
        """Подключение к WebSocket"""
        # Заглушка для WebSocket подключения
        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock()
        mock_ws.close = AsyncMock()
        
        self.connections.append(mock_ws)
        return mock_ws
    
    async def send_message(self, ws, message: dict):
        """Отправка сообщения через WebSocket"""
        self.messages.append(message)
        await ws.send(message)
    
    async def wait_for_message(self, ws, timeout: float = 5.0):
        """Ожидание сообщения от WebSocket"""
        # Заглушка для получения сообщения
        return {"type": "test_message", "data": {}}


@pytest.fixture
def ws_helper() -> WebSocketTestHelper:
    """Хелпер для WebSocket тестов"""
    return WebSocketTestHelper()


# Маркеры для категоризации тестов
def pytest_configure(config):
    """Конфигурация pytest с custom маркерами"""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "requires_db: mark test as requiring database")
    config.addinivalue_line("markers", "requires_redis: mark test as requiring Redis")
    config.addinivalue_line("markers", "requires_solana: mark test as requiring Solana connection")


# Скип тесты если нет необходимых зависимостей
def pytest_runtest_setup(item):
    """Автоматический скип тестов при отсутствии зависимостей"""
    if "requires_db" in item.keywords:
        try:
            import asyncpg
        except ImportError:
            pytest.skip("asyncpg not available")
    
    if "requires_redis" in item.keywords:
        try:
            import redis
        except ImportError:
            pytest.skip("redis not available")
    
    if "requires_solana" in item.keywords:
        try:
            import solana
        except ImportError:
            pytest.skip("solana not available")


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Автоматическая настройка тестовой среды"""
    # Устанавливаем переменные окружения для тестов
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["DEBUG"] = "True"
    os.environ["TESTING"] = "True"
    
    yield
    
    # Очистка после тестов
    test_env_vars = ["ENVIRONMENT", "DEBUG", "TESTING"]
    for var in test_env_vars:
        os.environ.pop(var, None)