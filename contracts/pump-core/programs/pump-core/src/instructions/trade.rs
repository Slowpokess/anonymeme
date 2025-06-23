/*!
💱 Торговые инструкции для бондинг-кривых
Production-ready покупка и продажа токенов с полной защитой
*/

use anchor_lang::prelude::*;
use anchor_lang::system_program;
use anchor_spl::{
    token::{self, Token, TokenAccount, Transfer, Mint},
    associated_token::AssociatedToken,
};

use crate::state::*;
use crate::errors::ErrorCode;
use crate::utils::bonding_curve::{calculate_buy_tokens, calculate_sell_tokens, CurveCalculation};

/// Контексты для покупки токенов
#[derive(Accounts)]
pub struct BuyTokens<'info> {
    /// Информация о токене
    #[account(
        mut,
        seeds = [TokenInfo::SEED.as_bytes(), mint.key().as_ref()],
        bump = token_info.bump,
        constraint = token_info.is_tradeable @ ErrorCode::TradingDisabled,
        constraint = !token_info.is_graduated @ ErrorCode::TokenGraduated,
        constraint = !token_info.is_frozen @ ErrorCode::TokenFrozen,
    )]
    pub token_info: Account<'info, TokenInfo>,

    /// Mint токена
    #[account(address = token_info.mint)]
    pub mint: Account<'info, Mint>,

    /// Хранилище SOL бондинг-кривой
    #[account(
        mut,
        seeds = [b"bonding_curve_vault", mint.key().as_ref()],
        bump = token_info.vault_bump,
    )]
    /// CHECK: Проверяется как PDA
    pub bonding_curve_vault: AccountInfo<'info>,

    /// Токен-аккаунт бондинг-кривой (содержит токены для продажи)
    #[account(
        mut,
        associated_token::mint = mint,
        associated_token::authority = bonding_curve_vault,
    )]
    pub bonding_curve_token_account: Account<'info, TokenAccount>,

    /// Токен-аккаунт покупателя
    #[account(
        init_if_needed,
        payer = buyer,
        associated_token::mint = mint,
        associated_token::authority = buyer,
    )]
    pub buyer_token_account: Account<'info, TokenAccount>,

    /// Профиль пользователя
    #[account(
        init_if_needed,
        payer = buyer,
        space = UserProfile::ACCOUNT_SIZE,
        seeds = [UserProfile::SEED.as_bytes(), buyer.key().as_ref()],
        bump,
    )]
    pub user_profile: Account<'info, UserProfile>,

    /// Покупатель
    #[account(mut)]
    pub buyer: Signer<'info>,

    /// Казначейство для комиссий
    #[account(
        mut,
        address = platform_config.treasury
    )]
    /// CHECK: Проверяется через address constraint
    pub treasury: AccountInfo<'info>,

    /// Глобальная конфигурация платформы
    #[account(
        mut,
        seeds = [PlatformConfig::SEED.as_bytes()],
        bump = platform_config.bump,
        constraint = !platform_config.emergency_paused @ ErrorCode::PlatformPaused,
        constraint = !platform_config.trading_paused @ ErrorCode::TradingPaused,
        constraint = !platform_config.reentrancy_guard @ ErrorCode::ReentrancyError,
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    /// Программы
    pub system_program: Program<'info, System>,
    pub token_program: Program<'info, Token>,
    pub associated_token_program: Program<'info, AssociatedToken>,
}

