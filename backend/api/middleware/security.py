#!/usr/bin/env python3
"""
🛡️ Security Middleware для Anonymeme API
Production-ready безопасность с расширенной защитой
"""

import time
import logging
import secrets
import hashlib
from typing import Dict, Set, Optional, Tuple
from datetime import datetime, timedelta
from ipaddress import ip_address, ip_network
import re

from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import jwt

from ..core.config import settings
from ..core.exceptions import (
    RateLimitException, SecurityException, BotActivityException,
    SuspiciousActivityException, AuthenticationException
)

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Комплексный middleware безопасности
    Включает rate limiting, bot detection, IP filtering, и другие защитные механизмы
    """
    
    def __init__(self, app):
        super().__init__(app)
        
        # Rate limiting storage (в продакшене использовать Redis)
        self.rate_limit_storage: Dict[str, Dict] = {}
        
        # Подозрительные IP адреса
        self.suspicious_ips: Set[str] = set()
        
        # Заблокированные IP
        self.blocked_ips: Set[str] = set()
        
        # Whitelist IP сетей (для админов)
        self.admin_networks = [
            ip_network("127.0.0.0/8"),    # localhost
            ip_network("10.0.0.0/8"),     # private
            ip_network("172.16.0.0/12"),  # private
            ip_network("192.168.0.0/16"), # private
        ]
        
        # Регулярные выражения для детекции ботов
        self.bot_patterns = [
            re.compile(r'bot|crawler|spider|scraper', re.IGNORECASE),
            re.compile(r'curl|wget|python-requests|http', re.IGNORECASE),
            re.compile(r'headless|phantom|selenium|puppeteer', re.IGNORECASE),
        ]
        
        # Паттерны подозрительных запросов
        self.attack_patterns = [
            re.compile(r'\.\./', re.IGNORECASE),  # Path traversal
            re.compile(r'<script|javascript:|data:', re.IGNORECASE),  # XSS
            re.compile(r'union.*select|drop.*table|insert.*into', re.IGNORECASE),  # SQL injection
            re.compile(r'exec\(|eval\(|system\(', re.IGNORECASE),  # Code injection
        ]
        
        # Защищенные endpoints (требуют аутентификации)
        self.protected_paths = {
            '/api/v1/trading/',
            '/api/v1/tokens/create',
            '/api/v1/users/profile',
            '/api/v1/admin/',
        }
        
        # Public endpoints (без аутентификации)
        self.public_paths = {
            '/api/v1/tokens',
            '/api/v1/analytics',
            '/health',
            '/metrics',
            '/docs',
            '/redoc',
        }
        
        logger.info("Security middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """Основная логика middleware"""
        start_time = time.time()
        
        try:
            # 1. Базовые проверки безопасности
            await self._check_request_security(request)
            
            # 2. IP фильтрация
            client_ip = self._get_client_ip(request)
            await self._check_ip_security(client_ip, request)
            
            # 3. Rate limiting
            await self._check_rate_limits(request, client_ip)
            
            # 4. Bot detection
            await self._check_bot_activity(request)
            
            # 5. Проверка аутентификации для защищенных endpoints
            await self._check_authentication(request)
            
            # 6. Добавление security headers
            response = await call_next(request)
            self._add_security_headers(response)
            
            # 7. Логирование запроса
            await self._log_request(request, response, time.time() - start_time)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Security check failed"
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Получение реального IP клиента"""
        # Проверяем заголовки прокси
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Берем первый IP из списка
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fallback на direct connection
        return request.client.host if request.client else "unknown"
    
    async def _check_request_security(self, request: Request):
        """Базовые проверки безопасности запроса"""
        
        # Проверка размера запроса
        content_length = request.headers.get("content-length")
        if content_length:
            length = int(content_length)
            if length > 10 * 1024 * 1024:  # 10MB лимит
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Request too large"
                )
        
        # Проверка на атакующие паттерны в URL
        url_str = str(request.url)
        for pattern in self.attack_patterns:
            if pattern.search(url_str):
                logger.warning(f"Attack pattern detected in URL: {url_str}")
                raise SecurityException(
                    "Suspicious request pattern detected",
                    error_code="ATTACK_PATTERN"
                )
        
        # Проверка User-Agent
        user_agent = request.headers.get("user-agent", "")
        if not user_agent or len(user_agent) < 10:
            raise SecurityException(
                "Invalid or missing User-Agent",
                error_code="INVALID_USER_AGENT"
            )
        
        # Проверка на подозрительные заголовки
        suspicious_headers = {
            "x-forwarded-host", "x-forwarded-server", "x-forwarded-proto"
        }
        for header in suspicious_headers:
            if header in request.headers:
                value = request.headers[header]
                if any(pattern.search(value) for pattern in self.attack_patterns):
                    raise SecurityException(
                        f"Suspicious header: {header}",
                        error_code="SUSPICIOUS_HEADER"
                    )
    
    async def _check_ip_security(self, client_ip: str, request: Request):
        """Проверка безопасности IP адреса"""
        
        # Проверка заблокированных IP
        if client_ip in self.blocked_ips:
            logger.warning(f"Blocked IP attempted access: {client_ip}")
            raise SecurityException(
                "Access denied from this IP address",
                error_code="IP_BLOCKED"
            )
        
        try:
            ip_obj = ip_address(client_ip)
        except ValueError:
            logger.warning(f"Invalid IP address: {client_ip}")
            raise SecurityException(
                "Invalid IP address",
                error_code="INVALID_IP"
            )
        
        # Проверка на локальные/приватные адреса в продакшене
        if settings.is_production and ip_obj.is_private:
            logger.warning(f"Private IP in production: {client_ip}")
            raise SecurityException(
                "Private IP not allowed in production",
                error_code="PRIVATE_IP"
            )
        
        # Дополнительные проверки для подозрительных IP
        if client_ip in self.suspicious_ips:
            # Более строгие лимиты для подозрительных IP
            await self._apply_strict_rate_limits(request, client_ip)
    
    async def _check_rate_limits(self, request: Request, client_ip: str):
        """Проверка rate limiting"""
        
        # Определение лимитов в зависимости от endpoint
        path = request.url.path
        
        if path.startswith("/api/v1/trading/"):
            # Строгие лимиты для торговых операций
            limit = 10  # 10 запросов в минуту
            window = 60
        elif path.startswith("/api/v1/tokens/create"):
            # Очень строгие лимиты для создания токенов
            limit = 3   # 3 токена в час
            window = 3600
        elif path.startswith("/api/v1/admin/"):
            # Лимиты для админ операций
            limit = 100
            window = 3600
        else:
            # Обычные API запросы
            limit = settings.RATE_LIMIT_REQUESTS
            window = settings.RATE_LIMIT_WINDOW
        
        # Ключ для rate limiting (IP + endpoint type)
        rate_key = f"{client_ip}:{path.split('/')[3] if len(path.split('/')) > 3 else 'general'}"
        
        current_time = int(time.time())
        window_start = current_time - (current_time % window)
        
        # Инициализация данных для IP
        if rate_key not in self.rate_limit_storage:
            self.rate_limit_storage[rate_key] = {
                "requests": [],
                "window_start": window_start
            }
        
        rate_data = self.rate_limit_storage[rate_key]
        
        # Очистка старых запросов
        rate_data["requests"] = [
            req_time for req_time in rate_data["requests"]
            if req_time >= window_start
        ]
        
        # Проверка лимита
        if len(rate_data["requests"]) >= limit:
            logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
            
            # Добавление IP в подозрительные при превышении лимитов
            self.suspicious_ips.add(client_ip)
            
            raise RateLimitException(
                detail=f"Rate limit exceeded. Max {limit} requests per {window} seconds.",
                retry_after=window - (current_time % window)
            )
        
        # Добавление текущего запроса
        rate_data["requests"].append(current_time)
        rate_data["window_start"] = window_start
    
    async def _apply_strict_rate_limits(self, request: Request, client_ip: str):
        """Применение строгих лимитов для подозрительных IP"""
        rate_key = f"strict:{client_ip}"
        limit = 5   # Только 5 запросов в минуту
        window = 60
        
        current_time = int(time.time())
        
        if rate_key not in self.rate_limit_storage:
            self.rate_limit_storage[rate_key] = {"requests": []}
        
        # Очистка старых запросов
        self.rate_limit_storage[rate_key]["requests"] = [
            req_time for req_time in self.rate_limit_storage[rate_key]["requests"]
            if req_time >= current_time - window
        ]
        
        if len(self.rate_limit_storage[rate_key]["requests"]) >= limit:
            # Блокировка IP при повторном нарушении
            self.blocked_ips.add(client_ip)
            logger.warning(f"IP {client_ip} blocked due to repeated violations")
            
            raise SecurityException(
                "IP blocked due to suspicious activity",
                error_code="IP_BLOCKED"
            )
        
        self.rate_limit_storage[rate_key]["requests"].append(current_time)
    
    async def _check_bot_activity(self, request: Request):
        """Детекция ботов и автоматизированных запросов"""
        
        user_agent = request.headers.get("user-agent", "")
        
        # Проверка на известные боты
        for pattern in self.bot_patterns:
            if pattern.search(user_agent):
                logger.info(f"Bot detected: {user_agent}")
                
                # Для некоторых ботов (например, поисковых) разрешаем доступ
                if any(bot in user_agent.lower() for bot in ['googlebot', 'bingbot']):
                    return
                
                raise BotActivityException()
        
        # Проверка на отсутствие стандартных браузерных заголовков
        browser_headers = ["accept", "accept-language", "accept-encoding"]
        missing_headers = [h for h in browser_headers if h not in request.headers]
        
        if len(missing_headers) >= 2:
            logger.warning(f"Possible bot - missing headers: {missing_headers}")
            raise BotActivityException()
        
        # Проверка на подозрительно быстрые запросы
        client_ip = self._get_client_ip(request)
        await self._check_request_timing(client_ip)
    
    async def _check_request_timing(self, client_ip: str):
        """Проверка времени между запросами"""
        timing_key = f"timing:{client_ip}"
        current_time = time.time()
        
        if timing_key in self.rate_limit_storage:
            last_request = self.rate_limit_storage[timing_key].get("last_request", 0)
            
            # Если запросы идут чаще чем каждые 100ms - подозрительно
            if current_time - last_request < 0.1:
                consecutive_fast = self.rate_limit_storage[timing_key].get("consecutive_fast", 0) + 1
                self.rate_limit_storage[timing_key]["consecutive_fast"] = consecutive_fast
                
                if consecutive_fast > 5:  # 5 быстрых запросов подряд
                    logger.warning(f"Suspicious fast requests from {client_ip}")
                    self.suspicious_ips.add(client_ip)
                    raise SuspiciousActivityException("fast_requests")
            else:
                self.rate_limit_storage[timing_key]["consecutive_fast"] = 0
        else:
            self.rate_limit_storage[timing_key] = {}
        
        self.rate_limit_storage[timing_key]["last_request"] = current_time
    
    async def _check_authentication(self, request: Request):
        """Проверка аутентификации для защищенных endpoints"""
        
        path = request.url.path
        
        # Проверка, требует ли endpoint аутентификации
        requires_auth = any(path.startswith(protected) for protected in self.protected_paths)
        
        if not requires_auth:
            return
        
        # Получение токена авторизации
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise AuthenticationException("Missing or invalid authorization token")
        
        token = auth_header.split(" ")[1]
        
        try:
            # Валидация JWT токена
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
            
            # Проверка срока действия
            exp = payload.get("exp")
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                raise AuthenticationException("Token expired")
            
            # Добавление пользователя в request state
            request.state.user_id = payload.get("user_id")
            request.state.wallet_address = payload.get("wallet_address")
            request.state.role = payload.get("role", "user")
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            raise AuthenticationException("Invalid token")
    
    def _add_security_headers(self, response: Response):
        """Добавление security headers в ответ"""
        
        # Основные security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS для HTTPS
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # CSP header
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "connect-src 'self' wss: https:",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # Rate limiting headers
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Window"] = str(settings.RATE_LIMIT_WINDOW)
        
        # API version
        response.headers["X-API-Version"] = settings.APP_VERSION
        
        # Request ID для трейсинга
        response.headers["X-Request-ID"] = secrets.token_urlsafe(16)
    
    async def _log_request(self, request: Request, response: Response, duration: float):
        """Логирование запроса"""
        
        client_ip = self._get_client_ip(request)
        
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "client_ip": client_ip,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "user_agent": request.headers.get("user-agent", ""),
            "user_id": getattr(request.state, "user_id", None),
        }
        
        # Логирование с разным уровнем в зависимости от статуса
        if response.status_code >= 500:
            logger.error("Request failed", extra=log_data)
        elif response.status_code >= 400:
            logger.warning("Request error", extra=log_data)
        else:
            logger.info("Request completed", extra=log_data)
    
    def add_suspicious_ip(self, ip: str):
        """Добавление IP в список подозрительных"""
        self.suspicious_ips.add(ip)
        logger.warning(f"IP {ip} marked as suspicious")
    
    def block_ip(self, ip: str):
        """Блокировка IP адреса"""
        self.blocked_ips.add(ip)
        logger.warning(f"IP {ip} blocked")
    
    def unblock_ip(self, ip: str):
        """Разблокировка IP адреса"""
        self.blocked_ips.discard(ip)
        self.suspicious_ips.discard(ip)
        logger.info(f"IP {ip} unblocked")
    
    def get_security_stats(self) -> Dict:
        """Получение статистики безопасности"""
        return {
            "blocked_ips_count": len(self.blocked_ips),
            "suspicious_ips_count": len(self.suspicious_ips),
            "rate_limit_entries": len(self.rate_limit_storage),
            "blocked_ips": list(self.blocked_ips),
            "suspicious_ips": list(self.suspicious_ips),
        }