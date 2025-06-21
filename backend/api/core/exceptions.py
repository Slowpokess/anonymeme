#!/usr/bin/env python3
"""
🚨 Кастомные исключения для Anonymeme API
Production-ready система обработки ошибок с детальной типизацией
"""

from typing import Any, Dict, Optional, Union
from fastapi import HTTPException, status


class CustomHTTPException(HTTPException):
    """
    Базовый класс для всех кастомных HTTP исключений
    Расширяет стандартный HTTPException дополнительными полями
    """
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code
        self.extra_data = extra_data or {}


# === ОШИБКИ ВАЛИДАЦИИ ===

class ValidationException(CustomHTTPException):
    """Ошибки валидации данных"""
    
    def __init__(
        self,
        detail: str = "Validation error",
        field: Optional[str] = None,
        value: Optional[Any] = None
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VALIDATION_ERROR",
            extra_data={"field": field, "value": value}
        )


class InvalidTokenException(ValidationException):
    """Ошибка при работе с невалидным токеном"""
    
    def __init__(self, token_address: str):
        super().__init__(
            detail=f"Token {token_address} is invalid or does not exist",
            field="token_address",
            value=token_address
        )
        self.error_code = "INVALID_TOKEN"


class InvalidAmountException(ValidationException):
    """Ошибка при указании некорректной суммы"""
    
    def __init__(self, amount: Union[int, float], min_amount: Union[int, float] = 0):
        super().__init__(
            detail=f"Amount {amount} is invalid. Must be greater than {min_amount}",
            field="amount",
            value=amount
        )
        self.error_code = "INVALID_AMOUNT"


class SlippageExceededException(ValidationException):
    """Ошибка превышения slippage"""
    
    def __init__(self, actual_slippage: float, max_slippage: float):
        super().__init__(
            detail=f"Slippage {actual_slippage:.2f}% exceeds maximum {max_slippage:.2f}%",
            extra_data={
                "actual_slippage": actual_slippage,
                "max_slippage": max_slippage
            }
        )
        self.error_code = "SLIPPAGE_EXCEEDED"


# === ОШИБКИ АУТЕНТИФИКАЦИИ И АВТОРИЗАЦИИ ===

class AuthenticationException(CustomHTTPException):
    """Базовый класс для ошибок аутентификации"""
    
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="AUTHENTICATION_FAILED",
            headers={"WWW-Authenticate": "Bearer"}
        )


class InvalidTokenAuthException(AuthenticationException):
    """Невалидный токен аутентификации"""
    
    def __init__(self):
        super().__init__(detail="Invalid authentication token")
        self.error_code = "INVALID_AUTH_TOKEN"


class TokenExpiredException(AuthenticationException):
    """Истекший токен аутентификации"""
    
    def __init__(self):
        super().__init__(detail="Authentication token has expired")
        self.error_code = "TOKEN_EXPIRED"


class AuthorizationException(CustomHTTPException):
    """Ошибки авторизации (недостаточно прав)"""
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="INSUFFICIENT_PERMISSIONS"
        )


class AdminRequiredException(AuthorizationException):
    """Требуются права администратора"""
    
    def __init__(self):
        super().__init__(detail="Administrator privileges required")
        self.error_code = "ADMIN_REQUIRED"


# === ОШИБКИ ТОРГОВЛИ ===

class TradingException(CustomHTTPException):
    """Базовый класс для ошибок торговли"""
    
    def __init__(self, detail: str, error_code: str = "TRADING_ERROR"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code
        )


class InsufficientBalanceException(TradingException):
    """Недостаточный баланс для совершения операции"""
    
    def __init__(self, required: Union[int, float], available: Union[int, float]):
        super().__init__(
            detail=f"Insufficient balance. Required: {required}, Available: {available}",
            error_code="INSUFFICIENT_BALANCE"
        )
        self.extra_data = {"required": required, "available": available}


class TradingPausedException(TradingException):
    """Торговля приостановлена"""
    
    def __init__(self, reason: str = "Trading is temporarily paused"):
        super().__init__(detail=reason, error_code="TRADING_PAUSED")


