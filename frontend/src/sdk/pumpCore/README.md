# 🚀 Pump Core SDK

TypeScript SDK для взаимодействия со смарт-контрактами Pump Core на Solana.

## 📦 Установка

SDK уже включен в проект. Просто импортируйте его:

```typescript
import { PumpCoreClient, createClient, CurveType } from '@/sdk/pumpCore'
```

## 🎯 Быстрый старт

### Создание клиента

```typescript
import { Connection } from '@solana/web3.js'
import { createClient } from '@/sdk/pumpCore'

const connection = new Connection('https://api.devnet.solana.com', 'confirmed')
const client = createClient(connection)
```

### Создание токена

```typescript
import { Keypair } from '@solana/web3.js'
import BN from 'bn.js'
import { CurveType } from '@/sdk/pumpCore'

const payer = Keypair.fromSecretKey(/* ваш приватный ключ */)

const result = await client.createToken(
  {
    name: 'My Memecoin',
    symbol: 'MEM',
    uri: 'https://arweave.net/metadata-uri',
    bondingCurve: {
      curveType: CurveType.Exponential,
      initialPrice: new BN(1_000_000), // 0.001 SOL
      growthFactor: new BN(100_001), // 1.00001
    },
    decimals: 9,
  },
  payer
)

console.log('Token created:', result.mint.toBase58())
console.log('Signature:', result.signature)
```

### Покупка токенов

```typescript
import BN from 'bn.js'

const trader = Keypair.fromSecretKey(/* ваш приватный ключ */)
const mint = new PublicKey('token mint address')

const result = await client.trade(
  {
    mint,
    amount: new BN(1_000_000_000), // 1 SOL
    isBuy: true,
    slippageBps: 100, // 1% slippage
  },
  trader
)

console.log('Trade executed:', result.signature)
console.log('Tokens received:', result.outputAmount.toString())
```

### Продажа токенов

```typescript
const result = await client.trade(
  {
    mint,
    amount: new BN(10_000_000_000), // 10,000 токенов
    isBuy: false,
    slippageBps: 100,
  },
  trader
)

console.log('SOL received:', result.outputAmount.toString())
```

### Градуация на DEX

```typescript
const creator = Keypair.fromSecretKey(/* ваш приватный ключ */)

const result = await client.graduateToDex(
  {
    mint,
    lockDuration: 86400 * 30, // 30 дней в секундах
    enableVesting: true,
  },
  creator
)

console.log('Graduated to DEX:', result.poolAddress.toBase58())
console.log('LP Mint:', result.lpMint.toBase58())
```

### Блокировка LP токенов

```typescript
const owner = Keypair.fromSecretKey(/* ваш приватный ключ */)
const lpMint = new PublicKey('lp mint address')
const tokenMint = new PublicKey('token mint address')

const signature = await client.lockLpTokens(
  {
    lpMint,
    tokenMint,
    amount: new BN(1_000_000_000),
    lockDuration: 86400 * 30, // 30 дней
    enableVesting: true,
  },
  owner
)

console.log('LP tokens locked:', signature)
```

## 🛠️ API Reference

### PumpCoreClient

Основной класс для взаимодействия с программой.

#### Methods

- `getPlatformConfig(): Promise<PlatformConfig | null>` - Получить конфигурацию платформы
- `getTokenInfo(mint: PublicKey): Promise<TokenInfo | null>` - Получить информацию о токене
- `getLpTokenLock(owner: PublicKey, lpMint: PublicKey): Promise<LpTokenLock | null>` - Получить информацию о блокировке LP
- `createToken(params, payer, options?): Promise<CreateTokenResult>` - Создать новый токен
- `trade(params, trader, options?): Promise<TradeResult>` - Купить или продать токены
- `graduateToDex(params, creator, options?): Promise<GraduationResult>` - Градуировать токен на DEX
- `lockLpTokens(params, owner, options?): Promise<string>` - Заблокировать LP токены
- `unlockLpTokens(lpMint, amount, owner, options?): Promise<string>` - Разблокировать LP токены

