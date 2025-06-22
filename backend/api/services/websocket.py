#!/usr/bin/env python3
"""
🔌 WebSocket сервис для real-time обновлений
Production-ready WebSocket server с комнатами и событиями
"""

import json
import logging
import asyncio
from typing import Dict, Set, Optional, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = None

import redis.asyncio as redis
from ..core.config import settings
from ..models.database import Token, Trade, User

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Типы WebSocket событий"""
    PRICE_UPDATE = "price_update"
    NEW_TRADE = "new_trade"
    TOKEN_CREATED = "token_created"
    TOKEN_GRADUATED = "token_graduated"
    USER_CONNECTED = "user_connected"
    USER_DISCONNECTED = "user_disconnected"
    PORTFOLIO_UPDATE = "portfolio_update"
    MARKET_STATS = "market_stats"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


@dataclass
class WebSocketMessage:
    """Структура WebSocket сообщения"""
    type: EventType
    data: Dict[str, Any]
    timestamp: str
    room: Optional[str] = None
    user_id: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str) -> 'WebSocketMessage':
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class ConnectionInfo:
    """Информация о WebSocket подключении"""
    websocket: WebSocketServerProtocol
    user_id: Optional[str] = None
    rooms: Set[str] = None
    connected_at: datetime = None
    last_ping: datetime = None
    
    def __post_init__(self):
        if self.rooms is None:
            self.rooms = set()
        if self.connected_at is None:
            self.connected_at = datetime.now(timezone.utc)
        if self.last_ping is None:
            self.last_ping = datetime.now(timezone.utc)


class WebSocketManager:
    """
    Менеджер WebSocket соединений
    Управляет подключениями, комнатами и отправкой сообщений
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.connections: Dict[str, ConnectionInfo] = {}
        self.rooms: Dict[str, Set[str]] = {}
        self.redis_client = redis_client
        self.server = None
        self.is_running = False
        
        # Статистика
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "errors": 0
        }
        
        logger.info("WebSocket Manager initialized")
    
    async def start_server(self, host: str = "localhost", port: int = 8765):
        """Запуск WebSocket сервера"""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("❌ websockets library not available")
            return False
        
        try:
            self.server = await websockets.serve(
                self.handle_connection,
                host,
                port,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.is_running = True
            logger.info(f"✅ WebSocket server started on ws://{host}:{port}")
            
            # Запуск фоновых задач
            asyncio.create_task(self.heartbeat_task())
            asyncio.create_task(self.cleanup_task())
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start WebSocket server: {e}")
            return False
    
    async def stop_server(self):
        """Остановка WebSocket сервера"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.is_running = False
            
            # Закрытие всех подключений
            for connection_id in list(self.connections.keys()):
                await self.disconnect_client(connection_id)
            
            logger.info("WebSocket server stopped")
    
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Обработка нового WebSocket подключения"""
        connection_id = self.generate_connection_id()
        
        try:
            # Регистрация подключения
            connection = ConnectionInfo(websocket=websocket)
            self.connections[connection_id] = connection
            self.stats["total_connections"] += 1
            self.stats["active_connections"] += 1
            
            logger.info(f"🔌 New WebSocket connection: {connection_id}")
            
            # Отправка приветственного сообщения
            await self.send_to_connection(connection_id, WebSocketMessage(
                type=EventType.USER_CONNECTED,
                data={"connection_id": connection_id, "timestamp": datetime.now(timezone.utc).isoformat()},
                timestamp=datetime.now(timezone.utc).isoformat()
            ))
            
            # Обработка входящих сообщений
            async for message in websocket:
                try:
                    await self.handle_message(connection_id, message)
                except Exception as e:
                    logger.error(f"Error handling message from {connection_id}: {e}")
                    await self.send_error(connection_id, str(e))
                    
        except (ConnectionClosedError, ConnectionClosedOK):
            logger.info(f"🔌 Connection {connection_id} closed normally")
        except Exception as e:
            logger.error(f"❌ Connection {connection_id} error: {e}")
            self.stats["errors"] += 1
        finally:
            await self.disconnect_client(connection_id)
    
    async def handle_message(self, connection_id: str, message_data: str):
        """Обработка входящего сообщения"""
        try:
            message = WebSocketMessage.from_json(message_data)
            connection = self.connections.get(connection_id)
            
            if not connection:
                return
            
            # Обновление времени последнего пинга
            connection.last_ping = datetime.now(timezone.utc)
            
            # Обработка различных типов сообщений
            if message.type == EventType.HEARTBEAT:
                await self.handle_heartbeat(connection_id)
            elif message.type == "join_room":
                await self.join_room(connection_id, message.data.get("room"))
            elif message.type == "leave_room":
                await self.leave_room(connection_id, message.data.get("room"))
            elif message.type == "authenticate":
                await self.authenticate_connection(connection_id, message.data.get("user_id"))
            else:
                logger.warning(f"Unknown message type: {message.type}")
                
        except json.JSONDecodeError:
            await self.send_error(connection_id, "Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.send_error(connection_id, str(e))
    
    async def handle_heartbeat(self, connection_id: str):
        """Обработка heartbeat пинга"""
        connection = self.connections.get(connection_id)
        if connection:
            connection.last_ping = datetime.now(timezone.utc)
            await self.send_to_connection(connection_id, WebSocketMessage(
                type=EventType.HEARTBEAT,
                data={"pong": True},
                timestamp=datetime.now(timezone.utc).isoformat()
            ))
    
    async def join_room(self, connection_id: str, room: str):
        """Присоединение к комнате"""
        if not room:
            await self.send_error(connection_id, "Room name is required")
            return
        
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        # Добавление в комнату
        if room not in self.rooms:
            self.rooms[room] = set()
        
        self.rooms[room].add(connection_id)
        connection.rooms.add(room)
        
        logger.info(f"Connection {connection_id} joined room {room}")
        
        # Отправка подтверждения
        await self.send_to_connection(connection_id, WebSocketMessage(
            type="room_joined",
            data={"room": room},
            timestamp=datetime.now(timezone.utc).isoformat()
        ))
    
    async def leave_room(self, connection_id: str, room: str):
        """Выход из комнаты"""
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        # Удаление из комнаты
        if room in self.rooms:
            self.rooms[room].discard(connection_id)
            if not self.rooms[room]:
                del self.rooms[room]
        
        connection.rooms.discard(room)
        
        logger.info(f"Connection {connection_id} left room {room}")
    
    async def authenticate_connection(self, connection_id: str, user_id: str):
        """Аутентификация подключения"""
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        connection.user_id = user_id
        
        # Автоматическое присоединение к пользовательской комнате
        await self.join_room(connection_id, f"user_{user_id}")
        
        logger.info(f"Connection {connection_id} authenticated as user {user_id}")
    
    async def disconnect_client(self, connection_id: str):
        """Отключение клиента"""
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        # Удаление из всех комнат
        for room in list(connection.rooms):
            await self.leave_room(connection_id, room)
        
        # Закрытие WebSocket
        try:
            if not connection.websocket.closed:
                await connection.websocket.close()
        except Exception as e:
            logger.error(f"Error closing websocket: {e}")
        
        # Удаление из списка подключений
        del self.connections[connection_id]
        self.stats["active_connections"] -= 1
        
        logger.info(f"🔌 Connection {connection_id} disconnected")
    
    async def send_to_connection(self, connection_id: str, message: WebSocketMessage):
        """Отправка сообщения конкретному подключению"""
        connection = self.connections.get(connection_id)
        if not connection or connection.websocket.closed:
            return False
        
        try:
            await connection.websocket.send(message.to_json())
            self.stats["messages_sent"] += 1
            return True
        except (ConnectionClosedError, ConnectionClosedOK):
            await self.disconnect_client(connection_id)
            return False
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            return False
    
    async def send_to_room(self, room: str, message: WebSocketMessage):
        """Отправка сообщения всем в комнате"""
        if room not in self.rooms:
            return 0
        
        message.room = room
        sent_count = 0
        
        # Отправка всем в комнате
        for connection_id in list(self.rooms[room]):
            if await self.send_to_connection(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    async def send_to_user(self, user_id: str, message: WebSocketMessage):
        """Отправка сообщения пользователю"""
        message.user_id = user_id
        return await self.send_to_room(f"user_{user_id}", message)
    
    async def broadcast(self, message: WebSocketMessage):
        """Отправка сообщения всем подключениям"""
        sent_count = 0
        
        for connection_id in list(self.connections.keys()):
            if await self.send_to_connection(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    async def send_error(self, connection_id: str, error_message: str):
        """Отправка сообщения об ошибке"""
        message = WebSocketMessage(
            type=EventType.ERROR,
            data={"error": error_message},
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        await self.send_to_connection(connection_id, message)
    
    # === BUSINESS LOGIC EVENTS ===
    
    async def notify_price_update(self, token_mint: str, price_data: Dict[str, Any]):
        """Уведомление об обновлении цены токена"""
        message = WebSocketMessage(
            type=EventType.PRICE_UPDATE,
            data={
                "token_mint": token_mint,
                **price_data
            },
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Отправка в комнату токена и глобальную комнату
        await self.send_to_room(f"token_{token_mint}", message)
        await self.send_to_room("global", message)
    
    async def notify_new_trade(self, trade_data: Dict[str, Any]):
        """Уведомление о новой торговой операции"""
        message = WebSocketMessage(
            type=EventType.NEW_TRADE,
            data=trade_data,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        token_mint = trade_data.get("token_mint")
        user_id = trade_data.get("user_id")
        
        # Отправка в различные комнаты
        if token_mint:
            await self.send_to_room(f"token_{token_mint}", message)
        if user_id:
            await self.send_to_user(user_id, message)
        await self.send_to_room("global", message)
    
    async def notify_token_created(self, token_data: Dict[str, Any]):
        """Уведомление о создании нового токена"""
        message = WebSocketMessage(
            type=EventType.TOKEN_CREATED,
            data=token_data,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        await self.broadcast(message)
    
    async def notify_portfolio_update(self, user_id: str, portfolio_data: Dict[str, Any]):
        """Уведомление об обновлении портфеля"""
        message = WebSocketMessage(
            type=EventType.PORTFOLIO_UPDATE,
            data=portfolio_data,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        await self.send_to_user(user_id, message)
    
    async def notify_market_stats(self, stats_data: Dict[str, Any]):
        """Уведомление об обновлении рыночной статистики"""
        message = WebSocketMessage(
            type=EventType.MARKET_STATS,
            data=stats_data,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        await self.send_to_room("global", message)
    
    # === BACKGROUND TASKS ===
    
    async def heartbeat_task(self):
        """Фоновая задача для поддержания соединений"""
        while self.is_running:
            try:
                current_time = datetime.now(timezone.utc)
                
                # Проверка неактивных подключений
                for connection_id, connection in list(self.connections.items()):
                    time_since_ping = (current_time - connection.last_ping).total_seconds()
                    
                    if time_since_ping > 120:  # 2 минуты без активности
                        logger.info(f"Disconnecting inactive connection: {connection_id}")
                        await self.disconnect_client(connection_id)
                
                await asyncio.sleep(30)  # Проверка каждые 30 секунд
                
            except Exception as e:
                logger.error(f"Error in heartbeat task: {e}")
                await asyncio.sleep(30)
    
    async def cleanup_task(self):
        """Фоновая задача для очистки ресурсов"""
        while self.is_running:
            try:
                # Очистка пустых комнат
                empty_rooms = [room for room, connections in self.rooms.items() if not connections]
                for room in empty_rooms:
                    del self.rooms[room]
                
                # Логирование статистики
                if self.stats["active_connections"] > 0:
                    logger.info(f"WebSocket Stats: {self.stats}")
                
                await asyncio.sleep(300)  # Каждые 5 минут
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(300)
    
    # === UTILITY METHODS ===
    
    def generate_connection_id(self) -> str:
        """Генерация уникального ID подключения"""
        import uuid
        return str(uuid.uuid4())
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики WebSocket сервера"""
        return {
            **self.stats,
            "rooms": {room: len(connections) for room, connections in self.rooms.items()},
            "connections_by_user": {
                conn.user_id: connection_id 
                for connection_id, conn in self.connections.items() 
                if conn.user_id
            }
        }
    
    def get_room_info(self, room: str) -> Dict[str, Any]:
        """Информация о комнате"""
        if room not in self.rooms:
            return {"exists": False}
        
        connections = self.rooms[room]
        users = [
            self.connections[conn_id].user_id 
            for conn_id in connections 
            if self.connections[conn_id].user_id
        ]
        
        return {
            "exists": True,
            "connection_count": len(connections),
            "user_count": len([u for u in users if u]),
            "users": list(set(users))
        }


# Глобальный экземпляр WebSocket менеджера
websocket_manager = WebSocketManager()


# События жизненного цикла для FastAPI
async def startup_websocket_service():
    """Запуск WebSocket сервиса"""
    if WEBSOCKETS_AVAILABLE:
        await websocket_manager.start_server(
            host=settings.WEBSOCKET_HOST,
            port=settings.WEBSOCKET_PORT
        )
    else:
        logger.warning("⚠️ WebSockets not available, real-time features disabled")


async def shutdown_websocket_service():
    """Остановка WebSocket сервиса"""
    await websocket_manager.stop_server()


# Dependency функция для FastAPI
def get_websocket_manager() -> WebSocketManager:
    """Dependency для получения WebSocket менеджера"""
    return websocket_manager


# Экспорт основных компонентов
__all__ = [
    'WebSocketManager',
    'WebSocketMessage',
    'EventType',
    'websocket_manager',
    'get_websocket_manager',
    'startup_websocket_service',
    'shutdown_websocket_service',
    'WEBSOCKETS_AVAILABLE'
]