class MaxTradeSizeExceededException(TradingException):
    """Превышен максимальный размер сделки"""
    
    def __init__(self, trade_size: float, max_size: float):
        super().__init__(
            detail=f"Trade size {trade_size} SOL exceeds maximum {max_size} SOL",
            error_code="MAX_TRADE_SIZE_EXCEEDED"
        )
        self.extra_data = {"trade_size": trade_size, "max_size": max_size}


class InsufficientLiquidityException(TradingException):
    """Недостаточная ликвидность"""
    
    def __init__(self, requested: Union[int, float], available: Union[int, float]):
        super().__init__(
            detail=f"Insufficient liquidity. Requested: {requested}, Available: {available}",
            error_code="INSUFFICIENT_LIQUIDITY"
        )
        self.extra_data = {"requested": requested, "available": available}


class TokenGraduatedException(TradingException):
    """Токен уже выпущен на DEX"""
    
    def __init__(self, token_address: str):
        super().__init__(
            detail=f"Token {token_address} has graduated to DEX. Use DEX for trading.",
            error_code="TOKEN_GRADUATED"
        )
        self.extra_data = {"token_address": token_address}


# === ОШИБКИ RATE LIMITING ===

class RateLimitException(CustomHTTPException):
    """Превышен лимит запросов"""
    
    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        retry_after: Optional[int] = None
    ):
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_code="RATE_LIMITED",
            headers=headers
        )


# === ОШИБКИ БЛОКЧЕЙНА ===

class BlockchainException(CustomHTTPException):
    """Базовый класс для ошибок блокчейна"""
    
    def __init__(
        self,
        detail: str,
        error_code: str = "BLOCKCHAIN_ERROR",
        transaction_signature: Optional[str] = None
    ):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code=error_code
        )
        if transaction_signature:
            self.extra_data["transaction_signature"] = transaction_signature


class SolanaRpcException(BlockchainException):
    """Ошибки Solana RPC"""
    
    def __init__(self, detail: str = "Solana RPC error"):
        super().__init__(detail=detail, error_code="SOLANA_RPC_ERROR")


class TransactionFailedException(BlockchainException):
    """Ошибка выполнения транзакции"""
    
    def __init__(
        self,
        signature: str,
        error_message: str = "Transaction failed"
    ):
        super().__init__(
            detail=f"Transaction {signature} failed: {error_message}",
            error_code="TRANSACTION_FAILED",
            transaction_signature=signature
        )


class InsufficientSolException(BlockchainException):
    """Недостаточно SOL для оплаты комиссии"""
    
    def __init__(self, required_sol: float):
        super().__init__(
            detail=f"Insufficient SOL for transaction fee. Required: {required_sol} SOL",
            error_code="INSUFFICIENT_SOL_FOR_FEE"
        )
        self.extra_data = {"required_sol": required_sol}


class ProgramException(BlockchainException):
    """Ошибки программы Solana"""
    
    def __init__(self, program_error: str, error_code_num: Optional[int] = None):
        detail = f"Program error: {program_error}"
        if error_code_num:
            detail += f" (Code: {error_code_num})"
        
        super().__init__(detail=detail, error_code="PROGRAM_ERROR")
        self.extra_data = {
            "program_error": program_error,
            "error_code_num": error_code_num
        }


# === ОШИБКИ БАЗЫ ДАННЫХ ===

class DatabaseException(CustomHTTPException):
    """Базовый класс для ошибок базы данных"""
    
    def __init__(self, detail: str = "Database error"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="DATABASE_ERROR"
        )


class RecordNotFoundException(DatabaseException):
    """Запись не найдена в базе данных"""
    
    def __init__(self, model: str, identifier: Union[str, int]):
        super().__init__(
            detail=f"{model} with id {identifier} not found",
            error_code="RECORD_NOT_FOUND"
        )
        self.status_code = status.HTTP_404_NOT_FOUND
        self.extra_data = {"model": model, "id": identifier}


class DuplicateRecordException(DatabaseException):
    """Попытка создания дублирующей записи"""
    
    def __init__(self, model: str, field: str, value: Any):
        super().__init__(
            detail=f"{model} with {field}={value} already exists",
            error_code="DUPLICATE_RECORD"
        )
        self.status_code = status.HTTP_409_CONFLICT
        self.extra_data = {"model": model, "field": field, "value": value}


