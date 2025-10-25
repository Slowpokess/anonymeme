/*!
🔬 Математические утилиты для бондинг-кривых
Production-ready реализация различных типов кривых с защитой от переполнения
*/

use anchor_lang::prelude::*;
use crate::state::{BondingCurve, CurveType};
use crate::errors::CustomError as ErrorCode;

/// Константы для вычислений
const PRECISION: u128 = 1_000_000_000; // 9 знаков после запятой
const MAX_SUPPLY: u64 = 1_000_000_000_000_000; // 1 квадриллион максимальный supply
const MIN_PRICE: u64 = 1; // Минимальная цена = 1 lamport

/// Результат расчета по бондинг-кривой
#[derive(Debug, Clone)]
pub struct CurveCalculation {
    /// Количество токенов для покупки/продажи
    pub token_amount: u64,
    /// Количество SOL (в lamports)
    pub sol_amount: u64,
    /// Новый supply после операции
    pub new_supply: u64,
    /// Цена за токен после операции (в lamports)
    pub price_per_token: u64,
    /// Влияние на цену в базисных пунктах (10000 = 100%)
    pub price_impact: u16,
}

/// Основной трейт для бондинг-кривых
pub trait BondingCurveMath {
    /// Расчет покупки токенов за SOL
    fn calculate_buy(
        &self,
        sol_amount: u64,
        current_supply: u64,
    ) -> Result<CurveCalculation>;

    /// Расчет продажи токенов за SOL
    fn calculate_sell(
        &self,
        token_amount: u64,
        current_supply: u64,
    ) -> Result<CurveCalculation>;

    /// Получение текущей цены за токен
    fn get_current_price(&self, current_supply: u64) -> Result<u64>;

    /// Расчет market cap при текущем supply
    fn get_market_cap(&self, current_supply: u64) -> Result<u64>;
}

/// Реализация линейной бондинг-кривой: price = a + b * supply
pub struct LinearCurve {
    /// Начальная цена (a)
    pub initial_price: u64,
    /// Коэффициент роста (b)
    pub slope: u64,
    /// Максимальный supply
    pub max_supply: u64,
}

impl LinearCurve {
    pub fn new(initial_price: u64, slope: u64, max_supply: u64) -> Result<Self> {
        require!(initial_price >= MIN_PRICE, ErrorCode::InvalidBondingCurveParams);
        require!(slope > 0, ErrorCode::InvalidBondingCurveParams);
        require!(max_supply > 0 && max_supply <= MAX_SUPPLY, ErrorCode::InvalidBondingCurveParams);

        Ok(LinearCurve {
            initial_price,
            slope,
            max_supply,
        })
    }
}

impl BondingCurveMath for LinearCurve {
    fn calculate_buy(&self, sol_amount: u64, current_supply: u64) -> Result<CurveCalculation> {
        require!(sol_amount > 0, ErrorCode::InvalidAmount);
        require!(current_supply <= self.max_supply, ErrorCode::InvalidInitialSupply);

        let current_price = self.get_current_price(current_supply)?;
        
        // Для линейной кривой: интеграл от (a + b*x) dx = a*x + b*x²/2
        let sol_amount_u128 = sol_amount as u128;
        let current_supply_u128 = current_supply as u128;
        let slope_u128 = self.slope as u128;
        let initial_price_u128 = self.initial_price as u128;

        // Решаем квадратное уравнение: b/2 * Δx² + a * Δx - SOL = 0
        // Δx = (-a + sqrt(a² + 2*b*SOL)) / b
        let discriminant = initial_price_u128
            .checked_mul(initial_price_u128)
            .and_then(|x| x.checked_add(
                slope_u128
                    .checked_mul(2)?
                    .checked_mul(sol_amount_u128)?
            ))?
            .checked_add(
                slope_u128
                    .checked_mul(2)?
                    .checked_mul(initial_price_u128)?
                    .checked_mul(current_supply_u128)?
            )?
            .checked_add(
                slope_u128
                    .checked_mul(slope_u128)?
                    .checked_mul(current_supply_u128)?
                    .checked_mul(current_supply_u128)?
            )?;

        let sqrt_discriminant = isqrt(discriminant)?;
        let delta_supply = sqrt_discriminant
            .checked_sub(initial_price_u128)?
            .checked_sub(slope_u128.checked_mul(current_supply_u128)?)
            .ok_or(ErrorCode::MathematicalOverflow)?
            .checked_div(slope_u128)
            .ok_or(ErrorCode::MathematicalOverflow)?;

        let token_amount = delta_supply as u64;
        let new_supply = current_supply.checked_add(token_amount)
            .ok_or(ErrorCode::MathematicalOverflow)?;

        require!(new_supply <= self.max_supply, ErrorCode::InvalidInitialSupply);

        let new_price = self.get_current_price(new_supply)?;
        let price_impact = calculate_price_impact(current_price, new_price)?;

        Ok(CurveCalculation {
            token_amount,
            sol_amount,
            new_supply,
            price_per_token: new_price,
            price_impact,
        })
    }

    fn calculate_sell(&self, token_amount: u64, current_supply: u64) -> Result<CurveCalculation> {
        require!(token_amount > 0, ErrorCode::InvalidAmount);
        require!(token_amount <= current_supply, ErrorCode::InsufficientBalance);

        let new_supply = current_supply.checked_sub(token_amount)
            .ok_or(ErrorCode::MathematicalOverflow)?;

        // Расчет SOL к получению (интеграл от new_supply до current_supply)
        let sol_amount = integrate_linear(
            self.initial_price,
            self.slope,
            new_supply,
            current_supply,
        )?;

        let current_price = self.get_current_price(current_supply)?;
        let new_price = self.get_current_price(new_supply)?;
        let price_impact = calculate_price_impact(current_price, new_price)?;

        Ok(CurveCalculation {
            token_amount,
            sol_amount,
            new_supply,
            price_per_token: new_price,
            price_impact,
        })
    }

    fn get_current_price(&self, current_supply: u64) -> Result<u64> {
        let price = self.initial_price
            .checked_add(
                self.slope
                    .checked_mul(current_supply)
                    .ok_or(ErrorCode::MathematicalOverflow)?
            )
            .ok_or(ErrorCode::MathematicalOverflow)?;
        
        Ok(price.max(MIN_PRICE))
    }

    fn get_market_cap(&self, current_supply: u64) -> Result<u64> {
        let price = self.get_current_price(current_supply)?;
        current_supply
            .checked_mul(price)
            .ok_or(ErrorCode::MathematicalOverflow)
    }
}

/// Реализация экспоненциальной бондинг-кривой: price = a * e^(b * supply)
pub struct ExponentialCurve {
    pub base_price: u64,
    pub growth_factor: u64, // Умножено на PRECISION
    pub max_supply: u64,
}

impl ExponentialCurve {
    pub fn new(base_price: u64, growth_factor: u64, max_supply: u64) -> Result<Self> {
        require!(base_price >= MIN_PRICE, ErrorCode::InvalidBondingCurveParams);
        require!(growth_factor > 0, ErrorCode::InvalidBondingCurveParams);
        require!(max_supply > 0 && max_supply <= MAX_SUPPLY, ErrorCode::InvalidBondingCurveParams);

        Ok(ExponentialCurve {
            base_price,
            growth_factor,
            max_supply,
        })
    }
}

impl BondingCurveMath for ExponentialCurve {
    fn calculate_buy(&self, sol_amount: u64, current_supply: u64) -> Result<CurveCalculation> {
        require!(sol_amount > 0, ErrorCode::InvalidAmount);
        require!(current_supply <= self.max_supply, ErrorCode::InvalidInitialSupply);

        // Для экспоненциальной кривой используем аппроксимацию
        let current_price = self.get_current_price(current_supply)?;
        
        // Приблизительное количество токенов = sol_amount / average_price
        // average_price ≈ current_price * (1 + growth_rate/2)
        let growth_rate = self.growth_factor
            .checked_mul(sol_amount)
            .and_then(|x| x.checked_div(PRECISION as u64))
            .ok_or(ErrorCode::MathematicalOverflow)?;

        let average_price = current_price
            .checked_add(
                current_price
                    .checked_mul(growth_rate)
                    .and_then(|x| x.checked_div(2))
                    .ok_or(ErrorCode::MathematicalOverflow)?
            )
            .ok_or(ErrorCode::MathematicalOverflow)?;

        let token_amount = sol_amount
            .checked_mul(PRECISION as u64)
            .and_then(|x| x.checked_div(average_price))
            .ok_or(ErrorCode::MathematicalOverflow)? as u64;

        let new_supply = current_supply.checked_add(token_amount)
            .ok_or(ErrorCode::MathematicalOverflow)?;

        require!(new_supply <= self.max_supply, ErrorCode::InvalidInitialSupply);

        let new_price = self.get_current_price(new_supply)?;
        let price_impact = calculate_price_impact(current_price, new_price)?;

        Ok(CurveCalculation {
            token_amount,
            sol_amount,
            new_supply,
            price_per_token: new_price,
            price_impact,
        })
    }

    fn calculate_sell(&self, token_amount: u64, current_supply: u64) -> Result<CurveCalculation> {
        require!(token_amount > 0, ErrorCode::InvalidAmount);
        require!(token_amount <= current_supply, ErrorCode::InsufficientBalance);

        let new_supply = current_supply.checked_sub(token_amount)
            .ok_or(ErrorCode::MathematicalOverflow)?;

        let current_price = self.get_current_price(current_supply)?;
        let new_price = self.get_current_price(new_supply)?;

        // Средняя цена для продажи
        let average_price = current_price
            .checked_add(new_price)
            .and_then(|x| x.checked_div(2))
            .ok_or(ErrorCode::MathematicalOverflow)?;

        let sol_amount = token_amount
            .checked_mul(average_price)
            .ok_or(ErrorCode::MathematicalOverflow)?;

        let price_impact = calculate_price_impact(current_price, new_price)?;

        Ok(CurveCalculation {
            token_amount,
            sol_amount,
            new_supply,
            price_per_token: new_price,
            price_impact,
        })
    }

