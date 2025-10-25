#!/usr/bin/env python3
"""
🛡️ Enhanced Security Middleware для Anonymeme API
Advanced security measures beyond basic middleware
"""

import time
import logging
import hashlib
import secrets
import asyncio
from typing import Dict, Set, Optional, List, Tuple
from datetime import datetime, timedelta
from ipaddress import ip_address, ip_network
from collections import defaultdict, deque
import re
import geoip2.database
import user_agents

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import redis.asyncio as redis

from ..core.config import settings
from ..core.exceptions import (
    SecurityException, RateLimitException, BotActivityException,
    SuspiciousActivityException
)

logger = logging.getLogger(__name__)


class AdvancedSecurityMiddleware(BaseHTTPMiddleware):
    """
    Расширенный security middleware с AI-powered threat detection
    """
    
    def __init__(self, app):
        super().__init__(app)
        
        # Redis для distributed rate limiting и shared state
        self.redis_pool = None
        self._init_redis()
        
        # Advanced rate limiting с burst protection
        self.rate_limiters = {
            'trading': RateLimiter(10, 60, burst_limit=3),      # 10/min, burst 3
            'token_creation': RateLimiter(3, 3600, burst_limit=1),  # 3/hour, burst 1
            'admin': RateLimiter(100, 3600, burst_limit=20),     # 100/hour, burst 20
            'api': RateLimiter(1000, 3600, burst_limit=50),      # 1000/hour, burst 50
            'auth': RateLimiter(5, 300, burst_limit=2),          # 5/5min, burst 2
        }
        
        # Threat detection patterns
        self.threat_patterns = {
            'sql_injection': [
                re.compile(r"union\s+select", re.IGNORECASE),
                re.compile(r"drop\s+table", re.IGNORECASE),
                re.compile(r"insert\s+into", re.IGNORECASE),
                re.compile(r"delete\s+from", re.IGNORECASE),
                re.compile(r"'.*or.*'.*=.*'", re.IGNORECASE),
                re.compile(r"--\s", re.IGNORECASE),
            ],
            'xss': [
                re.compile(r"<script[^>]*>", re.IGNORECASE),
                re.compile(r"javascript:", re.IGNORECASE),
                re.compile(r"vbscript:", re.IGNORECASE),
                re.compile(r"onload\s*=", re.IGNORECASE),
                re.compile(r"onerror\s*=", re.IGNORECASE),
            ],
            'path_traversal': [
                re.compile(r"\.\./", re.IGNORECASE),
                re.compile(r"\.\.\\", re.IGNORECASE),
                re.compile(r"%2e%2e%2f", re.IGNORECASE),
                re.compile(r"%2e%2e/", re.IGNORECASE),
            ],
            'command_injection': [
                re.compile(r";\s*cat\s+", re.IGNORECASE),
                re.compile(r";\s*ls\s+", re.IGNORECASE),
                re.compile(r";\s*rm\s+", re.IGNORECASE),
                re.compile(r";\s*curl\s+", re.IGNORECASE),
                re.compile(r";\s*wget\s+", re.IGNORECASE),
            ]
        }
        
        # Behavioral analysis
        self.user_behaviors: Dict[str, UserBehavior] = {}
        
        # IP reputation и geolocation
        self.suspicious_countries = {'CN', 'RU', 'KP', 'IR'}  # Configurable
        self.blocked_asns: Set[int] = set()  # Blocked ASNs
        
        # Honeypot endpoints для bot detection
        self.honeypot_paths = {
            '/admin.php', '/wp-admin/', '/phpmyadmin/', 
            '/robots.txt', '/.env', '/config.php'
        }
        
        # DDoS protection
        self.connection_limits = defaultdict(lambda: ConnectionTracker())
        
        logger.info("Enhanced security middleware initialized")
    
    async def _init_redis(self):
        """Инициализация Redis connection pool"""
        try:
            self.redis_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=20,
                retry_on_timeout=True,
                decode_responses=True
            )
            logger.info("Redis pool initialized for security middleware")
        except Exception as e:
            logger.error(f"Failed to initialize Redis pool: {e}")
    
    async def dispatch(self, request: Request, call_next):
        """Main security middleware logic"""
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        
        try:
            # 1. Basic security checks
            await self._perform_basic_checks(request, client_ip)
            
            # 2. Advanced threat detection
            await self._detect_threats(request, client_ip)
            
            # 3. Rate limiting с adaptive limits
            await self._adaptive_rate_limiting(request, client_ip)
            
            # 4. Behavioral analysis
            await self._analyze_behavior(request, client_ip)
            
            # 5. Geolocation и reputation checks
            await self._check_ip_reputation(request, client_ip)
            
            # 6. DDoS protection
            await self._ddos_protection(request, client_ip)
            
            # Process request
            response = await call_next(request)
            
            # 7. Response analysis
            await self._analyze_response(request, response, client_ip)
            
            # 8. Security headers
            self._add_enhanced_security_headers(response)
            
            # 9. Audit logging
            await self._security_audit_log(request, response, client_ip, time.time() - start_time)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Enhanced security middleware error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Security processing failed"
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Enhanced IP extraction with validation"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP and validate
            ip = forwarded_for.split(",")[0].strip()
            try:
                ip_address(ip)  # Validate IP format
                return ip
            except ValueError:
                pass
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            try:
                ip_address(real_ip)
                return real_ip
            except ValueError:
                pass
        
        # Fallback
        return request.client.host if request.client else "unknown"
    
    async def _perform_basic_checks(self, request: Request, client_ip: str):
        """Enhanced basic security checks"""
        
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length:
            length = int(content_length)
            if length > 50 * 1024 * 1024:  # 50MB limit
                raise SecurityException("Request too large", "REQUEST_TOO_LARGE")
        
        # Check for missing essential headers
        user_agent = request.headers.get("user-agent", "")
        if not user_agent or len(user_agent) < 5:
            raise SecurityException("Invalid User-Agent", "INVALID_USER_AGENT")
        
        # Check for suspicious headers
        suspicious_headers = {
            'x-forwarded-host', 'x-forwarded-server', 'x-cluster-client-ip'
        }
        for header in suspicious_headers:
            if header in request.headers:
                value = request.headers[header]
                if self._contains_threat_patterns(value):
                    raise SecurityException(f"Malicious header: {header}", "MALICIOUS_HEADER")
        
        # Validate IP address
        try:
            ip_obj = ip_address(client_ip)
        except ValueError:
            raise SecurityException("Invalid IP address", "INVALID_IP")
        
        # Block private IPs in production
        if settings.is_production and ip_obj.is_private:
            raise SecurityException("Private IP not allowed", "PRIVATE_IP_BLOCKED")
    
    async def _detect_threats(self, request: Request, client_ip: str):
        """AI-powered threat detection"""
        
        # Analyze URL for threats
        url_str = str(request.url)
        threat_type = self._analyze_for_threats(url_str)
        if threat_type:
            await self._record_threat(client_ip, threat_type, url_str)
            raise SecurityException(f"Threat detected: {threat_type}", f"THREAT_{threat_type.upper()}")
        
        # Analyze request body for threats (if present)
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = await request.body()
                if body:
                    body_str = body.decode('utf-8', errors='ignore')
                    threat_type = self._analyze_for_threats(body_str)
                    if threat_type:
                        await self._record_threat(client_ip, threat_type, "request_body")
                        raise SecurityException(f"Threat in request body: {threat_type}", f"BODY_THREAT_{threat_type.upper()}")
            except (UnicodeDecodeError, ValueError, OSError) as exc:
                # Конкретные ожидаемые исключения при чтении/декодировании тела запроса.
                # Логируем детально и продолжаем работу middleware корректно.
                logger.debug("Не удалось прочитать тело запроса: %s (%s)", exc, type(exc).__name__)
            except SecurityException:
                # Если наша проверка явно отметила угрозу - пробрасываем дальше.
                raise
            except Exception as exc:
                # Неожиданные ошибки: логируем и пробрасываем, т.к. лучше упасть явно, чем подавить.
                logger.exception("Неожиданная ошибка при чтении тела запроса: %s", exc)
                raise
        
        # Check for honeypot access
        if request.url.path in self.honeypot_paths:
            await self._record_threat(client_ip, "honeypot_access", request.url.path)
            raise SecurityException("Access to honeypot detected", "HONEYPOT_ACCESS")
    
    def _analyze_for_threats(self, content: str) -> Optional[str]:
        """Analyze content for threat patterns"""
        for threat_type, patterns in self.threat_patterns.items():
            for pattern in patterns:
                if pattern.search(content):
                    return threat_type
        return None
    
    def _contains_threat_patterns(self, content: str) -> bool:
        """Quick check if content contains any threat patterns"""
        return self._analyze_for_threats(content) is not None
    
    async def _adaptive_rate_limiting(self, request: Request, client_ip: str):
        """Adaptive rate limiting based on endpoint and user behavior"""
        
        path = request.url.path
        
        # Determine limiter type
        if path.startswith('/api/v1/trading/'):
            limiter_type = 'trading'
        elif path.startswith('/api/v1/tokens/create'):
            limiter_type = 'token_creation'
        elif path.startswith('/api/v1/admin/'):
            limiter_type = 'admin'
        elif path.startswith('/api/v1/auth/'):
            limiter_type = 'auth'
        else:
            limiter_type = 'api'
        
        # Get limiter and check
        limiter = self.rate_limiters[limiter_type]
        if not await limiter.check_limit(client_ip, self.redis_pool):
            # Adaptive punishment - increase timeout for repeat offenders
            timeout = await self._calculate_adaptive_timeout(client_ip, limiter_type)
            raise RateLimitException(
                f"Rate limit exceeded for {limiter_type}",
                retry_after=timeout
            )
    
    async def _calculate_adaptive_timeout(self, client_ip: str, limiter_type: str) -> int:
        """Calculate adaptive timeout based on violation history"""
        redis_client = redis.Redis(connection_pool=self.redis_pool)
        
        violation_key = f"violations:{client_ip}:{limiter_type}"
        violations = await redis_client.get(violation_key)
        violations = int(violations) if violations else 0
        
        # Increase timeout exponentially: 60s, 120s, 300s, 600s, 1800s
        timeouts = [60, 120, 300, 600, 1800]
        timeout_index = min(violations, len(timeouts) - 1)
        timeout = timeouts[timeout_index]
        
        # Record violation
        await redis_client.incr(violation_key)
        await redis_client.expire(violation_key, 3600)  # Reset after 1 hour
        
        return timeout
    
    async def _analyze_behavior(self, request: Request, client_ip: str):
        """Behavioral analysis for anomaly detection"""
        
        if client_ip not in self.user_behaviors:
            self.user_behaviors[client_ip] = UserBehavior()
        
        behavior = self.user_behaviors[client_ip]
        behavior.record_request(request)
        
        # Check for suspicious patterns
        if behavior.is_suspicious():
            suspicious_reason = behavior.get_suspicion_reason()
            await self._record_threat(client_ip, "suspicious_behavior", suspicious_reason)
            raise SuspiciousActivityException(suspicious_reason)
    
    async def _check_ip_reputation(self, request: Request, client_ip: str):
        """Check IP reputation and geolocation"""
        
        # Skip for local development
        if not settings.is_production:
            return
        
        try:
            # Simple geolocation check (in production, use proper GeoIP service)
            # This is a simplified implementation
            if self._is_suspicious_location(client_ip):
                await self._record_threat(client_ip, "suspicious_location", "high_risk_country")
                # Don't block, but apply stricter limits
                await self._apply_strict_monitoring(client_ip)
            
        except Exception as e:
            logger.warning(f"IP reputation check failed: {e}")
    
    def _is_suspicious_location(self, client_ip: str) -> bool:
        """Simple implementation - in production use proper GeoIP service"""
        # This is a placeholder - implement with actual GeoIP service
        return False
    
    async def _apply_strict_monitoring(self, client_ip: str):
        """Apply strict monitoring for suspicious IPs"""
        redis_client = redis.Redis(connection_pool=self.redis_pool)
        await redis_client.set(f"strict_monitoring:{client_ip}", "1", ex=3600)
    
    async def _ddos_protection(self, request: Request, client_ip: str):
        """DDoS protection with connection tracking"""
        
        tracker = self.connection_limits[client_ip]
        
        # Check concurrent connections
        if tracker.get_concurrent_connections() > 20:  # Max 20 concurrent
            raise SecurityException("Too many concurrent connections", "DDOS_PROTECTION")
        
        # Check request frequency
        if tracker.get_requests_per_second() > 10:  # Max 10 req/sec
            raise SecurityException("Request frequency too high", "DDOS_PROTECTION")
        
        tracker.record_connection()
    
    async def _analyze_response(self, request: Request, response: Response, client_ip: str):
        """Analyze response for security insights"""
        
        # Check for potential data leakage in error responses
        if response.status_code >= 500:
            # Log for security analysis
            logger.warning(f"Server error for IP {client_ip}: {response.status_code}")
        
        # Monitor for brute force attempts
        if response.status_code == 401 and request.url.path.startswith('/api/v1/auth/'):
            await self._record_failed_auth(client_ip)
    
    async def _record_failed_auth(self, client_ip: str):
        """Record failed authentication attempts"""
        redis_client = redis.Redis(connection_pool=self.redis_pool)
        
        key = f"failed_auth:{client_ip}"
        failures = await redis_client.incr(key)
        await redis_client.expire(key, 300)  # 5 minute window
        
        if failures >= 5:  # 5 failures in 5 minutes
            # Temporarily block authentication attempts
            await redis_client.set(f"auth_blocked:{client_ip}", "1", ex=900)  # 15 min block
            raise SecurityException("Too many failed authentication attempts", "AUTH_BRUTE_FORCE")
    
    def _add_enhanced_security_headers(self, response: Response):
        """Add enhanced security headers"""
        
        # Standard security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Enhanced CSP
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self' wss: https: ws:",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "upgrade-insecure-requests"
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # HSTS for production
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Additional security headers
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["X-Download-Options"] = "noopen"
        response.headers["X-DNS-Prefetch-Control"] = "off"
        
        # Rate limiting info
        response.headers["X-Security-Level"] = "enhanced"
        response.headers["X-Request-ID"] = secrets.token_urlsafe(16)
    
    async def _security_audit_log(self, request: Request, response: Response, 
                                client_ip: str, duration: float):
        """Comprehensive security audit logging"""
        
        audit_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "client_ip": client_ip,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "user_agent": request.headers.get("user-agent", ""),
            "referer": request.headers.get("referer", ""),
            "user_id": getattr(request.state, "user_id", None),
            "forwarded_for": request.headers.get("x-forwarded-for", ""),
            "content_length": request.headers.get("content-length", 0),
        }
        
        # Log to different levels based on security relevance
        if response.status_code >= 500:
            logger.error("Security audit - server error", extra=audit_data)
        elif response.status_code in [401, 403, 429]:
            logger.warning("Security audit - access denied", extra=audit_data)
        elif request.url.path.startswith('/api/v1/admin/'):
            logger.info("Security audit - admin access", extra=audit_data)
        elif request.url.path.startswith('/api/v1/trading/'):
            logger.info("Security audit - trading activity", extra=audit_data)
    
    async def _record_threat(self, client_ip: str, threat_type: str, details: str):
        """Record threat detection for analysis"""
        if not self.redis_pool:
            return
        
        redis_client = redis.Redis(connection_pool=self.redis_pool)
        
        threat_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "ip": client_ip,
            "type": threat_type,
            "details": details
        }
        
        # Store threat record
        await redis_client.lpush("security_threats", str(threat_data))
        await redis_client.ltrim("security_threats", 0, 9999)  # Keep last 10k threats
        
        # Update IP threat score
        threat_score_key = f"threat_score:{client_ip}"
        await redis_client.incr(threat_score_key)
        await redis_client.expire(threat_score_key, 86400)  # 24 hour window


