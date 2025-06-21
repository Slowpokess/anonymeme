#!/usr/bin/env python3
"""
📝 Logging Middleware для Anonymeme API
Production-ready structured logging с корреляцией запросов
"""

import time
import json
import uuid
import logging
import traceback
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from ..core.config import settings

# Настройка structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Production-ready middleware для структурированного логирования
    Обеспечивает трейсинг запросов, метрики производительности и аудит
    """
    
    def __init__(self, app):
        super().__init__(app)
        
        # Счетчики для метрик
        self.request_count = 0
        self.error_count = 0
        self.total_duration = 0.0
        
        # Пути которые не нужно логировать детально
        self.exclude_detailed_logging = {
            "/health",
            "/metrics", 
            "/favicon.ico",
            "/robots.txt"
        }
        
        # Чувствительные поля для маскировки
        self.sensitive_fields = {
            "password", "token", "secret", "key", "private",
            "authorization", "cookie", "session"
        }
        
        logger.info("Logging middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """Основная логика middleware"""
        
        # Генерация уникального ID запроса
        request_id = str(uuid.uuid4())
        correlation_id = request.headers.get("x-correlation-id", request_id)
        
        # Добавление ID в request state
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        
        # Время начала обработки
        start_time = time.time()
        
        # Логирование входящего запроса
        await self._log_request_start(request, request_id, correlation_id)
        
        try:
            # Выполнение запроса
            response = await call_next(request)
            
            # Время выполнения
            duration = time.time() - start_time
            
            # Логирование завершения запроса
            await self._log_request_end(
                request, response, request_id, correlation_id, duration
            )
            
            # Добавление headers для трейсинга
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id
            
            # Обновление метрик
            self._update_metrics(duration, response.status_code)
            
            return response
            
        except Exception as e:
            # Время выполнения до ошибки
            duration = time.time() - start_time
            
            # Логирование ошибки
            await self._log_request_error(
                request, e, request_id, correlation_id, duration
            )
            
            # Обновление метрик ошибок
            self.error_count += 1
            
            # Пробрасывание ошибки дальше
            raise
    
    async def _log_request_start(
        self, 
        request: Request, 
        request_id: str, 
        correlation_id: str
    ):
        """Логирование начала обработки запроса"""
        
        # Базовая информация о запросе
        log_data = {
            "event": "request_start",
            "request_id": request_id,
            "correlation_id": correlation_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "referer": request.headers.get("referer", ""),
            "content_type": request.headers.get("content-type", ""),
            "content_length": request.headers.get("content-length", "0"),
        }
        
        # Добавление информации о пользователе если доступна
        if hasattr(request.state, "user_id"):
            log_data.update({
                "user_id": request.state.user_id,
                "wallet_address": getattr(request.state, "wallet_address", ""),
                "user_role": getattr(request.state, "role", "")
            })
        
        # Логирование заголовков (с маскировкой чувствительных данных)
        if request.url.path not in self.exclude_detailed_logging:
            log_data["headers"] = self._mask_sensitive_data(dict(request.headers))
        
        logger.info("Incoming request", **log_data)
        
        # Специальное логирование для критических операций
        if self._is_critical_operation(request):
            await self._log_critical_operation(request, log_data)
    
    async def _log_request_end(
        self,
        request: Request,
        response: Response, 
        request_id: str,
        correlation_id: str,
        duration: float
    ):
        """Логирование завершения обработки запроса"""
        
        log_data = {
            "event": "request_end",
            "request_id": request_id,
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "response_size": len(response.body) if hasattr(response, 'body') else 0,
        }
        
        # Добавление информации о пользователе
        if hasattr(request.state, "user_id"):
            log_data["user_id"] = request.state.user_id
        
        # Определение уровня логирования по статус коду
        if response.status_code >= 500:
            log_level = "error"
        elif response.status_code >= 400:
            log_level = "warning"
        elif duration > 5.0:  # Медленные запросы
            log_level = "warning"
            log_data["slow_request"] = True
        else:
            log_level = "info"
        
        # Логирование с соответствующим уровнем
        getattr(logger, log_level)("Request completed", **log_data)
        
        # Дополнительная аналитика для торговых операций
        if request.url.path.startswith("/api/v1/trading/"):
            await self._log_trading_analytics(request, response, log_data)
    
    async def _log_request_error(
        self,
        request: Request,
        exception: Exception,
        request_id: str,
        correlation_id: str,
        duration: float
    ):
        """Логирование ошибок обработки запроса"""
        
        log_data = {
            "event": "request_error",
            "request_id": request_id,
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "duration_ms": round(duration * 1000, 2),
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "traceback": traceback.format_exc(),
        }
        
        # Добавление информации о пользователе
        if hasattr(request.state, "user_id"):
            log_data["user_id"] = request.state.user_id
        
        # Добавление контекста запроса для критических ошибок
        if isinstance(exception, (ValueError, TypeError, KeyError)):
            log_data["request_body"] = await self._get_safe_request_body(request)
            log_data["query_params"] = dict(request.query_params)
        
        logger.error("Request failed with exception", **log_data)
        
        # Отправка алерта для критических ошибок
        await self._send_error_alert(exception, log_data)
    
    async def _log_critical_operation(self, request: Request, base_log_data: Dict):
        """Специальное логирование критических операций"""
        
        operation_type = "unknown"
        
        if request.url.path.startswith("/api/v1/trading/"):
            operation_type = "trading"
        elif "/create" in request.url.path:
            operation_type = "token_creation"
        elif request.url.path.startswith("/api/v1/admin/"):
            operation_type = "admin_action"
        
        log_data = {
            **base_log_data,
            "event": "critical_operation",
            "operation_type": operation_type,
            "requires_audit": True,
        }
        
        # Получение тела запроса для аудита
        if request.method in ["POST", "PUT", "PATCH"]:
            log_data["request_body"] = await self._get_safe_request_body(request)
        
        logger.warning("Critical operation initiated", **log_data)
    
    async def _log_trading_analytics(
        self, 
        request: Request, 
        response: Response, 
        base_log_data: Dict
    ):
        """Аналитическое логирование торговых операций"""
        
        if response.status_code != 200:
            return
        
        try:
            # Попытка извлечь данные о торговле из ответа
            # В реальной реализации здесь будет парсинг response body
            
            analytics_data = {
                **base_log_data,
                "event": "trading_analytics",
                "trading_endpoint": request.url.path.split('/')[-1],
                "success": True,
            }
            
            # Если это POST запрос, добавляем данные из тела запроса
            if request.method == "POST":
                request_body = await self._get_safe_request_body(request)
                if request_body and isinstance(request_body, dict):
                    analytics_data.update({
                        "sol_amount": request_body.get("sol_amount"),
                        "token_amount": request_body.get("token_amount"),
                        "slippage_tolerance": request_body.get("slippage_tolerance"),
                    })
            
            logger.info("Trading operation analytics", **analytics_data)
            
        except Exception as e:
            logger.error(f"Failed to log trading analytics: {e}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Получение IP адреса клиента"""
        # Проверяем заголовки прокси
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else "unknown"
    
    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Маскировка чувствительных данных"""
        masked_data = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            
            # Проверка на чувствительные поля
            if any(sensitive in key_lower for sensitive in self.sensitive_fields):
                if isinstance(value, str) and len(value) > 8:
                    masked_data[key] = f"{value[:4]}...{value[-4:]}"
                else:
                    masked_data[key] = "***MASKED***"
            else:
                masked_data[key] = value
        
        return masked_data
    
    async def _get_safe_request_body(self, request: Request) -> Optional[Dict[str, Any]]:
        """Безопасное получение тела запроса"""
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                # Попытка получить JSON
                body = await request.json()
                
                # Маскировка чувствительных данных
                if isinstance(body, dict):
                    return self._mask_sensitive_data(body)
                return body
        except Exception:
            # Если не удалось распарсить JSON, возвращаем None
            pass
        
        return None
    
    def _is_critical_operation(self, request: Request) -> bool:
        """Проверка является ли операция критической"""
        critical_paths = [
            "/api/v1/trading/",
            "/api/v1/tokens/create",
            "/api/v1/admin/",
            "/api/v1/users/profile"  # Изменение профиля
        ]
        
        return any(request.url.path.startswith(path) for path in critical_paths)
    
    def _update_metrics(self, duration: float, status_code: int):
        """Обновление метрик производительности"""
        self.request_count += 1
        self.total_duration += duration
        
        # Счетчик ошибок
        if status_code >= 400:
            self.error_count += 1
    
    async def _send_error_alert(self, exception: Exception, log_data: Dict):
        """Отправка алертов для критических ошибок"""
        
        # Критические ошибки требующие немедленного внимания
        critical_exceptions = [
            "DatabaseException",
            "BlockchainException", 
            "SecurityException",
            "InternalServerError"
        ]
        
        if type(exception).__name__ in critical_exceptions:
            # В продакшене здесь будет интеграция с системой алертов
            # (Slack, PagerDuty, email и т.д.)
            logger.critical("Critical error alert", alert=True, **log_data)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получение метрик логирования"""
        avg_duration = (
            self.total_duration / self.request_count 
            if self.request_count > 0 
            else 0
        )
        
        error_rate = (
            (self.error_count / self.request_count) * 100 
            if self.request_count > 0 
            else 0
        )
        
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate_percent": round(error_rate, 2),
            "average_duration_ms": round(avg_duration * 1000, 2),
            "total_duration_seconds": round(self.total_duration, 2),
        }
    
    def reset_metrics(self):
        """Сброс метрик (для тестов или периодической очистки)"""
        self.request_count = 0
        self.error_count = 0
        self.total_duration = 0.0
        
        logger.info("Logging metrics reset")


# === ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ ===

class AuditLogger:
    """Специальный логгер для аудита критических операций"""
    
    def __init__(self):
        self.audit_logger = structlog.get_logger("audit")
    
    async def log_user_action(
        self,
        user_id: str,
        action: str,
        resource: str,
        details: Dict[str, Any],
        request_id: str
    ):
        """Логирование действий пользователя"""
        
        audit_data = {
            "event": "user_action",
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "details": details,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.audit_logger.info("User action audit", **audit_data)
    
    async def log_admin_action(
        self,
        admin_id: str,
        action: str,
        target: str,
        changes: Dict[str, Any],
        request_id: str
    ):
        """Логирование административных действий"""
        
        audit_data = {
            "event": "admin_action",
            "admin_id": admin_id,
            "action": action,
            "target": target,
            "changes": changes,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "severity": "high"
        }
        
        self.audit_logger.warning("Admin action audit", **audit_data)
    
    async def log_security_event(
        self,
        event_type: str,
        source_ip: str,
        details: Dict[str, Any],
        severity: str = "medium"
    ):
        """Логирование событий безопасности"""
        
        security_data = {
            "event": "security_event",
            "event_type": event_type,
            "source_ip": source_ip,
            "details": details,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        log_level = "error" if severity == "high" else "warning"
        getattr(self.audit_logger, log_level)("Security event", **security_data)


# Глобальный экземпляр аудит логгера
audit_logger = AuditLogger()


# === ДЕКОРАТОРЫ ДЛЯ ЛОГИРОВАНИЯ ===

def log_function_call(
    logger_name: Optional[str] = None,
    log_args: bool = True,
    log_result: bool = False,
    mask_sensitive: bool = True
):
    """
    Декоратор для логирования вызовов функций
    """
    def decorator(func):
        func_logger = structlog.get_logger(logger_name or func.__module__)
        
        async def async_wrapper(*args, **kwargs):
            func_name = func.__name__
            
            log_data = {
                "function": func_name,
                "event": "function_call_start"
            }
            
            if log_args:
                log_data["args"] = args[1:] if args else []  # Исключаем self
                log_data["kwargs"] = kwargs
            
            func_logger.debug("Function call started", **log_data)
            
            start_time = time.time()
            
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                duration = time.time() - start_time
                
                log_data.update({
                    "event": "function_call_end",
                    "duration_ms": round(duration * 1000, 2),
                    "success": True
                })
                
                if log_result and result is not None:
                    log_data["result"] = result
                
                func_logger.debug("Function call completed", **log_data)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                log_data.update({
                    "event": "function_call_error",
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                
                func_logger.error("Function call failed", **log_data)
                raise
        
        def sync_wrapper(*args, **kwargs):
            # Синхронная версия wrapper'а
            func_logger = structlog.get_logger(logger_name or func.__module__)
            
            log_data = {
                "function": func.__name__,
                "event": "function_call_start"
            }
            
            func_logger.debug("Function call started", **log_data)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                log_data.update({
                    "event": "function_call_end",
                    "duration_ms": round(duration * 1000, 2),
                    "success": True
                })
                
                func_logger.debug("Function call completed", **log_data)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                log_data.update({
                    "event": "function_call_error", 
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e)
                })
                
                func_logger.error("Function call failed", **log_data)
                raise
        
        import asyncio
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator