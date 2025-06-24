# 📊 Anonymeme Platform Monitoring Stack

Comprehensive monitoring solution для Anonymeme Platform с использованием Prometheus, Grafana, и других современных инструментов.

## 🏗️ Architecture Overview

### Core Components

- **Prometheus** - Сбор и хранение метрик
- **Grafana** - Визуализация и дашборды
- **Alertmanager** - Управление alert'ами и уведомлениями
- **Jaeger** - Distributed tracing
- **ELK Stack** - Централизованное логирование

### Exporters & Collectors

- **Node Exporter** - Системные метрики (CPU, Memory, Disk, Network)
- **cAdvisor** - Метрики Docker контейнеров
- **Postgres Exporter** - Метрики базы данных
- **Redis Exporter** - Метрики кеша
- **Blackbox Exporter** - Мониторинг внешних сервисов
- **Custom Solana Exporter** - Метрики blockchain'а
- **Application Metrics Collector** - Бизнес-метрики

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- 4GB+ RAM для полного monitoring stack
- Настроенные environment variables

### Environment Variables

Создайте `.env` файл:

```bash
# Environment
ENVIRONMENT=development
AWS_REGION=us-west-2

# Database
DB_HOST=postgres
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=anonymeme

# Redis
REDIS_HOST=redis
REDIS_PASSWORD=

# Monitoring Credentials
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your_secure_password
METRICS_USERNAME=metrics
METRICS_PASSWORD=metrics_secret

# Slack Notifications
SLACK_WEBHOOK_DEFAULT=https://hooks.slack.com/services/...
SLACK_WEBHOOK_CRITICAL=https://hooks.slack.com/services/...
SLACK_WEBHOOK_DEVOPS=https://hooks.slack.com/services/...
SLACK_WEBHOOK_SECURITY=https://hooks.slack.com/services/...
SLACK_WEBHOOK_BUSINESS=https://hooks.slack.com/services/...

# Email Notifications
SMTP_HOST=smtp.gmail.com:587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
CRITICAL_ALERTS_EMAIL=critical@anonymeme.io
DEVOPS_EMAIL=devops@anonymeme.io
SECURITY_EMAIL=security@anonymeme.io

# PagerDuty Integration
PAGERDUTY_DEVOPS_KEY=your_pagerduty_integration_key
PAGERDUTY_SECURITY_KEY=your_security_pagerduty_key

# Solana Configuration
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_WS_URL=wss://api.mainnet-beta.solana.com
CONTRACT_ADDRESS=your_contract_address
```

### Deployment

1. **Start Monitoring Stack:**
```bash
# Basic monitoring (Prometheus + Grafana + Alertmanager)
docker-compose -f monitoring/docker-compose.monitoring.yml up -d prometheus grafana alertmanager

# Full stack с exporters
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Только specific services
docker-compose -f monitoring/docker-compose.monitoring.yml up -d prometheus grafana node-exporter
```

2. **Verify Services:**
```bash
# Check all services are running
docker-compose -f monitoring/docker-compose.monitoring.yml ps

# View logs
docker-compose -f monitoring/docker-compose.monitoring.yml logs -f prometheus
```

3. **Access Dashboards:**
- **Grafana:** http://localhost:3030 (admin/admin123)
- **Prometheus:** http://localhost:9090
- **Alertmanager:** http://localhost:9093
- **Jaeger:** http://localhost:16686
- **Kibana:** http://localhost:5601

## 📊 Dashboards

### Available Dashboards

1. **System Overview** - Общий обзор платформы
   - Service health status
   - API metrics (request rate, response time, error rate)
   - System resources usage
   - Business metrics (trading volume, active users)

2. **API Dashboard** - Детальные API метрики
   - Endpoint-specific performance
   - Error breakdown by endpoint
   - Rate limiting metrics
   - Authentication metrics

3. **Infrastructure Dashboard** - Системная инфраструктура
   - Server resources (CPU, Memory, Disk, Network)
   - Container metrics
   - Database performance
   - Cache performance

4. **Business Dashboard** - Бизнес-метрики
   - Trading volume and trends
   - User activity metrics
   - Token creation and performance
   - Revenue metrics

5. **Security Dashboard** - Безопасность
   - Authentication failures
   - Rate limiting hits
   - Suspicious activity detection
   - Security scan results

### Dashboard Import

Dashboards автоматически загружаются через Grafana provisioning. Для manual import:

1. Open Grafana → Import
2. Upload JSON files from `monitoring/grafana/dashboards/`
3. Configure data source (Prometheus)

## 🚨 Alerting

### Alert Levels

- **Critical** - Требует немедленного вмешательства
  - Service down
  - High error rates (>10%)
  - Resource exhaustion (>95%)
  - Security incidents

- **Warning** - Требует внимания
  - Elevated response times
  - Moderate resource usage (>70%)
  - Performance degradation

### Notification Channels

1. **Slack Integration**
   - Different channels для разных team'ов
   - Critical alerts → immediate notifications
   - Warning alerts → regular notifications

2. **Email Notifications**
   - Critical alerts → executive team
   - Team-specific alerts → responsible teams

3. **PagerDuty Integration**
   - After-hours critical alerts
   - Escalation policies
   - On-call rotations

### Alert Configuration

Alerts настраиваются в файлах:
- `monitoring/prometheus/alerts/critical.yml`
- `monitoring/prometheus/alerts/warning.yml`

Routing и notification настройки:
- `monitoring/alertmanager/alertmanager.yml`

## 📈 Metrics Collection

### System Metrics

- **CPU Usage** - по сервисам и общий
- **Memory Usage** - использование RAM и swap
- **Disk Usage** - свободное место и I/O
- **Network I/O** - трафик и ошибки

