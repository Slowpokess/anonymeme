# 🌍 Environment Management Guide

Comprehensive руководство по управлению окружениями для Anonymeme Platform.

## 📋 Обзор

Anonymeme Platform поддерживает три основных окружения:
- **Development** - Локальная разработка
- **Staging** - Тестирование production-like среды
- **Production** - Боевая среда

## 🔐 Структура Environment Variables

### Категории переменных:

1. **🌍 Environment Configuration** - Основные настройки окружения
2. **🗄️ Database Configuration** - Настройки PostgreSQL и Redis
3. **🌐 Solana Blockchain** - Конфигурация блокчейна
4. **🔐 Security & Authentication** - JWT, шифрование, CORS
5. **📊 API Configuration** - Настройки API сервера
6. **🔌 WebSocket Configuration** - Real-time соединения
7. **⚡ Background Tasks** - Celery и задачи
8. **📈 Monitoring** - Prometheus, Grafana, логирование
9. **🌐 Frontend** - Next.js настройки
10. **💰 Platform Business Logic** - Торговые комиссии, лимиты

## 🚀 Quick Start

### Development Environment

```bash
# 1. Клонируйте репозиторий
git clone <repository-url>
cd anonymeme

# 2. Запустите setup скрипт
./scripts/env/setup-environment.sh development

# 3. Запустите сервисы
docker-compose -f docker-compose.development.yml up -d

# 4. Проверьте статус
docker-compose -f docker-compose.development.yml ps
```

### Staging Environment

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

### Production Environment

```bash
# 1. Настройте AWS и другие внешние сервисы
export AWS_REGION=us-west-2
# ... другие переменные

# 2. Запустите setup
./scripts/env/setup-environment.sh production

# 3. Деплой через Docker Swarm или Kubernetes
docker stack deploy -c docker-compose.production.yml anonymeme-prod
```

## 🔐 Secrets Management

### Архитектура Secrets

```
Local Development:
~/.anonymeme/secrets/development/
├── development_db_password.txt
├── development_jwt_secret.txt
└── ...

Staging (AWS Secrets Manager):
anonymeme/staging/
├── staging_db_password
├── staging_jwt_secret
└── ...

Production (AWS Secrets Manager + KMS):
anonymeme/prod/
├── prod_db_password (encrypted with KMS)
├── prod_jwt_secret (encrypted with KMS)
└── ...
```

### Использование Secrets Manager

```bash
# Генерация secrets для development
./scripts/secrets/secrets-manager.py --provider local --environment development generate

# Генерация secrets для staging
./scripts/secrets/secrets-manager.py --provider aws --environment staging generate

# Получение specific secret
./scripts/secrets/secrets-manager.py --provider aws --environment production get prod_jwt_secret

# Ротация secrets
./scripts/secrets/secrets-manager.py --provider aws --environment production rotate

# Экспорт для development
./scripts/secrets/secrets-manager.py --provider local --environment development export
```

## 📁 Структура файлов

```
anonymeme/
├── .env.example                    # Template для всех сред
├── .env.development                # Development переменные
├── .env.staging                    # Staging переменные  
├── .env.production                 # Production переменные
├── docker-compose.yml             # Базовая конфигурация
├── docker-compose.development.yml # Development compose
├── docker-compose.staging.yml     # Staging compose
├── docker-compose.production.yml  # Production compose
├── scripts/
│   ├── env/
│   │   └── setup-environment.sh   # Setup скрипт
│   └── secrets/
│       ├── secrets-manager.py     # Secrets manager
│       ├── secrets-development.json
│       ├── secrets-staging.json
│       └── secrets-production.json
└── infrastructure/
    ├── monitoring/
    │   ├── prometheus.development.yml
    │   ├── prometheus.staging.yml
    │   └── prometheus.production.yml
    ├── nginx/
    │   ├── development.conf
    │   ├── staging.conf
    │   └── production.conf
    └── ssl/
        ├── development/
        ├── staging/
        └── production/
```

## 🔧 Конфигурация по средам

### Development
- **Цель**: Локальная разработка и тестирование
- **Secrets**: Локальное хранение
- **Database**: Local PostgreSQL
- **SSL**: Отключен
- **Monitoring**: Базовый Grafana/Prometheus
- **Особенности**: Hot reload, debug режим, relaxed security

### Staging  
- **Цель**: Production-like тестирование
- **Secrets**: AWS Secrets Manager
- **Database**: AWS RDS или аналог
- **SSL**: Self-signed certificates
- **Monitoring**: Полный stack с alerting
- **Особенности**: Real services, но test data

