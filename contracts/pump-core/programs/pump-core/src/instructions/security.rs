// contracts/pump-core/programs/pump-core/src/instructions/security.rs

use anchor_lang::prelude::*;
use anchor_spl::token::Mint;
use crate::state::*;
use crate::errors::CustomError;

#[derive(Accounts)]
pub struct UpdateSecurity<'info> {
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

pub fn update_security_params(
    ctx: Context<UpdateSecurity>,
    new_params: SecurityParams,
) -> Result<()> {
    // Validate new security parameters
    require!(new_params.max_trade_size > 0, CustomError::InvalidSecurityParams);
    require!(new_params.whale_tax_rate <= 0.5, CustomError::InvalidSecurityParams); // Max 50%
    require!(new_params.early_sell_tax <= 0.3, CustomError::InvalidSecurityParams); // Max 30%
    require!(new_params.min_hold_time <= 86400, CustomError::InvalidSecurityParams); // Max 24 hours
    require!(new_params.circuit_breaker_threshold > 0.0 && new_params.circuit_breaker_threshold <= 1.0, CustomError::InvalidSecurityParams);

    let platform_config = &mut ctx.accounts.platform_config;
    let old_params = platform_config.security_params.clone();
    
    platform_config.security_params = new_params.clone();

    emit!(EmergencyAction {
        admin: ctx.accounts.admin.key(),
        action: "SecurityParamsUpdated".to_string(),
        target: platform_config.key(),
        reason: "Admin updated security parameters".to_string(),
        timestamp: Clock::get()?.unix_timestamp,
    });

    msg!("Security parameters updated by admin: {}", ctx.accounts.admin.key());
    msg!("Old max trade size: {}, New: {}", old_params.max_trade_size, new_params.max_trade_size);
    msg!("Old whale tax: {}%, New: {}%", old_params.whale_tax_rate * 100.0, new_params.whale_tax_rate * 100.0);

    Ok(())
}

#[derive(Accounts)]
pub struct EmergencyControl<'info> {
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

pub fn toggle_emergency_pause(
    ctx: Context<EmergencyControl>,
    pause: bool,
) -> Result<()> {
    let platform_config = &mut ctx.accounts.platform_config;
    let _old_state = platform_config.paused;
    
    platform_config.paused = pause;

    let action = if pause { "EmergencyPause" } else { "EmergencyUnpause" };
    let reason = if pause { 
        "Platform paused for security reasons" 
    } else { 
        "Platform unpaused - normal operations resumed" 
    };

    emit!(EmergencyAction {
        admin: ctx.accounts.admin.key(),
        action: action.to_string(),
        target: platform_config.key(),
        reason: reason.to_string(),
        timestamp: Clock::get()?.unix_timestamp,
    });

    msg!("Platform {} by admin: {}", 
         if pause { "PAUSED" } else { "UNPAUSED" }, 
         ctx.accounts.admin.key());

    Ok(())
}

#[derive(Accounts)]
pub struct UpdateUserReputation<'info> {
    #[account(
        mut,
        seeds = [UserProfile::SEED_PREFIX.as_bytes(), user.key().as_ref()],
        bump = user_profile.bump
    )]
    pub user_profile: Account<'info, UserProfile>,

    /// CHECK: The user whose reputation is being updated
    pub user: AccountInfo<'info>,

    #[account(
        seeds = [PlatformConfig::SEED.as_bytes()],
        bump = platform_config.bump,
        constraint = platform_config.admin == admin.key() @ CustomError::AdminOnly
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    #[account(mut)]
    pub admin: Signer<'info>,
}

pub fn update_user_reputation(
    ctx: Context<UpdateUserReputation>,
    reputation_delta: i32,
) -> Result<()> {
    let user_profile = &mut ctx.accounts.user_profile;
    let old_reputation = user_profile.reputation_score;

    // Apply reputation change
    if reputation_delta > 0 {
        user_profile.reputation_score = (user_profile.reputation_score + reputation_delta as f64).min(100.0);
    } else {
        user_profile.reputation_score = (user_profile.reputation_score + reputation_delta as f64).max(0.0);
    }

    // Check if user should be banned due to low reputation
    if user_profile.reputation_score < 10.0 && !user_profile.banned {
        user_profile.banned = true;
        user_profile.ban_reason = "Reputation too low".to_string();
    }

    msg!("User {} reputation updated: {} -> {} (delta: {})",
         ctx.accounts.user.key(),
         old_reputation,
         user_profile.reputation_score,
         reputation_delta);

    Ok(())
}

#[derive(Accounts)]
pub struct ReportActivity<'info> {
    #[account(
        init,
        payer = reporter,
        space = SuspiciousActivityReport::ACCOUNT_SIZE,
        seeds = [
            SuspiciousActivityReport::SEED_PREFIX.as_bytes(),
            reported_user.key().as_ref(),
            reporter.key().as_ref(),
            &Clock::get()?.unix_timestamp.to_le_bytes()
        ],
        bump
    )]
    pub report: Account<'info, SuspiciousActivityReport>,

    /// CHECK: User being reported
    pub reported_user: AccountInfo<'info>,

    #[account(mut)]
    pub reporter: Signer<'info>,

    #[account(
        seeds = [PlatformConfig::SEED.as_bytes()],
        bump = platform_config.bump
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

pub fn report_suspicious_activity(
    ctx: Context<ReportActivity>,
    reported_user: Pubkey,
    reason: ReportReason,
    description: String,
) -> Result<()> {
    require!(description.len() <= 500, CustomError::DescriptionTooLong);
    require!(ctx.accounts.reporter.key() != reported_user, CustomError::SelfReferralNotAllowed);

    let clock = Clock::get()?;
    let report = &mut ctx.accounts.report;

    report.reporter = ctx.accounts.reporter.key();
    report.reported_user = reported_user;
    report.reason = reason.clone();
    report.description = description.clone();
    report.evidence_uri = String::new(); // Can be added later
    report.created_at = clock.unix_timestamp;
    report.reviewed = false;
    report.reviewer = Pubkey::default();
    report.action_taken = String::new();
    report.bump = ctx.bumps.report;

    // Auto-flag if multiple reports
    // TODO: Implement logic to count existing reports for this user

    emit!(SuspiciousActivityDetected {
        user: reported_user,
        activity_type: format!("{:?}", reason),
        risk_score: calculate_risk_score(&reason),
        auto_flagged: false,
        timestamp: clock.unix_timestamp,
    });

    msg!("Suspicious activity reported: {} reported {} for {:?}",
         ctx.accounts.reporter.key(),
         reported_user,
         reason);

    Ok(())
}

// Helper function to calculate risk score based on report reason
fn calculate_risk_score(reason: &ReportReason) -> f64 {
    match reason {
        ReportReason::RugPull => 95.0,
        ReportReason::Scam => 90.0,
        ReportReason::MarketManipulation => 85.0,
        ReportReason::FakeMetadata => 70.0,
        ReportReason::Impersonation => 75.0,
        ReportReason::Spam => 40.0,
        ReportReason::Other => 50.0,
    }
}

#[derive(Accounts)]
pub struct ViewTokenInfo<'info> {
    #[account(
        seeds = [TokenInfo::SEED_PREFIX.as_bytes(), mint.key().as_ref()],
        bump = token_info.bump
    )]
    pub token_info: Account<'info, TokenInfo>,

    pub mint: Account<'info, Mint>,
}

pub fn get_token_price(ctx: Context<ViewTokenInfo>) -> Result<u64> {
    let token_info = &ctx.accounts.token_info;
    Ok(token_info.bonding_curve.current_price)
}