### Application Metrics

- **API Performance** - response time, throughput, errors
- **Database Metrics** - connections, queries, performance
- **Cache Metrics** - hit rate, memory usage, connections
- **Authentication** - login attempts, failures, sessions

### Business Metrics

- **Trading Volume** - объем торгов по периодам
- **User Activity** - активные пользователи, регистрации
- **Token Metrics** - создание, performance, market cap
- **Transaction Metrics** - success rate, volume, fees

### Security Metrics

- **Failed Authentications** - rate и patterns
- **Rate Limiting** - hits и blocked requests
- **Suspicious Activity** - anomaly detection scores
- **Vulnerability Scans** - results и trends

## 🔧 Configuration

### Prometheus Configuration

Основная конфигурация в `monitoring/prometheus/prometheus.yml`:

- **Scrape Intervals** - 15s default, 5s для trading metrics
- **Retention** - 30 days data retention
- **Storage** - 50GB limit с compression
- **Security** - basic auth для protected endpoints

### Recording Rules

Recording rules в `monitoring/prometheus/rules/application.yml`:

- **Performance Aggregations** - 5min averages
- **Business Metrics** - hourly summaries
- **Resource Usage** - by-service aggregations
- **SLA Calculations** - availability и error budgets

### Grafana Provisioning

Автоматическая настройка через:
- `monitoring/grafana/provisioning/datasources/`
- `monitoring/grafana/provisioning/dashboards/`

## 🔍 Troubleshooting

### Common Issues

1. **High Memory Usage**
```bash
# Check Prometheus memory usage
docker stats anonymeme-prometheus

# Reduce retention if needed
# Edit prometheus.yml: --storage.tsdb.retention.time=15d
```

2. **Missing Metrics**
```bash
# Check scrape targets
curl http://localhost:9090/api/v1/targets

# Check specific exporter
curl http://localhost:9100/metrics  # Node exporter
curl http://localhost:9187/metrics  # Postgres exporter
```

3. **Alert Not Firing**
```bash
# Check alert rules
curl http://localhost:9090/api/v1/rules

# Check alertmanager config
curl http://localhost:9093/api/v1/status
```

### Health Checks

```bash
# Check all services health
./scripts/monitoring/health_check.sh

# Individual service checks
curl -f http://localhost:9090/-/healthy  # Prometheus
curl -f http://localhost:3030/api/health # Grafana
curl -f http://localhost:9093/-/healthy  # Alertmanager
```

### Log Analysis

```bash
# View service logs
docker-compose -f monitoring/docker-compose.monitoring.yml logs -f prometheus
docker-compose -f monitoring/docker-compose.monitoring.yml logs -f grafana
docker-compose -f monitoring/docker-compose.monitoring.yml logs -f alertmanager

# Check for errors
docker-compose -f monitoring/docker-compose.monitoring.yml logs | grep ERROR
```

## 🛡️ Security

### Access Control

- **Grafana Authentication** - admin user с secure password
- **Prometheus Security** - basic auth для sensitive endpoints
- **Network Isolation** - dedicated monitoring network
- **SSL/TLS** - для production environments

### Data Protection

- **Metrics Anonymization** - remove sensitive data
- **Access Logs** - audit trail для dashboard access
- **Backup Strategy** - regular backups важных dashboards
- **Retention Policies** - data cleanup по schedule

## 📚 Documentation

### Runbooks

- [Service Down Runbook](runbooks/service-down.md)
- [High CPU Usage](runbooks/high-cpu.md)
- [Database Issues](runbooks/database-issues.md)
- [Security Incidents](runbooks/security-incidents.md)

### Team Resources

- [On-Call Guide](docs/oncall-guide.md)
- [Dashboard Creation](docs/dashboard-creation.md)
- [Alert Tuning](docs/alert-tuning.md)
- [Performance Analysis](docs/performance-analysis.md)

## 🔄 Maintenance

### Regular Tasks

1. **Weekly**
   - Review alert noise и tune thresholds
   - Check dashboard usage и optimize
   - Update exported data sources
   - Review system performance trends

2. **Monthly**
   - Clean up old metrics data
   - Review и update alert rules
   - Update monitoring stack versions
   - Conduct monitoring system health check

3. **Quarterly**
   - Capacity planning review
   - Security audit мониторинга
   - Team training updates
   - Disaster recovery testing

### Backup & Recovery

```bash
# Backup Grafana dashboards
./scripts/monitoring/backup_dashboards.sh

# Backup Prometheus data
./scripts/monitoring/backup_metrics.sh

# Restore from backup
./scripts/monitoring/restore_backup.sh
```

## 🤝 Contributing

### Adding New Metrics

1. Add metric collection в appropriate exporter
2. Update Prometheus scrape config
3. Create or update Grafana dashboard
4. Add relevant alerts если needed
5. Update documentation

### Dashboard Development

1. Create dashboard в Grafana UI
2. Export JSON configuration
3. Add to `monitoring/grafana/dashboards/`
4. Test automated provisioning
5. Update team documentation

## 📞 Support

### Team Contacts

- **DevOps Team:** devops@anonymeme.io
- **Security Team:** security@anonymeme.io
- **On-Call:** oncall@anonymeme.io

### Emergency Procedures

1. **Critical System Down:**
   - Check #alerts-critical Slack channel
   - Follow service-down runbook
   - Escalate to on-call engineer

2. **Monitoring System Issues:**
   - Check monitoring stack health
   - Review logs для error messages
   - Contact DevOps team для assistance

---

🔗 **Related Documentation:**
- [API Documentation](../docs/api.md)
- [Deployment Guide](../docs/deployment.md)
- [Security Guidelines](../docs/security.md)