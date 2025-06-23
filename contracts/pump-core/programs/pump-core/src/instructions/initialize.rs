/*!
🚀 Инициализация платформы Anonymeme
Production-ready инструкция для первичной настройки смарт-контракта
*/

use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::ErrorCode;

/// Контексты для инициализации платформы
#[derive(Accounts)]
pub struct InitializePlatform<'info> {
    /// Глобальная конфигурация платформы (PDA)
    #[account(
        init,
        payer = admin,
        space = PlatformConfig::ACCOUNT_SIZE,
        seeds = [PlatformConfig::SEED.as_bytes()],
        bump
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    /// Администратор платформы (подписывает транзакцию)
    #[account(mut)]
    pub admin: Signer<'info>,

    /// Казначейство для сбора комиссий
    /// CHECK: Проверяется в логике инструкции
    pub treasury: AccountInfo<'info>,

    /// Системная программа Solana
    pub system_program: Program<'info, System>,
    
    /// Sysvar для проверки аренды
    pub rent: Sysvar<'info, Rent>,
}

/// Инициализация платформы с полной валидацией и безопасностью
pub fn initialize_platform(
    ctx: Context<InitializePlatform>,
    fee_rate: u16, // В базисных пунктах (10000 = 100%)
    treasury: Pubkey,
    security_params: SecurityParams,
) -> Result<()> {
    msg!("🚀 Инициализация платформы Anonymeme...");

    // === ВАЛИДАЦИЯ ВХОДНЫХ ПАРАМЕТРОВ ===
    
    // Проверка fee_rate (максимум 10% = 1000 базисных пунктов)
    require!(fee_rate <= 1000, ErrorCode::InvalidFeeRate);
    
    // Проверка treasury (не должен быть нулевым)
    require!(treasury != Pubkey::default(), ErrorCode::InvalidTreasury);
    require!(treasury != ctx.accounts.admin.key(), ErrorCode::TreasurySameAsAdmin);
    
    // Валидация параметров безопасности
    validate_security_params(&security_params)?;
    
    // Проверка rent exemption
    let rent = &ctx.accounts.rent;
    let platform_config_lamports = ctx.accounts.platform_config.to_account_info().lamports();
    require!(
        rent.is_exempt(platform_config_lamports, PlatformConfig::ACCOUNT_SIZE),
        ErrorCode::InsufficientRentExemption
    );

    // === ИНИЦИАЛИЗАЦИЯ ПЛАТФОРМЫ ===
    
    let platform_config = &mut ctx.accounts.platform_config;
    let clock = Clock::get()?;

    // Основные параметры
    platform_config.admin = ctx.accounts.admin.key();
    platform_config.treasury = treasury;
    platform_config.fee_rate = fee_rate;
    platform_config.emergency_paused = false;
    platform_config.trading_paused = false;
    platform_config.bump = ctx.bumps.platform_config;

    // Статистика платформы
    platform_config.total_tokens_created = 0;
    platform_config.total_volume_sol = 0;
    platform_config.total_fees_collected = 0;
    platform_config.total_trades = 0;

    // Параметры токенов
    platform_config.graduation_fee = 1_000_000_000; // 1 SOL
    platform_config.min_initial_liquidity = 100_000_000; // 0.1 SOL
    platform_config.max_initial_supply = 1_000_000_000_000; // 1T токенов
    platform_config.min_token_name_length = 3;
    platform_config.max_token_name_length = 32;

    // Системная информация
    platform_config.initialized_at = clock.unix_timestamp;
    platform_config.last_updated = clock.unix_timestamp;
    platform_config.platform_version = 1;

    // Безопасность
    platform_config.security_params = security_params;
    platform_config.emergency_contacts = [Pubkey::default(); 3];
    
    // Reentrancy protection
    platform_config.reentrancy_guard = false;

    // === СОБЫТИЯ ===
    
    emit!(PlatformInitializedEvent {
        admin: ctx.accounts.admin.key(),
        treasury,
        fee_rate,
        timestamp: clock.unix_timestamp,
        platform_version: 1,
    });

    msg!("✅ Платформа инициализирована успешно!");
    msg!("   Администратор: {}", ctx.accounts.admin.key());
    msg!("   Казначейство: {}", treasury);
    msg!("   Комиссия платформы: {}%", fee_rate as f64 / 100.0);
    msg!("   Время инициализации: {}", clock.unix_timestamp);

    Ok(())
}

/// Валидация параметров безопасности
fn validate_security_params(params: &SecurityParams) -> Result<()> {
    // Максимальный размер сделки (не более 1000 SOL)
    require!(
        params.max_trade_size_sol > 0 && params.max_trade_size_sol <= 1000_000_000_000,
        ErrorCode::InvalidMaxTradeSize
    );

    // Максимальный slippage (не более 50% = 5000 базисных пунктов)
    require!(
        params.max_slippage_bps <= 5000,
        ErrorCode::InvalidMaxSlippage
    );

    // Налог на китов (не более 20% = 2000 базисных пунктов)
    require!(
        params.whale_tax_bps <= 2000,
        ErrorCode::InvalidWhaleTax
    );

    // Пороги для определения китов
    require!(
        params.whale_threshold_sol > 0 && params.whale_threshold_sol <= 100_000_000_000,
        ErrorCode::InvalidWhaleThreshold
    );

    // Rate limiting (минимум 1 сделка в секунду, максимум 1000)
    require!(
        params.rate_limit_per_minute >= 1 && params.rate_limit_per_minute <= 1000,
        ErrorCode::InvalidRateLimit
    );

    // Cooldown период (максимум 1 час = 3600 секунд)
    require!(
        params.cooldown_period_seconds <= 3600,
        ErrorCode::InvalidCooldownPeriod
    );

    Ok(())
}

/// Событие инициализации платформы
#[event]
pub struct PlatformInitializedEvent {
    /// Администратор платформы
    pub admin: Pubkey,
    /// Адрес казначейства
    pub treasury: Pubkey,
    /// Комиссия в базисных пунктах
    pub fee_rate: u16,
    /// Время инициализации
    pub timestamp: i64,
    /// Версия платформы
    pub platform_version: u8,
}