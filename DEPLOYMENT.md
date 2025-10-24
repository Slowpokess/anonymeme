# Руководство по Deployment - Anonymeme Platform

Полное руководство по развертыванию платформы Anonymeme на Solana blockchain (devnet и mainnet).

## Содержание

- [Быстрый старт](#быстрый-старт)
- [Prerequisite](#prerequisite)
- [Smart Contracts](#smart-contracts)
  - [Компиляция через GitHub Actions](#компиляция-через-github-actions)
  - [Локальная компиляция](#локальная-компиляция)
  - [Deployment на Devnet](#deployment-на-devnet)
  - [Deployment на Mainnet](#deployment-на-mainnet)
- [Backend API](#backend-api)
- [Frontend](#frontend)
- [Post-Deployment](#post-deployment)
- [Troubleshooting](#troubleshooting)

---

## Быстрый старт

### Devnet (Тестирование)

```bash
# 1. Trigger компиляции через GitHub Actions
# Перейдите на GitHub → Actions → "Build and Deploy Contracts"
# → Run workflow → выберите "devnet" → Run

# 2. После успешной компиляции скачайте артефакты
# GitHub → Actions → выберите успешный run → Artifacts

# 3. Или используйте локальную компиляцию и деплой
cd contracts/pump-core
anchor build
anchor deploy --provider.cluster devnet
```

### Mainnet (Production)

⚠️ **ВНИМАНИЕ:** Deployment на mainnet требует тщательной подготовки и аудита!

```bash
# 1. Полный security audit
# 2. Extensive testing на devnet
# 3. Code review
# 4. Deployment через GitHub Actions с утверждением
```

---

## Prerequisite

### Инструменты для разработки

| Инструмент | Версия | Установка |
|------------|--------|-----------|
| **Rust** | 1.90.0+ | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| **Solana CLI** | 1.16.25 | `sh -c "$(curl -sSfL https://release.solana.com/v1.16.25/install)"` |
| **Anchor CLI** | 0.29.0 | `npm install -g @coral-xyz/anchor-cli@0.29.0` |
| **Node.js** | 20+ | `nvm install 20` |
| **Python** | 3.12+ | `pyenv install 3.12` |

### GitHub Secrets (для CI/CD)

Настройте следующие secrets в GitHub repository:

```bash
# Перейдите: Settings → Secrets and variables → Actions → New repository secret

# Для Devnet deployment
DEVNET_DEPLOY_KEYPAIR=<base64-encoded-keypair>

# Для Mainnet deployment
MAINNET_DEPLOY_KEYPAIR=<base64-encoded-keypair>

# Для Backend API
DATABASE_URL=postgresql://user:password@host:5432/database
REDIS_URL=redis://host:6379
SECRET_KEY=<your-secret-key>
JWT_SECRET_KEY=<your-jwt-secret>

# Для Frontend
NEXT_PUBLIC_API_URL=https://api.anonymeme.com
NEXT_PUBLIC_PUMP_CORE_PROGRAM_ID=<deployed-program-id>
NEXT_PUBLIC_CLUSTER=<mainnet-beta|devnet>
```

### Создание Deployment Keypair

```bash
# Для Devnet
solana-keygen new --outfile ~/.config/solana/devnet-deploy.json

# Для Mainnet
solana-keygen new --outfile ~/.config/solana/mainnet-deploy.json

# Показать адрес
solana-keygen pubkey ~/.config/solana/devnet-deploy.json

# Конвертировать в base64 для GitHub Secrets
cat ~/.config/solana/devnet-deploy.json | base64
```

### Пополнение кошелька

```bash
# Devnet (бесплатные SOL для тестирования)
solana config set --url devnet
solana airdrop 2

# Mainnet (купите SOL на бирже и переведите)
# Для deployment обычно требуется 2-5 SOL
```

---

## Smart Contracts

### Компиляция через GitHub Actions (Рекомендуется)

Это **предпочтительный метод** для production builds.

#### Шаги:

1. **Перейдите в GitHub Actions:**
   ```
   https://github.com/your-org/anonymeme/actions
   ```

2. **Выберите workflow:**
   - "Build and Deploy Contracts" для manual deployment
   - "Continuous Integration" для автоматической компиляции при push

3. **Запустите manual workflow:**
   - Нажмите "Run workflow"
   - Выберите параметры:
     - **environment**: `devnet` или `mainnet`
     - **deploy**: `true` для автоматического деплоя
     - **run_tests**: `true` для запуска тестов перед деплоем
   - Нажмите "Run workflow"

4. **Скачайте артефакты:**
   - Дождитесь завершения workflow
   - Скачайте artifacts:
     - `pump-core-program-{SHA}` - скомпилированная программа
     - `pump-core-idl-{SHA}` - IDL для SDK
     - `deployment-info-{env}-{SHA}` - метаданные деплоя (если деплой был выполнен)

#### Преимущества CI/CD компиляции:

- ✅ Reproducible builds
- ✅ Автоматические security scans
- ✅ Версионирование артефактов
- ✅ Полная audit trail
- ✅ Нет проблем с локальным окружением

### Локальная компиляция

Для быстрой итерации во время разработки.

```bash
# 1. Установить зависимости
cd contracts/pump-core
npm install

# 2. Скомпилировать
anchor build

# 3. Проверить результат
ls -lh target/deploy/pump_core.so

# 4. Показать Program ID
solana-keygen pubkey target/deploy/pump_core-keypair.json
```

Подробнее см. [contracts/pump-core/BUILD.md](contracts/pump-core/BUILD.md).

### Deployment на Devnet

#### Автоматический deployment через GitHub Actions:

1. Запустите workflow "Build and Deploy Contracts"
2. Выберите:
   - environment: `devnet`
   - deploy: `true`
   - run_tests: `true`
3. Workflow автоматически:
   - Скомпилирует программу
   - Запустит тесты
   - Задеплоит на devnet
   - Сохранит deployment metadata

#### Ручной deployment:

```bash
# 1. Настроить Solana CLI
solana config set --url devnet
solana config set --keypair ~/.config/solana/devnet-deploy.json

# 2. Проверить баланс
solana balance
# Если нужно, получить airdrop
solana airdrop 2

# 3. Deploy через Anchor
cd contracts/pump-core
anchor deploy --provider.cluster devnet

# 4. Получить Program ID
PROGRAM_ID=$(solana-keygen pubkey target/deploy/pump_core-keypair.json)
echo "Deployed Program ID: $PROGRAM_ID"

# 5. Verify deployment
solana program show $PROGRAM_ID

# 6. Initialize platform
anchor run initialize-platform --provider.cluster devnet
```

### Deployment на Mainnet

⚠️ **КРИТИЧЕСКИ ВАЖНО:** Следуйте этому чеклисту!

#### Pre-Deployment Checklist:

- [ ] **Security Audit**: Проведен полный аудит кода квалифицированной компанией
- [ ] **Extensive Testing**: Все тесты проходят на devnet
- [ ] **Code Review**: Минимум 2 senior разработчика проверили код
- [ ] **Penetration Testing**: Протестированы все возможные векторы атак
- [ ] **Economic Model**: Проверена математика bonding curves
- [ ] **Rug Pull Protection**: LP Token Lock работает корректно
- [ ] **Emergency Procedures**: Готов план действий при инцидентах
- [ ] **Monitoring**: Настроен мониторинг транзакций и ошибок
- [ ] **Multisig**: Используется multisig wallet для upgrade authority
- [ ] **Insurance**: Рассмотрено страхование протокола

#### Deployment Steps:

```bash
# 1. Final check на devnet
cd contracts/pump-core
anchor test --provider.cluster devnet

# 2. Настроить mainnet
solana config set --url mainnet-beta
solana config set --keypair ~/.config/solana/mainnet-deploy.json

# 3. Проверить баланс (нужно 2-5 SOL)
solana balance

# 4. Компиляция production build через GitHub Actions
# Используйте GitHub Actions для reproducible build!

# 5. Deploy (ТОЛЬКО через утвержденный процесс!)
anchor deploy --provider.cluster mainnet-beta

# 6. Получить Program ID
PROGRAM_ID=$(solana-keygen pubkey target/deploy/pump_core-keypair.json)
echo "Mainnet Program ID: $PROGRAM_ID"

# 7. Set upgrade authority to multisig
solana program set-upgrade-authority \
  $PROGRAM_ID \
  <MULTISIG_ADDRESS> \
  --keypair ~/.config/solana/mainnet-deploy.json

# 8. Verify on Solana Explorer
echo "Verify at: https://explorer.solana.com/address/$PROGRAM_ID"

# 9. Initialize platform с production параметрами
anchor run initialize-platform --provider.cluster mainnet-beta
```

#### Post-Deployment Mainnet:

```bash
# 1. Verify program deployment
solana program show $PROGRAM_ID

# 2. Test basic operations
# Создайте тестовый токен с минимальной суммой

# 3. Monitor transactions
# Настройте alerts для необычной активности

# 4. Announce deployment
# Опубликуйте Program ID в официальных каналах
```

---

## Backend API

### Devnet Deployment

```bash
cd backend

# 1. Setup Python environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Setup .env
cp .env.example .env.devnet
# Edit .env.devnet with devnet settings

# 3. Run migrations
alembic upgrade head

# 4. Start server
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Deployment (Docker)

```bash
# 1. Build image
docker build -t anonymeme-backend:latest ./backend

# 2. Run with docker-compose
docker-compose -f docker-compose.prod.yml up -d

# 3. Run migrations
docker-compose exec backend alembic upgrade head

# 4. Check health
curl https://api.anonymeme.com/health
```

---

## Frontend

### Development

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Setup environment
cp .env.example .env.local
# Edit .env.local с devnet settings

# 3. Update Program ID
echo "NEXT_PUBLIC_PUMP_CORE_PROGRAM_ID=<your-program-id>" >> .env.local

# 4. Run dev server
npm run dev
```

### Production Deployment (Vercel)

```bash
# 1. Install Vercel CLI
npm install -g vercel

# 2. Login
vercel login

# 3. Deploy
vercel --prod

# OR через GitHub integration:
# 1. Connect repo to Vercel
# 2. Set environment variables in Vercel dashboard
# 3. Push to main branch
```

### Alternative: Self-hosted

```bash
# 1. Build production bundle
cd frontend
npm run build

# 2. Start production server
npm start

# OR with PM2
npm install -g pm2
pm2 start npm --name "anonymeme-frontend" -- start

# 3. Setup Nginx reverse proxy
# See nginx.conf.example
```

---

## Post-Deployment

### Инициализация Platform

После deployment smart contract необходимо инициализировать платформу:

```bash
cd contracts/pump-core

# Создать initialization script
cat > scripts/initialize.ts <<EOF
import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { PumpCore } from "../target/types/pump_core";

async function main() {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.PumpCore as Program<PumpCore>;

  // Initialize platform
  await program.methods
    .initializePlatform({
      platformFeePercent: 100, // 1%
      raydiumFeePercent: 25,   // 0.25%
      graduationThreshold: new anchor.BN("300000000000000"), // 300k tokens
      minLockDuration: new anchor.BN(86400), // 1 day
      maxLockDuration: new anchor.BN(31536000), // 1 year
    })
    .accounts({
      authority: provider.wallet.publicKey,
    })
    .rpc();

  console.log("Platform initialized successfully!");
}

main();
EOF

# Запустить инициализацию
npx ts-node scripts/initialize.ts
```

### Мониторинг

#### Smart Contract Monitoring:

```bash
# Watch program logs
solana logs $PROGRAM_ID

# Monitor transactions
solana program show $PROGRAM_ID

# Check account activity
solana account $PROGRAM_ID
```

#### Application Monitoring:

- **Sentry**: Error tracking
- **DataDog**: Performance monitoring
- **Prometheus + Grafana**: Metrics
- **ELK Stack**: Log aggregation

### Security

#### Program Security:

```bash
# 1. Set upgrade authority to multisig
solana program set-upgrade-authority \
  $PROGRAM_ID \
  $MULTISIG_ADDRESS

# 2. Regular security audits
# Schedule quarterly audits

# 3. Bug bounty program
# Offer rewards for vulnerability reports
```

#### API Security:

- Rate limiting
- DDoS protection (Cloudflare)
- Input validation
- SQL injection prevention
- XSS protection

### Backups

```bash
# 1. Program keypair backup
gpg --encrypt ~/.config/solana/mainnet-deploy.json

# 2. Database backups (automated)
# Setup daily backups with retention policy

# 3. Configuration backups
# Version control all configs
```

---

## Troubleshooting

### Smart Contract Deployment Errors

#### "Insufficient funds for deployment"

```bash
# Check balance
solana balance

# Need at least 2 SOL for deployment
solana airdrop 2  # devnet only
```

#### "Program already deployed at this address"

```bash
# Either upgrade existing program
anchor upgrade target/deploy/pump_core.so --program-id $PROGRAM_ID

# Or generate new keypair
solana-keygen new --outfile target/deploy/pump_core-keypair.json --force
anchor deploy
```

#### "Transaction simulation failed"

```bash
# Increase compute units in program
# Check for account size issues
# Verify all PDAs are correctly derived
```

### CI/CD Issues

#### "GitHub Actions build failing"

1. Check workflow logs
2. Verify all secrets are set
3. Check Rust/Solana versions match
4. Ensure sufficient GitHub Actions minutes

#### "Artifacts not uploading"

```bash
# Verify artifact paths in workflow
# Check retention days setting
# Ensure build completed successfully
```

### Frontend Issues

#### "Failed to connect to wallet"

```bash
# Check wallet adapter versions
# Verify network cluster setting
# Test with different wallets
```

#### "Transaction fails with 'Program not found'"

```bash
# Verify NEXT_PUBLIC_PUMP_CORE_PROGRAM_ID is correct
# Check you're on correct network (devnet/mainnet)
# Ensure program is deployed
```

---

## Emergency Procedures

### Program Pause (if critical bug found)

```bash
# If pause functionality implemented:
anchor run emergency-pause --provider.cluster mainnet-beta

# Otherwise, coordinate with validators to halt program
```

### Upgrade Procedure

```bash
# 1. Build new version
anchor build

# 2. Test thoroughly on devnet
anchor upgrade --program-id $DEVNET_PROGRAM_ID --provider.cluster devnet

# 3. Announce upgrade window to users

# 4. Upgrade mainnet (requires upgrade authority)
anchor upgrade target/deploy/pump_core.so \
  --program-id $MAINNET_PROGRAM_ID \
  --provider.cluster mainnet-beta
```

---

## Best Practices

### Development Workflow:

1. **Feature branch** → Develop locally
2. **PR to develop** → CI runs tests
3. **Deploy to devnet** → Integration testing
4. **PR to main** → Code review
5. **Deploy to mainnet** → After approval

### Security:

- Never commit private keys
- Use environment variables
- Rotate API keys regularly
- Enable 2FA everywhere
- Use hardware wallets for mainnet

### Monitoring:

- Set up alerts for:
  - Failed transactions
  - Unusual activity
  - High error rates
  - Performance degradation

---

## Дополнительные ресурсы

- [Anchor Documentation](https://www.anchor-lang.com/)
- [Solana Documentation](https://docs.solana.com/)
- [Project README](README.md)
- [Build Guide](contracts/pump-core/BUILD.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## Support

- **GitHub Issues**: https://github.com/your-org/anonymeme/issues
- **Discord**: https://discord.gg/anonymeme
- **Email**: security@anonymeme.com (security issues only)

---

**⚠️ DISCLAIMER**: Deployment на blockchain является необратимым действием. Убедитесь что вы полностью понимаете последствия и протестировали все на devnet перед deployment на mainnet.
