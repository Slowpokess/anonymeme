// contracts/pump-core/programs/pump-core/src/utils/bonding_curve.rs

use anchor_lang::prelude::*;
use crate::state::{BondingCurve, CurveType};
use crate::errors::CustomError;

/// Calculate the amount of tokens to receive when buying with SOL
pub fn calculate_buy_amount(
    curve: &BondingCurve,
    current_sol_reserves: u64,
    current_token_reserves: u64,
    sol_amount: u64,
) -> Result<u64> {
    require!(sol_amount > 0, CustomError::InvalidAmount);
    require!(current_token_reserves > 0, CustomError::InsufficientLiquidity);

    match curve.curve_type {
        CurveType::Linear => {
            calculate_linear_buy(curve, current_sol_reserves, current_token_reserves, sol_amount)
        },
        CurveType::Exponential => {
            calculate_exponential_buy(curve, current_sol_reserves, current_token_reserves, sol_amount)
        },
        CurveType::Logarithmic => {
            calculate_logarithmic_buy(curve, current_sol_reserves, current_token_reserves, sol_amount)
        },
        CurveType::Sigmoid => {
            calculate_sigmoid_buy(curve, current_sol_reserves, current_token_reserves, sol_amount)
        },
        CurveType::ConstantProduct => {
            calculate_constant_product_buy(current_sol_reserves, current_token_reserves, sol_amount)
        },
    }
}

/// Calculate the amount of SOL to receive when selling tokens
pub fn calculate_sell_amount(
    curve: &BondingCurve,
    current_sol_reserves: u64,
    current_token_reserves: u64,
    token_amount: u64,
) -> Result<u64> {
    require!(token_amount > 0, CustomError::InvalidAmount);
    require!(current_sol_reserves > 0, CustomError::InsufficientLiquidity);

    match curve.curve_type {
        CurveType::Linear => {
            calculate_linear_sell(curve, current_sol_reserves, current_token_reserves, token_amount)
        },
        CurveType::Exponential => {
            calculate_exponential_sell(curve, current_sol_reserves, current_token_reserves, token_amount)
        },
        CurveType::Logarithmic => {
            calculate_logarithmic_sell(curve, current_sol_reserves, current_token_reserves, token_amount)
        },
        CurveType::Sigmoid => {
            calculate_sigmoid_sell(curve, current_sol_reserves, current_token_reserves, token_amount)
        },
        CurveType::ConstantProduct => {
            calculate_constant_product_sell(current_sol_reserves, current_token_reserves, token_amount)
        },
    }
}

/// Calculate current token price based on reserves
pub fn calculate_current_price(
    curve: &BondingCurve,
    current_sol_reserves: u64,
    current_token_reserves: u64,
) -> Result<u64> {
    if current_token_reserves == 0 {
        return Ok(curve.graduation_threshold);
    }

    match curve.curve_type {
        CurveType::Linear => {
            calculate_linear_price(curve, current_sol_reserves, current_token_reserves)
        },
        CurveType::Exponential => {
            calculate_exponential_price(curve, current_sol_reserves, current_token_reserves)
        },
        CurveType::Logarithmic => {
            calculate_logarithmic_price(curve, current_sol_reserves, current_token_reserves)
        },
        CurveType::Sigmoid => {
            calculate_sigmoid_price(curve, current_sol_reserves, current_token_reserves)
        },
        CurveType::ConstantProduct => {
            // For constant product: price = sol_reserves / token_reserves
            if current_token_reserves > 0 {
                Ok((current_sol_reserves * 1_000_000_000) / current_token_reserves) // Price in lamports per token
            } else {
                Ok(curve.initial_price)
            }
        },
    }
}

/// Calculate market capitalization
pub fn calculate_market_cap(
    curve: &BondingCurve,
    current_sol_reserves: u64,
    current_token_reserves: u64,
    total_supply: u64,
) -> Result<u64> {
    let current_price = calculate_current_price(curve, current_sol_reserves, current_token_reserves)?;
    
    // Market cap = current_price * circulating_supply
    let circulating_supply = total_supply.saturating_sub(current_token_reserves);
    let market_cap = (current_price as u128)
        .saturating_mul(circulating_supply as u128) / 1_000_000_000; // Adjust for decimals
    
    Ok(market_cap.min(u64::MAX as u128) as u64)
}