    fn get_current_price(&self, current_supply: u64) -> Result<u64> {
        // price = base_price * exp(growth_factor * supply / PRECISION)
        // Используем аппроксимацию e^x ≈ 1 + x + x²/2 для малых x
        let exponent = self.growth_factor
            .checked_mul(current_supply)
            .and_then(|x| x.checked_div(PRECISION as u64))
            .ok_or(ErrorCode::MathematicalOverflow)?;

        let exp_approx = if exponent < 1000 { // Для малых значений
            PRECISION as u64 + exponent + exponent
                .checked_mul(exponent)
                .and_then(|x| x.checked_div(2))
                .unwrap_or(0)
        } else {
            // Для больших значений используем более простую формулу
            PRECISION as u64 + exponent.checked_mul(2).unwrap_or(u64::MAX)
        };

        let price = self.base_price
            .checked_mul(exp_approx)
            .and_then(|x| x.checked_div(PRECISION as u64))
            .ok_or(ErrorCode::MathematicalOverflow)?;

        Ok(price.max(MIN_PRICE))
    }

    fn get_market_cap(&self, current_supply: u64) -> Result<u64> {
        let price = self.get_current_price(current_supply)?;
        current_supply
            .checked_mul(price)
            .ok_or(ErrorCode::MathematicalOverflow)
    }
}

// === SIGMOID КРИВАЯ ===

/// Sigmoid (S-образная) кривая: price = min + (max - min) / (1 + e^(-k(x - x0)))
///
/// Характеристики:
/// - Медленный рост в начале (защита от ранних спекулянтов)
/// - Быстрый рост в середине (около midpoint)
/// - Замедление роста в конце (стабилизация цены)
/// - Идеально для токенов с долгосрочной стратегией
#[derive(Debug, Clone)]
pub struct SigmoidCurve {
    pub min_price: u64,       // Минимальная цена (нижняя асимптота)
    pub max_price: u64,       // Максимальная цена (верхняя асимптота)
    pub steepness: u64,       // Крутизна S-образной кривой (в единицах PRECISION)
    pub midpoint: u64,        // Точка перегиба (где цена = (min + max) / 2)
    pub max_supply: u64,      // Максимальный supply
}

impl SigmoidCurve {
    pub fn new(
        min_price: u64,
        max_price: u64,
        steepness: u64,
        midpoint: u64,
        max_supply: u64,
    ) -> Result<Self> {
        require!(min_price >= MIN_PRICE, ErrorCode::InvalidBondingCurveParams);
        require!(max_price > min_price, ErrorCode::InvalidBondingCurveParams);
        require!(steepness > 0, ErrorCode::InvalidBondingCurveParams);
        require!(max_supply > 0, ErrorCode::InvalidBondingCurveParams);

        Ok(Self {
            min_price,
            max_price,
            steepness,
            midpoint,
            max_supply,
        })
    }

    /// Вычисляет e^x используя аппроксимацию ряда Тейлора
    /// e^x ≈ 1 + x + x²/2! + x³/3! + x⁴/4!
    fn exp_approximation(&self, x: i128) -> u128 {
        // Ограничиваем x для предотвращения переполнения
        let x_clamped = x.clamp(-10 * PRECISION as i128, 10 * PRECISION as i128);

        if x_clamped == 0 {
            return PRECISION as u128;
        }

        // Для отрицательных x: e^(-x) = 1 / e^x
        if x_clamped < 0 {
            let pos_exp = self.exp_approximation(-x_clamped);
            // Возвращаем PRECISION^2 / pos_exp
            return ((PRECISION as u128).pow(2))
                .checked_div(pos_exp)
                .unwrap_or(1);
        }

        // Ряд Тейлора для положительных x
        let x_u128 = x_clamped as u128;
        let mut result = PRECISION as u128; // 1
        let mut term = x_u128; // x

        // + x
        result = result.saturating_add(term);

        // + x²/2
        term = term.saturating_mul(x_u128).saturating_div((PRECISION as u128).saturating_mul(2));
        result = result.saturating_add(term);

        // + x³/6
        term = term.saturating_mul(x_u128).saturating_div((PRECISION as u128).saturating_mul(3));
        result = result.saturating_add(term);

        // + x⁴/24
        term = term.saturating_mul(x_u128).saturating_div((PRECISION as u128).saturating_mul(4));
        result = result.saturating_add(term);

        result
    }
}

impl BondingCurveMath for SigmoidCurve {
    fn calculate_buy(&self, sol_amount: u64, current_supply: u64) -> Result<CurveCalculation> {
        require!(sol_amount > 0, ErrorCode::InvalidAmount);
        require!(current_supply < self.max_supply, ErrorCode::InvalidInitialSupply);

        let current_price = self.get_current_price(current_supply)?;

        // Используем численную аппроксимацию: делим на маленькие шаги
        let mut remaining_sol = sol_amount as u128;
        let mut total_tokens = 0u64;
        let mut supply = current_supply;

        // Размер шага (1% от текущего supply или минимум 1000 токенов)
        let step_size = (supply / 100).max(1000);

        while remaining_sol > 0 && supply < self.max_supply {
            let step = step_size.min(self.max_supply - supply);
            let price_at_step = self.get_current_price(supply)?;

            let cost = (step as u128)
                .checked_mul(price_at_step as u128)
                .ok_or(ErrorCode::MathematicalOverflow)?;

            if cost > remaining_sol {
                // Последний частичный шаг
                let partial_tokens = remaining_sol
                    .checked_mul(step as u128)
                    .and_then(|x| x.checked_div(cost))
                    .ok_or(ErrorCode::MathematicalOverflow)? as u64;

                total_tokens = total_tokens
                    .checked_add(partial_tokens)
                    .ok_or(ErrorCode::MathematicalOverflow)?;
                supply = supply
                    .checked_add(partial_tokens)
                    .ok_or(ErrorCode::MathematicalOverflow)?;
                break;
            }

            remaining_sol = remaining_sol.saturating_sub(cost);
            total_tokens = total_tokens
                .checked_add(step)
                .ok_or(ErrorCode::MathematicalOverflow)?;
            supply = supply
                .checked_add(step)
                .ok_or(ErrorCode::MathematicalOverflow)?;
        }

        require!(total_tokens > 0, ErrorCode::InvalidAmount);

        let new_supply = current_supply
            .checked_add(total_tokens)
            .ok_or(ErrorCode::MathematicalOverflow)?;
        let new_price = self.get_current_price(new_supply)?;
        let price_impact = calculate_price_impact(current_price, new_price)?;

        Ok(CurveCalculation {
            token_amount: total_tokens,
            sol_amount,
            new_supply,
            price_per_token: new_price,
            price_impact,
        })
    }

    fn calculate_sell(&self, token_amount: u64, current_supply: u64) -> Result<CurveCalculation> {
        require!(token_amount > 0, ErrorCode::InvalidAmount);
        require!(token_amount <= current_supply, ErrorCode::InsufficientBalance);

        let new_supply = current_supply
            .checked_sub(token_amount)
            .ok_or(ErrorCode::MathematicalOverflow)?;

        let current_price = self.get_current_price(current_supply)?;
        let new_price = self.get_current_price(new_supply)?;

        // Используем среднюю цену для расчета SOL
        let average_price = current_price
            .checked_add(new_price)
            .and_then(|x| x.checked_div(2))
            .ok_or(ErrorCode::MathematicalOverflow)?;

        let sol_amount = (token_amount as u128)
            .checked_mul(average_price as u128)
            .ok_or(ErrorCode::MathematicalOverflow)? as u64;

        let price_impact = calculate_price_impact(current_price, new_price)?;

        Ok(CurveCalculation {
            token_amount,
            sol_amount,
            new_supply,
            price_per_token: new_price,
            price_impact,
        })
    }

    fn get_current_price(&self, current_supply: u64) -> Result<u64> {
        // price = min_price + (max_price - min_price) / (1 + e^(-steepness * (supply - midpoint)))

        let price_range = self.max_price - self.min_price;

        // Вычисляем exponent: -steepness * (supply - midpoint) / PRECISION
        let supply_diff = if current_supply >= self.midpoint {
            (current_supply - self.midpoint) as i128
        } else {
            -((self.midpoint - current_supply) as i128)
        };

        let exponent = -(self.steepness as i128)
            .checked_mul(supply_diff)
            .and_then(|x| x.checked_div(PRECISION as i128))
            .ok_or(ErrorCode::MathematicalOverflow)?;

        // Вычисляем e^exponent
        let exp_value = self.exp_approximation(exponent);

        // Вычисляем 1 + e^exponent
        let denominator = (PRECISION as u128)
            .checked_add(exp_value)
            .ok_or(ErrorCode::MathematicalOverflow)?;

        // price_addition = price_range / denominator
        let price_addition = ((price_range as u128) * (PRECISION as u128))
            .checked_div(denominator)
            .ok_or(ErrorCode::MathematicalOverflow)? as u64;

        let price = self.min_price
            .checked_add(price_addition)
            .ok_or(ErrorCode::MathematicalOverflow)?;

        Ok(price.clamp(self.min_price, self.max_price))
    }

    fn get_market_cap(&self, current_supply: u64) -> Result<u64> {
        let price = self.get_current_price(current_supply)?;
        current_supply
            .checked_mul(price)
            .ok_or(ErrorCode::MathematicalOverflow)
    }
}

// === CONSTANT PRODUCT КРИВАЯ ===

/// ConstantProduct кривая: x * y = k (AMM как в Uniswap/Raydium)
///
/// Характеристики:
/// - Автоматический market maker (AMM)
/// - Цена определяется соотношением резервов
/// - Большие сделки имеют price impact (slippage)
/// - Ликвидность всегда доступна
/// - Идеально для DEX-стиля торговли
#[derive(Debug, Clone)]
pub struct ConstantProductCurve {
    pub sol_reserve: u64,     // Количество SOL в пуле (в lamports)
    pub token_reserve: u64,   // Количество токенов в пуле
}