/// Контексты для продажи токенов
#[derive(Accounts)]
pub struct SellTokens<'info> {
    /// Информация о токене
    #[account(
        mut,
        seeds = [TokenInfo::SEED.as_bytes(), mint.key().as_ref()],
        bump = token_info.bump,
        constraint = token_info.is_tradeable @ ErrorCode::TradingDisabled,
        constraint = !token_info.is_graduated @ ErrorCode::TokenGraduated,
        constraint = !token_info.is_frozen @ ErrorCode::TokenFrozen,
    )]
    pub token_info: Account<'info, TokenInfo>,

    /// Mint токена
    #[account(address = token_info.mint)]
    pub mint: Account<'info, Mint>,

    /// Хранилище SOL бондинг-кривой
    #[account(
        mut,
        seeds = [b"bonding_curve_vault", mint.key().as_ref()],
        bump = token_info.vault_bump,
    )]
    /// CHECK: Проверяется как PDA
    pub bonding_curve_vault: AccountInfo<'info>,

    /// Токен-аккаунт бондинг-кривой (принимает токены)
    #[account(
        mut,
        associated_token::mint = mint,
        associated_token::authority = bonding_curve_vault,
    )]
    pub bonding_curve_token_account: Account<'info, TokenAccount>,

    /// Токен-аккаунт продавца
    #[account(
        mut,
        associated_token::mint = mint,
        associated_token::authority = seller,
        constraint = seller_token_account.amount > 0 @ ErrorCode::InsufficientBalance,
    )]
    pub seller_token_account: Account<'info, TokenAccount>,

    /// Профиль пользователя
    #[account(
        init_if_needed,
        payer = seller,
        space = UserProfile::ACCOUNT_SIZE,
        seeds = [UserProfile::SEED.as_bytes(), seller.key().as_ref()],
        bump,
    )]
    pub user_profile: Account<'info, UserProfile>,

    /// Продавец
    #[account(mut)]
    pub seller: Signer<'info>,

    /// Казначейство для комиссий
    #[account(
        mut,
        address = platform_config.treasury
    )]
    /// CHECK: Проверяется через address constraint
    pub treasury: AccountInfo<'info>,

    /// Глобальная конфигурация платформы
    #[account(
        mut,
        seeds = [PlatformConfig::SEED.as_bytes()],
        bump = platform_config.bump,
        constraint = !platform_config.emergency_paused @ ErrorCode::PlatformPaused,
        constraint = !platform_config.trading_paused @ ErrorCode::TradingPaused,
        constraint = !platform_config.reentrancy_guard @ ErrorCode::ReentrancyError,
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    /// Программы
    pub system_program: Program<'info, System>,
    pub token_program: Program<'info, Token>,
    pub associated_token_program: Program<'info, AssociatedToken>,
}

