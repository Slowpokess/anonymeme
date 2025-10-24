# Руководство по компиляции Smart Contracts

## Обзор

Проект Anonymeme использует **Anchor Framework 0.29.0** для разработки Solana smart contracts. Компиляция производится через GitHub Actions CI/CD для обеспечения воспроизводимости и безопасности.

## Методы компиляции

### 1. Компиляция через GitHub Actions (Рекомендуется)

Это **предпочтительный метод** для production builds.

#### Преимущества:
- ✅ Воспроизводимая среда компиляции
- ✅ Автоматическое сохранение артефактов
- ✅ Интеграция с security scans
- ✅ Автоматические тесты перед компиляцией
- ✅ Нет проблем с зависимостями локального окружения

#### Процесс:

**Автоматический trigger:**
```bash
# Push в ветки main или develop автоматически запускает компиляцию
git push origin main
```

**Ручной trigger:**
1. Перейдите в GitHub → Actions
2. Выберите workflow "Build and Deploy Contracts"
3. Нажмите "Run workflow"
4. Выберите ветку и параметры
5. Нажмите "Run workflow"

**Скачать скомпилированные артефакты:**
1. GitHub → Actions → выберите успешный run
2. В разделе "Artifacts" скачайте:
   - `pump-core-program` - скомпилированный .so файл
   - `pump-core-idl` - IDL файл для TypeScript SDK
   - `pump-core-keypair` - Program keypair (для devnet)

### 2. Локальная компиляция (Для разработки)

Используется для быстрой итерации во время разработки.

#### Требования:
- **Rust** 1.90.0+
- **Solana CLI** 1.16.25
- **Anchor CLI** 0.29.0
- **Node.js** 20+

#### Установка инструментов:

```bash
# 1. Установить Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# 2. Установить Solana CLI
sh -c "$(curl -sSfL https://release.solana.com/v1.16.25/install)"
export PATH="$HOME/.local/share/solana/install/active_release/bin:$PATH"

# 3. Установить Anchor CLI
npm install -g @coral-xyz/anchor-cli@0.29.0

# 4. Проверить установку
anchor --version  # Должно показать: anchor-cli 0.29.0
solana --version  # Должно показать: solana-cli 1.16.25
```

#### Компиляция:

```bash
cd contracts/pump-core

# Установить npm зависимости
npm install

# Компилировать программу
anchor build

# Проверить результаты
ls -lh target/deploy/
# Должны появиться:
# - pump_core.so (скомпилированная программа)
# - pump_core-keypair.json (program keypair)
```

#### Запуск тестов:

```bash
# Запустить все тесты
anchor test

# Запустить конкретный тест
anchor test --skip-build -- tests/bonding-curve.ts

# Запустить тесты без перезапуска validator
anchor test --skip-local-validator
```

### 3. Docker компиляция (Изолированное окружение)

Используется для полной изоляции и reproducible builds.

#### Создать Dockerfile:

```dockerfile
# contracts/pump-core/Dockerfile.build
FROM rust:1.90

# Установить Solana CLI
RUN sh -c "$(curl -sSfL https://release.solana.com/v1.16.25/install)"
ENV PATH="/root/.local/share/solana/install/active_release/bin:$PATH"

# Установить Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
RUN apt-get install -y nodejs

# Установить Anchor CLI
RUN npm install -g @coral-xyz/anchor-cli@0.29.0

WORKDIR /workspace

# Копировать проект
COPY . .

# Установить зависимости
RUN npm install

# Компилировать
RUN anchor build

# Выходной volume для артефактов
VOLUME ["/workspace/target"]

CMD ["echo", "Build completed! Artifacts in /workspace/target/deploy/"]
```

#### Компиляция через Docker:

```bash
# Build image
docker build -f Dockerfile.build -t pump-core-builder .

# Запустить компиляцию
docker run --rm -v $(pwd)/target:/workspace/target pump-core-builder

# Результаты в ./target/deploy/
```

## Артефакты компиляции

После успешной компиляции в директории `target/deploy/` появятся:

| Файл | Описание | Использование |
|------|----------|---------------|
| `pump_core.so` | Скомпилированная Solana программа (BPF bytecode) | Деплоится на Solana blockchain |
| `pump_core-keypair.json` | Keypair программы (адрес) | Используется для deployment |
| `../idl/pump_core.json` | Interface Definition Language | Генерация TypeScript SDK |