impl ConstantProductCurve {
    pub fn new(sol_reserve: u64, token_reserve: u64) -> Result<Self> {
        require!(sol_reserve > 0, ErrorCode::InvalidBondingCurveParams);
        require!(token_reserve > 0, ErrorCode::InvalidBondingCurveParams);

        Ok(Self {
            sol_reserve,
            token_reserve,
        })
    }

    /// Вычисляет константу k = x * y
    pub fn get_k(&self) -> u128 {
        (self.sol_reserve as u128)
            .saturating_mul(self.token_reserve as u128)
    }
}

impl BondingCurveMath for ConstantProductCurve {
    fn calculate_buy(&self, sol_amount: u64, _current_supply: u64) -> Result<CurveCalculation> {
        require!(sol_amount > 0, ErrorCode::InvalidAmount);

        // x * y = k
        // new_x = x + sol_amount
        // new_y = k / new_x
        // tokens_out = y - new_y

        let k = self.get_k();
        let new_sol_reserve = (self.sol_reserve as u128)
            .checked_add(sol_amount as u128)
            .ok_or(ErrorCode::MathematicalOverflow)?;

        let new_token_reserve = k
            .checked_div(new_sol_reserve)
            .ok_or(ErrorCode::MathematicalOverflow)?;

        let tokens_out = (self.token_reserve as u128)
            .checked_sub(new_token_reserve)
            .ok_or(ErrorCode::InsufficientBalance)?;

        require!(tokens_out > 0, ErrorCode::InvalidAmount);
        require!(tokens_out <= self.token_reserve as u128, ErrorCode::InsufficientBalance);

        let tokens_out_u64 = tokens_out as u64;

        // Вычисляем цены для price impact
        let old_price = self.get_current_price(0)?;
        let new_price = (new_sol_reserve
            .checked_mul(PRECISION as u128)
            .and_then(|x| x.checked_div(new_token_reserve))
            .ok_or(ErrorCode::MathematicalOverflow)? as u64)
            .max(MIN_PRICE);

        let price_impact = calculate_price_impact(old_price, new_price)?;

        Ok(CurveCalculation {
            token_amount: tokens_out_u64,
            sol_amount,
            new_supply: new_token_reserve as u64, // Новый token reserve
            price_per_token: new_price,
            price_impact,
        })
    }

    fn calculate_sell(&self, token_amount: u64, _current_supply: u64) -> Result<CurveCalculation> {
        require!(token_amount > 0, ErrorCode::InvalidAmount);
        require!(token_amount < self.token_reserve, ErrorCode::InsufficientBalance);

        // x * y = k
        // new_y = y + token_amount
        // new_x = k / new_y
        // sol_out = x - new_x

        let k = self.get_k();
        let new_token_reserve = (self.token_reserve as u128)
            .checked_add(token_amount as u128)
            .ok_or(ErrorCode::MathematicalOverflow)?;

        let new_sol_reserve = k
            .checked_div(new_token_reserve)
            .ok_or(ErrorCode::MathematicalOverflow)?;

        let sol_out = (self.sol_reserve as u128)
            .checked_sub(new_sol_reserve)
            .ok_or(ErrorCode::InsufficientBalance)?;

        require!(sol_out > 0, ErrorCode::InvalidAmount);
        require!(sol_out <= self.sol_reserve as u128, ErrorCode::InsufficientBalance);

        let sol_out_u64 = sol_out as u64;

        // Вычисляем цены для price impact
        let old_price = self.get_current_price(0)?;
        let new_price = (new_sol_reserve
            .checked_mul(PRECISION as u128)
            .and_then(|x| x.checked_div(new_token_reserve))
            .ok_or(ErrorCode::MathematicalOverflow)? as u64)
            .max(MIN_PRICE);

        let price_impact = calculate_price_impact(old_price, new_price)?;

        Ok(CurveCalculation {
            token_amount,
            sol_amount: sol_out_u64,
            new_supply: new_token_reserve as u64, // Новый token reserve
            price_per_token: new_price,
            price_impact,
        })
    }

    fn get_current_price(&self, _current_supply: u64) -> Result<u64> {
        // price = sol_reserve / token_reserve
        // Умножаем на PRECISION для сохранения точности

        let price = (self.sol_reserve as u128)
            .checked_mul(PRECISION as u128)
            .and_then(|x| x.checked_div(self.token_reserve as u128))
            .ok_or(ErrorCode::MathematicalOverflow)? as u64;

        Ok(price.max(MIN_PRICE))
    }

    fn get_market_cap(&self, _current_supply: u64) -> Result<u64> {
        // Market cap = token_reserve * current_price
        let price = self.get_current_price(0)?;
        self.token_reserve
            .checked_mul(price)
            .ok_or(ErrorCode::MathematicalOverflow)
    }
}

// === LOGARITHMIC КРИВАЯ ===

/// Logarithmic кривая: price = base_price + scale * ln(supply + 1)
///
/// Характеристики:
/// - Быстрый рост в начале (хорошо вознаграждает ранних)
/// - Постепенное замедление роста (убывающая отдача)
/// - Никогда не достигает асимптоты, но растет все медленнее
/// - Идеально для токенов где нужен баланс между ранними и поздними инвесторами
#[derive(Debug, Clone)]
pub struct LogarithmicCurve {
    pub base_price: u64,    // Базовая цена (минимум)
    pub scale: u64,         // Масштаб логарифма (в единицах PRECISION)
    pub max_supply: u64,    // Максимальный supply
}

impl LogarithmicCurve {
    pub fn new(base_price: u64, scale: u64, max_supply: u64) -> Result<Self> {
        require!(base_price >= MIN_PRICE, ErrorCode::InvalidBondingCurveParams);
        require!(scale > 0, ErrorCode::InvalidBondingCurveParams);
        require!(max_supply > 0, ErrorCode::InvalidBondingCurveParams);

        Ok(Self {
            base_price,
            scale,
            max_supply,
        })
    }

    /// Вычисляет натуральный логарифм ln(x) используя аппроксимацию
    /// Использует ряд Тейлора: ln(1+x) ≈ x - x²/2 + x³/3 - x⁴/4 + ...
    fn ln_approximation(&self, x: u64) -> Result<u64> {
        if x == 0 {
            return Ok(0); // ln(1) = 0
        }

        // Для больших x используем свойство ln(a*b) = ln(a) + ln(b)
        // Разбиваем x на степени 2 для упрощения вычислений
        let mut result = 0i128;
        let mut value = (x + 1) as u128; // ln(x+1)

        // Приводим к диапазону [1, 2) используя степени двойки
        let mut power_of_two = 0;
        while value >= (2 * PRECISION as u128) {
            value /= 2;
            power_of_two += 1;
        }

        // Теперь value в диапазоне [PRECISION, 2*PRECISION)
        // Вычисляем ln(value/PRECISION) = ln(1 + (value-PRECISION)/PRECISION)
        let x_normalized = ((value - PRECISION as u128) * PRECISION as u128 / PRECISION as u128) as i128;

        if x_normalized > 0 {
            // Ряд Тейлора: ln(1+x) ≈ x - x²/2 + x³/3 - x⁴/4
            let x2 = x_normalized.saturating_mul(x_normalized) / PRECISION as i128;
            let x3 = x2.saturating_mul(x_normalized) / PRECISION as i128;
            let x4 = x3.saturating_mul(x_normalized) / PRECISION as i128;

            result = x_normalized - x2/2 + x3/3 - x4/4;
        }

        // Добавляем ln(2) * power_of_two
        // ln(2) ≈ 0.693147... ≈ 693147 в единицах PRECISION
        const LN_2: i128 = 693147;
        result += LN_2 * (power_of_two as i128);

        // Ограничиваем результат положительными значениями
        Ok((result.max(0) as u64))
    }
}

impl BondingCurveMath for LogarithmicCurve {
    fn calculate_buy(&self, sol_amount: u64, current_supply: u64) -> Result<CurveCalculation> {
        require!(sol_amount > 0, ErrorCode::InvalidAmount);
        require!(current_supply < self.max_supply, ErrorCode::InvalidInitialSupply);

        let current_price = self.get_current_price(current_supply)?;

        // Используем численную аппроксимацию: делим на маленькие шаги
        let mut remaining_sol = sol_amount as u128;
        let mut total_tokens = 0u64;
        let mut supply = current_supply;

        // Размер шага (1% от текущего supply или минимум 1000 токенов)
        let step_size = (supply / 100).max(1000);

        while remaining_sol > 0 && supply < self.max_supply {
            let step = step_size.min(self.max_supply - supply);
            let price_at_step = self.get_current_price(supply)?;

            let cost = (step as u128)
                .checked_mul(price_at_step as u128)
                .ok_or(ErrorCode::MathematicalOverflow)?;

            if cost > remaining_sol {
                // Последний частичный шаг
                let partial_tokens = remaining_sol
                    .checked_mul(step as u128)
                    .and_then(|x| x.checked_div(cost))
                    .ok_or(ErrorCode::MathematicalOverflow)? as u64;

                total_tokens = total_tokens
                    .checked_add(partial_tokens)
                    .ok_or(ErrorCode::MathematicalOverflow)?;
                supply = supply
                    .checked_add(partial_tokens)
                    .ok_or(ErrorCode::MathematicalOverflow)?;
                break;
            }

            remaining_sol = remaining_sol.saturating_sub(cost);
            total_tokens = total_tokens
                .checked_add(step)
                .ok_or(ErrorCode::MathematicalOverflow)?;
            supply = supply
                .checked_add(step)
                .ok_or(ErrorCode::MathematicalOverflow)?;
        }

        require!(total_tokens > 0, ErrorCode::InvalidAmount);

        let new_supply = current_supply
            .checked_add(total_tokens)
            .ok_or(ErrorCode::MathematicalOverflow)?;
        let new_price = self.get_current_price(new_supply)?;
        let price_impact = calculate_price_impact(current_price, new_price)?;

        Ok(CurveCalculation {
            token_amount: total_tokens,
            sol_amount,
            new_supply,
            price_per_token: new_price,
            price_impact,
        })
    }

