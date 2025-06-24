# 🔧 Инструкция по настройке GitHub для CD Pipeline

## 1. Создание Environments (ОБЯЗАТЕЛЬНО!)

### Шаг 1: Перейдите в настройки репозитория
1. Откройте ваш репозиторий на GitHub
2. Нажмите **Settings** (вкладка справа)
3. В левом меню найдите **Environments**

### Шаг 2: Создайте environment "staging"
1. Нажмите **New environment**
2. Введите имя: `staging`
3. Нажмите **Configure environment**
4. **НЕ добавляйте** Required reviewers (для staging)
5. Нажмите **Save protection rules**

### Шаг 3: Создайте environment "production"
1. Нажмите **New environment**
2. Введите имя: `production`
3. Нажмите **Configure environment**
4. **ВКЛЮЧИТЕ** Required reviewers
5. Добавьте себя как reviewer
6. **ВКЛЮЧИТЕ** Wait timer: 5 minutes
7. Нажмите **Save protection rules**

## 2. Добавление AWS Secrets (ОБЯЗАТЕЛЬНО!)

### Шаг 1: Перейдите к секретам
1. В том же меню Settings
2. Найдите **Secrets and variables** → **Actions**

### Шаг 2: Добавьте секреты для Staging
1. Нажмите **New repository secret**
2. Name: `AWS_ACCESS_KEY_ID`
3. Secret: ваш AWS Access Key для staging
4. Нажмите **Add secret**

5. Повторите для `AWS_SECRET_ACCESS_KEY`

### Шаг 3: Добавьте секреты для Production
1. Name: `AWS_ACCESS_KEY_ID_PROD`
2. Secret: ваш AWS Access Key для production
3. Name: `AWS_SECRET_ACCESS_KEY_PROD`
4. Secret: ваш AWS Secret Key для production

## 3. Дополнительные секреты (рекомендуется)

Добавьте эти секреты по той же схеме:
- `DOCKER_USERNAME` - имя пользователя Docker Hub
- `DOCKER_PASSWORD` - пароль Docker Hub
- `DB_PASSWORD` - пароль базы данных
- `REDIS_PASSWORD` - пароль Redis
- `SECRET_KEY` - секретный ключ приложения
- `JWT_SECRET_KEY` - секрет для JWT токенов

## 4. Проверка настройки

После настройки у вас должно быть:
- ✅ 2 environments: staging, production
- ✅ 4+ secrets в Actions secrets
- ✅ Production environment с required reviewers

## 5. Что произойдет после настройки

1. **CD pipeline перестанет падать** с ошибками environment
2. **AWS deployment будет работать** 
3. **Production deployment потребует вашего одобрения**
4. **Staging deployment будет автоматическим**

⚠️ **ВАЖНО**: Без этой настройки CD pipeline НЕ БУДЕТ РАБОТАТЬ!