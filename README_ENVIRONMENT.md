# 🚀 Environment Setup - Quick Start Guide

Быстрый старт для всех окружений Anonymeme Platform.

## 📋 Prerequisites

Убедитесь, что у вас установлены:
- Docker & Docker Compose
- Python 3.8+
- Node.js 18+
- Git

## 🛠️ Development Environment

Для локальной разработки:

```bash
# 1. Клонируйте репозиторий
git clone <repository-url>
cd anonymeme

# 2. Автоматическая настройка
./scripts/env/setup-environment.sh development

# 3. Проверьте сервисы
docker-compose -f docker-compose.development.yml ps
```

**Готово!** Ваши сервисы доступны по адресам:
- 🌐 Frontend: http://localhost:3000
- ⚡ Backend API: http://localhost:8000
- 🔄 WebSocket: ws://localhost:8001
- 📊 Grafana: http://localhost:3001 (admin/admin123)
- 🔍 Prometheus: http://localhost:9090

## 🧪 Staging Environment

Для staging окружения:

```bash
# 1. Настройте AWS credentials
export AWS_REGION=us-west-2
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret

# 2. Запустите setup
./scripts/env/setup-environment.sh staging

# 3. Запустите сервисы
docker-compose -f docker-compose.staging.yml up -d
```

## 🚀 Production Environment

Для production:

```bash
# 1. Настройте все необходимые переменные
export AWS_REGION=us-west-2
# ... другие переменные

# 2. Запустите setup
./scripts/env/setup-environment.sh production

# 3. Деплой (Docker Swarm)
docker stack deploy -c docker-compose.production.yml anonymeme-prod
```

## 🔐 Secrets Management

### Development (локальные secrets)
```bash
# Генерация всех secrets
./scripts/secrets/secrets-manager.py --provider local --environment development generate

# Экспорт в .env файл
./scripts/secrets/secrets-manager.py --provider local --environment development export
```

### Staging/Production (AWS Secrets Manager)
```bash
# Генерация secrets в AWS
./scripts/secrets/secrets-manager.py --provider aws --environment staging generate

# Ротация secrets
./scripts/secrets/secrets-manager.py --provider aws --environment production rotate
```

## 🔄 Environment Switching

```bash
# Остановка текущего окружения
docker-compose -f docker-compose.development.yml down

# Переключение на staging
docker-compose -f docker-compose.staging.yml up -d

# Переключение обратно
docker-compose -f docker-compose.staging.yml down
docker-compose -f docker-compose.development.yml up -d
```

## 📊 Мониторинг

### Development
- **Grafana**: http://localhost:3001 (admin/admin123)
- **Prometheus**: http://localhost:9090  
- **Redis UI**: http://localhost:8081
- **Database UI**: http://localhost:8080
- **Email Testing**: http://localhost:8025

### Staging/Production
- **Grafana**: https://{env}-grafana.anonymeme.io
- **Prometheus**: https://{env}-prometheus.anonymeme.io
- **Alerts**: Integrated with Slack/PagerDuty

## 🐛 Troubleshooting

### Проблема: Сервисы не запускаются
```bash
# Проверьте Docker
docker info

# Проверьте логи
docker-compose -f docker-compose.development.yml logs

# Пересоздайте контейнеры
docker-compose -f docker-compose.development.yml down -v
docker-compose -f docker-compose.development.yml up -d --build
```

### Проблема: Database connection error
```bash
# Проверьте PostgreSQL
docker-compose -f docker-compose.development.yml logs postgres

# Перезапустите БД
docker-compose -f docker-compose.development.yml restart postgres
```

### Проблема: Secrets не найдены
```bash
# Сгенерируйте заново
./scripts/secrets/secrets-manager.py --provider local --environment development generate --force

# Проверьте список
./scripts/secrets/secrets-manager.py --provider local --environment development list
```

## 📝 Environment Files

```
.env.example          # Template для всех сред
.env.development      # Development настройки
.env.staging          # Staging настройки  
.env.production       # Production настройки
```

## 🔗 Дополнительная документация

- [📖 Environment Management Guide](./docs/ENVIRONMENT_MANAGEMENT.md)
- [🔐 Security Guide](./docs/SECURITY.md) 
- [🚀 Deployment Guide](./docs/DEPLOYMENT.md)
- [📊 Monitoring Guide](./docs/MONITORING.md)

## ⚡ Quick Commands

```bash
# Просмотр статуса сервисов
docker-compose -f docker-compose.development.yml ps

# Просмотр логов
docker-compose -f docker-compose.development.yml logs -f [service]

# Перезапуск сервиса
docker-compose -f docker-compose.development.yml restart [service]

# Остановка всех сервисов
docker-compose -f docker-compose.development.yml down

# Полная очистка (⚠️ удалит данные)
docker-compose -f docker-compose.development.yml down -v --remove-orphans
```

## 🎯 What's Next?

После успешного запуска окружения:

1. ✅ Проверьте health checks всех сервисов
2. ✅ Запустите тесты: `npm test` или `pytest`
3. ✅ Ознакомьтесь с API документацией: http://localhost:8000/docs
4. ✅ Настройте IDE для development
5. ✅ Изучите monitoring dashboards

Удачной разработки! 🚀