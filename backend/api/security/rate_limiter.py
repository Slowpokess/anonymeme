#!/usr/bin/env python3
"""
⚡ Advanced Rate Limiter для Anonymeme API
Distributed rate limiting с Redis и adaptive algorithms
"""

import time
import asyncio
import logging
import hashlib
import json
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import redis.asyncio as redis
from functools import wraps

from ..core.config import settings
from ..core.exceptions import RateLimitException

logger = logging.getLogger(__name__)


class LimitType(Enum):
    """Types of rate limits"""
    REQUESTS_PER_MINUTE = "rpm"
    REQUESTS_PER_HOUR = "rph"
    REQUESTS_PER_DAY = "rpd"
    BANDWIDTH_PER_MINUTE = "bpm"
    CONCURRENT_CONNECTIONS = "cc"


@dataclass
class RateLimit:
    """Rate limit configuration"""
    limit: int
    window: int  # seconds
    burst_limit: Optional[int] = None
    grace_period: Optional[int] = None  # seconds of grace after limit
    penalty_multiplier: float = 1.5  # multiplier for penalty timeouts


@dataclass
class RateLimitConfig:
    """Complete rate limiting configuration for an endpoint"""
    endpoint: str
    method: str
    limits: List[RateLimit] = field(default_factory=list)
    user_type_multipliers: Dict[str, float] = field(default_factory=dict)
    ip_whitelist: List[str] = field(default_factory=list)
    bypass_conditions: List[str] = field(default_factory=list)


@dataclass
class RateLimitStatus:
    """Current rate limit status"""
    limited: bool
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None
    limit_type: Optional[str] = None
    penalty_active: bool = False