/// Покупка токенов за SOL
pub fn buy_tokens(
    ctx: Context<BuyTokens>,
    sol_amount: u64,
    min_tokens_out: u64,
    slippage_tolerance: u16, // В базисных пунктах (100 = 1%)
) -> Result<()> {
    msg!("💰 Покупка токенов за {} SOL", sol_amount as f64 / 1_000_000_000.0);

    let clock = Clock::get()?;
    let platform_config = &mut ctx.accounts.platform_config;
    let token_info = &mut ctx.accounts.token_info;
    let user_profile = &mut ctx.accounts.user_profile;

    // === ЗАЩИТА ОТ РЕЕНТРАНТНОСТИ ===
    platform_config.reentrancy_guard = true;

    // === ВАЛИДАЦИЯ ПАРАМЕТРОВ ===
    validate_buy_params(sol_amount, slippage_tolerance, platform_config)?;

    // === ПРОВЕРКА RATE LIMITING ===
    check_rate_limiting(user_profile, &clock, platform_config)?;

    // === РАСЧЕТ ПО БОНДИНГ-КРИВОЙ ===
    let current_supply = token_info.current_supply;
    let calculation = calculate_buy_tokens(
        &token_info.bonding_curve,
        sol_amount,
        current_supply,
    )?;

    // === ПРОВЕРКА SLIPPAGE ===
    require!(
        calculation.token_amount >= min_tokens_out,
        ErrorCode::SlippageExceeded
    );

    require!(
        calculation.price_impact <= slippage_tolerance,
        ErrorCode::SlippageExceeded
    );

    // === ПРОВЕРКА ЛИКВИДНОСТИ ===
    require!(
        ctx.accounts.bonding_curve_token_account.amount >= calculation.token_amount,
        ErrorCode::InsufficientLiquidity
    );

    // === РАСЧЕТ КОМИССИЙ ===
    let platform_fee = calculate_platform_fee(sol_amount, platform_config.fee_rate)?;
    let whale_tax = calculate_whale_tax(
        sol_amount,
        user_profile,
        &platform_config.security_params,
    )?;
    let total_fees = platform_fee.checked_add(whale_tax)
        .ok_or(ErrorCode::MathOverflow)?;

    let net_sol_amount = sol_amount.checked_sub(total_fees)
        .ok_or(ErrorCode::InsufficientFunds)?;

    // === ВЫПОЛНЕНИЕ ТОРГОВЛИ ===

    // 1. Перевод SOL от покупателя в хранилище
    let sol_transfer_ctx = CpiContext::new(
        ctx.accounts.system_program.to_account_info(),
        system_program::Transfer {
            from: ctx.accounts.buyer.to_account_info(),
            to: ctx.accounts.bonding_curve_vault.to_account_info(),
        },
    );
    system_program::transfer(sol_transfer_ctx, net_sol_amount)?;

    // 2. Перевод комиссий в казначейство
    if total_fees > 0 {
        let fee_transfer_ctx = CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            system_program::Transfer {
                from: ctx.accounts.buyer.to_account_info(),
                to: ctx.accounts.treasury.to_account_info(),
            },
        );
        system_program::transfer(fee_transfer_ctx, total_fees)?;
    }

    // 3. Перевод токенов покупателю
    let vault_seeds = &[
        b"bonding_curve_vault",
        ctx.accounts.mint.key().as_ref(),
        &[token_info.vault_bump],
    ];
    let vault_signer = &[&vault_seeds[..]];

    let token_transfer_ctx = CpiContext::new_with_signer(
        ctx.accounts.token_program.to_account_info(),
        Transfer {
            from: ctx.accounts.bonding_curve_token_account.to_account_info(),
            to: ctx.accounts.buyer_token_account.to_account_info(),
            authority: ctx.accounts.bonding_curve_vault.to_account_info(),
        },
        vault_signer,
    );
    token::transfer(token_transfer_ctx, calculation.token_amount)?;

    // === ОБНОВЛЕНИЕ СОСТОЯНИЯ ===
    update_token_info_after_buy(token_info, &calculation, sol_amount, &clock)?;
    update_user_profile_after_trade(user_profile, sol_amount, calculation.token_amount, true, &clock)?;
    update_platform_stats_after_trade(platform_config, sol_amount, total_fees, &clock)?;

    // === ПРОВЕРКА НА ВЫПУСК ===
    check_graduation_criteria(token_info, platform_config)?;

    // === СОБЫТИЯ ===
    emit!(TokenTradeEvent {
        mint: ctx.accounts.mint.key(),
        trader: ctx.accounts.buyer.key(),
        trade_type: TradeType::Buy,
        sol_amount,
        token_amount: calculation.token_amount,
        price_per_token: calculation.price_per_token,
        price_impact: calculation.price_impact,
        platform_fee,
        whale_tax,
        timestamp: clock.unix_timestamp,
    });

    // === СНЯТИЕ ЗАЩИТЫ ОТ РЕЕНТРАНТНОСТИ ===
    platform_config.reentrancy_guard = false;

    msg!("✅ Покупка завершена: {} токенов за {} SOL", 
         calculation.token_amount, 
         sol_amount as f64 / 1_000_000_000.0);

    Ok(())
}