### Production
- **Цель**: Боевая среда
- **Secrets**: AWS Secrets Manager + KMS + Cross-region replication
- **Database**: High-availability PostgreSQL cluster
- **SSL**: Valid certificates (Let's Encrypt/Commercial)
- **Monitoring**: Full observability с SLA monitoring
- **Особенности**: Maximum security, redundancy, compliance

## 🚨 Security Best Practices

### General
1. **Never commit secrets** в git
2. **Use different secrets** для каждой среды  
3. **Rotate secrets regularly** (automated для production)
4. **Use external secret managers** для staging/production
5. **Encrypt secrets at rest** и in transit

### Development
- ✅ Local secrets storage допустимо
- ✅ Simplified authentication для удобства
- ✅ Mock external services
- ⚠️ Never use production data

### Staging
- ✅ External secret manager (AWS/GCP/Vault)
- ✅ Production-like security но test data
- ✅ Automated secret rotation
- ⚠️ Separate AWS account/project

### Production
- ✅ Enterprise-grade secret management
- ✅ Multi-factor authentication
- ✅ Approval workflows для secret changes
- ✅ Audit logging всех access
- ✅ Cross-region replication
- ✅ Compliance requirements (GDPR, etc.)

## 📊 Monitoring & Observability

### Development
```yaml
Services:
  - Grafana: http://localhost:3001 (admin/admin123)
  - Prometheus: http://localhost:9090
  - Redis Commander: http://localhost:8081
  - pgAdmin: http://localhost:8080
  - MailHog: http://localhost:8025
  - Jaeger: http://localhost:16686
```

### Staging/Production
```yaml
Services:
  - Grafana: https://{env}-grafana.anonymeme.io
  - Prometheus: https://{env}-prometheus.anonymeme.io
  - AlertManager: Integrated
  - Log Aggregation: Fluentd → CloudWatch/ELK
  - Distributed Tracing: Jaeger
  - Uptime Monitoring: External service
```

## 🔄 Environment Switching

### Быстрое переключение
```bash
# Остановка текущего environment
docker-compose -f docker-compose.development.yml down

# Переключение на staging
docker-compose -f docker-compose.staging.yml up -d

# Проверка статуса
docker-compose -f docker-compose.staging.yml ps
```

### Переключение secrets provider
```bash
# Экспорт secrets из AWS в local для testing
./scripts/secrets/secrets-manager.py --provider aws --environment staging export --output .env.staging.secrets

# Импорт в local storage
./scripts/secrets/secrets-manager.py --provider local --environment staging generate
```

## 🐛 Troubleshooting

### Общие проблемы

#### 1. Secrets не найдены
```bash
# Проверить secrets
./scripts/secrets/secrets-manager.py --provider local --environment development list

# Сгенерировать заново
./scripts/secrets/secrets-manager.py --provider local --environment development generate --force
```

#### 2. Database connection error
```bash
# Проверить статус PostgreSQL
docker-compose -f docker-compose.development.yml ps postgres

# Проверить логи
docker-compose -f docker-compose.development.yml logs postgres

# Перезапустить
docker-compose -f docker-compose.development.yml restart postgres
```

#### 3. Environment variables не загружены
```bash
# Проверить .env файл
cat .env.development

# Проверить права доступа
ls -la .env.development

# Пересоздать environment
./scripts/env/setup-environment.sh development --no-start
```

#### 4. SSL certificate проблемы
```bash
# Для staging - перегенерировать self-signed
openssl req -x509 -newkey rsa:4096 -keyout infrastructure/ssl/staging/key.pem \
    -out infrastructure/ssl/staging/cert.pem -days 365 -nodes \
    -subj "/C=US/ST=CA/L=SF/O=Anonymeme/CN=staging.anonymeme.io"
```

## 📝 Environment Variables Reference

### Critical Variables
```bash
# Must be set для всех сред
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379
JWT_SECRET=your-secret-key
SOLANA_RPC_URL=https://api.solana.com

# Environment-specific
NODE_ENV=development|staging|production
ENVIRONMENT=development|staging|production
DEBUG=true|false
LOG_LEVEL=debug|info|warn|error
```

### Optional но Recommended
```bash
# Monitoring
ENABLE_METRICS=true
PROMETHEUS_PORT=9090
GRAFANA_ADMIN_PASSWORD=secure-password

# Security
ENABLE_ANTI_BOT=true
RATE_LIMIT_PER_MINUTE=60
CORS_ORIGINS=https://domain.com

# Performance
API_REQUEST_TIMEOUT=30000
REDIS_POOL_SIZE=10
DB_POOL_MAX=20
```

## 🔄 Migration между средами

### Development → Staging
1. Export development configuration
2. Update secrets для staging
3. Setup staging infrastructure
4. Deploy и test
5. Update DNS/routing

### Staging → Production  
1. Security audit
2. Performance testing
3. Backup staging data
4. Setup production infrastructure
5. Blue-green deployment
6. Monitor и rollback plan

## 📋 Checklist для Production Deploy

### Pre-deployment
- [ ] All secrets rotated и secure
- [ ] SSL certificates valid
- [ ] Monitoring configured
- [ ] Backup strategy implemented
- [ ] Disaster recovery plan
- [ ] Security scan passed
- [ ] Performance testing passed
- [ ] Compliance requirements met

### Post-deployment
- [ ] Health checks passing
- [ ] Monitoring alerts configured
- [ ] Log aggregation working
- [ ] Backup verification
- [ ] User acceptance testing
- [ ] Performance monitoring
- [ ] Security monitoring

## 🔗 Related Documentation

- [Security Guide](./SECURITY.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Monitoring Guide](./MONITORING.md)
- [API Documentation](./API.md)
- [Development Guide](./DEVELOPMENT.md)