// === LINEAR BONDING CURVE ===
// Price increases linearly: price = initial_price + (slope * tokens_sold)

fn calculate_linear_buy(
    curve: &BondingCurve,
    current_sol_reserves: u64,
    current_token_reserves: u64,
    sol_amount: u64,
) -> Result<u64> {
    let current_price = curve.initial_price + 
        (curve.slope * (curve.initial_supply - current_token_reserves) as f64) as u64;
    
    // For linear curve: tokens = sol_amount / average_price
    // Average price between current and new price
    let tokens_to_buy = (sol_amount as f64 / (current_price as f64 + curve.slope / 2.0)) as u64;
    
    // Apply volatility damper
    let damped_tokens = (tokens_to_buy as f64 / curve.volatility_damper) as u64;
    
    Ok(damped_tokens.min(current_token_reserves))
}

fn calculate_linear_sell(
    curve: &BondingCurve,
    current_sol_reserves: u64,
    current_token_reserves: u64,
    token_amount: u64,
) -> Result<u64> {
    let current_price = curve.initial_price + 
        (curve.slope * (curve.initial_supply - current_token_reserves) as f64) as u64;
    
    // For selling, price decreases
    let average_price = current_price.saturating_sub((curve.slope * token_amount as f64 / 2.0) as u64);
    let sol_to_receive = (token_amount as f64 * average_price as f64 * curve.volatility_damper) as u64;
    
    Ok(sol_to_receive.min(current_sol_reserves))
}

fn calculate_linear_price(
    curve: &BondingCurve,
    _current_sol_reserves: u64,
    current_token_reserves: u64,
) -> Result<u64> {
    let tokens_sold = curve.initial_supply.saturating_sub(current_token_reserves);
    let price = curve.initial_price + (curve.slope * tokens_sold as f64) as u64;
    Ok(price)
}

// === EXPONENTIAL BONDING CURVE ===
// Price increases exponentially: price = initial_price * e^(slope * tokens_sold)

fn calculate_exponential_buy(
    curve: &BondingCurve,
    _current_sol_reserves: u64,
    current_token_reserves: u64,
    sol_amount: u64,
) -> Result<u64> {
    let tokens_sold = curve.initial_supply.saturating_sub(current_token_reserves);
    let current_price = curve.initial_price as f64 * 
        (curve.slope * tokens_sold as f64 / 1_000_000.0).exp(); // Scale down for numerical stability
    
    // Estimate tokens to buy using numerical integration approximation
    let estimated_tokens = (sol_amount as f64 / (current_price * 1.1)) as u64; // Conservative estimate
    let damped_tokens = (estimated_tokens as f64 / curve.volatility_damper) as u64;
    
    Ok(damped_tokens.min(current_token_reserves))
}

fn calculate_exponential_sell(
    curve: &BondingCurve,
    _current_sol_reserves: u64,
    current_token_reserves: u64,
    token_amount: u64,
) -> Result<u64> {
    let tokens_sold = curve.initial_supply.saturating_sub(current_token_reserves);
    let current_price = curve.initial_price as f64 * 
        (curve.slope * tokens_sold as f64 / 1_000_000.0).exp();
    
    // Conservative sell price (slightly lower than current)
    let sell_price = current_price * 0.95 * curve.volatility_damper;
    let sol_to_receive = (token_amount as f64 * sell_price) as u64;
    
    Ok(sol_to_receive)
}

fn calculate_exponential_price(
    curve: &BondingCurve,
    _current_sol_reserves: u64,
    current_token_reserves: u64,
) -> Result<u64> {
    let tokens_sold = curve.initial_supply.saturating_sub(current_token_reserves);
    let price = curve.initial_price as f64 * 
        (curve.slope * tokens_sold as f64 / 1_000_000.0).exp();
    
    Ok((price as u64).min(curve.graduation_threshold))
}

// === LOGARITHMIC BONDING CURVE ===
// Price increases logarithmically: price = initial_price + slope * ln(1 + tokens_sold)