/// Продажа токенов за SOL
pub fn sell_tokens(
    ctx: Context<SellTokens>,
    token_amount: u64,
    min_sol_out: u64,
    slippage_tolerance: u16,
) -> Result<()> {
    msg!("💸 Продажа {} токенов", token_amount);

    let clock = Clock::get()?;
    let platform_config = &mut ctx.accounts.platform_config;
    let token_info = &mut ctx.accounts.token_info;
    let user_profile = &mut ctx.accounts.user_profile;

    // === ЗАЩИТА ОТ РЕЕНТРАНТНОСТИ ===
    platform_config.reentrancy_guard = true;

    // === ВАЛИДАЦИЯ ПАРАМЕТРОВ ===
    validate_sell_params(token_amount, slippage_tolerance, platform_config)?;

    // === ПРОВЕРКА RATE LIMITING ===
    check_rate_limiting(user_profile, &clock, platform_config)?;

    // === ПРОВЕРКА БАЛАНСА ===
    require!(
        ctx.accounts.seller_token_account.amount >= token_amount,
        ErrorCode::InsufficientBalance
    );

    // === РАСЧЕТ ПО БОНДИНГ-КРИВОЙ ===
    let current_supply = token_info.current_supply;
    let calculation = calculate_sell_tokens(
        &token_info.bonding_curve,
        token_amount,
        current_supply,
    )?;

    // === ПРОВЕРКА SLIPPAGE ===
    require!(
        calculation.sol_amount >= min_sol_out,
        ErrorCode::SlippageExceeded
    );

    require!(
        calculation.price_impact <= slippage_tolerance,
        ErrorCode::SlippageExceeded
    );

    // === ПРОВЕРКА ЛИКВИДНОСТИ SOL ===
    require!(
        ctx.accounts.bonding_curve_vault.lamports() >= calculation.sol_amount,
        ErrorCode::InsufficientLiquidity
    );

    // === РАСЧЕТ КОМИССИЙ ===
    let platform_fee = calculate_platform_fee(calculation.sol_amount, platform_config.fee_rate)?;
    let whale_tax = calculate_whale_tax(
        calculation.sol_amount,
        user_profile,
        &platform_config.security_params,
    )?;
    let total_fees = platform_fee.checked_add(whale_tax)
        .ok_or(ErrorCode::MathOverflow)?;

    let net_sol_amount = calculation.sol_amount.checked_sub(total_fees)
        .ok_or(ErrorCode::InsufficientFunds)?;

    // === ВЫПОЛНЕНИЕ ТОРГОВЛИ ===

    // 1. Перевод токенов от продавца в хранилище
    let token_transfer_ctx = CpiContext::new(
        ctx.accounts.token_program.to_account_info(),
        Transfer {
            from: ctx.accounts.seller_token_account.to_account_info(),
            to: ctx.accounts.bonding_curve_token_account.to_account_info(),
            authority: ctx.accounts.seller.to_account_info(),
        },
    );
    token::transfer(token_transfer_ctx, token_amount)?;

    // 2. Перевод SOL продавцу (за вычетом комиссий)
    **ctx.accounts.bonding_curve_vault.to_account_info().try_borrow_mut_lamports()? -= net_sol_amount;
    **ctx.accounts.seller.to_account_info().try_borrow_mut_lamports()? += net_sol_amount;

    // 3. Перевод комиссий в казначейство
    if total_fees > 0 {
        **ctx.accounts.bonding_curve_vault.to_account_info().try_borrow_mut_lamports()? -= total_fees;
        **ctx.accounts.treasury.to_account_info().try_borrow_mut_lamports()? += total_fees;
    }

    // === ОБНОВЛЕНИЕ СОСТОЯНИЯ ===
    update_token_info_after_sell(token_info, &calculation, calculation.sol_amount, &clock)?;
    update_user_profile_after_trade(user_profile, calculation.sol_amount, token_amount, false, &clock)?;
    update_platform_stats_after_trade(platform_config, calculation.sol_amount, total_fees, &clock)?;

    // === СОБЫТИЯ ===
    emit!(TokenTradeEvent {
        mint: ctx.accounts.mint.key(),
        trader: ctx.accounts.seller.key(),
        trade_type: TradeType::Sell,
        sol_amount: calculation.sol_amount,
        token_amount,
        price_per_token: calculation.price_per_token,
        price_impact: calculation.price_impact,
        platform_fee,
        whale_tax,
        timestamp: clock.unix_timestamp,
    });

    // === СНЯТИЕ ЗАЩИТЫ ОТ РЕЕНТРАНТНОСТИ ===
    platform_config.reentrancy_guard = false;

    msg!("✅ Продажа завершена: {} SOL за {} токенов", 
         net_sol_amount as f64 / 1_000_000_000.0, 
         token_amount);

    Ok(())
}

// === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

