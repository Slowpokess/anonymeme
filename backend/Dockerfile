# ===================================================================
# Anonymeme Backend Dockerfile
# Production-ready multi-stage build for FastAPI application
# ===================================================================

# === STAGE 1: Base image with Python ===
FROM python:3.11-slim as base

# Метаданные
LABEL maintainer="Anonymeme Team"
LABEL version="1.0.0"
LABEL description="Anonymeme Backend API"

# Переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.6.1

# Создание пользователя для безопасности
RUN groupadd -r anonymeme && useradd -r -g anonymeme anonymeme

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# === STAGE 2: Development dependencies ===
FROM base as dev-deps

# Установка Poetry для управления зависимостями
RUN pip install poetry==$POETRY_VERSION

# Копирование файлов зависимостей
WORKDIR /app
COPY requirements.txt ./

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# === STAGE 3: Production image ===
FROM base as production

# Установка runtime зависимостей
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Создание директорий приложения
WORKDIR /app
RUN chown anonymeme:anonymeme /app

# Копирование зависимостей из dev-deps stage
COPY --from=dev-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dev-deps /usr/local/bin /usr/local/bin

# Копирование исходного кода
COPY --chown=anonymeme:anonymeme . .

# Создание директорий для логов и временных файлов
RUN mkdir -p /app/logs /app/tmp && \
    chown -R anonymeme:anonymeme /app/logs /app/tmp

# Переключение на непривилегированного пользователя
USER anonymeme

# Настройка переменных окружения
ENV PYTHONPATH=/app \
    PORT=8000 \
    HOST=0.0.0.0 \
    WORKERS=4

# Здоровье приложения
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Экспорт портов
EXPOSE $PORT

# === STAGE 4: Development image ===
FROM dev-deps as development

# Установка дополнительных dev зависимостей
RUN pip install --no-cache-dir \
    jupyter \
    ipython \
    pytest-watch \
    debugpy

# Копирование исходного кода
COPY --chown=anonymeme:anonymeme . .

# Переключение на пользователя
USER anonymeme

# Команда для разработки с hot-reload
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]

# === STAGE 5: Testing image ===
FROM dev-deps as testing

# Копирование исходного кода и тестов
COPY --chown=anonymeme:anonymeme . .

# Переключение на пользователя
USER anonymeme

# Команда для запуска тестов
CMD ["python", "-m", "pytest", "-v", "--cov=.", "--cov-report=html", "--cov-report=term"]

# === DEFAULT: Production stage ===
FROM production as final

# Команда по умолчанию для продакшена
CMD ["gunicorn", "api.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--timeout", "30", \
     "--keep-alive", "2", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]

# ===================================================================
# BUILD INSTRUCTIONS
# ===================================================================

# Development build:
# docker build --target development -t anonymeme-backend:dev .
# docker run -p 8000:8000 -v $(pwd):/app anonymeme-backend:dev

# Production build:
# docker build --target production -t anonymeme-backend:prod .
# docker run -p 8000:8000 anonymeme-backend:prod

# Testing build:
# docker build --target testing -t anonymeme-backend:test .
# docker run anonymeme-backend:test

# Multi-platform build:
# docker buildx build --platform linux/amd64,linux/arm64 -t anonymeme-backend:latest .

# ===================================================================
# ENVIRONMENT VARIABLES
# ===================================================================

# Required environment variables:
# - DATABASE_URL: PostgreSQL connection string
# - REDIS_URL: Redis connection string
# - SECRET_KEY: JWT secret key
# - SOLANA_RPC_URL: Solana RPC endpoint

# Optional environment variables:
# - DEBUG: Enable debug mode (default: false)
# - LOG_LEVEL: Logging level (default: info)
# - WORKERS: Number of worker processes (default: 4)
# - MAX_REQUESTS: Max requests per worker (default: 1000)

# Example docker-compose.yml:
# version: '3.8'
# services:
#   backend:
#     build: .
#     ports:
#       - "8000:8000"
#     environment:
#       - DATABASE_URL=postgresql://user:pass@db:5432/anonymeme
#       - REDIS_URL=redis://redis:6379
#       - SECRET_KEY=your-secret-key
#     depends_on:
#       - db
#       - redis