class AdvancedRateLimiter:
    """
    Advanced distributed rate limiter с adaptive algorithms
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis_pool = None
        self._init_redis()
        
        # Configuration templates
        self.configs = self._load_default_configs()
        
        # Adaptive settings
        self.adaptive_enabled = True
        self.global_load_threshold = 0.8  # When to start adaptive limiting
        
        # Penalty tracking
        self.penalty_tracker = {}
        
        logger.info("Advanced rate limiter initialized")
    
    def _init_redis(self):
        """Initialize Redis connection pool"""
        try:
            self.redis_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                decode_responses=True
            )
            logger.info("Redis pool initialized for rate limiter")
        except Exception as e:
            logger.error(f"Failed to initialize Redis pool: {e}")
            self.redis_pool = None
    
    def _load_default_configs(self) -> Dict[str, RateLimitConfig]:
        """Load default rate limiting configurations"""
        configs = {}
        
        # Trading endpoints - very strict
        configs['trading'] = RateLimitConfig(
            endpoint='/api/v1/trading/*',
            method='*',
            limits=[
                RateLimit(10, 60, burst_limit=3),      # 10/min, burst 3
                RateLimit(100, 3600, burst_limit=20),   # 100/hour, burst 20
                RateLimit(1000, 86400)                  # 1000/day
            ],
            user_type_multipliers={
                'premium': 2.0,
                'vip': 5.0,
                'admin': 10.0
            }
        )
        
        # Token creation - extremely strict
        configs['token_creation'] = RateLimitConfig(
            endpoint='/api/v1/tokens/create',
            method='POST',
            limits=[
                RateLimit(3, 3600, burst_limit=1),      # 3/hour, burst 1
                RateLimit(10, 86400),                   # 10/day
                RateLimit(50, 604800)                   # 50/week
            ],
            user_type_multipliers={
                'premium': 1.5,
                'vip': 3.0,
                'admin': 10.0
            }
        )
        
        # Authentication - moderate but with penalties
        configs['auth'] = RateLimitConfig(
            endpoint='/api/v1/auth/*',
            method='*',
            limits=[
                RateLimit(5, 300, burst_limit=2, penalty_multiplier=2.0),  # 5/5min
                RateLimit(20, 3600, burst_limit=5),     # 20/hour
                RateLimit(100, 86400)                   # 100/day
            ]
        )
        
        # Admin endpoints - strict with IP whitelist
        configs['admin'] = RateLimitConfig(
            endpoint='/api/v1/admin/*',
            method='*',
            limits=[
                RateLimit(100, 3600, burst_limit=20),   # 100/hour
                RateLimit(1000, 86400)                  # 1000/day
            ],
            ip_whitelist=['127.0.0.1', '10.0.0.0/8'],
            user_type_multipliers={
                'admin': 5.0,
                'superadmin': 10.0
            }
        )
        
        # General API - reasonable limits
        configs['api'] = RateLimitConfig(
            endpoint='/api/v1/*',
            method='*',
            limits=[
                RateLimit(1000, 3600, burst_limit=50),  # 1000/hour
                RateLimit(10000, 86400)                 # 10000/day
            ],
            user_type_multipliers={
                'premium': 2.0,
                'vip': 3.0,
                'admin': 10.0
            }
        )
        
        # Public endpoints - generous but monitored
        configs['public'] = RateLimitConfig(
            endpoint='/api/v1/tokens',
            method='GET',
            limits=[
                RateLimit(2000, 3600, burst_limit=100), # 2000/hour
                RateLimit(20000, 86400)                 # 20000/day
            ]
        )
        
        return configs
    
    async def check_rate_limit(self, identifier: str, endpoint: str, method: str,
                             user_type: str = 'default', content_length: int = 0,
                             ip_address: str = None) -> RateLimitStatus:
        """
        Check if request should be rate limited
        
        Args:
            identifier: Unique identifier (user_id, ip, api_key)
            endpoint: API endpoint path
            method: HTTP method
            user_type: Type of user (default, premium, vip, admin)
            content_length: Request size in bytes
            ip_address: Client IP address
        
        Returns:
            RateLimitStatus with current status
        """
        
        if not self.redis_pool:
            # Fallback to allow all requests if Redis unavailable
            return RateLimitStatus(limited=False, remaining=1000, reset_time=int(time.time()) + 3600)
        
        # Find matching configuration
        config = self._find_matching_config(endpoint, method)
        if not config:
            # No specific config, use default API limits
            config = self.configs.get('api')
        
        # Check IP whitelist
        if ip_address and self._is_whitelisted_ip(ip_address, config):
            return RateLimitStatus(limited=False, remaining=10000, reset_time=int(time.time()) + 3600)
        
        # Apply user type multiplier
        multiplier = config.user_type_multipliers.get(user_type, 1.0)
        
        # Check adaptive scaling
        if self.adaptive_enabled:
            adaptive_multiplier = await self._get_adaptive_multiplier()
            multiplier *= adaptive_multiplier
        
        # Check each limit in the configuration
        most_restrictive_status = None
        
        for limit_config in config.limits:
            status = await self._check_single_limit(
                identifier, endpoint, method, limit_config, multiplier
            )
            
            if status.limited:
                return status
            
            # Track most restrictive non-limited status
            if (most_restrictive_status is None or 
                status.remaining < most_restrictive_status.remaining):
                most_restrictive_status = status
        
        return most_restrictive_status or RateLimitStatus(
            limited=False, remaining=1000, reset_time=int(time.time()) + 3600
        )
    
    def _find_matching_config(self, endpoint: str, method: str) -> Optional[RateLimitConfig]:
        """Find the most specific matching rate limit configuration"""
        matches = []
        
        for config_name, config in self.configs.items():
            if self._endpoint_matches(endpoint, config.endpoint) and \
               self._method_matches(method, config.method):
                # Score by specificity (more specific patterns score higher)
                specificity = len([c for c in config.endpoint if c not in ['*', '?']])
                matches.append((specificity, config))
        
        if matches:
            # Return most specific match
            matches.sort(key=lambda x: x[0], reverse=True)
            return matches[0][1]
        
        return None
    
    def _endpoint_matches(self, endpoint: str, pattern: str) -> bool:
        """Check if endpoint matches pattern with wildcards"""
        import fnmatch
        return fnmatch.fnmatch(endpoint, pattern)
    
    def _method_matches(self, method: str, pattern: str) -> bool:
        """Check if method matches pattern"""
        return pattern == '*' or method.upper() == pattern.upper()
    
    def _is_whitelisted_ip(self, ip_address: str, config: RateLimitConfig) -> bool:
        """Check if IP is whitelisted"""
        if not config.ip_whitelist:
            return False
        
        from ipaddress import ip_address as parse_ip, ip_network
        
        try:
            ip = parse_ip(ip_address)
            for whitelist_entry in config.ip_whitelist:
                if '/' in whitelist_entry:
                    # CIDR notation
                    if ip in ip_network(whitelist_entry):
                        return True
                else:
                    # Direct IP match
                    if str(ip) == whitelist_entry:
                        return True
        except (ValueError, TypeError, AttributeError) as e:
            # Ожидаемые ошибки при парсинге IP или сети
            logger.warning("Ошибка при проверке whitelist для IP %s: %s", ip_address, e)
        except Exception as e:
            # Неожиданные ошибки логируем
            logger.exception("Неожиданная ошибка в _is_whitelisted_ip: %s", e)

        return False
    
    async def _get_adaptive_multiplier(self) -> float:
        """Calculate adaptive multiplier based on system load"""
        try:
            redis_client = redis.Redis(connection_pool=self.redis_pool)
            
            # Get system load metrics
            current_rps = await self._get_current_rps(redis_client)
            error_rate = await self._get_error_rate(redis_client)
            
            # Calculate adaptive multiplier
            multiplier = 1.0
            
            # Reduce limits if high load
            if current_rps > 1000:  # High load threshold
                multiplier *= 0.7
            elif current_rps > 500:  # Medium load threshold
                multiplier *= 0.85
            
            # Reduce limits if high error rate
            if error_rate > 0.1:  # 10% error rate
                multiplier *= 0.6
            elif error_rate > 0.05:  # 5% error rate
                multiplier *= 0.8
            
            return max(0.1, multiplier)  # Minimum 10% of original limits

        except (ValueError, TypeError, KeyError) as e:
            # Ожидаемые ошибки при парсинге метрик
            logger.debug("Ошибка при расчете adaptive multiplier: %s", e)
            return 1.0
        except Exception as e:
            # Неожиданные ошибки логируем
            logger.exception("Неожиданная ошибка в _get_adaptive_multiplier: %s", e)
            return 1.0
    
    async def _get_current_rps(self, redis_client: redis.Redis) -> float:
        """Get current requests per second"""
        try:
            # Count requests in last 60 seconds
            current_time = int(time.time())
            count = await redis_client.zcount(
                "global_requests",
                current_time - 60,
                current_time
            )
            return count / 60.0
        except (ValueError, TypeError) as e:
            # Ожидаемые ошибки при работе с Redis
            logger.debug("Ошибка при получении RPS: %s", e)
            return 0.0
        except Exception as e:
            # Неожиданные ошибки логируем
            logger.exception("Неожиданная ошибка в _get_current_rps: %s", e)
            return 0.0
    
    async def _get_error_rate(self, redis_client: redis.Redis) -> float:
        """Get current error rate"""
        try:
            total_key = "global_requests_total"
            error_key = "global_requests_errors"
            
            total = await redis_client.get(total_key)
            errors = await redis_client.get(error_key)
            
            if not total or not errors:
                return 0.0
            
            return float(errors) / float(total)
        except (ValueError, TypeError, ZeroDivisionError) as e:
            # Ожидаемые ошибки при расчете error rate
            logger.debug("Ошибка при получении error rate: %s", e)
            return 0.0
        except Exception as e:
            # Неожиданные ошибки логируем
            logger.exception("Неожиданная ошибка в _get_error_rate: %s", e)
            return 0.0
    
    async def _check_single_limit(self, identifier: str, endpoint: str, method: str,
                                limit_config: RateLimit, multiplier: float) -> RateLimitStatus:
        """Check a single rate limit configuration"""
        
        adjusted_limit = int(limit_config.limit * multiplier)
        adjusted_burst = int((limit_config.burst_limit or limit_config.limit) * multiplier)
        
        redis_client = redis.Redis(connection_pool=self.redis_pool)
        current_time = int(time.time())
        
        # Create unique key for this limit
        limit_key = f"rate_limit:{identifier}:{endpoint}:{method}:{limit_config.window}"
        
        # Sliding window rate limiting using sorted sets
        try:
            # Remove expired entries
            await redis_client.zremrangebyscore(
                limit_key,
                0,
                current_time - limit_config.window
            )
            
            # Count current requests
            current_count = await redis_client.zcard(limit_key)
            
            # Check burst limit (requests in last 10 seconds)
            burst_count = await redis_client.zcount(
                limit_key,
                current_time - 10,
                current_time
            )
            
            # Check if limits exceeded
            if burst_count >= adjusted_burst:
                penalty_time = await self._apply_penalty(
                    identifier, endpoint, limit_config.penalty_multiplier
                )
                return RateLimitStatus(
                    limited=True,
                    remaining=0,
                    reset_time=current_time + 10,  # Burst window
                    retry_after=penalty_time or 10,
                    limit_type="burst",
                    penalty_active=penalty_time is not None
                )
            
            if current_count >= adjusted_limit:
                penalty_time = await self._apply_penalty(
                    identifier, endpoint, limit_config.penalty_multiplier
                )
                return RateLimitStatus(
                    limited=True,
                    remaining=0,
                    reset_time=current_time + limit_config.window,
                    retry_after=penalty_time or limit_config.window,
                    limit_type="window",
                    penalty_active=penalty_time is not None
                )
            
            # Add current request
            await redis_client.zadd(limit_key, {str(current_time): current_time})
            await redis_client.expire(limit_key, limit_config.window)
            
            # Update global metrics
            await self._update_global_metrics(redis_client)
            
            return RateLimitStatus(
                limited=False,
                remaining=adjusted_limit - current_count - 1,
                reset_time=current_time + limit_config.window
            )
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Fail open - allow request on error
            return RateLimitStatus(
                limited=False,
                remaining=adjusted_limit,
                reset_time=current_time + limit_config.window
            )
    
    async def _apply_penalty(self, identifier: str, endpoint: str, 
                           penalty_multiplier: float) -> Optional[int]:
        """Apply penalty for repeat violations"""
        try:
            redis_client = redis.Redis(connection_pool=self.redis_pool)
            
            penalty_key = f"penalty:{identifier}:{endpoint}"
            violations = await redis_client.get(penalty_key)
            violations = int(violations) if violations else 0
            
            if violations > 0:
                # Exponential backoff: 30s, 60s, 120s, 300s, 600s
                penalty_seconds = min(30 * (penalty_multiplier ** violations), 600)
                
                # Set penalty period
                penalty_end_key = f"penalty_end:{identifier}:{endpoint}"
                penalty_end = int(time.time()) + int(penalty_seconds)
                await redis_client.set(penalty_end_key, penalty_end, ex=int(penalty_seconds))
                
                # Record violation
                await redis_client.incr(penalty_key)
                await redis_client.expire(penalty_key, 3600)  # Reset after 1 hour
                
                return int(penalty_seconds)
            else:
                # First violation - record it
                await redis_client.incr(penalty_key)
                await redis_client.expire(penalty_key, 3600)
                return None
                
        except Exception as e:
            logger.error(f"Penalty application error: {e}")
            return None
    
    async def _update_global_metrics(self, redis_client: redis.Redis):
        """Update global system metrics"""
        try:
            current_time = int(time.time())
            
            # Add to global request tracking
            await redis_client.zadd("global_requests", {str(current_time): current_time})
            await redis_client.expire("global_requests", 3600)  # Keep 1 hour
            
            # Increment total counter
            await redis_client.incr("global_requests_total")
            await redis_client.expire("global_requests_total", 3600)
            
        except Exception as e:
            logger.warning(f"Failed to update global metrics: {e}")
    
    async def record_error(self, identifier: str, endpoint: str, error_code: int):
        """Record an error for rate limiting decisions"""
        try:
            redis_client = redis.Redis(connection_pool=self.redis_pool)
            
            # Update global error counter
            await redis_client.incr("global_requests_errors")
            await redis_client.expire("global_requests_errors", 3600)
            
            # Track user-specific errors
            error_key = f"errors:{identifier}:{endpoint}"
            await redis_client.incr(error_key)
            await redis_client.expire(error_key, 300)  # 5 minute window
            
        except Exception as e:
            logger.warning(f"Failed to record error: {e}")
    
    async def get_rate_limit_info(self, identifier: str, endpoint: str, 
                                method: str) -> Dict[str, Any]:
        """Get detailed rate limit information for an identifier"""
        try:
            redis_client = redis.Redis(connection_pool=self.redis_pool)
            
            config = self._find_matching_config(endpoint, method)
            if not config:
                config = self.configs.get('api')
            
            info = {
                'identifier': identifier,
                'endpoint': endpoint,
                'method': method,
                'limits': [],
                'penalties': {},
                'global_stats': {}
            }
            
            # Get limit info for each configured limit
            for limit_config in config.limits:
                limit_key = f"rate_limit:{identifier}:{endpoint}:{method}:{limit_config.window}"
                current_count = await redis_client.zcard(limit_key)
                
                info['limits'].append({
                    'window_seconds': limit_config.window,
                    'limit': limit_config.limit,
                    'burst_limit': limit_config.burst_limit,
                    'current_count': current_count,
                    'remaining': max(0, limit_config.limit - current_count),
                    'reset_time': int(time.time()) + limit_config.window
                })
            
            # Get penalty info
            penalty_key = f"penalty:{identifier}:{endpoint}"
            penalty_end_key = f"penalty_end:{identifier}:{endpoint}"
            
            violations = await redis_client.get(penalty_key)
            penalty_end = await redis_client.get(penalty_end_key)
            
            info['penalties'] = {
                'violations': int(violations) if violations else 0,
                'penalty_until': int(penalty_end) if penalty_end else None,
                'currently_penalized': bool(penalty_end and int(penalty_end) > time.time())
            }
            
            # Get global stats
            current_rps = await self._get_current_rps(redis_client)
            error_rate = await self._get_error_rate(redis_client)
            
            info['global_stats'] = {
                'current_rps': current_rps,
                'error_rate': error_rate,
                'adaptive_multiplier': await self._get_adaptive_multiplier()
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get rate limit info: {e}")
            return {'error': str(e)}
    
    async def reset_rate_limits(self, identifier: str, endpoint: str = None):
        """Reset rate limits for an identifier"""
        try:
            redis_client = redis.Redis(connection_pool=self.redis_pool)
            
            if endpoint:
                # Reset specific endpoint
                pattern = f"rate_limit:{identifier}:{endpoint}:*"
                penalty_pattern = f"penalty*:{identifier}:{endpoint}"
            else:
                # Reset all for identifier
                pattern = f"rate_limit:{identifier}:*"
                penalty_pattern = f"penalty*:{identifier}:*"
            
            # Get matching keys
            limit_keys = await redis_client.keys(pattern)
            penalty_keys = await redis_client.keys(penalty_pattern)
            
            # Delete keys
            all_keys = limit_keys + penalty_keys
            if all_keys:
                await redis_client.delete(*all_keys)
                logger.info(f"Reset {len(all_keys)} rate limit keys for {identifier}")
            
        except Exception as e:
            logger.error(f"Failed to reset rate limits: {e}")
    
    def add_custom_config(self, name: str, config: RateLimitConfig):
        """Add custom rate limiting configuration"""
        self.configs[name] = config
        logger.info(f"Added custom rate limit config: {name}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        return {
            'configs_loaded': len(self.configs),
            'adaptive_enabled': self.adaptive_enabled,
            'redis_connected': self.redis_pool is not None,
            'available_configs': list(self.configs.keys())
        }


# Decorator for easy rate limiting
def rate_limit(endpoint: str, method: str = '*', 
               limits: List[RateLimit] = None,
               identifier_func: callable = None):
    """
    Decorator for rate limiting functions
    
    Args:
        endpoint: Endpoint pattern
        method: HTTP method pattern
        limits: List of rate limits to apply
        identifier_func: Function to extract identifier from request
    """
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This would be implemented based on your framework
            # For FastAPI, you'd extract request from args/kwargs
            # For now, this is a placeholder
            
            limiter = AdvancedRateLimiter()
            
            # Extract identifier (implement based on your framework)
            identifier = "default"
            if identifier_func:
                identifier = identifier_func(*args, **kwargs)
            
            # Check rate limits
            status = await limiter.check_rate_limit(identifier, endpoint, method)
            
            if status.limited:
                raise RateLimitException(
                    f"Rate limit exceeded for {endpoint}",
                    retry_after=status.retry_after
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Example usage
async def example_usage():
    """Example of how to use the advanced rate limiter"""
    
    limiter = AdvancedRateLimiter()
    
    # Check rate limit for a trading request
    status = await limiter.check_rate_limit(
        identifier="user_123",
        endpoint="/api/v1/trading/buy",
        method="POST",
        user_type="premium",
        ip_address="192.168.1.1"
    )
    
    if status.limited:
        print(f"Rate limited! Retry after {status.retry_after} seconds")
    else:
        print(f"Request allowed. {status.remaining} requests remaining")
    
    # Get detailed info
    info = await limiter.get_rate_limit_info("user_123", "/api/v1/trading/buy", "POST")
    print(f"Rate limit info: {info}")
    
    # Add custom configuration
    custom_config = RateLimitConfig(
        endpoint="/api/v1/custom/*",
        method="POST",
        limits=[RateLimit(5, 60)],  # 5 requests per minute
        user_type_multipliers={"vip": 2.0}
    )
    limiter.add_custom_config("custom", custom_config)


if __name__ == "__main__":
    asyncio.run(example_usage())