### PDA Helpers

Функции для расчета Program Derived Addresses:

- `getPlatformConfigPDA(programId?)` - PDA конфигурации платформы
- `getTokenInfoPDA(mint, programId?)` - PDA информации о токене
- `getBondingCurveVaultPDA(mint, programId?)` - PDA хранилища бондинг-кривой
- `getMetadataPDA(mint)` - PDA метаданных Metaplex
- `getLpTokenLockPDA(owner, lpMint, programId?)` - PDA блокировки LP токенов
- `getTokenPDAs(mint, programId?)` - Все PDA для токена сразу

### Types

#### CurveType

```typescript
enum CurveType {
  Linear = 'Linear',
  Exponential = 'Exponential',
  Sigmoid = 'Sigmoid',
  ConstantProduct = 'ConstantProduct',
  Logarithmic = 'Logarithmic',
}
```

#### BondingCurveParams

```typescript
interface BondingCurveParams {
  curveType: CurveType
  initialPrice: BN
  slope?: BN // Для Linear
  growthFactor?: BN // Для Exponential
  midpoint?: BN // Для Sigmoid
  steepness?: BN // Для Sigmoid
  k?: BN // Для ConstantProduct
  base?: BN // Для Logarithmic
  scaleFactor?: BN // Для Logarithmic
}
```

## 📚 Примеры

### Пример 1: Создание токена с линейной кривой

```typescript
const result = await client.createToken(
  {
    name: 'Linear Token',
    symbol: 'LIN',
    uri: 'https://arweave.net/metadata',
    bondingCurve: {
      curveType: CurveType.Linear,
      initialPrice: new BN(5_000_000), // 0.005 SOL
      slope: new BN(50), // Рост цены
    },
  },
  payer
)
```

### Пример 2: Batch операции

```typescript
import { getTokenPDAs } from '@/sdk/pumpCore'

// Получить все PDA для токена одним вызовом
const pdas = getTokenPDAs(mint)
console.log('Token Info PDA:', pdas.tokenInfo.address.toBase58())
console.log('Vault PDA:', pdas.bondingCurveVault.address.toBase58())
console.log('Metadata PDA:', pdas.metadata.address.toBase58())
```

### Пример 3: Обработка ошибок

```typescript
import { PumpCoreError } from '@/sdk/pumpCore'

try {
  const result = await client.trade(params, trader)
} catch (error: any) {
  if (error.code === PumpCoreError.SlippageExceeded) {
    console.error('Slippage exceeded, try increasing slippage tolerance')
  } else if (error.code === PumpCoreError.InsufficientBalance) {
    console.error('Insufficient balance')
  } else {
    console.error('Unknown error:', error)
  }
}
```

## 🔧 Конфигурация

### Настройки клиента

```typescript
const client = createClient(connection, {
  programId: new PublicKey('your-program-id'),
  commitment: 'confirmed',
  skipPreflight: false,
})
```

### Опции транзакций

```typescript
const result = await client.trade(params, trader, {
  skipPreflight: false,
  commitment: 'confirmed',
  maxRetries: 3,
  preflightCommitment: 'confirmed',
})
```

## 📝 Важные замечания

1. **IDL файл**: После компиляции смарт-контрактов SDK автоматически загрузит IDL для десериализации данных
2. **Placeholder инструкции**: Текущие instruction builders - это placeholders. После генерации IDL они будут заменены на реальные Anchor инструкции
3. **BN (Big Numbers)**: Все числовые значения используют BN из библиотеки `bn.js` для точности
4. **Commitment**: По умолчанию используется 'confirmed' commitment для баланса между скоростью и финальностью

## 🚧 TODO

- [ ] Интеграция IDL после компиляции контрактов
- [ ] Реализация десериализации account data
- [ ] Добавление event listeners для программных событий
- [ ] Добавление estimate функций для предварительной оценки трейдов
- [ ] Batch операции для нескольких транзакций

## 📄 Лицензия

MIT