fn calculate_logarithmic_buy(
    curve: &BondingCurve,
    _current_sol_reserves: u64,
    current_token_reserves: u64,
    sol_amount: u64,
) -> Result<u64> {
    let tokens_sold = curve.initial_supply.saturating_sub(current_token_reserves);
    let current_price = curve.initial_price as f64 + 
        curve.slope * (1.0 + tokens_sold as f64).ln();
    
    // Estimate tokens using average price method
    let estimated_tokens = (sol_amount as f64 / current_price) as u64;
    let damped_tokens = (estimated_tokens as f64 / curve.volatility_damper) as u64;
    
    Ok(damped_tokens.min(current_token_reserves))
}

fn calculate_logarithmic_sell(
    curve: &BondingCurve,
    _current_sol_reserves: u64,
    current_token_reserves: u64,
    token_amount: u64,
) -> Result<u64> {
    let tokens_sold = curve.initial_supply.saturating_sub(current_token_reserves);
    let current_price = curve.initial_price as f64 + 
        curve.slope * (1.0 + tokens_sold as f64).ln();
    
    let sell_price = current_price * 0.98 * curve.volatility_damper; // Small discount for selling
    let sol_to_receive = (token_amount as f64 * sell_price) as u64;
    
    Ok(sol_to_receive)
}

fn calculate_logarithmic_price(
    curve: &BondingCurve,
    _current_sol_reserves: u64,
    current_token_reserves: u64,
) -> Result<u64> {
    let tokens_sold = curve.initial_supply.saturating_sub(current_token_reserves);
    let price = curve.initial_price as f64 + 
        curve.slope * (1.0 + tokens_sold as f64).ln();
    
    Ok((price as u64).min(curve.graduation_threshold))
}

// === SIGMOID BONDING CURVE ===
// S-shaped curve: price = initial_price + (graduation_threshold - initial_price) / (1 + e^(-slope * progress))

fn calculate_sigmoid_buy(
    curve: &BondingCurve,
    _current_sol_reserves: u64,
    current_token_reserves: u64,
    sol_amount: u64,
) -> Result<u64> {
    let progress = (curve.initial_supply.saturating_sub(current_token_reserves)) as f64 / curve.initial_supply as f64;
    let price_range = curve.graduation_threshold.saturating_sub(curve.initial_price) as f64;
    let sigmoid_factor = 1.0 / (1.0 + (-curve.slope * (progress - 0.5)).exp());
    let current_price = curve.initial_price as f64 + price_range * sigmoid_factor;
    
    let estimated_tokens = (sol_amount as f64 / current_price) as u64;
    let damped_tokens = (estimated_tokens as f64 / curve.volatility_damper) as u64;
    
    Ok(damped_tokens.min(current_token_reserves))
}

fn calculate_sigmoid_sell(
    curve: &BondingCurve,
    _current_sol_reserves: u64,
    current_token_reserves: u64,
    token_amount: u64,
) -> Result<u64> {
    let progress = (curve.initial_supply.saturating_sub(current_token_reserves)) as f64 / curve.initial_supply as f64;
    let price_range = curve.graduation_threshold.saturating_sub(curve.initial_price) as f64;
    let sigmoid_factor = 1.0 / (1.0 + (-curve.slope * (progress - 0.5)).exp());
    let current_price = curve.initial_price as f64 + price_range * sigmoid_factor;
    
    let sell_price = current_price * 0.97 * curve.volatility_damper; // Slightly lower for selling
    let sol_to_receive = (token_amount as f64 * sell_price) as u64;
    
    Ok(sol_to_receive)
}

fn calculate_sigmoid_price(
    curve: &BondingCurve,
    _current_sol_reserves: u64,
    current_token_reserves: u64,
) -> Result<u64> {
    let progress = (curve.initial_supply.saturating_sub(current_token_reserves)) as f64 / curve.initial_supply as f64;
    let price_range = curve.graduation_threshold.saturating_sub(curve.initial_price) as f64;
    let sigmoid_factor = 1.0 / (1.0 + (-curve.slope * (progress - 0.5)).exp());
    let price = curve.initial_price as f64 + price_range * sigmoid_factor;
    
    Ok((price as u64).min(curve.graduation_threshold))
}

