// contracts/pump-core/programs/pump-core/src/instructions/admin.rs

use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::CustomError;

#[derive(Accounts)]
pub struct UpdatePlatformConfig<'info> {
    #[account(
        mut,
        seeds = [PlatformConfig::SEED.as_bytes()],
        bump = platform_config.bump,
        constraint = platform_config.admin == admin.key() @ CustomError::AdminOnly
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    #[account(mut)]
    pub admin: Signer<'info>,
}

pub fn update_platform_fee(
    ctx: Context<UpdatePlatformConfig>,
    new_fee_rate: f64,
) -> Result<()> {
    require!(new_fee_rate >= 0.0 && new_fee_rate <= 10.0, CustomError::InvalidFee);

    let platform_config = &mut ctx.accounts.platform_config;
    let old_fee = platform_config.fee_rate;
    
    platform_config.fee_rate = new_fee_rate;

    emit!(EmergencyAction {
        admin: ctx.accounts.admin.key(),
        action: "FeeRateUpdated".to_string(),
        target: platform_config.key(),
        reason: format!("Fee rate changed from {}% to {}%", old_fee, new_fee_rate),
        timestamp: Clock::get()?.unix_timestamp,
    });

    msg!("Platform fee updated from {}% to {}%", old_fee, new_fee_rate);

    Ok(())
}

pub fn update_treasury(
    ctx: Context<UpdatePlatformConfig>,
    new_treasury: Pubkey,
) -> Result<()> {
    let platform_config = &mut ctx.accounts.platform_config;
    let old_treasury = platform_config.treasury;
    
    platform_config.treasury = new_treasury;

    emit!(EmergencyAction {
        admin: ctx.accounts.admin.key(),
        action: "TreasuryUpdated".to_string(),
        target: new_treasury,
        reason: format!("Treasury changed from {} to {}", old_treasury, new_treasury),
        timestamp: Clock::get()?.unix_timestamp,
    });

    msg!("Treasury updated from {} to {}", old_treasury, new_treasury);

    Ok(())
}

#[derive(Accounts)]
pub struct TransferAdmin<'info> {
    #[account(
        mut,
        seeds = [PlatformConfig::SEED.as_bytes()],
        bump = platform_config.bump,
        constraint = platform_config.admin == current_admin.key() @ CustomError::AdminOnly
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    #[account(mut)]
    pub current_admin: Signer<'info>,

    /// CHECK: New admin public key
    pub new_admin: AccountInfo<'info>,
}

pub fn transfer_admin(ctx: Context<TransferAdmin>) -> Result<()> {
    let platform_config = &mut ctx.accounts.platform_config;
    let old_admin = platform_config.admin;
    let new_admin = ctx.accounts.new_admin.key();

    require!(old_admin != new_admin, CustomError::InvalidAccount);

    platform_config.admin = new_admin;

    emit!(EmergencyAction {
        admin: old_admin,
        action: "AdminTransferred".to_string(),
        target: new_admin,
        reason: format!("Admin transferred from {} to {}", old_admin, new_admin),
        timestamp: Clock::get()?.unix_timestamp,
    });

    msg!("Admin transferred from {} to {}", old_admin, new_admin);

    Ok(())
}