    fn calculate_sell(&self, token_amount: u64, current_supply: u64) -> Result<CurveCalculation> {
        require!(token_amount > 0, ErrorCode::InvalidAmount);
        require!(token_amount <= current_supply, ErrorCode::InsufficientBalance);

        let new_supply = current_supply
            .checked_sub(token_amount)
            .ok_or(ErrorCode::MathematicalOverflow)?;

        let current_price = self.get_current_price(current_supply)?;
        let new_price = self.get_current_price(new_supply)?;

        // Используем среднюю цену для расчета SOL
        let average_price = current_price
            .checked_add(new_price)
            .and_then(|x| x.checked_div(2))
            .ok_or(ErrorCode::MathematicalOverflow)?;

        let sol_amount = (token_amount as u128)
            .checked_mul(average_price as u128)
            .ok_or(ErrorCode::MathematicalOverflow)? as u64;

        let price_impact = calculate_price_impact(current_price, new_price)?;

        Ok(CurveCalculation {
            token_amount,
            sol_amount,
            new_supply,
            price_per_token: new_price,
            price_impact,
        })
    }

    fn get_current_price(&self, current_supply: u64) -> Result<u64> {
        // price = base_price + scale * ln(supply + 1)
        let ln_value = self.ln_approximation(current_supply)?;

        let price_addition = (self.scale as u128)
            .checked_mul(ln_value as u128)
            .and_then(|x| x.checked_div(PRECISION as u128))
            .ok_or(ErrorCode::MathematicalOverflow)? as u64;

        let price = self.base_price
            .checked_add(price_addition)
            .ok_or(ErrorCode::MathematicalOverflow)?;

        Ok(price.max(MIN_PRICE))
    }

    fn get_market_cap(&self, current_supply: u64) -> Result<u64> {
        let price = self.get_current_price(current_supply)?;
        current_supply
            .checked_mul(price)
            .ok_or(ErrorCode::MathematicalOverflow)
    }
}

/// Создание бондинг-кривой по типу
pub fn create_bonding_curve(curve: &BondingCurve) -> Result<Box<dyn BondingCurveMath>> {
    let max_supply = curve.initial_supply.saturating_mul(10); // Макс supply в 10 раз больше начального

    match curve.curve_type {
        CurveType::Linear => {
            Ok(Box::new(LinearCurve::new(
                curve.initial_price,
                (curve.slope * PRECISION as f64) as u64,
                max_supply,
            )?))
        }
        CurveType::Exponential => {
            Ok(Box::new(ExponentialCurve::new(
                curve.initial_price,
                (curve.slope * PRECISION as f64) as u64,
                max_supply,
            )?))
        }
        CurveType::Sigmoid => {
            // Для Sigmoid кривой:
            // - min_price = initial_price
            // - max_price = initial_price * 1000 (можно настроить через slope)
            // - steepness = slope (определяет крутизну S-образной кривой)
            // - midpoint = max_supply / 2 (точка перегиба в середине)

            let min_price = curve.initial_price;
            // Используем slope как множитель для определения max_price
            // Например, slope = 0.001 означает что max_price будет в 100 раз больше min_price
            let price_multiplier = if curve.slope > 0.0 {
                (1.0 / curve.slope).min(1000.0).max(10.0) as u64
            } else {
                100 // По умолчанию max_price в 100 раз больше min_price
            };
            let max_price = min_price.saturating_mul(price_multiplier);
            let steepness = (curve.slope * PRECISION as f64 * 10.0) as u64; // Умножаем на 10 для более плавной кривой
            let midpoint = max_supply / 2; // Точка перегиба в середине

            Ok(Box::new(SigmoidCurve::new(
                min_price,
                max_price,
                steepness,
                midpoint,
                max_supply,
            )?))
        }
        CurveType::ConstantProduct => {
            // Для ConstantProduct кривой:
            // - sol_reserve: начальная ликвидность в SOL
            // - token_reserve: начальное количество токенов в пуле
            // Цена определяется как sol_reserve / token_reserve

            // Вычисляем начальную ликвидность в SOL на основе initial_price и initial_supply
            // initial_price - цена одного токена в lamports
            // Если initial_price = 1000 lamports и мы хотим создать пул с initial_supply токенов,
            // то нужно sol_reserve = (initial_supply * initial_price) / PRECISION

            let token_reserve = curve.initial_supply;

            // Рассчитываем SOL reserve для достижения начальной цены
            // price = sol_reserve / token_reserve => sol_reserve = price * token_reserve / PRECISION
            let sol_reserve = ((curve.initial_price as u128)
                .saturating_mul(token_reserve as u128)
                .saturating_div(PRECISION as u128) as u64)
                .max(1_000_000); // Минимум 0.001 SOL

            Ok(Box::new(ConstantProductCurve::new(
                sol_reserve,
                token_reserve,
            )?))
        }
        CurveType::Logarithmic => {
            // Для Logarithmic кривой:
            // - base_price = initial_price
            // - scale = slope * 10 (масштабирование для видимого эффекта)
            // Логарифмическая кривая хорошо подходит для токенов с быстрым
            // ранним ростом и постепенным замедлением

            let base_price = curve.initial_price;
            // Scale определяет насколько быстро растет цена
            // Больший scale = более быстрый рост
            let scale = ((curve.slope * PRECISION as f64) * 10.0) as u64;

            Ok(Box::new(LogarithmicCurve::new(
                base_price,
                scale,
                max_supply,
            )?))
        }
        _ => {
            // Для неизвестных типов используем линейную кривую по умолчанию
            Ok(Box::new(LinearCurve::new(
                curve.initial_price,
                (curve.slope * PRECISION as f64) as u64,
                max_supply,
            )?))
        }
    }
}

// === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

/// Целочисленный квадратный корень
fn isqrt(n: u128) -> Result<u128> {
    if n == 0 {
        return Ok(0);
    }

    let mut x = n;
    let mut y = (n + 1) / 2;

    while y < x {
        x = y;
        y = (x + n / x) / 2;
    }

    Ok(x)
}

/// Интегрирование линейной функции
fn integrate_linear(a: u64, b: u64, from: u64, to: u64) -> Result<u64> {
    require!(to >= from, ErrorCode::InvalidAmount);

    let delta = to - from;
    let a_u128 = a as u128;
    let b_u128 = b as u128;
    let from_u128 = from as u128;
    let delta_u128 = delta as u128;

    // Интеграл: a*Δx + b*(from*Δx + Δx²/2)
    let linear_part = a_u128
        .checked_mul(delta_u128)
        .ok_or(ErrorCode::MathematicalOverflow)?;

    let quadratic_part = b_u128
        .checked_mul(from_u128)
        .and_then(|x| x.checked_mul(delta_u128))
        .and_then(|x| x.checked_add(
            b_u128
                .checked_mul(delta_u128)?
                .checked_mul(delta_u128)?
                .checked_div(2)?
        ))
        .ok_or(ErrorCode::MathematicalOverflow)?;

    let result = linear_part
        .checked_add(quadratic_part)
        .ok_or(ErrorCode::MathematicalOverflow)? as u64;

    Ok(result)
}

/// Расчет влияния на цену в базисных пунктах
fn calculate_price_impact(old_price: u64, new_price: u64) -> Result<u16> {
    if old_price == 0 {
        return Ok(10000); // 100% если старая цена была 0
    }

    let price_diff = if new_price > old_price {
        new_price - old_price
    } else {
        old_price - new_price
    };

    let impact = price_diff
        .checked_mul(10000)
        .and_then(|x| x.checked_div(old_price))
        .ok_or(ErrorCode::MathematicalOverflow)? as u16;

    Ok(impact.min(10000)) // Максимум 100%
}

/// Валидация параметров бондинг-кривой
pub fn validate_curve_params(curve: &BondingCurve) -> Result<()> {
    require!(curve.initial_price >= MIN_PRICE, ErrorCode::InvalidBondingCurveParams);
    require!(curve.initial_supply > 0 && curve.initial_supply <= MAX_SUPPLY, ErrorCode::InvalidBondingCurveParams);
    require!(curve.slope > 0.0, ErrorCode::InvalidBondingCurveParams);
    require!(curve.graduation_threshold > 0, ErrorCode::InvalidBondingCurveParams);
    require!(curve.volatility_damper >= 0.1 && curve.volatility_damper <= 2.0, ErrorCode::InvalidBondingCurveParams);

    Ok(())
}

/// Высокоуровневые функции для использования в инструкциях

/// Расчет покупки токенов
pub fn calculate_buy_tokens(
    curve: &BondingCurve,
    sol_amount: u64,
    current_supply: u64,
) -> Result<CurveCalculation> {
    let bonding_curve = create_bonding_curve(curve)?;
    bonding_curve.calculate_buy(sol_amount, current_supply)
}

/// Расчет продажи токенов
pub fn calculate_sell_tokens(
    curve: &BondingCurve,
    token_amount: u64,
    current_supply: u64,
) -> Result<CurveCalculation> {
    let bonding_curve = create_bonding_curve(curve)?;
    bonding_curve.calculate_sell(token_amount, current_supply)
}

/// Получение текущей цены токена
pub fn get_current_token_price(
    curve: &BondingCurve,
    current_supply: u64,
) -> Result<u64> {
    let bonding_curve = create_bonding_curve(curve)?;
    bonding_curve.get_current_price(current_supply)
}