class RateLimiter:
    """Advanced rate limiter with burst protection"""
    
    def __init__(self, limit: int, window: int, burst_limit: int = None):
        self.limit = limit
        self.window = window
        self.burst_limit = burst_limit or limit // 10
    
    async def check_limit(self, key: str, redis_pool) -> bool:
        """Check if request is within limits"""
        if not redis_pool:
            return True  # Allow if Redis not available
        
        redis_client = redis.Redis(connection_pool=redis_pool)
        current_time = int(time.time())
        
        # Sliding window rate limiting
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(f"rate_limit:{key}", 0, current_time - self.window)
        pipe.zcard(f"rate_limit:{key}")
        pipe.zadd(f"rate_limit:{key}", {str(current_time): current_time})
        pipe.expire(f"rate_limit:{key}", self.window)
        
        results = await pipe.execute()
        request_count = results[1]
        
        # Check burst limit
        burst_window = 10  # 10 second burst window
        burst_count = await redis_client.zcount(
            f"rate_limit:{key}",
            current_time - burst_window,
            current_time
        )
        
        if burst_count > self.burst_limit:
            return False
        
        return request_count < self.limit


class UserBehavior:
    """User behavior analysis"""
    
    def __init__(self):
        self.request_times = deque(maxlen=100)
        self.paths = deque(maxlen=50)
        self.user_agents = deque(maxlen=10)
        self.patterns = defaultdict(int)
    
    def record_request(self, request: Request):
        """Record request for behavior analysis"""
        current_time = time.time()
        self.request_times.append(current_time)
        self.paths.append(request.url.path)
        self.user_agents.append(request.headers.get("user-agent", ""))
        
        # Analyze patterns
        self._analyze_timing_patterns()
        self._analyze_path_patterns()
        self._analyze_user_agent_patterns()
    
    def _analyze_timing_patterns(self):
        """Analyze request timing for bot-like behavior"""
        if len(self.request_times) < 10:
            return
        
        # Check for regular intervals (bot-like)
        intervals = []
        for i in range(1, len(self.request_times)):
            intervals.append(self.request_times[i] - self.request_times[i-1])
        
        # If most intervals are very similar, it's suspicious
        if len(set(round(interval, 1) for interval in intervals[-10:])) <= 2:
            self.patterns['regular_intervals'] += 1
    
    def _analyze_path_patterns(self):
        """Analyze path access patterns"""
        if len(self.paths) < 5:
            return
        
        # Check for sequential enumeration
        recent_paths = list(self.paths)[-10:]
        if self._is_sequential_enumeration(recent_paths):
            self.patterns['sequential_enumeration'] += 1
    
    def _analyze_user_agent_patterns(self):
        """Analyze User-Agent patterns"""
        if len(self.user_agents) < 3:
            return
        
        # Check for changing User-Agents (suspicious)
        unique_agents = set(self.user_agents)
        if len(unique_agents) > len(self.user_agents) // 2:
            self.patterns['changing_user_agents'] += 1
    
    def _is_sequential_enumeration(self, paths: List[str]) -> bool:
        """Check if paths show sequential enumeration pattern"""
        # Simple check for numeric sequences in paths
        numeric_parts = []
        for path in paths:
            numbers = re.findall(r'\d+', path)
            if numbers:
                numeric_parts.extend(int(n) for n in numbers)
        
        if len(numeric_parts) >= 3:
            # Check if numbers are sequential
            sorted_numbers = sorted(numeric_parts[-5:])
            is_sequential = all(
                sorted_numbers[i] + 1 == sorted_numbers[i + 1]
                for i in range(len(sorted_numbers) - 1)
            )
            return is_sequential
        
        return False
    
    def is_suspicious(self) -> bool:
        """Determine if behavior is suspicious"""
        suspicion_score = 0
        
        for pattern, count in self.patterns.items():
            if pattern == 'regular_intervals' and count >= 3:
                suspicion_score += 2
            elif pattern == 'sequential_enumeration' and count >= 2:
                suspicion_score += 3
            elif pattern == 'changing_user_agents' and count >= 2:
                suspicion_score += 1
        
        return suspicion_score >= 3
    
    def get_suspicion_reason(self) -> str:
        """Get reason for suspicion"""
        reasons = []
        for pattern, count in self.patterns.items():
            if count > 0:
                reasons.append(pattern.replace('_', ' '))
        return ', '.join(reasons) if reasons else 'unknown'


class ConnectionTracker:
    """Track connections for DDoS protection"""
    
    def __init__(self):
        self.connections = deque(maxlen=1000)
        self.active_connections = 0
    
    def record_connection(self):
        """Record a new connection"""
        current_time = time.time()
        self.connections.append(current_time)
        self.active_connections += 1
        
        # Simulate connection closing after 30 seconds
        asyncio.create_task(self._close_connection_after_delay())
    
    async def _close_connection_after_delay(self):
        """Simulate connection closing"""
        await asyncio.sleep(30)
        self.active_connections = max(0, self.active_connections - 1)
    
    def get_concurrent_connections(self) -> int:
        """Get current concurrent connections"""
        return self.active_connections
    
    def get_requests_per_second(self) -> float:
        """Get current requests per second"""
        if len(self.connections) < 2:
            return 0
        
        # Count requests in last second
        current_time = time.time()
        recent_requests = [
            t for t in self.connections
            if current_time - t <= 1.0
        ]
        
        return len(recent_requests)