// === CONSTANT PRODUCT BONDING CURVE ===
// AMM-style: x * y = k (where x = SOL, y = tokens)

fn calculate_constant_product_buy(
    current_sol_reserves: u64,
    current_token_reserves: u64,
    sol_amount: u64,
) -> Result<u64> {
    require!(current_sol_reserves > 0 && current_token_reserves > 0, CustomError::InsufficientLiquidity);
    
    let k = (current_sol_reserves as u128) * (current_token_reserves as u128);
    let new_sol_reserves = current_sol_reserves + sol_amount;
    let new_token_reserves = k / (new_sol_reserves as u128);
    
    let tokens_to_receive = current_token_reserves.saturating_sub(new_token_reserves as u64);
    
    Ok(tokens_to_receive)
}

fn calculate_constant_product_sell(
    current_sol_reserves: u64,
    current_token_reserves: u64,
    token_amount: u64,
) -> Result<u64> {
    require!(current_sol_reserves > 0 && current_token_reserves > 0, CustomError::InsufficientLiquidity);
    
    let k = (current_sol_reserves as u128) * (current_token_reserves as u128);
    let new_token_reserves = current_token_reserves + token_amount;
    let new_sol_reserves = k / (new_token_reserves as u128);
    
    let sol_to_receive = current_sol_reserves.saturating_sub(new_sol_reserves as u64);
    
    Ok(sol_to_receive)
}

/// Calculate progress towards graduation (0.0 to 1.0)
pub fn calculate_graduation_progress(
    curve: &BondingCurve,
    current_market_cap: u64,
) -> f64 {
    if curve.graduation_threshold == 0 {
        return 0.0;
    }
    
    let progress = current_market_cap as f64 / curve.graduation_threshold as f64;
    progress.min(1.0)
}

/// Validate bonding curve parameters
pub fn validate_bonding_curve_params(
    curve_type: &CurveType,
    initial_price: u64,
    graduation_threshold: u64,
    slope: f64,
    initial_supply: u64,
) -> Result<()> {
    require!(initial_price > 0, CustomError::InvalidBondingCurveParams);
    require!(graduation_threshold > initial_price, CustomError::InvalidBondingCurveParams);
    require!(initial_supply > 0, CustomError::InvalidBondingCurveParams);
    
    match curve_type {
        CurveType::Linear => {
            require!(slope > 0.0, CustomError::InvalidBondingCurveParams);
            require!(slope < 1000.0, CustomError::InvalidBondingCurveParams); // Reasonable upper bound
        },
        CurveType::Exponential => {
            require!(slope > 0.0 && slope < 0.001, CustomError::InvalidBondingCurveParams); // Small values for stability
        },
        CurveType::Logarithmic => {
            require!(slope > 0.0 && slope < 10000.0, CustomError::InvalidBondingCurveParams);
        },
        CurveType::Sigmoid => {
            require!(slope > 0.0 && slope < 100.0, CustomError::InvalidBondingCurveParams);
        },
        CurveType::ConstantProduct => {
            // No additional validation needed
        },
    }
    
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_linear_curve_calculations() {
        let curve = BondingCurve {
            curve_type: CurveType::Linear,
            initial_price: 1000,
            current_price: 1000,
            graduation_threshold: 100000,
            slope: 0.1,
            volatility_damper: 1.0,
            initial_supply: 1000000000,
        };

        let sol_reserves = 0;
        let token_reserves = 1000000000;
        let sol_amount = 10000;

        let tokens = calculate_buy_amount(&curve, sol_reserves, token_reserves, sol_amount).unwrap();
        assert!(tokens > 0);
        assert!(tokens <= token_reserves);
    }

    #[test]
    fn test_constant_product_curve() {
        let sol_reserves = 100000000; // 0.1 SOL
        let token_reserves = 1000000000; // 1000 tokens
        let sol_amount = 10000000; // 0.01 SOL

        let tokens = calculate_constant_product_buy(sol_reserves, token_reserves, sol_amount).unwrap();
        assert!(tokens > 0);
        assert!(tokens < token_reserves);
    }
}