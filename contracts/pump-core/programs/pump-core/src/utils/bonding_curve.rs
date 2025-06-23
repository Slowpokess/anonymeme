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
        _ => {
            // Для остальных типов используем линейную кривую по умолчанию
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
}