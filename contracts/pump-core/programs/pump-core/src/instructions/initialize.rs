// contracts/pump-core/programs/pump-core/src/instructions/initialize.rs

use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::CustomError;

#[derive(Accounts)]
pub struct InitializePlatform<'info> {
    #[account(
        init,
        payer = admin,
        space = PlatformConfig::ACCOUNT_SIZE,
        seeds = [PlatformConfig::SEED.as_bytes()],
        bump
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    #[account(mut)]
    pub admin: Signer<'info>,

    /// CHECK: Treasury account for collecting fees
    pub treasury: AccountInfo<'info>,

    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

pub fn initialize_platform(
    ctx: Context<InitializePlatform>,
    fee_rate: f64,
    treasury: Pubkey,
    security_params: SecurityParams,
) -> Result<()> {
    // Валидация параметров
    require!(fee_rate >= 0.0 && fee_rate <= 10.0, CustomError::InvalidFee);
    require!(security_params.max_trade_size > 0, CustomError::InvalidSecurityParams);
    require!(security_params.whale_tax_rate <= 0.5, CustomError::InvalidSecurityParams);

    let platform_config = &mut ctx.accounts.platform_config;
    let _clock = Clock::get()?;

    // Инициализация конфигурации платформы
    platform_config.admin = ctx.accounts.admin.key();
    platform_config.treasury = treasury;
    platform_config.fee_rate = fee_rate;
    platform_config.paused = false;
    platform_config.total_tokens_created = 0;
    platform_config.total_volume = 0;
    platform_config.total_fees_collected = 0;
    platform_config.graduation_fee = 1_000_000_000; // 1 SOL
    platform_config.min_initial_liquidity = 100_000_000; // 0.1 SOL
    platform_config.platform_version = 1;
    platform_config.emergency_contacts = [Pubkey::default(); 3];
    platform_config.security_params = security_params;
    platform_config.trading_locked = false; // Initialize reentrancy protection
    platform_config.bump = ctx.bumps.platform_config;

    msg!("Platform initialized successfully!");
    msg!("Admin: {}", ctx.accounts.admin.key());
    msg!("Treasury: {}", treasury);
    msg!("Fee rate: {}%", fee_rate);

    Ok(())
}