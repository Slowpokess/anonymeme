# 🔑 Откуда взять AWS Credentials - Полная инструкция

## 🎯 **ТРИ ВАРИАНТА НА ВЫБОР**

### **ВАРИАНТ 1: AWS FREE TIER (РЕКОМЕНДУЕТСЯ для тестирования)**

#### Шаг 1: Создать бесплатный AWS аккаунт
1. Перейдите на https://aws.amazon.com
2. Нажмите **Create an AWS Account**
3. Заполните данные (нужна банковская карта, но плата не взимается в рамках Free Tier)
4. Подтвердите телефон и email

#### Шаг 2: Создать IAM пользователя
1. Войдите в **AWS Console**
2. Найдите сервис **IAM** (в поиске наберите "IAM")
3. Перейдите в **Users** → **Create user**
4. Имя пользователя: `anonymeme-deploy`
5. **Attach policies directly** → найдите и выберите:
   - `AmazonEC2FullAccess` (для серверов)
   - `AmazonS3FullAccess` (для файлов)
   - `SecretsManagerReadWrite` (для секретов)
6. **Create user**

#### Шаг 3: Получить ключи
1. Кликните на созданного пользователя
2. **Security credentials** → **Create access key**
3. Выберите **Command Line Interface (CLI)**
4. Поставьте галочку "I understand..."
5. **Create access key**
6. **СКОПИРУЙТЕ И СОХРАНИТЕ:**
   ```
   Access key ID: AKIAIOSFODNN7EXAMPLE     ← это ваш AWS_ACCESS_KEY_ID
   Secret access key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY  ← это ваш AWS_SECRET_ACCESS_KEY
   ```

### **ВАРИАНТ 2: ЛОКАЛЬНЫЙ DEPLOYMENT (БЕЗ AWS)**

Если не хотите использовать AWS, можете запускать все локально:

#### Что добавить в GitHub Secrets:
```
AWS_ACCESS_KEY_ID=fake_key_for_local
AWS_SECRET_ACCESS_KEY=fake_secret_for_local
AWS_ACCESS_KEY_ID_PROD=fake_key_for_local
AWS_SECRET_ACCESS_KEY_PROD=fake_secret_for_local
```

#### Изменить deployment на локальный
В `.github/workflows/cd.yml` заменить AWS команды на Docker:
```yaml
# Вместо AWS deployment
- name: 🐳 Deploy with Docker Compose
  run: |
    docker-compose -f docker-compose.staging.yml up -d
```

### **ВАРИАНТ 3: ДРУГИЕ ОБЛАЧНЫЕ ПРОВАЙДЕРЫ**

#### Google Cloud Platform (GCP)
```bash
# Установить gcloud CLI
curl https://sdk.cloud.google.com | bash

# Получить ключи
gcloud auth application-default login
gcloud iam service-accounts keys create key.json --iam-account=your-service@project.iam.gserviceaccount.com
```

#### DigitalOcean
```bash
# Создать Droplet (сервер)
# Получить API ключ в Control Panel → API → Personal access tokens
DIGITALOCEAN_TOKEN=your_token_here
```

## 🔧 **КАК ДОБАВИТЬ В GITHUB ПОСЛЕ ПОЛУЧЕНИЯ КЛЮЧЕЙ**

### Шаг 1: Открыть репозиторий
1. Перейдите на GitHub в ваш репозиторий
2. **Settings** → **Secrets and variables** → **Actions**

### Шаг 2: Добавить секреты
Нажмите **New repository secret** для каждого:

```
Name: AWS_ACCESS_KEY_ID
Value: AKIAIOSFODNN7EXAMPLE  (ваш реальный ключ)

Name: AWS_SECRET_ACCESS_KEY  
Value: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY  (ваш реальный секрет)

Name: AWS_ACCESS_KEY_ID_PROD
Value: AKIAIOSFODNN7EXAMPLE  (тот же или другой для production)

Name: AWS_SECRET_ACCESS_KEY_PROD
Value: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY  (тот же или другой для production)
```

## 🛡️ **БЕЗОПАСНОСТЬ**

### ⚠️ **ВАЖНО - ЧТО НИКОГДА НЕ ДЕЛАТЬ:**
- ❌ НЕ коммитьте ключи в git
- ❌ НЕ сохраняйте в .env файлах  
- ❌ НЕ пишите в код
- ❌ НЕ присылайте в мессенджерах

### ✅ **ПРАВИЛЬНО:**
- ✅ Сохранить в GitHub Secrets
- ✅ Использовать IAM роли с минимальными правами
- ✅ Регулярно ротировать ключи
- ✅ Включить MFA на AWS аккаунте

## 💰 **СТОИМОСТЬ**

### AWS Free Tier включает:
- ✅ 750 часов EC2 t2.micro в месяц (1 год бесплатно)
- ✅ 5GB S3 storage
- ✅ 1 million Lambda requests
- ✅ 25GB DynamoDB storage

### Для разработки достаточно бесплатного уровня!

## 🚀 **БЫСТРЫЙ СТАРТ**

### Если торопитесь - минимум что нужно:
1. **Создать AWS аккаунт** (10 минут)
2. **Создать IAM пользователя** (5 минут)  
3. **Скопировать ключи в GitHub Secrets** (2 минуты)
4. **Создать Environments в GitHub** (2 минуты)

**Общее время: 20 минут**

### После этого ваш CD pipeline заработает! 🎉

## 🆘 **ЕСЛИ ЧТО-ТО НЕ РАБОТАЕТ**

Напишите мне какая именно ошибка возникает, и я помогу исправить!