/// Валидация параметров покупки
fn validate_buy_params(
    sol_amount: u64,
    slippage_tolerance: u16,
    platform_config: &PlatformConfig,
) -> Result<()> {
    require!(sol_amount > 0, ErrorCode::InvalidAmount);
    require!(
        sol_amount <= platform_config.security_params.max_trade_size_sol,
        ErrorCode::MaxTradeSizeExceeded
    );
    require!(
        slippage_tolerance <= platform_config.security_params.max_slippage_bps,
        ErrorCode::InvalidSlippageTolerance
    );
    Ok(())
}

/// Валидация параметров продажи
fn validate_sell_params(
    token_amount: u64,
    slippage_tolerance: u16,
    platform_config: &PlatformConfig,
) -> Result<()> {
    require!(token_amount > 0, ErrorCode::InvalidAmount);
    require!(
        slippage_tolerance <= platform_config.security_params.max_slippage_bps,
        ErrorCode::InvalidSlippageTolerance
    );
    Ok(())
}

/// Проверка rate limiting
fn check_rate_limiting(
    user_profile: &UserProfile,
    clock: &Clock,
    platform_config: &PlatformConfig,
) -> Result<()> {
    let time_since_last_trade = clock.unix_timestamp - user_profile.last_trade_timestamp;
    let cooldown_period = platform_config.security_params.cooldown_period_seconds as i64;
    
    require!(
        time_since_last_trade >= cooldown_period,
        ErrorCode::TradeCooldownActive
    );

    // Проверка лимита сделок в минуту
    let trades_in_last_minute = user_profile.trades_last_minute;
    require!(
        trades_in_last_minute < platform_config.security_params.rate_limit_per_minute,
        ErrorCode::RateLimitExceeded
    );

    Ok(())
}

/// Расчет комиссии платформы
fn calculate_platform_fee(amount: u64, fee_rate: u16) -> Result<u64> {
    let fee = (amount as u128)
        .checked_mul(fee_rate as u128)
        .and_then(|x| x.checked_div(10000)) // fee_rate в базисных пунктах
        .ok_or(ErrorCode::MathOverflow)? as u64;
    Ok(fee)
}

/// Расчет налога на китов
fn calculate_whale_tax(
    amount: u64,
    user_profile: &UserProfile,
    security_params: &SecurityParams,
) -> Result<u64> {
    // Определяем, является ли пользователь китом
    let is_whale = amount >= security_params.whale_threshold_sol ||
                   user_profile.total_volume_sol >= security_params.whale_threshold_sol;

    if is_whale {
        let tax = (amount as u128)
            .checked_mul(security_params.whale_tax_bps as u128)
            .and_then(|x| x.checked_div(10000))
            .ok_or(ErrorCode::MathOverflow)? as u64;
        Ok(tax)
    } else {
        Ok(0)
    }
}

/// Обновление информации о токене после покупки
fn update_token_info_after_buy(
    token_info: &mut TokenInfo,
    calculation: &CurveCalculation,
    sol_amount: u64,
    clock: &Clock,
) -> Result<()> {
    token_info.current_supply = calculation.new_supply;
    token_info.circulating_supply = token_info.circulating_supply
        .checked_add(calculation.token_amount)
        .ok_or(ErrorCode::MathOverflow)?;
    token_info.total_volume_sol = token_info.total_volume_sol
        .checked_add(sol_amount)
        .ok_or(ErrorCode::MathOverflow)?;
    token_info.total_trades = token_info.total_trades
        .checked_add(1)
        .ok_or(ErrorCode::MathOverflow)?;
    token_info.last_trade_at = clock.unix_timestamp;
    Ok(())
}

/// Обновление информации о токене после продажи
fn update_token_info_after_sell(
    token_info: &mut TokenInfo,
    calculation: &CurveCalculation,
    sol_amount: u64,
    clock: &Clock,
) -> Result<()> {
    token_info.current_supply = calculation.new_supply;
    token_info.circulating_supply = token_info.circulating_supply
        .checked_sub(calculation.token_amount)
        .ok_or(ErrorCode::MathOverflow)?;
    token_info.total_volume_sol = token_info.total_volume_sol
        .checked_add(sol_amount)
        .ok_or(ErrorCode::MathOverflow)?;
    token_info.total_trades = token_info.total_trades
        .checked_add(1)
        .ok_or(ErrorCode::MathOverflow)?;
    token_info.last_trade_at = clock.unix_timestamp;
    Ok(())
}

