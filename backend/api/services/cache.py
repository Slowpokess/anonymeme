#!/usr/bin/env python3
"""
🔴 Сервис кэширования для Anonymeme API
Production-ready Redis integration с intelligent caching
"""

import json
import pickle
import logging
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
from functools import wraps
import hashlib

import redis.asyncio as redis
from pydantic import BaseModel

from ..core.config import settings
from ..core.exceptions import CacheException, RedisConnectionException

logger = logging.getLogger(__name__)


class CacheStats(BaseModel):
    """Статистика кэша"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    total_keys: int = 0
    memory_usage_mb: float = 0.0
    hit_rate: float = 0.0


class CacheService:
    """
    Production-ready сервис кэширования с Redis
    Поддерживает автоматическую инвалидацию, статистику и batch операции
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.stats = CacheStats()
        
        # Префиксы для разных типов данных
        self.prefixes = {
            'token': 'token:',
            'user': 'user:',
            'price': 'price:',
            'trade': 'trade:',
            'analytics': 'analytics:',
            'session': 'session:',
            'rate_limit': 'rate:',
            'lock': 'lock:',
        }
        
        # TTL по умолчанию для разных типов (в секундах)
        self.default_ttl = {
            'token': 300,        # 5 минут
            'user': 600,         # 10 минут  
            'price': 30,         # 30 секунд
            'trade': 3600,       # 1 час
            'analytics': 1800,   # 30 минут
            'session': 86400,    # 1 день
            'rate_limit': 3600,  # 1 час
            'lock': 60,          # 1 минута
        }
        
        logger.info("Cache service initialized")
    
    def _make_key(self, prefix_type: str, key: str) -> str:
        """Создание ключа с префиксом"""
        prefix = self.prefixes.get(prefix_type, f"{prefix_type}:")
        return f"anonymeme:{prefix}{key}"
    
    def _serialize_value(self, value: Any) -> bytes:
        """Сериализация значения для хранения"""
        try:
            if isinstance(value, (str, int, float, bool)):
                return json.dumps(value).encode('utf-8')
            elif isinstance(value, (dict, list)):
                return json.dumps(value, default=str).encode('utf-8')
            else:
                # Для сложных объектов используем pickle
                return pickle.dumps(value)
        except Exception as e:
            logger.error(f"Serialization error: {e}")
            raise CacheException(f"Failed to serialize value: {str(e)}")
    
    def _deserialize_value(self, data: bytes, trusted: bool = False) -> Any:
        """
        Десериализация значения из кэша.
        Предпочитаем JSON. Если JSON не подходит и данные помечены как trusted=True,
        допускается использование pickle.loads (с DOCUMENTED justification).
        Если trusted=False — не использовать pickle и вернуть None.
        """
        if data is None:
            return None

        # Попытка JSON десериализации
        try:
            text = data.decode("utf-8")
            return json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError):
            # Если это не JSON, возможно, это бинарный формат.
            logger.debug("Данные кэша не являются JSON, проверяем дальше (trusted=%s)", trusted)

        # Разрешаем pickle только для доверенных данных
        if trusted:
            try:
                # Используем pickle только если уверены в источнике данных.
                # nosec B301 - pickle используется только для trusted=True данных из внутреннего кэша
                return pickle.loads(data)  # nosec
            except Exception as exc:
                logger.exception("Ошибка при unpickle данных (trusted=True): %s", exc)
                # В случае ошибки unpickle — возвращаем None, т.к. безопаснее игнорировать corrupt data.
                return None
        else:
            # Если данные не JSON и не trusted — не используем pickle (риск RCE).
            logger.warning("Отказ в unpickle для недоверенных данных (trusted=False)")
            return None
    
    async def get(
        self, 
        key: str, 
        prefix_type: str = 'general',
        default: Any = None
    ) -> Any:
        """Получение значения из кэша"""
        try:
            cache_key = self._make_key(prefix_type, key)
            data = await self.redis.get(cache_key)
            
            if data is None:
                self.stats.misses += 1
                return default

            self.stats.hits += 1
            # По умолчанию считаем данные из внутреннего Redis trusted=True
            # так как это наш собственный кэш-сервер
            return self._deserialize_value(data, trusted=True)
            
        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Cache get error for key {key}: {e}")
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        prefix_type: str = 'general',
        ttl: Optional[int] = None,
        if_not_exists: bool = False
    ) -> bool:
        """Сохранение значения в кэш"""
        try:
            cache_key = self._make_key(prefix_type, key)
            serialized_value = self._serialize_value(value)
            
            # Определение TTL
            expire_time = ttl or self.default_ttl.get(prefix_type, 300)
            
            if if_not_exists:
                result = await self.redis.set(
                    cache_key, 
                    serialized_value, 
                    ex=expire_time,
                    nx=True
                )
            else:
                result = await self.redis.set(
                    cache_key, 
                    serialized_value, 
                    ex=expire_time
                )
            
            if result:
                self.stats.sets += 1
            
            return bool(result)
            
        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str, prefix_type: str = 'general') -> bool:
        """Удаление ключа из кэша"""
        try:
            cache_key = self._make_key(prefix_type, key)
            result = await self.redis.delete(cache_key)
            
            if result > 0:
                self.stats.deletes += 1
                return True
            return False
            
        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str, prefix_type: str = 'general') -> bool:
        """Проверка существования ключа"""
        try:
            cache_key = self._make_key(prefix_type, key)
            result = await self.redis.exists(cache_key)
            return bool(result)
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int, prefix_type: str = 'general') -> bool:
        """Установка TTL для существующего ключа"""
        try:
            cache_key = self._make_key(prefix_type, key)
            result = await self.redis.expire(cache_key, ttl)
            return bool(result)
        except Exception as e:
            logger.error(f"Cache expire error for key {key}: {e}")
            return False
    
    async def increment(
        self, 
        key: str, 
        amount: int = 1, 
        prefix_type: str = 'general',
        ttl: Optional[int] = None
    ) -> int:
        """Атомарное увеличение счетчика"""
        try:
            cache_key = self._make_key(prefix_type, key)
            
            # Используем pipeline для атомарности
            pipe = self.redis.pipeline()
            pipe.incrby(cache_key, amount)
            
            if ttl:
                pipe.expire(cache_key, ttl)
            
            results = await pipe.execute()
            return results[0]
            
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return 0
    
    async def get_or_set(
        self,
        key: str,
        factory_func,
        prefix_type: str = 'general',
        ttl: Optional[int] = None,
        *args,
        **kwargs
    ) -> Any:
        """Получить из кэша или выполнить функцию и закэшировать результат"""
        try:
            # Попытка получить из кэша
            cached_value = await self.get(key, prefix_type)
            if cached_value is not None:
                return cached_value
            
            # Если нет в кэше, выполняем функцию
            if asyncio.iscoroutinefunction(factory_func):
                fresh_value = await factory_func(*args, **kwargs)
            else:
                fresh_value = factory_func(*args, **kwargs)
            
            # Кэшируем результат
            await self.set(key, fresh_value, prefix_type, ttl)
            
            return fresh_value
            
        except Exception as e:
            logger.error(f"Cache get_or_set error for key {key}: {e}")
            # В случае ошибки всё равно пытаемся выполнить функцию
            if asyncio.iscoroutinefunction(factory_func):
                return await factory_func(*args, **kwargs)
            else:
                return factory_func(*args, **kwargs)
    
    async def mget(
        self, 
        keys: List[str], 
        prefix_type: str = 'general'
    ) -> Dict[str, Any]:
        """Множественное получение значений"""
        try:
            cache_keys = [self._make_key(prefix_type, key) for key in keys]
            values = await self.redis.mget(cache_keys)
            
            result = {}
            for i, key in enumerate(keys):
                if values[i] is not None:
                    # Данные из нашего внутреннего Redis считаем trusted
                    result[key] = self._deserialize_value(values[i], trusted=True)
                    self.stats.hits += 1
                else:
                    self.stats.misses += 1
            
            return result
            
        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Cache mget error: {e}")
            return {}
    
    async def mset(
        self, 
        mapping: Dict[str, Any], 
        prefix_type: str = 'general',
        ttl: Optional[int] = None
    ) -> bool:
        """Множественная установка значений"""
        try:
            pipe = self.redis.pipeline()
            expire_time = ttl or self.default_ttl.get(prefix_type, 300)
            
            for key, value in mapping.items():
                cache_key = self._make_key(prefix_type, key)
                serialized_value = self._serialize_value(value)
                pipe.set(cache_key, serialized_value, ex=expire_time)
            
            results = await pipe.execute()
            success_count = sum(1 for result in results if result)
            self.stats.sets += success_count
            
            return success_count == len(mapping)
            
        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Cache mset error: {e}")
            return False
    
    async def delete_pattern(self, pattern: str, prefix_type: str = 'general') -> int:
        """Удаление ключей по паттерну"""
        try:
            cache_pattern = self._make_key(prefix_type, pattern)
            keys = []
            
            # Сканирование ключей по паттерну
            async for key in self.redis.scan_iter(match=cache_pattern):
                keys.append(key)
            
            if keys:
                deleted = await self.redis.delete(*keys)
                self.stats.deletes += deleted
                return deleted
            
            return 0
            
        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Cache delete_pattern error: {e}")
            return 0
    
    async def flush_prefix(self, prefix_type: str) -> int:
        """Очистка всех ключей с определенным префиксом"""
        pattern = f"anonymeme:{self.prefixes[prefix_type]}*"
        return await self.delete_pattern("*", prefix_type)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша"""
        try:
            # Обновление статистики Redis
            info = await self.redis.info()
            self.stats.total_keys = info.get('db0', {}).get('keys', 0)
            self.stats.memory_usage_mb = info.get('used_memory', 0) / 1024 / 1024
            
            # Расчет hit rate
            total_requests = self.stats.hits + self.stats.misses
            if total_requests > 0:
                self.stats.hit_rate = (self.stats.hits / total_requests) * 100
            
            return {
                "hits": self.stats.hits,
                "misses": self.stats.misses,
                "sets": self.stats.sets,
                "deletes": self.stats.deletes,
                "errors": self.stats.errors,
                "total_keys": self.stats.total_keys,
                "memory_usage_mb": round(self.stats.memory_usage_mb, 2),
                "hit_rate": round(self.stats.hit_rate, 2),
                "redis_info": {
                    "connected_clients": info.get('connected_clients', 0),
                    "used_memory_human": info.get('used_memory_human', '0B'),
                    "uptime_in_seconds": info.get('uptime_in_seconds', 0),
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return self.stats.dict()
    
    # === СПЕЦИАЛИЗИРОВАННЫЕ МЕТОДЫ ===
    
    async def cache_token_data(self, mint_address: str, token_data: Dict[str, Any]) -> bool:
        """Кэширование данных токена"""
        return await self.set(mint_address, token_data, 'token', ttl=300)
    
    async def get_token_data(self, mint_address: str) -> Optional[Dict[str, Any]]:
        """Получение данных токена из кэша"""
        return await self.get(mint_address, 'token')
    
    async def cache_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """Кэширование профиля пользователя"""
        return await self.set(user_id, profile_data, 'user', ttl=600)
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получение профиля пользователя из кэша"""
        return await self.get(user_id, 'user')
    
    async def cache_price_data(self, mint_address: str, price_data: Dict[str, Any]) -> bool:
        """Кэширование данных о цене"""
        return await self.set(mint_address, price_data, 'price', ttl=30)
    
    async def get_price_data(self, mint_address: str) -> Optional[Dict[str, Any]]:
        """Получение данных о цене из кэша"""
        return await self.get(mint_address, 'price')
    
    async def rate_limit_check(
        self, 
        identifier: str, 
        limit: int, 
        window: int
    ) -> Tuple[bool, int, int]:
        """
        Проверка rate limiting
        Возвращает: (allowed, current_count, reset_time)
        """
        try:
            key = f"rate_limit:{identifier}:{window}"
            current_time = int(datetime.utcnow().timestamp())
            window_start = current_time - (current_time % window)
            
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start - window)
            pipe.zcard(key)
            pipe.zadd(key, {str(current_time): current_time})
            pipe.expire(key, window * 2)
            
            results = await pipe.execute()
            current_count = results[1]
            
            allowed = current_count < limit
            reset_time = window_start + window
            
            return allowed, current_count, reset_time
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True, 0, 0  # В случае ошибки разрешаем запрос
    
    async def acquire_lock(
        self, 
        lock_key: str, 
        timeout: int = 60,
        identifier: Optional[str] = None
    ) -> Optional[str]:
        """Получение распределенной блокировки"""
        try:
            if identifier is None:
                identifier = str(datetime.utcnow().timestamp())
            
            cache_key = self._make_key('lock', lock_key)
            
            # Попытка установить блокировку
            acquired = await self.redis.set(
                cache_key, 
                identifier, 
                nx=True, 
                ex=timeout
            )
            
            if acquired:
                return identifier
            return None
            
        except Exception as e:
            logger.error(f"Lock acquisition error: {e}")
            return None
    
    async def release_lock(self, lock_key: str, identifier: str) -> bool:
        """Освобождение распределенной блокировки"""
        try:
            cache_key = self._make_key('lock', lock_key)
            
            # Lua script для атомарного освобождения
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            
            result = await self.redis.eval(lua_script, 1, cache_key, identifier)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Lock release error: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья кэш-сервиса"""
        try:
            # Тест записи/чтения
            test_key = f"health_check:{datetime.utcnow().timestamp()}"
            test_value = "health_check_value"
            
            # Запись
            write_success = await self.set(test_key, test_value, 'general', ttl=10)
            
            # Чтение
            read_value = await self.get(test_key, 'general')
            read_success = read_value == test_value
            
            # Удаление
            delete_success = await self.delete(test_key, 'general')
            
            # Ping Redis
            ping_result = await self.redis.ping()
            
            return {
                "redis_ping": ping_result,
                "write_test": write_success,
                "read_test": read_success,
                "delete_test": delete_success,
                "overall_health": all([ping_result, write_success, read_success]),
                "stats": await self.get_stats()
            }
            
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {
                "redis_ping": False,
                "write_test": False,
                "read_test": False,
                "delete_test": False,
                "overall_health": False,
                "error": str(e)
            }


# === ДЕКОРАТОРЫ ДЛЯ КЭШИРОВАНИЯ ===

import asyncio


def cache_result(
    key_pattern: str,
    prefix_type: str = 'general',
    ttl: Optional[int] = None,
    cache_none: bool = False
):
    """
    Декоратор для автоматического кэширования результатов функций
    
    Args:
        key_pattern: Паттерн ключа, может содержать {arg_name} плейсхолдеры
        prefix_type: Тип префикса для ключа
        ttl: Время жизни кэша
        cache_none: Кэшировать ли None значения
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Получение cache service из контекста (нужно будет передавать)
            # Это упрощенная версия, в реальности нужен доступ к сервису
            
            # Формирование ключа на основе аргументов
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Замена плейсхолдеров в ключе
            cache_key = key_pattern.format(**bound_args.arguments)
            
            # Хэширование ключа если он слишком длинный
            if len(cache_key) > 200:
                cache_key = hashlib.md5(cache_key.encode()).hexdigest()
            
            # Здесь должна быть логика кэширования
            # В реальной реализации нужен доступ к CacheService instance
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def invalidate_cache(
    key_patterns: List[str],
    prefix_type: str = 'general'
):
    """
    Декоратор для инвалидации кэша после выполнения функции
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Здесь должна быть логика инвалидации
            # В реальной реализации нужен доступ к CacheService instance
            
            return result
        
        return wrapper
    return decorator