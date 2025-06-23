#!/usr/bin/env python3
"""
🔌 WebSocket роуты для real-time обновлений
Обработка WebSocket подключений через FastAPI
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.websockets import WebSocketState

from ..services.websocket import get_websocket_manager, WebSocketManager, WebSocketMessage, EventType
from ..core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None,
    room: Optional[str] = None,
    user_id: Optional[str] = None,
    ws_manager: WebSocketManager = Depends(get_websocket_manager)
):
    """
    WebSocket endpoint для real-time соединений
    
    Параметры:
    - token: JWT токен для аутентификации (опционально)
    - room: Комната для автоматического присоединения
    - user_id: ID пользователя для аутентификации
    """
    # Принятие WebSocket соединения
    await websocket.accept()
    
    connection_id = ws_manager.generate_connection_id()
    logger.info(f"🔌 WebSocket подключение принято: {connection_id}")
    
    try:
        # Регистрация подключения в менеджере
        from ..services.websocket import ConnectionInfo
        connection = ConnectionInfo(websocket=websocket)
        ws_manager.connections[connection_id] = connection
        ws_manager.stats["total_connections"] += 1
        ws_manager.stats["active_connections"] += 1
        
        # Аутентификация пользователя если передан user_id
        if user_id:
            connection.user_id = user_id
            await ws_manager.join_room(connection_id, f"user_{user_id}")
            logger.info(f"WebSocket {connection_id} аутентифицирован как пользователь {user_id}")
        
        # Автоматическое присоединение к комнате
        if room:
            await ws_manager.join_room(connection_id, room)
        
        # Присоединение к глобальной комнате для общих уведомлений
        await ws_manager.join_room(connection_id, "global")
        
        # Отправка приветственного сообщения
        welcome_message = WebSocketMessage(
            type=EventType.USER_CONNECTED,
            data={
                "connection_id": connection_id,
                "user_id": user_id,
                "joined_rooms": list(connection.rooms),
                "server_time": datetime.now(timezone.utc).isoformat(),
                "message": "🎉 Добро пожаловать в Anonymeme real-time!"
            },
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        await websocket.send_text(welcome_message.to_json())
        
        # Основной цикл обработки сообщений
        while True:
            try:
                # Получение сообщения от клиента
                data = await websocket.receive_text()
                
                # Обновление времени последней активности
                connection.last_ping = datetime.now(timezone.utc)
                
                # Парсинг и обработка сообщения
                try:
                    message_data = json.loads(data)
                    message_type = message_data.get("type")
                    message_payload = message_data.get("data", {})
                    
                    # Обработка различных типов сообщений
                    if message_type == "heartbeat":
                        # Ответ на heartbeat
                        pong_message = WebSocketMessage(
                            type=EventType.HEARTBEAT,
                            data={"pong": True, "server_time": datetime.now(timezone.utc).isoformat()},
                            timestamp=datetime.now(timezone.utc).isoformat()
                        )
                        await websocket.send_text(pong_message.to_json())
                        
                    elif message_type == "join_room":
                        # Присоединение к комнате
                        room_name = message_payload.get("room")
                        if room_name:
                            await ws_manager.join_room(connection_id, room_name)
                            
                            response = WebSocketMessage(
                                type="room_joined",
                                data={"room": room_name, "success": True},
                                timestamp=datetime.now(timezone.utc).isoformat()
                            )
                            await websocket.send_text(response.to_json())
                        
                    elif message_type == "leave_room":
                        # Выход из комнаты
                        room_name = message_payload.get("room")
                        if room_name:
                            await ws_manager.leave_room(connection_id, room_name)
                            
                            response = WebSocketMessage(
                                type="room_left",
                                data={"room": room_name, "success": True},
                                timestamp=datetime.now(timezone.utc).isoformat()
                            )
                            await websocket.send_text(response.to_json())
                    
                    elif message_type == "subscribe":
                        # Подписка на события токена/пользователя
                        subscribe_to = message_payload.get("subscribe_to")
                        if subscribe_to:
                            # Подписка на обновления конкретного токена
                            if subscribe_to.startswith("token_"):
                                await ws_manager.join_room(connection_id, subscribe_to)
                            # Подписка на обновления пользователя
                            elif subscribe_to.startswith("user_"):
                                if connection.user_id:  # Только аутентифицированные пользователи
                                    await ws_manager.join_room(connection_id, subscribe_to)
                            
                            response = WebSocketMessage(
                                type="subscribed",
                                data={"subscription": subscribe_to, "success": True},
                                timestamp=datetime.now(timezone.utc).isoformat()
                            )
                            await websocket.send_text(response.to_json())
                    
                    elif message_type == "get_room_info":
                        # Получение информации о комнате
                        room_name = message_payload.get("room")
                        if room_name:
                            room_info = ws_manager.get_room_info(room_name)
                            response = WebSocketMessage(
                                type="room_info",
                                data={"room": room_name, "info": room_info},
                                timestamp=datetime.now(timezone.utc).isoformat()
                            )
                            await websocket.send_text(response.to_json())
                    
                    else:
                        # Неизвестный тип сообщения
                        error_response = WebSocketMessage(
                            type=EventType.ERROR,
                            data={"error": f"Неизвестный тип сообщения: {message_type}"},
                            timestamp=datetime.now(timezone.utc).isoformat()
                        )
                        await websocket.send_text(error_response.to_json())
                        
                except json.JSONDecodeError:
                    # Ошибка парсинга JSON
                    error_response = WebSocketMessage(
                        type=EventType.ERROR,
                        data={"error": "Неверный формат JSON"},
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
                    await websocket.send_text(error_response.to_json())
                    
                except Exception as e:
                    logger.error(f"Ошибка обработки сообщения от {connection_id}: {e}")
                    error_response = WebSocketMessage(
                        type=EventType.ERROR,
                        data={"error": f"Ошибка обработки сообщения: {str(e)}"},
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
                    await websocket.send_text(error_response.to_json())
                
            except WebSocketDisconnect:
                logger.info(f"🔌 WebSocket {connection_id} отключен клиентом")
                break
                
            except Exception as e:
                logger.error(f"❌ Ошибка в WebSocket цикле {connection_id}: {e}")
                break
    
    except Exception as e:
        logger.error(f"❌ Критическая ошибка WebSocket {connection_id}: {e}")
    
    finally:
        # Очистка при отключении
        await cleanup_connection(connection_id, ws_manager)


async def cleanup_connection(connection_id: str, ws_manager: WebSocketManager):
    """Очистка ресурсов при отключении WebSocket"""
    try:
        connection = ws_manager.connections.get(connection_id)
        if not connection:
            return
        
        # Отправка уведомления об отключении
        disconnect_message = WebSocketMessage(
            type=EventType.USER_DISCONNECTED,
            data={
                "connection_id": connection_id,
                "user_id": connection.user_id,
                "disconnect_time": datetime.now(timezone.utc).isoformat()
            },
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Уведомление всех комнат о отключении пользователя
        for room in list(connection.rooms):
            if room != f"user_{connection.user_id}":  # Не уведомляем личную комнату
                await ws_manager.send_to_room(room, disconnect_message)
        
        # Удаление из всех комнат
        for room in list(connection.rooms):
            await ws_manager.leave_room(connection_id, room)
        
        # Закрытие WebSocket если еще открыт
        if connection.websocket.client_state == WebSocketState.CONNECTED:
            await connection.websocket.close()
        
        # Удаление из списка подключений
        if connection_id in ws_manager.connections:
            del ws_manager.connections[connection_id]
            ws_manager.stats["active_connections"] -= 1
        
        logger.info(f"✅ WebSocket {connection_id} очищен")
        
    except Exception as e:
        logger.error(f"❌ Ошибка очистки WebSocket {connection_id}: {e}")


@router.get("/ws/stats")
async def get_websocket_stats(
    ws_manager: WebSocketManager = Depends(get_websocket_manager)
):
    """
    Получение статистики WebSocket сервера
    Полезно для мониторинга и отладки
    """
    try:
        stats = ws_manager.get_stats()
        
        return {
            "success": True,
            "data": {
                "websocket_stats": stats,
                "server_info": {
                    "is_running": ws_manager.is_running,
                    "max_connections": settings.WEBSOCKET_MAX_CONNECTIONS,
                    "server_time": datetime.now(timezone.utc).isoformat()
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения WebSocket статистики: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось получить статистику WebSocket"
        )


@router.get("/ws/rooms/{room_name}")
async def get_room_info(
    room_name: str,
    ws_manager: WebSocketManager = Depends(get_websocket_manager)
):
    """
    Получение информации о конкретной WebSocket комнате
    """
    try:
        room_info = ws_manager.get_room_info(room_name)
        
        return {
            "success": True,
            "data": {
                "room_name": room_name,
                "room_info": room_info
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения информации о комнате {room_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось получить информацию о комнате"
        )


@router.post("/ws/broadcast")
async def broadcast_message(
    message_type: str,
    data: Dict[str, Any],
    room: Optional[str] = None,
    user_id: Optional[str] = None,
    ws_manager: WebSocketManager = Depends(get_websocket_manager)
):
    """
    API endpoint для отправки сообщений через WebSocket
    Используется внутренними сервисами для уведомлений
    """
    try:
        message = WebSocketMessage(
            type=message_type,
            data=data,
            timestamp=datetime.now(timezone.utc).isoformat(),
            room=room,
            user_id=user_id
        )
        
        sent_count = 0
        
        if user_id:
            # Отправка конкретному пользователю
            sent_count = await ws_manager.send_to_user(user_id, message)
        elif room:
            # Отправка в комнату
            sent_count = await ws_manager.send_to_room(room, message)
        else:
            # Отправка всем
            sent_count = await ws_manager.broadcast(message)
        
        return {
            "success": True,
            "data": {
                "message_sent": True,
                "recipients_count": sent_count,
                "message_type": message_type,
                "target": user_id or room or "all"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка отправки WebSocket сообщения: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось отправить сообщение"
        )