class DatabaseConnectionException(DatabaseException):
    """Ошибка подключения к базе данных"""
    
    def __init__(self):
        super().__init__(
            detail="Unable to connect to database",
            error_code="DATABASE_CONNECTION_ERROR"
        )


# === ОШИБКИ КЭША ===

class CacheException(CustomHTTPException):
    """Ошибки системы кэширования"""
    
    def __init__(self, detail: str = "Cache error"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="CACHE_ERROR"
        )


class RedisConnectionException(CacheException):
    """Ошибка подключения к Redis"""
    
    def __init__(self):
        super().__init__(
            detail="Unable to connect to Redis cache",
            error_code="REDIS_CONNECTION_ERROR"
        )


# === ОШИБКИ БЕЗОПАСНОСТИ ===

class SecurityException(CustomHTTPException):
    """Базовый класс для ошибок безопасности"""
    
    def __init__(self, detail: str, error_code: str = "SECURITY_ERROR"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code=error_code
        )


class SuspiciousActivityException(SecurityException):
    """Обнаружена подозрительная активность"""
    
    def __init__(self, activity_type: str):
        super().__init__(
            detail=f"Suspicious activity detected: {activity_type}",
            error_code="SUSPICIOUS_ACTIVITY"
        )
        self.extra_data = {"activity_type": activity_type}


class BotActivityException(SecurityException):
    """Обнаружена активность бота"""
    
    def __init__(self):
        super().__init__(
            detail="Bot activity detected. Please verify you are human.",
            error_code="BOT_ACTIVITY"
        )


class SpamProtectionException(SecurityException):
    """Срабатывание защиты от спама"""
    
    def __init__(self, cooldown_seconds: int):
        super().__init__(
            detail=f"Spam protection triggered. Please wait {cooldown_seconds} seconds.",
            error_code="SPAM_PROTECTION"
        )
        self.extra_data = {"cooldown_seconds": cooldown_seconds}


# === ОШИБКИ ВНЕШНИХ СЕРВИСОВ ===

class ExternalServiceException(CustomHTTPException):
    """Ошибки внешних сервисов"""
    
    def __init__(self, service: str, detail: str = "External service error"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{service}: {detail}",
            error_code="EXTERNAL_SERVICE_ERROR"
        )
        self.extra_data = {"service": service}


class PriceFeedException(ExternalServiceException):
    """Ошибки получения данных о ценах"""
    
    def __init__(self, detail: str = "Price feed unavailable"):
        super().__init__(service="Price Feed", detail=detail)
        self.error_code = "PRICE_FEED_ERROR"


# === UTILITY ФУНКЦИИ ===

def handle_database_error(error: Exception) -> DatabaseException:
    """
    Конвертация ошибок SQLAlchemy в кастомные исключения
    """
    error_str = str(error)
    
    if "duplicate key" in error_str.lower():
        return DuplicateRecordException("Record", "unknown", "unknown")
    elif "not found" in error_str.lower():
        return RecordNotFoundException("Record", "unknown")
    elif "connection" in error_str.lower():
        return DatabaseConnectionException()
    else:
        return DatabaseException(f"Database error: {error_str}")


def handle_solana_error(error: Exception) -> BlockchainException:
    """
    Конвертация ошибок Solana в кастомные исключения
    """
    error_str = str(error)
    
    if "insufficient" in error_str.lower() and "sol" in error_str.lower():
        return InsufficientSolException(0.001)  # Примерная сумма
    elif "transaction failed" in error_str.lower():
        return TransactionFailedException("unknown", error_str)
    elif "rpc" in error_str.lower():
        return SolanaRpcException(error_str)
    else:
        return BlockchainException(f"Blockchain error: {error_str}")


def handle_redis_error(error: Exception) -> CacheException:
    """
    Конвертация ошибок Redis в кастомные исключения
    """
    error_str = str(error)
    
    if "connection" in error_str.lower():
        return RedisConnectionException()
    else:
        return CacheException(f"Cache error: {error_str}")


# === EXCEPTION MAPPING ===

EXCEPTION_MAPPING = {
    "ValidationError": ValidationException,
    "AuthenticationError": AuthenticationException,
    "AuthorizationError": AuthorizationException,
    "TradingError": TradingException,
    "BlockchainError": BlockchainException,
    "DatabaseError": DatabaseException,
    "CacheError": CacheException,
    "SecurityError": SecurityException,
}