### Проверка размера программы:

```bash
# Размер не должен превышать 400KB для эффективного deployment
ls -lh target/deploy/pump_core.so

# Если программа слишком большая, оптимизируйте:
# 1. Включите оптимизацию в Cargo.toml
# 2. Удалите неиспользуемый код
# 3. Используйте feature flags для опциональной функциональности
```

## Обновление SDK после компиляции

После компиляции необходимо обновить TypeScript SDK с реальными типами из IDL:

```bash
# 1. Скопировать IDL в frontend
cp target/idl/pump_core.json ../../frontend/src/sdk/pumpCore/idl.json

# 2. Обновить SDK types (автоматическая генерация)
cd ../../frontend
npm run generate-types  # Если настроен скрипт

# ИЛИ вручную:
# - Обновить types.ts используя IDL
# - Обновить client.ts с реальными инструкциями
```

## Troubleshooting

### Ошибка: "no such command: build-bpf"

**Причина:** Не установлен Solana CLI или неполная установка.

**Решение:**
```bash
# Переустановить Solana CLI
sh -c "$(curl -sSfL https://release.solana.com/v1.16.25/install)"
export PATH="$HOME/.local/share/solana/install/active_release/bin:$PATH"

# Установить build tools
solana-install init 1.16.25
```

### Ошибка: "Package binary version is not correct"

**Причина:** Несоответствие версий Anchor CLI и SDK.

**Решение:**
```bash
# Проверить версии
anchor --version
cat package.json | grep "@coral-xyz/anchor"

# Синхронизировать версии
npm uninstall -g @coral-xyz/anchor-cli
npm install -g @coral-xyz/anchor-cli@0.29.0
```

### Ошибка: "error: linker `rust-lld` not found"

**Причина:** Отсутствуют компоненты Rust для Solana.

**Решение:**
```bash
# Установить BPF toolchain
cargo install cargo-build-sbf
solana-install init 1.16.25
```

### Ошибка компиляции из-за зависимостей

**Причина:** Устаревшие или несовместимые зависимости.

**Решение:**
```bash
# Очистить кеш и пересобрать
cargo clean
rm -rf target/
anchor build
```

### GitHub Actions не собирает программу

**Причина:** CI может пропускать компиляцию если директория не найдена.

**Решение:**
1. Проверьте что `contracts/pump-core/Anchor.toml` существует
2. Проверьте логи CI workflow
3. Убедитесь что не добавлены в `.gitignore`

## Deployment после компиляции

После успешной компиляции следуйте инструкциям в [DEPLOYMENT.md](../../DEPLOYMENT.md):

```bash
# 1. Devnet deployment
solana config set --url devnet
anchor deploy --provider.cluster devnet

# 2. Mainnet deployment (только после полного тестирования!)
solana config set --url mainnet
anchor deploy --provider.cluster mainnet
```

## Best Practices

1. **Всегда компилируйте через CI/CD для production builds**
   - Гарантирует воспроизводимость
   - Автоматические security checks
   - Сохранение артефактов

2. **Локальная компиляция только для разработки**
   - Быстрее для итераций
   - Но может давать разные результаты на разных машинах

3. **Версионируйте артефакты**
   - Сохраняйте .so файлы с версией (pump_core_v1.0.0.so)
   - Сохраняйте IDL файлы вместе с программой

4. **Тестируйте перед deployment**
   ```bash
   # Всегда запускайте тесты
   anchor test

   # Проверяйте на devnet перед mainnet
   anchor deploy --provider.cluster devnet
   ```

5. **Документируйте изменения в программе**
   - Обновляйте CHANGELOG.md
   - Указывайте breaking changes
   - Документируйте новые инструкции

## Дополнительные ресурсы

- [Anchor Documentation](https://www.anchor-lang.com/)
- [Solana Documentation](https://docs.solana.com/)
- [Anchor Discord](https://discord.gg/anchor)
- [Project README](../../README.md)
- [Deployment Guide](../../DEPLOYMENT.md)

## Контакты и поддержка

При проблемах с компиляцией:
1. Проверьте [Troubleshooting](#troubleshooting) выше
2. Проверьте логи GitHub Actions
3. Создайте issue в репозитории с описанием проблемы и логами
