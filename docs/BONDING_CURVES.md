# Бондинг-кривые в AnonyMeme

## Оглавление
1. [Обзор](#обзор)
2. [Типы кривых](#типы-кривых)
   - [Linear (Линейная)](#1-linear-линейная)
   - [Exponential (Экспоненциальная)](#2-exponential-экспоненциальная)
   - [Sigmoid (S-образная)](#3-sigmoid-s-образная)
   - [ConstantProduct (AMM)](#4-constantproduct-amm)
   - [Logarithmic (Логарифмическая)](#5-logarithmic-логарифмическая)
3. [Сравнительная таблица](#сравнительная-таблица)
4. [Рекомендации по выбору](#рекомендации-по-выбору)
5. [Примеры использования](#примеры-использования)

---

## Обзор

**Бондинг-кривая** (Bonding Curve) — это математическая функция, которая определяет зависимость цены токена от его текущего предложения (supply). Когда пользователи покупают токены, supply растет и цена увеличивается согласно кривой. При продаже — наоборот.

### Ключевые преимущества:
- **Автоматическое ценообразование**: Не требуется маркет-мейкер
- **Мгновенная ликвидность**: Всегда можно купить/продать токены
- **Прозрачность**: Цена определяется математической формулой
- **Честный запуск**: Все участники покупают по одним правилам

### Базовые концепции:
- **Supply** — текущее количество выпущенных токенов
- **Price** — цена одного токена (в lamports SOL)
- **Market Cap** — рыночная капитализация = `supply × price`
- **Price Impact** — влияние сделки на цену (в базисных пунктах, 10000 = 100%)

---

## Типы кривых

### 1. Linear (Линейная)

#### Математическая формула:
```
price = initial_price + slope × supply
```

#### Параметры:
- `initial_price` — начальная цена (в lamports)
- `slope` — коэффициент роста цены
- `max_supply` — максимальное предложение

#### Характеристика:
Цена растет **равномерно** с каждым проданным токеном. Самая простая и предсказуемая кривая.

```
   Price
      ^
      |                    /
      |                  /
      |                /
      |              /
      |            /
      |          /
      |        /
      |______/________________> Supply
      0
```

#### Когда использовать:
✅ Для стабильных проектов с долгосрочной перспективой
✅ Когда нужна предсказуемая динамика цены
✅ Для utility-токенов с реальным применением
✅ Если хотите избежать спекулятивных всплесков

❌ Не подходит для мем-коинов с вирусным ростом
❌ Меньше защиты от ранних распродаж

#### Рекомендуемые параметры:

**Conservative (Консервативная стратегия):**
```rust
initial_price: 1_000_000,      // 0.001 SOL
slope: 10,                     // Медленный рост
max_supply: 1_000_000_000_000, // 1 млн токенов
```

**Balanced (Сбалансированная стратегия):**
```rust
initial_price: 5_000_000,      // 0.005 SOL
slope: 50,                     // Умеренный рост
max_supply: 500_000_000_000,   // 500k токенов
```

**Aggressive (Агрессивная стратегия):**
```rust
initial_price: 10_000_000,     // 0.01 SOL
slope: 200,                    // Быстрый рост
max_supply: 100_000_000_000,   // 100k токенов
```

---

### 2. Exponential (Экспоненциальная)

#### Математическая формула:
```
price = base_price × e^(growth_factor × supply / PRECISION)
```

#### Параметры:
- `base_price` — базовая цена (в lamports)
- `growth_factor` — фактор роста (умножен на PRECISION = 10^9)
- `max_supply` — максимальное предложение

#### Характеристика:
Цена растет **экспоненциально** — медленно в начале, затем очень быстро. Идеальна для вирусных проектов.

```
   Price
      ^
      |                       |
      |                      /
      |                    /
      |                  /
      |               /
      |            /
      |         /
      |_______/___________________> Supply
      0
```

#### Когда использовать:
✅ Для мем-коинов с вирусным потенциалом
✅ Если ожидаете быстрый рост сообщества
✅ Чтобы вознаградить ранних участников
✅ Для создания FOMO-эффекта

❌ Высокий риск резких просадок
❌ Может отпугнуть поздних покупателей
❌ Сложнее рассчитать справедливую цену

#### Рекомендуемые параметры:

**Conservative:**
```rust
base_price: 1_000_000,         // 0.001 SOL
growth_factor: 1_000_000,      // 0.001 (медленная экспонента)
max_supply: 1_000_000_000_000,
```

**Balanced:**
```rust
base_price: 5_000_000,         // 0.005 SOL
growth_factor: 5_000_000,      // 0.005 (умеренная экспонента)
max_supply: 500_000_000_000,
```

**Aggressive:**
```rust
base_price: 10_000_000,        // 0.01 SOL
growth_factor: 10_000_000,     // 0.01 (быстрая экспонента)
max_supply: 100_000_000_000,
```

---

### 3. Sigmoid (S-образная)

#### Математическая формула:
```
price = min_price + (max_price - min_price) / (1 + e^(-steepness × (supply - midpoint)))
```

#### Параметры:
- `min_price` — минимальная цена (нижняя асимптота)
- `max_price` — максимальная цена (верхняя асимптота)
- `steepness` — крутизна S-кривой (умножена на PRECISION)
- `midpoint` — точка перегиба (где цена = (min + max) / 2)
- `max_supply` — максимальное предложение

#### Характеристика:
Цена растет **S-образно**: медленно в начале, быстро в середине, снова медленно в конце. Самая сбалансированная кривая.

```
   Price
      ^
      |  max ____________
      |               /
      |             /
      |           /
      |         /  <-- midpoint (точка перегиба)
      |       /
      |     /
      |___/________________> Supply
      min
```

#### Когда использовать:
✅ Для сбалансированного подхода
✅ Если нужна защита от ранних дампов
✅ Для проектов с четким roadmap
✅ Чтобы ограничить максимальную цену

❌ Сложнее настроить параметры
❌ Менее предсказуемая для пользователей

#### Рекомендуемые параметры:

**Conservative:**
```rust
min_price: 1_000_000,          // 0.001 SOL
max_price: 100_000_000,        // 0.1 SOL (100x рост)
steepness: 1_000_000_000,      // 1.0 (плавная S-кривая)
midpoint: 500_000_000_000,     // Середина пути
max_supply: 1_000_000_000_000,
```

**Balanced:**
```rust
min_price: 5_000_000,          // 0.005 SOL
max_price: 500_000_000,        // 0.5 SOL (100x рост)
steepness: 5_000_000_000,      // 5.0 (умеренная крутизна)
midpoint: 250_000_000_000,
max_supply: 500_000_000_000,
```

**Aggressive:**
```rust
min_price: 10_000_000,         // 0.01 SOL
max_price: 1_000_000_000,      // 1 SOL (100x рост)
steepness: 10_000_000_000,     // 10.0 (крутая S-кривая)
midpoint: 50_000_000_000,
max_supply: 100_000_000_000,
```

---

### 4. ConstantProduct (AMM)

#### Математическая формула:
```
x × y = k (константа)

где:
- x = sol_reserve (резервы SOL)
- y = token_reserve (резервы токенов)
- k = константа произведения
```

Цена = `sol_reserve / token_reserve`

#### Параметры:
- `sol_reserve` — количество SOL в пуле (в lamports)
- `token_reserve` — количество токенов в пуле

#### Характеристика:
Работает как **автоматический маркет-мейкер** (AMM) по принципу Uniswap/Raydium. Цена определяется соотношением резервов.

```
   Token Reserve
      ^
      |  \
      |    \
      |      \
      |        \  <-- x*y=k (гипербола)
      |          \
      |            \
      |              \
      |________________\___> SOL Reserve
```

#### Когда использовать:
✅ Для имитации DEX-подобной ликвидности
✅ Если нужна двусторонняя ликвидность с первого дня
✅ Для проектов, планирующих миграцию на DEX
✅ Когда важна симметрия покупок/продаж

❌ Более сложная для понимания пользователями
❌ Требует начальную ликвидность (оба резерва)
❌ Меньше контроля над динамикой цены

#### Рекомендуемые параметры:

**Conservative:**
```rust
sol_reserve: 10_000_000_000,      // 10 SOL начальной ликвидности
token_reserve: 100_000_000_000,   // 100k токенов
// Начальная цена: 10/100k = 0.0001 SOL за токен
```

**Balanced:**
```rust
sol_reserve: 50_000_000_000,      // 50 SOL
token_reserve: 500_000_000_000,   // 500k токенов
// Начальная цена: 50/500k = 0.0001 SOL за токен
```

**Aggressive:**
```rust
sol_reserve: 100_000_000_000,     // 100 SOL
token_reserve: 1_000_000_000_000, // 1M токенов
// Начальная цена: 100/1M = 0.0001 SOL за токен
```

---

### 5. Logarithmic (Логарифмическая)

#### Математическая формула:
```
price = base_price + scale × ln(supply + 1)
```

#### Параметры:
- `base_price` — базовая цена (минимум)
- `scale` — масштаб логарифма (умножен на PRECISION)
- `max_supply` — максимальное предложение

#### Характеристика:
Цена растет **логарифмически** — быстро в начале, затем замедляется. Противоположность экспоненте.

```
   Price
      ^
      |  _______________
      | /
      |/
      /
      /
     /|
    / |
   /  |
  /   |________________________> Supply
  0
```

#### Когда использовать:
✅ Для reward-токенов и программ лояльности
✅ Если хотите поощрить ранних участников, но избежать экстремального роста
✅ Для токенов с большим max_supply
✅ Когда нужна стабилизация цены со временем

❌ Менее привлекательна для спекулянтов
❌ Ограниченный потенциал роста для поздних покупателей

#### Рекомендуемые параметры:

**Conservative:**
```rust
base_price: 1_000_000,         // 0.001 SOL (минимум)
scale: 10_000_000_000,         // 10.0 (медленный рост)
max_supply: 10_000_000_000_000, // 10 млн токенов
```

**Balanced:**
```rust
base_price: 5_000_000,         // 0.005 SOL
scale: 50_000_000_000,         // 50.0 (умеренный рост)
max_supply: 5_000_000_000_000, // 5 млн токенов
```

**Aggressive:**
```rust
base_price: 10_000_000,        // 0.01 SOL
scale: 100_000_000_000,        // 100.0 (быстрый начальный рост)
max_supply: 1_000_000_000_000, // 1 млн токенов
```

---

## Сравнительная таблица

| Характеристика | Linear | Exponential | Sigmoid | ConstantProduct | Logarithmic |
|----------------|--------|-------------|---------|-----------------|-------------|
| **Сложность настройки** | ⭐ Простая | ⭐⭐ Средняя | ⭐⭐⭐ Сложная | ⭐⭐ Средняя | ⭐⭐ Средняя |
| **Предсказуемость** | ⭐⭐⭐⭐⭐ Высокая | ⭐⭐ Низкая | ⭐⭐⭐ Средняя | ⭐⭐⭐ Средняя | ⭐⭐⭐⭐ Высокая |
| **Награда ранним** | ⭐⭐ Низкая | ⭐⭐⭐⭐⭐ Очень высокая | ⭐⭐⭐ Средняя | ⭐⭐⭐ Средняя | ⭐⭐⭐⭐ Высокая |
| **Защита от дампа** | ⭐⭐ Низкая | ⭐ Очень низкая | ⭐⭐⭐⭐ Высокая | ⭐⭐⭐ Средняя | ⭐⭐⭐⭐ Высокая |
| **Потенциал роста** | ⭐⭐⭐ Средний | ⭐⭐⭐⭐⭐ Очень высокий | ⭐⭐⭐⭐ Высокий | ⭐⭐⭐ Средний | ⭐⭐ Низкий |
| **Стабильность** | ⭐⭐⭐⭐ Высокая | ⭐ Низкая | ⭐⭐⭐⭐ Высокая | ⭐⭐⭐ Средняя | ⭐⭐⭐⭐⭐ Очень высокая |
| **Для мем-коинов** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Для utility-токенов** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Для long-term** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## Рекомендации по выбору

### По типу проекта:

#### 🎭 Мем-коин / Community Token
**Рекомендуем**: Exponential или Sigmoid
- Exponential для максимального вирусного эффекта
- Sigmoid для более сбалансированного роста

#### 🏢 Utility Token / Product
**Рекомендуем**: Linear или Logarithmic
- Linear для простоты и предсказуемости
- Logarithmic для награды ранних пользователей

#### 🎨 NFT / Art Project
**Рекомендуем**: Sigmoid или ConstantProduct
- Sigmoid для контроля диапазона цен
- ConstantProduct для DEX-подобной ликвидности

#### 💰 DeFi / Governance Token
**Рекомендуем**: ConstantProduct или Linear
- ConstantProduct для интеграции с DEX
- Linear для справедливого распределения

### По стратегии роста:

#### 🐢 Conservative (Медленный устойчивый рост)
1. **Linear** — самый безопасный выбор
2. **Logarithmic** — награда ранним с последующей стабилизацией
3. **Sigmoid** (с низким steepness) — сбалансированный рост

#### ⚖️ Balanced (Умеренный рост)
1. **Sigmoid** — оптимальный баланс
2. **ConstantProduct** — рыночное ценообразование
3. **Linear** (с высоким slope) — умеренно-агрессивный

#### 🚀 Aggressive (Быстрый вирусный рост)
1. **Exponential** — максимальный FOMO
2. **Sigmoid** (с высоким steepness) — контролируемая агрессия
3. **Logarithmic** (с высоким scale) — сильный старт

### По аудитории:

#### 👥 Широкая аудитория (новички)
- **Linear** — проще всего понять
- **Exponential** — интуитивно понятный рост

#### 🧠 Опытные крипто-пользователи
- **Sigmoid** — ценят сбалансированность
- **ConstantProduct** — знакомы с AMM

#### 🐋 Крупные инвесторы
- **ConstantProduct** — глубокая ликвидность
- **Sigmoid** — предсказуемый ceiling цены

---

## Примеры использования

### Пример 1: Создание токена с Linear кривой

```rust
use pump_core::utils::bonding_curve::{LinearCurve, BondingCurveMath};

// Создаем линейную кривую
let curve = LinearCurve::new(
    1_000_000,      // initial_price: 0.001 SOL
    50,             // slope: умеренный рост
    1_000_000_000,  // max_supply: 1 млн токенов
)?;

// Расчет покупки
let buy_result = curve.calculate_buy(
    10_000_000_000, // 10 SOL
    0,              // текущий supply = 0
)?;

msg!("Вы получите {} токенов", buy_result.token_amount);
msg!("Новая цена: {} lamports", buy_result.price_per_token);
msg!("Price impact: {}%", buy_result.price_impact as f64 / 100.0);
```

### Пример 2: Сравнение цен на разных кривых

```rust
// При одинаковых начальных условиях:
let supply = 100_000; // 100k токенов продано

// Linear
let linear = LinearCurve::new(1_000_000, 50, 1_000_000_000)?;
let linear_price = linear.get_current_price(supply)?;
// Результат: ~1_005_000 lamports (0.001005 SOL)

// Exponential
let expo = ExponentialCurve::new(1_000_000, 5_000_000, 1_000_000_000)?;
let expo_price = expo.get_current_price(supply)?;
// Результат: значительно выше из-за экспоненты

// Sigmoid
let sigmoid = SigmoidCurve::new(
    1_000_000,      // min
    100_000_000,    // max
    5_000_000_000,  // steepness
    500_000,        // midpoint
    1_000_000_000   // max_supply
)?;
let sigmoid_price = sigmoid.get_current_price(supply)?;
// Результат: где-то между min и midpoint
```

### Пример 3: Интеграция в create_token

```rust
#[derive(Accounts)]
pub struct CreateToken<'info> {
    // ... accounts
}

pub fn create_token(
    ctx: Context<CreateToken>,
    curve_type: CurveType,
    curve_params: Vec<u64>,
) -> Result<()> {
    let bonding_curve = match curve_type {
        CurveType::Linear => {
            require!(curve_params.len() == 3, ErrorCode::InvalidParams);
            BondingCurve::Linear(LinearCurve::new(
                curve_params[0], // initial_price
                curve_params[1], // slope
                curve_params[2], // max_supply
            )?)
        },
        CurveType::Exponential => {
            require!(curve_params.len() == 3, ErrorCode::InvalidParams);
            BondingCurve::Exponential(ExponentialCurve::new(
                curve_params[0], // base_price
                curve_params[1], // growth_factor
                curve_params[2], // max_supply
            )?)
        },
        CurveType::Sigmoid => {
            require!(curve_params.len() == 5, ErrorCode::InvalidParams);
            BondingCurve::Sigmoid(SigmoidCurve::new(
                curve_params[0], // min_price
                curve_params[1], // max_price
                curve_params[2], // steepness
                curve_params[3], // midpoint
                curve_params[4], // max_supply
            )?)
        },
        CurveType::ConstantProduct => {
            require!(curve_params.len() == 2, ErrorCode::InvalidParams);
            BondingCurve::ConstantProduct(ConstantProductCurve::new(
                curve_params[0], // sol_reserve
                curve_params[1], // token_reserve
            )?)
        },
        CurveType::Logarithmic => {
            require!(curve_params.len() == 3, ErrorCode::InvalidParams);
            BondingCurve::Logarithmic(LogarithmicCurve::new(
                curve_params[0], // base_price
                curve_params[1], // scale
                curve_params[2], // max_supply
            )?)
        },
    };

    // Сохраняем в токен
    ctx.accounts.token.bonding_curve = bonding_curve;

    Ok(())
}
```

### Пример 4: Фронтенд-интеграция (TypeScript)

```typescript
import { BN } from '@coral-xyz/anchor';

// Типы кривых
enum CurveType {
  Linear = 0,
  Exponential = 1,
  Sigmoid = 2,
  ConstantProduct = 3,
  Logarithmic = 4,
}

// Пресет "Balanced Linear"
const createBalancedLinearToken = async (
  program: Program,
  name: string,
  symbol: string,
) => {
  const curveParams = [
    new BN(5_000_000),       // 0.005 SOL начальная цена
    new BN(50),              // умеренный slope
    new BN(500_000_000_000), // 500k токенов max supply
  ];

  const tx = await program.methods
    .createToken(name, symbol, CurveType.Linear, curveParams)
    .accounts({ /* ... */ })
    .rpc();

  return tx;
};

// Пресет "Viral Exponential"
const createViralExponentialToken = async (
  program: Program,
  name: string,
  symbol: string,
) => {
  const curveParams = [
    new BN(10_000_000),      // 0.01 SOL базовая цена
    new BN(10_000_000),      // 0.01 growth factor (агрессивный)
    new BN(100_000_000_000), // 100k токенов max supply
  ];

  const tx = await program.methods
    .createToken(name, symbol, CurveType.Exponential, curveParams)
    .accounts({ /* ... */ })
    .rpc();

  return tx;
};

// Симуляция цены
const simulatePrice = (
  curveType: CurveType,
  params: BN[],
  supply: number,
): number => {
  switch (curveType) {
    case CurveType.Linear:
      return params[0].toNumber() + params[1].toNumber() * supply;

    case CurveType.Exponential:
      return params[0].toNumber() * Math.exp((params[1].toNumber() * supply) / 1e9);

    case CurveType.Sigmoid:
      const min = params[0].toNumber();
      const max = params[1].toNumber();
      const k = params[2].toNumber() / 1e9;
      const mid = params[3].toNumber();
      return min + (max - min) / (1 + Math.exp(-k * (supply - mid)));

    case CurveType.Logarithmic:
      return params[0].toNumber() + (params[1].toNumber() / 1e9) * Math.log(supply + 1);

    case CurveType.ConstantProduct:
      return params[0].toNumber() / params[1].toNumber();
  }
};
```

---

## Технические детали

### Точность вычислений
Все расчеты используют целочисленную арифметику с точностью:
- `PRECISION = 1_000_000_000` (9 знаков после запятой)
- Все операции используют `checked_*` методы для защиты от переполнения

### Аппроксимации
Для сложных математических функций используются аппроксимации:
- **Exponential**: Ряд Тейлора `e^x ≈ 1 + x + x²/2`
- **Logarithmic**: Нормализация + ряд Тейлора `ln(1+x) ≈ x - x²/2 + x³/3 - x⁴/4`

### Числовое интегрирование
Для кривых без аналитического решения интеграла используется численное интегрирование методом трапеций с адаптивным шагом.

### Безопасность
Все функции включают проверки:
- Защита от переполнения (`checked_add`, `checked_mul`, etc.)
- Валидация параметров (`require!` макросы)
- Проверка границ supply
- Расчет price impact для предупреждения о больших сделках

---

## FAQ

### Q: Можно ли изменить кривую после создания токена?
**A**: Нет, кривая фиксируется при создании для обеспечения честности и предсказуемости.

### Q: Что происходит при достижении max_supply?
**A**: Дальнейшая покупка невозможна. Система вернет ошибку `InvalidInitialSupply`.

### Q: Как работает миграция на DEX?
**A**: При достижении graduation threshold вся ликвидность переносится на Raydium с созданием постоянного пула. Подробнее в `graduate_to_dex.rs`.

### Q: Можно ли создать свою кривую?
**A**: Да! Реализуйте трейт `BondingCurveMath` и добавьте новый вариант в enum `CurveType`.

### Q: Какие комиссии берет платформа?
**A**: Конфигурируется в `pump-core`, обычно 1-2% на каждую операцию.

### Q: Защищена ли система от sandwich attacks?
**A**: Да, через параметр `min_tokens_out` / `min_sol_out` при выполнении сделки. Всегда устанавливайте slippage tolerance!

---

## Дополнительные ресурсы

- **Исходный код**: `/contracts/pump-core/programs/pump-core/src/utils/bonding_curve.rs`
- **Тесты**: `/contracts/pump-core/programs/pump-core/tests/bonding_curve_tests.rs`
- **State модели**: `/contracts/pump-core/programs/pump-core/src/state.rs`
- **Примеры интеграции**: `/frontend/src/utils/bondingCurve.ts`

---

**Создано**: 2025-01-XX
**Версия**: 1.0.0
**Авторы**: AnonyMeme Development Team