/// Обновление профиля пользователя после торговли
fn update_user_profile_after_trade(
    user_profile: &mut UserProfile,
    sol_amount: u64,
    token_amount: u64,
    is_buy: bool,
    clock: &Clock,
) -> Result<()> {
    user_profile.total_volume_sol = user_profile.total_volume_sol
        .checked_add(sol_amount)
        .ok_or(ErrorCode::MathOverflow)?;
    
    if is_buy {
        user_profile.total_tokens_bought = user_profile.total_tokens_bought
            .checked_add(token_amount)
            .ok_or(ErrorCode::MathOverflow)?;
    } else {
        user_profile.total_tokens_sold = user_profile.total_tokens_sold
            .checked_add(token_amount)
            .ok_or(ErrorCode::MathOverflow)?;
    }

    user_profile.total_trades = user_profile.total_trades
        .checked_add(1)
        .ok_or(ErrorCode::MathOverflow)?;
    
    user_profile.last_trade_timestamp = clock.unix_timestamp;

    // Обновление rate limiting счетчика
    let minute_ago = clock.unix_timestamp - 60;
    if user_profile.last_trade_timestamp > minute_ago {
        user_profile.trades_last_minute = user_profile.trades_last_minute
            .checked_add(1)
            .ok_or(ErrorCode::MathOverflow)?;
    } else {
        user_profile.trades_last_minute = 1;
    }

    Ok(())
}

/// Обновление статистики платформы
fn update_platform_stats_after_trade(
    platform_config: &mut PlatformConfig,
    sol_amount: u64,
    fees: u64,
    clock: &Clock,
) -> Result<()> {
    platform_config.total_volume_sol = platform_config.total_volume_sol
        .checked_add(sol_amount)
        .ok_or(ErrorCode::MathOverflow)?;
    
    platform_config.total_fees_collected = platform_config.total_fees_collected
        .checked_add(fees)
        .ok_or(ErrorCode::MathOverflow)?;
    
    platform_config.total_trades = platform_config.total_trades
        .checked_add(1)
        .ok_or(ErrorCode::MathOverflow)?;
    
    platform_config.last_updated = clock.unix_timestamp;
    
    Ok(())
}

/// Проверка критериев для выпуска на DEX
fn check_graduation_criteria(
    token_info: &mut TokenInfo,
    platform_config: &PlatformConfig,
) -> Result<()> {
    // Проверяем, достигли ли критериев для выпуска
    let market_cap = token_info.current_supply
        .checked_mul(token_info.bonding_curve.initial_price)
        .ok_or(ErrorCode::MathOverflow)?;

    let graduation_threshold = platform_config.graduation_fee
        .checked_mul(1000) // Например, 1000 SOL market cap
        .ok_or(ErrorCode::MathOverflow)?;

    if market_cap >= graduation_threshold {
        msg!("🎓 Токен готов к выпуску на DEX!");
        // Здесь можно добавить логику автоматического выпуска
        // или просто уведомление
    }

    Ok(())
}

/// Событие торговли
#[event]
pub struct TokenTradeEvent {
    /// Mint токена
    pub mint: Pubkey,
    /// Трейдер
    pub trader: Pubkey,
    /// Тип сделки
    pub trade_type: TradeType,
    /// Количество SOL
    pub sol_amount: u64,
    /// Количество токенов
    pub token_amount: u64,
    /// Цена за токен
    pub price_per_token: u64,
    /// Влияние на цену
    pub price_impact: u16,
    /// Комиссия платформы
    pub platform_fee: u64,
    /// Налог на китов
    pub whale_tax: u64,
    /// Время сделки
    pub timestamp: i64,
}

/// Тип торговой операции
#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum TradeType {
    Buy,
    Sell,
}