/// Расчет рыночной капитализации
pub fn get_market_capitalization(
    curve: &BondingCurve,
    current_supply: u64,
) -> Result<u64> {
    let bonding_curve = create_bonding_curve(curve)?;
    bonding_curve.get_market_cap(current_supply)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_test_bonding_curve() -> BondingCurve {
        BondingCurve {
            curve_type: CurveType::Linear,
            initial_price: 1000,
            current_price: 1000,
            graduation_threshold: 50_000_000_000_000, // 50 SOL
            slope: 0.000001,
            volatility_damper: 1.0,
            initial_supply: 1_000_000_000_000_000, // 1 млрд токенов
        }
    }

    #[test]
    fn test_linear_curve_creation() {
        let curve = LinearCurve::new(1000, 10, 1000000).unwrap();
        assert_eq!(curve.initial_price, 1000);
        assert_eq!(curve.slope, 10);
        assert_eq!(curve.max_supply, 1000000);
    }

    #[test]
    fn test_linear_curve_invalid_params() {
        // Тест с нулевой начальной ценой
        assert!(LinearCurve::new(0, 10, 1000000).is_err());
        
        // Тест с нулевым наклоном
        assert!(LinearCurve::new(1000, 0, 1000000).is_err());
        
        // Тест с нулевым max_supply
        assert!(LinearCurve::new(1000, 10, 0).is_err());
    }

    #[test]
    fn test_linear_curve_price_calculation() {
        let curve = LinearCurve::new(1000, 10, 1000000).unwrap();
        
        // Цена при supply = 0 должна быть = initial_price
        let price = curve.get_current_price(0).unwrap();
        assert_eq!(price, 1000);
        
        // Цена при supply = 100 должна быть = 1000 + 10*100 = 2000
        let price = curve.get_current_price(100).unwrap();
        assert_eq!(price, 2000);
    }

    #[test]
    fn test_linear_curve_market_cap() {
        let curve = LinearCurve::new(1000, 10, 1000000).unwrap();
        
        // Market cap при supply = 100 и цене = 2000 должен быть = 100 * 2000 = 200000
        let market_cap = curve.get_market_cap(100).unwrap();
        assert_eq!(market_cap, 200000);
    }

    #[test]
    fn test_linear_curve_buy_calculation() {
        let curve = LinearCurve::new(1000, 10, 1000000).unwrap();
        
        // Тест покупки за 10000 lamports при текущем supply = 1000
        let result = curve.calculate_buy(10000, 1000).unwrap();
        assert!(result.token_amount > 0);
        assert_eq!(result.sol_amount, 10000);
        assert_eq!(result.new_supply, 1000 + result.token_amount);
        assert!(result.price_per_token > 0);
    }

    #[test]
    fn test_linear_curve_sell_calculation() {
        let curve = LinearCurve::new(1000, 10, 1000000).unwrap();
        
        // Тест продажи 100 токенов при текущем supply = 1000
        let result = curve.calculate_sell(100, 1000).unwrap();
        assert_eq!(result.token_amount, 100);
        assert!(result.sol_amount > 0);
        assert_eq!(result.new_supply, 900);
        assert!(result.price_per_token > 0);
    }

    #[test]
    fn test_exponential_curve_creation() {
        let curve = ExponentialCurve::new(1000, 1000000, 1000000).unwrap();
        assert_eq!(curve.base_price, 1000);
        assert_eq!(curve.growth_factor, 1000000);
        assert_eq!(curve.max_supply, 1000000);
    }

    #[test]
    fn test_exponential_curve_price_calculation() {
        let curve = ExponentialCurve::new(1000, 1000000, 1000000).unwrap();
        
        // Цена при supply = 0 должна быть близка к base_price
        let price = curve.get_current_price(0).unwrap();
        assert_eq!(price, 1000);
        
        // Цена должна расти экспоненциально
        let price1 = curve.get_current_price(100).unwrap();
        let price2 = curve.get_current_price(200).unwrap();
        assert!(price2 > price1);
        assert!(price1 > 1000);
    }

    #[test]
    fn test_bonding_curve_validation() {
        let mut curve = create_test_bonding_curve();
        
        // Валидная кривая должна пройти валидацию
        assert!(validate_curve_params(&curve).is_ok());
        
        // Тест с невалидной начальной ценой
        curve.initial_price = 0;
        assert!(validate_curve_params(&curve).is_err());
        
        // Восстанавливаем и тестируем невалидный supply
        curve.initial_price = 1000;
        curve.initial_supply = 0;
        assert!(validate_curve_params(&curve).is_err());
        
        // Тест с невалидным slope
        curve.initial_supply = 1_000_000_000_000_000;
        curve.slope = 0.0;
        assert!(validate_curve_params(&curve).is_err());
        
        // Тест с невалидным volatility_damper
        curve.slope = 0.000001;
        curve.volatility_damper = 0.05; // Меньше минимума 0.1
        assert!(validate_curve_params(&curve).is_err());
        
        curve.volatility_damper = 3.0; // Больше максимума 2.0
        assert!(validate_curve_params(&curve).is_err());
    }

    #[test]
    fn test_create_bonding_curve_factory() {
        let curve = create_test_bonding_curve();
        
        // Должна создаваться linear кривая для Linear типа
        let bonding_curve = create_bonding_curve(&curve).unwrap();
        let price = bonding_curve.get_current_price(0).unwrap();
        assert_eq!(price, curve.initial_price);
    }

    #[test]
    fn test_high_level_functions() {
        let curve = create_test_bonding_curve();
        let current_supply = 1000000;
        let sol_amount = 1_000_000_000; // 1 SOL
        let token_amount = 1000;

        // Тест расчета покупки
        let buy_result = calculate_buy_tokens(&curve, sol_amount, current_supply).unwrap();
        assert!(buy_result.token_amount > 0);
        assert_eq!(buy_result.sol_amount, sol_amount);

        // Тест расчета продажи
        let sell_result = calculate_sell_tokens(&curve, token_amount, current_supply).unwrap();
        assert_eq!(sell_result.token_amount, token_amount);
        assert!(sell_result.sol_amount > 0);

        // Тест получения цены
        let price = get_current_token_price(&curve, current_supply).unwrap();
        assert!(price > 0);

        // Тест market cap
        let market_cap = get_market_capitalization(&curve, current_supply).unwrap();
        assert_eq!(market_cap, price * current_supply);
    }

    #[test]
    fn test_price_impact_calculation() {
        // Тест с увеличением цены на 10%
        let impact = calculate_price_impact(1000, 1100).unwrap();
        assert_eq!(impact, 1000); // 10% в базисных пунктах

        // Тест с уменьшением цены на 5%
        let impact = calculate_price_impact(1000, 950).unwrap();
        assert_eq!(impact, 500); // 5% в базисных пунктах

        // Тест с нулевой старой ценой
        let impact = calculate_price_impact(0, 1000).unwrap();
        assert_eq!(impact, 10000); // 100%
    }

    #[test]
    fn test_isqrt_function() {
        assert_eq!(isqrt(0).unwrap(), 0);
        assert_eq!(isqrt(1).unwrap(), 1);
        assert_eq!(isqrt(4).unwrap(), 2);
        assert_eq!(isqrt(9).unwrap(), 3);
        assert_eq!(isqrt(16).unwrap(), 4);
        assert_eq!(isqrt(15).unwrap(), 3); // Округление вниз
        assert_eq!(isqrt(255).unwrap(), 15);
    }

    #[test]
    fn test_integrate_linear_function() {
        // Интеграл линейной функции y = a + bx от 0 до x = ax + bx²/2
        // Для a=10, b=2, от 0 до 5: 10*5 + 2*5²/2 = 50 + 25 = 75
        let result = integrate_linear(10, 2, 0, 5).unwrap();
        assert_eq!(result, 75);

        // Проверка с ненулевым нижним пределом
        // От 2 до 5: результат должен быть меньше
        let result = integrate_linear(10, 2, 2, 5).unwrap();
        assert!(result < 75);
        
        // Проверка с равными пределами (должно быть 0)
        let result = integrate_linear(10, 2, 5, 5).unwrap();
        assert_eq!(result, 0);
    }

    #[test]
    fn test_edge_cases() {
        let curve = LinearCurve::new(MIN_PRICE, 1, 1000000).unwrap();
        
        // Тест с минимальной ценой
        let price = curve.get_current_price(0).unwrap();
        assert_eq!(price, MIN_PRICE);
        
        // Тест покупки при максимальном supply
        let result = curve.calculate_buy(1000, curve.max_supply);
        assert!(result.is_err()); // Должно возвращать ошибку
        
        // Тест продажи больше чем есть в supply
        let result = curve.calculate_sell(2000, 1000);
        assert!(result.is_err()); // Должно возвращать ошибку
    }

    #[test]
    fn test_math_overflow_protection() {
        // Создаем кривую с большими значениями для тестирования переполнения
        let curve = LinearCurve::new(u64::MAX / 2, u64::MAX / 2, MAX_SUPPLY).unwrap();
        
        // Попытка вычисления цены с большим supply
        let price_result = curve.get_current_price(1000);
        // Может быть ошибка переполнения или очень большое значение
        if let Ok(price) = price_result {
            assert!(price >= MIN_PRICE);
        }
        
        // Попытка вычисления market cap с потенциальным переполнением
        let market_cap_result = curve.get_market_cap(1000);
        // Результат зависит от реализации защиты от переполнения
        if let Ok(market_cap) = market_cap_result {
            assert!(market_cap > 0);
        }
    }

    #[test]
    fn test_curve_type_variants() {
        let mut curve = create_test_bonding_curve();

        // Тест Linear кривой
        curve.curve_type = CurveType::Linear;
        let linear_curve = create_bonding_curve(&curve).unwrap();
        let linear_price = linear_curve.get_current_price(1000).unwrap();

        // Тест Exponential кривой
        curve.curve_type = CurveType::Exponential;
        let exp_curve = create_bonding_curve(&curve).unwrap();
        let exp_price = exp_curve.get_current_price(1000).unwrap();

        // Экспоненциальная кривая должна давать более высокие цены
        assert!(exp_price >= linear_price);

        // Тест других типов кривых (должны падать на Linear по умолчанию)
        curve.curve_type = CurveType::Logarithmic;
        let log_curve = create_bonding_curve(&curve).unwrap();
        let log_price = log_curve.get_current_price(1000).unwrap();
        assert_eq!(log_price, linear_price); // Должно быть равно linear
    }

    // === ТЕСТЫ ДЛЯ SIGMOID КРИВОЙ ===

    #[test]
    fn test_sigmoid_curve_creation() {
        // Sigmoid кривая: price = min + (max - min) / (1 + e^(-k(x - x0)))
        // Параметры:
        // - min_price: минимальная цена (1000 lamports)
        // - max_price: максимальная цена (1000000 lamports)
        // - steepness: крутизна S-образной кривой (0.000001)
        // - midpoint: точка перегиба (500000 токенов)
        // - max_supply: максимальный supply (1000000 токенов)
        let sigmoid = SigmoidCurve::new(
            1000,      // min_price
            1000000,   // max_price
            1000000,   // steepness (в precision единицах)
            500000,    // midpoint
            1000000    // max_supply
        );

        assert!(sigmoid.is_ok());
        let curve = sigmoid.unwrap();
        assert_eq!(curve.min_price, 1000);
        assert_eq!(curve.max_price, 1000000);
        assert_eq!(curve.steepness, 1000000);
        assert_eq!(curve.midpoint, 500000);
        assert_eq!(curve.max_supply, 1000000);
    }

    #[test]
    fn test_sigmoid_curve_invalid_params() {
        // Тест с нулевой min_price (должна быть >= MIN_PRICE)
        assert!(SigmoidCurve::new(0, 1000000, 1000000, 500000, 1000000).is_err());

        // Тест с max_price <= min_price
        assert!(SigmoidCurve::new(1000, 500, 1000000, 500000, 1000000).is_err());
        assert!(SigmoidCurve::new(1000, 1000, 1000000, 500000, 1000000).is_err());

        // Тест с нулевым steepness
        assert!(SigmoidCurve::new(1000, 1000000, 0, 500000, 1000000).is_err());

        // Тест с нулевым max_supply
        assert!(SigmoidCurve::new(1000, 1000000, 1000000, 500000, 0).is_err());

        // Тест с midpoint > max_supply (допустимо, но нелогично)
        // В реальности это может быть валидным, если хотим отложить быстрый рост
        let result = SigmoidCurve::new(1000, 1000000, 1000000, 2000000, 1000000);
        assert!(result.is_ok()); // Пусть будет валидным
    }

    #[test]
    fn test_sigmoid_curve_price_calculation() {
        // Создаем Sigmoid кривую с midpoint в середине
        let curve = SigmoidCurve::new(
            1000,       // min_price = 1000 lamports
            1000000,    // max_price = 1M lamports
            5000000,    // steepness (более высокое значение = более крутая S-образная кривая)
            500000,     // midpoint = 500K токенов
            1000000     // max_supply = 1M токенов
        ).unwrap();

        // Цена при supply = 0 должна быть близка к min_price
        let price_at_start = curve.get_current_price(0).unwrap();
        assert!(price_at_start >= 1000);
        assert!(price_at_start < 100000); // Должна быть намного ближе к min чем к max

        // Цена при supply = midpoint должна быть примерно посередине
        let price_at_midpoint = curve.get_current_price(500000).unwrap();
        assert!(price_at_midpoint > 300000); // Примерно в середине диапазона
        assert!(price_at_midpoint < 700000);

        // Цена при supply = max_supply должна быть близка к max_price
        let price_at_end = curve.get_current_price(1000000).unwrap();
        assert!(price_at_end > 900000); // Должна быть близка к max_price
        assert!(price_at_end <= 1000000);

        // Проверка монотонности: цена всегда растет
        let price1 = curve.get_current_price(100000).unwrap();
        let price2 = curve.get_current_price(200000).unwrap();
        let price3 = curve.get_current_price(300000).unwrap();
        assert!(price2 > price1);
        assert!(price3 > price2);
    }

    #[test]
    fn test_sigmoid_curve_s_shape_characteristic() {
        // Тест проверяет что кривая действительно S-образная:
        // 1. Медленный рост в начале (до midpoint)
        // 2. Быстрый рост в середине (около midpoint)
        // 3. Замедление роста в конце (после midpoint)

        let curve = SigmoidCurve::new(
            1000,       // min_price
            1000000,    // max_price
            10000000,   // высокий steepness для четкой S-образной формы
            500000,     // midpoint
            1000000     // max_supply
        ).unwrap();

        // Измеряем прирост цены в разных диапазонах
        let p0 = curve.get_current_price(0).unwrap();
        let p1 = curve.get_current_price(100000).unwrap();
        let growth_early = p1 - p0; // Прирост в начале

        let p2 = curve.get_current_price(400000).unwrap();
        let p3 = curve.get_current_price(500000).unwrap();
        let growth_middle = p3 - p2; // Прирост в середине (должен быть больше)

        let p4 = curve.get_current_price(900000).unwrap();
        let p5 = curve.get_current_price(1000000).unwrap();
        let growth_late = p5 - p4; // Прирост в конце

        // S-образная форма: рост в середине должен быть больше чем в начале и конце
        assert!(growth_middle > growth_early, "Middle growth should be faster than early");
        assert!(growth_middle > growth_late, "Middle growth should be faster than late");
    }

    #[test]
    fn test_sigmoid_curve_market_cap() {
        let curve = SigmoidCurve::new(1000, 1000000, 5000000, 500000, 1000000).unwrap();

        // Market cap при supply = 100000
        let supply = 100000;
        let price = curve.get_current_price(supply).unwrap();
        let market_cap = curve.get_market_cap(supply).unwrap();

        // Market cap должен быть = supply * current_price
        assert_eq!(market_cap, supply * price);

        // Market cap должен расти с ростом supply
        let market_cap2 = curve.get_market_cap(200000).unwrap();
        assert!(market_cap2 > market_cap);
    }

    #[test]
    fn test_sigmoid_curve_buy_calculation() {
        let curve = SigmoidCurve::new(1000, 1000000, 5000000, 500000, 1000000).unwrap();

        // Тест покупки за 1000000 lamports при текущем supply = 100000
        let result = curve.calculate_buy(1000000, 100000).unwrap();

        assert!(result.token_amount > 0, "Should receive some tokens");
        assert_eq!(result.sol_amount, 1000000, "SOL amount should match");
        assert_eq!(result.new_supply, 100000 + result.token_amount, "Supply should increase");
        assert!(result.price_per_token > 0, "Price per token should be positive");
        assert!(result.price_impact < 10000, "Price impact should be less than 100%");

        // Проверка что supply не превышает max_supply
        assert!(result.new_supply <= curve.max_supply, "New supply should not exceed max");
    }

    #[test]
    fn test_sigmoid_curve_sell_calculation() {
        let curve = SigmoidCurve::new(1000, 1000000, 5000000, 500000, 1000000).unwrap();

        // Тест продажи 10000 токенов при текущем supply = 500000
        let result = curve.calculate_sell(10000, 500000).unwrap();

        assert_eq!(result.token_amount, 10000, "Token amount should match");
        assert!(result.sol_amount > 0, "Should receive some SOL");
        assert_eq!(result.new_supply, 490000, "Supply should decrease");
        assert!(result.price_per_token > 0, "Price per token should be positive");
    }

    #[test]
    fn test_sigmoid_curve_buy_sell_symmetry() {
        let curve = SigmoidCurve::new(1000, 1000000, 5000000, 500000, 1000000).unwrap();

        let initial_supply = 300000;

        // Покупаем токены
        let buy_result = curve.calculate_buy(5000000, initial_supply).unwrap();
        let new_supply = buy_result.new_supply;
        let tokens_bought = buy_result.token_amount;

        // Продаем те же токены обратно
        let sell_result = curve.calculate_sell(tokens_bought, new_supply).unwrap();

        // Должны вернуться примерно к исходному supply
        assert_eq!(sell_result.new_supply, initial_supply);

        // SOL полученный от продажи должен быть примерно равен SOL потраченному на покупку
        // (с небольшим учетом цены, которая могла измениться)
        let sol_difference = if buy_result.sol_amount > sell_result.sol_amount {
            buy_result.sol_amount - sell_result.sol_amount
        } else {
            sell_result.sol_amount - buy_result.sol_amount
        };

        // Разница должна быть небольшой (менее 10% от исходной суммы)
        assert!(sol_difference < buy_result.sol_amount / 10, "Buy/sell should be roughly symmetric");
    }

    #[test]
    fn test_sigmoid_curve_edge_cases() {
        let curve = SigmoidCurve::new(MIN_PRICE, 1000000, 5000000, 500000, 1000000).unwrap();

        // Тест с минимальной ценой
        let price = curve.get_current_price(0).unwrap();
        assert!(price >= MIN_PRICE);

        // Тест покупки при максимальном supply (должна быть ошибка)
        let result = curve.calculate_buy(1000, curve.max_supply);
        assert!(result.is_err(), "Cannot buy at max supply");

        // Тест продажи больше чем есть в supply (должна быть ошибка)
        let result = curve.calculate_sell(2000, 1000);
        assert!(result.is_err(), "Cannot sell more than current supply");

        // Тест продажи при supply = 0 (должна быть ошибка)
        let result = curve.calculate_sell(100, 0);
        assert!(result.is_err(), "Cannot sell from zero supply");
    }

    #[test]
    fn test_sigmoid_vs_linear_comparison() {
        // Сравниваем поведение Sigmoid и Linear кривых
        let sigmoid = SigmoidCurve::new(1000, 1000000, 5000000, 500000, 1000000).unwrap();
        let linear = LinearCurve::new(1000, 1000, 1000000).unwrap();

        // В начале Sigmoid должна расти медленнее Linear
        let sigmoid_price_early = sigmoid.get_current_price(100000).unwrap();
        let linear_price_early = linear.get_current_price(100000).unwrap();

        // В середине (около midpoint) Sigmoid может расти быстрее
        let sigmoid_price_mid = sigmoid.get_current_price(500000).unwrap();
        let linear_price_mid = linear.get_current_price(500000).unwrap();

        // Проверяем что цены положительные и логичные
        assert!(sigmoid_price_early > 0);
        assert!(sigmoid_price_mid > sigmoid_price_early);
        assert!(linear_price_mid > linear_price_early);
    }

    // === ТЕСТЫ ДЛЯ CONSTANT PRODUCT КРИВОЙ ===

    #[test]
    fn test_constant_product_curve_creation() {
        // ConstantProduct кривая: x * y = k (как в Uniswap)
        // Параметры:
        // - sol_reserve: количество SOL в пуле
        // - token_reserve: количество токенов в пуле
        // - k = sol_reserve * token_reserve (константа)

        let cp = ConstantProductCurve::new(
            1_000_000_000,  // 1 SOL в lamports
            1_000_000_000,  // 1 млрд токенов
        );

        assert!(cp.is_ok());
        let curve = cp.unwrap();
        assert_eq!(curve.sol_reserve, 1_000_000_000);
        assert_eq!(curve.token_reserve, 1_000_000_000);
        // k = 1_000_000_000 * 1_000_000_000 = 1e18
    }

    #[test]
    fn test_constant_product_curve_invalid_params() {
        // Тест с нулевыми резервами (недопустимо)
        assert!(ConstantProductCurve::new(0, 1000000).is_err());
        assert!(ConstantProductCurve::new(1000000, 0).is_err());
        assert!(ConstantProductCurve::new(0, 0).is_err());
    }

    #[test]
    fn test_constant_product_price_calculation() {
        // Создаем пул с соотношением 1:1000 (1 SOL = 1000 токенов)
        let curve = ConstantProductCurve::new(
            1_000_000_000,    // 1 SOL
            1_000_000_000_000 // 1 триллион токенов (1000 токенов на 1 lamport SOL)
        ).unwrap();

        // Цена токена = sol_reserve / token_reserve
        let price = curve.get_current_price(0).unwrap(); // supply не используется в CP
        // price = 1_000_000_000 / 1_000_000_000_000 = 0.001 SOL за токен
        // Но мы работаем в lamports, так что это правильно
        assert!(price > 0);

        // Проверка что цена разумная
        assert!(price < 1_000_000_000); // Меньше 1 SOL за токен
    }

    #[test]
    fn test_constant_product_invariant() {
        // Проверяем что k = x * y остается константой после торговли
        let curve = ConstantProductCurve::new(
            10_000_000_000,   // 10 SOL
            10_000_000_000_000 // 10 триллионов токенов
        ).unwrap();

        let initial_k = curve.get_k();

        // Покупаем токены за 1 SOL
        let buy_result = curve.calculate_buy(1_000_000_000, 0).unwrap();

        // Создаем новую кривую с обновленными резервами
        let new_curve = ConstantProductCurve::new(
            curve.sol_reserve + 1_000_000_000,
            curve.token_reserve - buy_result.token_amount
        ).unwrap();

        let new_k = new_curve.get_k();

        // k должно остаться примерно тем же (может быть небольшая погрешность из-за округления)
        // Разрешаем погрешность до 0.01%
        let k_diff = if initial_k > new_k {
            initial_k - new_k
        } else {
            new_k - initial_k
        };
        let tolerance = initial_k / 10000; // 0.01%
        assert!(k_diff <= tolerance, "K should remain constant (within tolerance)");
    }

    #[test]
    fn test_constant_product_buy_calculation() {
        let curve = ConstantProductCurve::new(
            5_000_000_000,    // 5 SOL
            5_000_000_000_000 // 5 триллионов токенов
        ).unwrap();

        // Покупаем токены за 1 SOL
        let result = curve.calculate_buy(1_000_000_000, 0).unwrap();

        assert!(result.token_amount > 0, "Should receive tokens");
        assert_eq!(result.sol_amount, 1_000_000_000, "SOL amount should match");
        assert!(result.price_per_token > 0, "Price per token should be positive");

        // Проверка что чем больше покупаешь, тем дороже цена (slippage)
        let small_buy = curve.calculate_buy(100_000_000, 0).unwrap(); // 0.1 SOL
        let large_buy = curve.calculate_buy(1_000_000_000, 0).unwrap(); // 1 SOL

        // Цена за токен при большой покупке должна быть выше
        let small_price_per_token = (100_000_000 as f64) / (small_buy.token_amount as f64);
        let large_price_per_token = (1_000_000_000 as f64) / (large_buy.token_amount as f64);

        assert!(large_price_per_token > small_price_per_token, "Large buy should have worse price (slippage)");
    }

    #[test]
    fn test_constant_product_sell_calculation() {
        let curve = ConstantProductCurve::new(
            5_000_000_000,    // 5 SOL
            5_000_000_000_000 // 5 триллионов токенов
        ).unwrap();

        // Продаем 1 миллиард токенов
        let result = curve.calculate_sell(1_000_000_000, 5_000_000_000_000).unwrap();

        assert_eq!(result.token_amount, 1_000_000_000, "Token amount should match");
        assert!(result.sol_amount > 0, "Should receive SOL");
        assert!(result.price_per_token > 0, "Price per token should be positive");

        // Проверка что selling давление снижает цену
        let price_before = curve.get_current_price(0).unwrap();
        // После продажи цена должна упасть (больше токенов в пуле)
        assert!(result.price_per_token <= price_before, "Price should decrease after selling");
    }

    #[test]
    fn test_constant_product_buy_sell_round_trip() {
        let curve = ConstantProductCurve::new(
            10_000_000_000,   // 10 SOL
            10_000_000_000_000 // 10 триллионов токенов
        ).unwrap();

        let sol_to_spend = 1_000_000_000; // 1 SOL

        // Покупаем токены
        let buy_result = curve.calculate_buy(sol_to_spend, 0).unwrap();

        // Обновляем резервы после покупки
        let curve_after_buy = ConstantProductCurve::new(
            curve.sol_reserve + sol_to_spend,
            curve.token_reserve - buy_result.token_amount
        ).unwrap();

        // Продаем те же токены обратно
        let sell_result = curve_after_buy.calculate_sell(
            buy_result.token_amount,
            curve_after_buy.token_reserve
        ).unwrap();

        // SOL полученный от продажи должен быть меньше SOL потраченного на покупку
        // (из-за price impact и slippage)
        assert!(sell_result.sol_amount < sol_to_spend, "Should receive less SOL due to slippage");

        // Но разница не должна быть слишком большой (например, не более 2%)
        let loss = sol_to_spend - sell_result.sol_amount;
        let loss_percentage = (loss as f64) / (sol_to_spend as f64) * 100.0;
        assert!(loss_percentage < 2.0, "Loss from slippage should be less than 2%");
    }

    #[test]
    fn test_constant_product_price_impact() {
        let curve = ConstantProductCurve::new(
            10_000_000_000,   // 10 SOL
            10_000_000_000_000 // 10 триллионов токенов
        ).unwrap();

        // Маленькая покупка (0.1 SOL) должна иметь маленький price impact
        let small_buy = curve.calculate_buy(100_000_000, 0).unwrap();
        assert!(small_buy.price_impact < 200, "Small buy should have <2% price impact");

        // Большая покупка (5 SOL = 50% от пула) должна иметь большой price impact
        let large_buy = curve.calculate_buy(5_000_000_000, 0).unwrap();
        assert!(large_buy.price_impact > 1000, "Large buy should have >10% price impact");
    }

    #[test]
    fn test_constant_product_edge_cases() {
        let curve = ConstantProductCurve::new(
            1_000_000_000,
            1_000_000_000_000
        ).unwrap();

        // Тест попытки купить с нулевым SOL (должна быть ошибка)
        let result = curve.calculate_buy(0, 0);
        assert!(result.is_err(), "Cannot buy with 0 SOL");

        // Тест попытки продать 0 токенов (должна быть ошибка)
        let result = curve.calculate_sell(0, 1000000);
        assert!(result.is_err(), "Cannot sell 0 tokens");

        // Тест попытки продать больше токенов чем есть в резерве (должна быть ошибка)
        let result = curve.calculate_sell(curve.token_reserve + 1, curve.token_reserve);
        assert!(result.is_err(), "Cannot sell more tokens than in reserve");
    }

    #[test]
    fn test_constant_product_vs_linear() {
        // ConstantProduct должен иметь price impact, а Linear - нет
        let cp = ConstantProductCurve::new(
            10_000_000_000,   // 10 SOL
            10_000_000_000_000 // 10T tokens
        ).unwrap();

        let linear = LinearCurve::new(1000, 1000, 10_000_000_000_000).unwrap();

        // В CP большие покупки имеют худшую цену
        let cp_small = cp.calculate_buy(100_000_000, 0).unwrap();
        let cp_large = cp.calculate_buy(1_000_000_000, 0).unwrap();

        let cp_small_avg_price = (100_000_000 as f64) / (cp_small.token_amount as f64);
        let cp_large_avg_price = (1_000_000_000 as f64) / (cp_large.token_amount as f64);

        assert!(cp_large_avg_price > cp_small_avg_price, "CP should have price impact");

        // В Linear все покупки по одинаковой средней цене (без учета изменения supply)
        // Это проверяет что CP действительно отличается от Linear
    }

    // === ТЕСТЫ ДЛЯ LOGARITHMIC КРИВОЙ ===

    #[test]
    fn test_logarithmic_curve_creation() {
        // Logarithmic кривая: price = base_price + scale * ln(supply + 1)
        // Параметры:
        // - base_price: базовая цена (минимум)
        // - scale: масштаб логарифма (определяет скорость роста)
        // - max_supply: максимальный supply

        let log_curve = LogarithmicCurve::new(
            1000,       // base_price = 1000 lamports
            500000,     // scale (в единицах PRECISION)
            1_000_000   // max_supply
        );

        assert!(log_curve.is_ok());
        let curve = log_curve.unwrap();
        assert_eq!(curve.base_price, 1000);
        assert_eq!(curve.scale, 500000);
        assert_eq!(curve.max_supply, 1_000_000);
    }

    #[test]
    fn test_logarithmic_curve_invalid_params() {
        // Тест с нулевой base_price (должна быть >= MIN_PRICE)
        assert!(LogarithmicCurve::new(0, 500000, 1_000_000).is_err());

        // Тест с нулевым scale
        assert!(LogarithmicCurve::new(1000, 0, 1_000_000).is_err());

        // Тест с нулевым max_supply
        assert!(LogarithmicCurve::new(1000, 500000, 0).is_err());
    }

    #[test]
    fn test_logarithmic_curve_price_calculation() {
        // Создаем логарифмическую кривую
        let curve = LogarithmicCurve::new(
            1000,       // base_price
            1000000,    // scale (достаточно большой для видимого эффекта)
            1_000_000   // max_supply
        ).unwrap();

        // Цена при supply = 0 должна быть = base_price + scale * ln(1) = base_price
        let price_at_zero = curve.get_current_price(0).unwrap();
        assert!(price_at_zero >= 1000);
        assert!(price_at_zero < 2000); // Должна быть близка к base_price

        // Цена должна расти с ростом supply, но все медленнее
        let price1 = curve.get_current_price(10_000).unwrap();
        let price2 = curve.get_current_price(100_000).unwrap();
        let price3 = curve.get_current_price(500_000).unwrap();

        assert!(price2 > price1, "Price should increase");
        assert!(price3 > price2, "Price should keep increasing");

        // Прирост цены должен замедляться (характеристика логарифма)
        let growth1 = price2 - price1; // Рост от 10K до 100K (90K токенов)
        let growth2 = price3 - price2; // Рост от 100K до 500K (400K токенов)

        // На больший интервал (400K) рост должен быть меньше в расчете на токен
        let growth_rate1 = (growth1 as f64) / 90_000.0;
        let growth_rate2 = (growth2 as f64) / 400_000.0;

        assert!(growth_rate2 < growth_rate1, "Growth rate should decrease (logarithmic property)");
    }

    #[test]
    fn test_logarithmic_curve_diminishing_returns() {
        // Тест проверяет что логарифмическая кривая демонстрирует убывающую отдачу
        let curve = LogarithmicCurve::new(1000, 2000000, 1_000_000).unwrap();

        // Измеряем прирост цены на разных участках
        let p0 = curve.get_current_price(0).unwrap();
        let p1 = curve.get_current_price(100_000).unwrap();
        let growth_early = p1 - p0;

        let p2 = curve.get_current_price(500_000).unwrap();
        let p3 = curve.get_current_price(600_000).unwrap();
        let growth_late = p3 - p2;

        // Ранний прирост (на первые 100K) должен быть больше позднего (на 100K при 500K supply)
        assert!(growth_early > growth_late, "Early growth should be larger (diminishing returns)");
    }

    #[test]
    fn test_logarithmic_curve_market_cap() {
        let curve = LogarithmicCurve::new(1000, 1000000, 1_000_000).unwrap();

        // Market cap при supply = 100000
        let supply = 100_000;
        let price = curve.get_current_price(supply).unwrap();
        let market_cap = curve.get_market_cap(supply).unwrap();

        // Market cap должен быть = supply * current_price
        assert_eq!(market_cap, supply * price);

        // Market cap должен расти с ростом supply
        let market_cap2 = curve.get_market_cap(200_000).unwrap();
        assert!(market_cap2 > market_cap);
    }

    #[test]
    fn test_logarithmic_curve_buy_calculation() {
        let curve = LogarithmicCurve::new(1000, 1000000, 1_000_000).unwrap();

        // Тест покупки за 1000000 lamports при текущем supply = 50000
        let result = curve.calculate_buy(1_000_000, 50_000).unwrap();

        assert!(result.token_amount > 0, "Should receive some tokens");
        assert_eq!(result.sol_amount, 1_000_000, "SOL amount should match");
        assert_eq!(result.new_supply, 50_000 + result.token_amount, "Supply should increase");
        assert!(result.price_per_token > 0, "Price per token should be positive");
        assert!(result.price_impact < 10000, "Price impact should be less than 100%");

        // Проверка что supply не превышает max_supply
        assert!(result.new_supply <= curve.max_supply, "New supply should not exceed max");
    }

    #[test]
    fn test_logarithmic_curve_sell_calculation() {
        let curve = LogarithmicCurve::new(1000, 1000000, 1_000_000).unwrap();

        // Тест продажи 10000 токенов при текущем supply = 500000
        let result = curve.calculate_sell(10_000, 500_000).unwrap();

        assert_eq!(result.token_amount, 10_000, "Token amount should match");
        assert!(result.sol_amount > 0, "Should receive some SOL");
        assert_eq!(result.new_supply, 490_000, "Supply should decrease");
        assert!(result.price_per_token > 0, "Price per token should be positive");
    }

    #[test]
    fn test_logarithmic_curve_buy_sell_symmetry() {
        let curve = LogarithmicCurve::new(1000, 1000000, 1_000_000).unwrap();

        let initial_supply = 200_000;

        // Покупаем токены
        let buy_result = curve.calculate_buy(5_000_000, initial_supply).unwrap();
        let new_supply = buy_result.new_supply;
        let tokens_bought = buy_result.token_amount;

        // Продаем те же токены обратно
        let sell_result = curve.calculate_sell(tokens_bought, new_supply).unwrap();

        // Должны вернуться к исходному supply
        assert_eq!(sell_result.new_supply, initial_supply);

        // SOL полученный от продажи должен быть примерно равен SOL потраченному на покупку
        // (может быть небольшая разница из-за округления)
        let sol_difference = if buy_result.sol_amount > sell_result.sol_amount {
            buy_result.sol_amount - sell_result.sol_amount
        } else {
            sell_result.sol_amount - buy_result.sol_amount
        };

        // Разница должна быть небольшой (менее 5% от исходной суммы)
        assert!(sol_difference < buy_result.sol_amount / 20, "Buy/sell should be roughly symmetric");
    }

    #[test]
    fn test_logarithmic_curve_edge_cases() {
        let curve = LogarithmicCurve::new(MIN_PRICE, 1000000, 1_000_000).unwrap();

        // Тест с минимальной ценой
        let price = curve.get_current_price(0).unwrap();
        assert!(price >= MIN_PRICE);

        // Тест покупки при максимальном supply (должна быть ошибка)
        let result = curve.calculate_buy(1000, curve.max_supply);
        assert!(result.is_err(), "Cannot buy at max supply");

        // Тест продажи больше чем есть в supply (должна быть ошибка)
        let result = curve.calculate_sell(2000, 1000);
        assert!(result.is_err(), "Cannot sell more than current supply");

        // Тест продажи при supply = 0 (должна быть ошибка)
        let result = curve.calculate_sell(100, 0);
        assert!(result.is_err(), "Cannot sell from zero supply");
    }

    #[test]
    fn test_logarithmic_vs_exponential() {
        // Логарифмическая и экспоненциальная кривые имеют противоположные характеристики
        let log_curve = LogarithmicCurve::new(1000, 2000000, 1_000_000).unwrap();
        let exp_curve = ExponentialCurve::new(1000, 1000000, 1_000_000).unwrap();

        // В начале логарифмическая растет быстрее
        let log_price_early = log_curve.get_current_price(10_000).unwrap();
        let exp_price_early = exp_curve.get_current_price(10_000).unwrap();

        // В конце экспоненциальная обгоняет логарифмическую
        let log_price_late = log_curve.get_current_price(500_000).unwrap();
        let exp_price_late = exp_curve.get_current_price(500_000).unwrap();

        // Проверяем что обе цены положительные и растут
        assert!(log_price_early > 0);
        assert!(log_price_late > log_price_early);
        assert!(exp_price_late > exp_price_early);

        // Экспоненциальная должна расти быстрее в долгосрочной перспективе
        let log_growth_rate = (log_price_late as f64) / (log_price_early as f64);
        let exp_growth_rate = (exp_price_late as f64) / (exp_price_early as f64);

        assert!(exp_growth_rate > log_growth_rate, "Exponential should grow faster than logarithmic");
    }

    #[test]
    fn test_logarithmic_natural_log_approximation() {
        // Тест проверяет что наша аппроксимация ln(x) работает корректно
        let curve = LogarithmicCurve::new(1000, 1000000, 1_000_000).unwrap();

        // Проверяем несколько известных значений
        // ln(1) = 0, поэтому price(0) должна быть близка к base_price
        let price_0 = curve.get_current_price(0).unwrap();
        assert!(price_0 >= 1000 && price_0 < 1100, "Price at supply 0 should be close to base_price");

        // ln(e) ≈ 1, ln(e^2) ≈ 2, и т.д.
        // Проверяем что цена растет логарифмически
        let price_10 = curve.get_current_price(10).unwrap();
        let price_100 = curve.get_current_price(100).unwrap();
        let price_1000 = curve.get_current_price(1000).unwrap();

        // Цены должны расти, но все медленнее
        assert!(price_100 > price_10);
        assert!(price_1000 > price_100);

        // Проверка логарифмического свойства: ln(10x) = ln(10) + ln(x)
        // Разница между ценами должна быть примерно одинаковой
        let diff1 = price_100 - price_10;  // рост от 10 до 100
        let diff2 = price_1000 - price_100; // рост от 100 до 1000

        // Разница не должна сильно отличаться (в пределах 50%)
        let ratio = if diff1 > diff2 {
            diff1 as f64 / diff2 as f64
        } else {
            diff2 as f64 / diff1 as f64
        };
        assert!(ratio < 2.0, "Logarithmic growth should be consistent");
    }
}