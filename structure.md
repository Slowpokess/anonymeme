crypto-pump-anon
├── contracts
│   ├── bonding_curve_contract (Rust, Anchor)
│   │   ├── src
│   │   ├── tests
│   │   └── Cargo.toml
│   ├── token_management_contract (Rust, Anchor)
│   │   ├── src
│   │   ├── tests
│   │   └── Cargo.toml
│   └── dex_listing_contract (Raydium/Jupiter integration)
│       ├── src
│       ├── tests
│       └── Cargo.toml
│
├── backend
│   ├── api (FastAPI)
│   │   ├── routes
│   │   ├── models
│   │   ├── schemas
│   │   ├── services
│   │   └── main.py
│   ├── worker (асинхронные задачи Celery)
│   │   ├── tasks
│   │   ├── scheduler
│   │   └── worker.py
│   ├── websocket_service (для UI real-time данных)
│   │   ├── events
│   │   └── server.py
│   ├── tests
│   │   ├── unit_tests
│   │   └── integration_tests
│   └── Dockerfile
│
├── frontend
│   ├── components (React, Next.js)
│   ├── pages
│   │   ├── index.tsx
│   │   ├── create_token.tsx
│   │   ├── trade.tsx
│   │   └── analytics.tsx
│   ├── hooks (Web3.js, RPC)
│   ├── utils (шифрование, приватность, утилиты)
│   ├── styles (Tailwind CSS + кастомные стили)
│   ├── public (статические ресурсы)
│   ├── tests (Jest, Cypress)
│   └── Dockerfile
│
├── infrastructure
│   ├── docker-compose.yml (для локального запуска)
│   ├── kubernetes
│   │   ├── deployments
│   │   ├── services
│   │   ├── ingress
│   │   ├── configmaps
│   │   └── secrets
│   ├── terraform (Infrastructure-as-Code, управление облаком)
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── monitoring (Prometheus, Grafana, Loki, alertmanager)
│   │   ├── prometheus.yml
│   │   ├── grafana-dashboard.json
│   │   └── alert_rules.yml
│   └── security
│       ├── cloudflare-onion-config.yaml
│       ├── ddos_protection_config.yaml
│       └── tor_hidden_service.conf
│
├── scripts (полезные bash/python-скрипты для деплоя, миграций)
│   ├── deploy_contracts.sh
│   ├── migrate_database.py
│   └── create_token_script.js
│
├── ci-cd (GitHub Actions / GitLab CI)
│   ├── build.yml
│   ├── test.yml
│   └── deploy.yml
│
├── docs
│   ├── whitepaper.md
│   ├── privacy_policy.md
│   ├── security.md (описание мер защиты)
│   ├── api_documentation.md
│   └── user_guide.md
│
├── .github
│   ├── workflows (CI/CD actions)
│   ├── ISSUE_TEMPLATE
│   └── PULL_REQUEST_TEMPLATE.md
│
├── .env.example (шаблоны переменных окружения)
├── .gitignore
└── README.md
