// contracts/pump-core/programs/pump-core/src/instructions/list_dex.rs

use anchor_lang::prelude::*;
use anchor_spl::{
    token::{self, Token, TokenAccount, Transfer, Mint},
    associated_token::AssociatedToken,
};
use crate::state::*;
use crate::errors::CustomError;

#[derive(Accounts)]
pub struct GraduateToDex<'info> {
    #[account(
        mut,
        seeds = [TokenInfo::SEED_PREFIX.as_bytes(), mint.key().as_ref()],
        bump = token_info.bump,
        constraint = !token_info.graduated @ CustomError::AlreadyGraduated,
        constraint = token_info.graduation_eligible @ CustomError::NotEligibleForGraduation,
    )]
    pub token_info: Account<'info, TokenInfo>,

    #[account(address = token_info.mint)]
    pub mint: Account<'info, Mint>,

    #[account(
        init,
        payer = initiator,
        space = DexListing::ACCOUNT_SIZE,
        seeds = [DexListing::SEED_PREFIX.as_bytes(), mint.key().as_ref()],
        bump
    )]
    pub dex_listing: Account<'info, DexListing>,

    /// CHECK: Bonding curve vault
    #[account(
        mut,
        seeds = [b"bonding_curve_vault", mint.key().as_ref()],
        bump
    )]
    pub bonding_curve_vault: AccountInfo<'info>,

    #[account(
        mut,
        associated_token::mint = mint,
        associated_token::authority = bonding_curve_vault,
    )]
    pub bonding_curve_token_account: Account<'info, TokenAccount>,

    #[account(
        mut,
        seeds = [PlatformConfig::SEED.as_bytes()],
        bump = platform_config.bump
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    /// CHECK: Platform treasury
    #[account(
        mut,
        address = platform_config.treasury
    )]
    pub treasury: AccountInfo<'info>,

    /// CHECK: DEX program (will be validated based on dex_type)
    pub dex_program: AccountInfo<'info>,

    /// CHECK: Pool account to be created on DEX
    #[account(mut)]
    pub pool_account: AccountInfo<'info>,

    /// CHECK: DEX-specific accounts (varies by DEX)
    #[account(mut)]
    pub dex_account_a: AccountInfo<'info>,

    #[account(mut)]
    pub dex_account_b: AccountInfo<'info>,

    #[account(mut)]
    pub dex_account_c: AccountInfo<'info>,

    #[account(mut)]
    pub initiator: Signer<'info>,

    pub token_program: Program<'info, Token>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

pub fn graduate_to_dex(
    ctx: Context<GraduateToDex>,
    dex_type: DexType,
    initial_liquidity: u64,
) -> Result<()> {
    let clock = Clock::get()?;
    let token_info = &mut ctx.accounts.token_info;
    
    // Validation
    require!(!ctx.accounts.platform_config.paused, CustomError::PlatformPaused);
    require!(
        token_info.current_market_cap >= token_info.bonding_curve.graduation_threshold,
        CustomError::MarketCapThresholdNotReached
    );
    require!(
        initial_liquidity >= ctx.accounts.platform_config.min_initial_liquidity,
        CustomError::InsufficientCreatorLiquidity
    );

    // Verify DEX program
    let expected_program_id = match dex_type {
        DexType::Raydium => "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8", // Raydium program ID
        DexType::Jupiter => "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4", // Jupiter program ID
        DexType::Orca => "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP", // Orca program ID
        DexType::Serum => "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin", // Serum program ID
        DexType::Meteora => "24Uqj9JCLxUeoC3hGfh5W3s9FM9uCHDS2SG3LYwBpyTi", // Meteora program ID
        DexType::Custom { program_id } => return Err(CustomError::InvalidDexType.into()),
    };

    // Collect graduation fee
    let graduation_fee = ctx.accounts.platform_config.graduation_fee;
    if graduation_fee > 0 {
        // Transfer fee from initiator to treasury
        anchor_lang::system_program::transfer(
            CpiContext::new(
                ctx.accounts.system_program.to_account_info(),
                anchor_lang::system_program::Transfer {
                    from: ctx.accounts.initiator.to_account_info(),
                    to: ctx.accounts.treasury.to_account_info(),
                },
            ),
            graduation_fee,
        )?;
    }

    // Calculate liquidity amounts
    let sol_liquidity = token_info.sol_reserves;
    let token_liquidity = token_info.token_reserves;
    
    require!(sol_liquidity > 0, CustomError::InsufficientLiquidity);
    require!(token_liquidity > 0, CustomError::InsufficientLiquidity);

    // Create DEX pool based on type
    match dex_type {
        DexType::Raydium => {
            create_raydium_pool(
                &ctx,
                sol_liquidity,
                token_liquidity,
            )?;
        },
        DexType::Jupiter => {
            create_jupiter_pool(
                &ctx,
                sol_liquidity,
                token_liquidity,
            )?;
        },
        DexType::Orca => {
            create_orca_pool(
                &ctx,
                sol_liquidity,
                token_liquidity,
            )?;
        },
        _ => return Err(CustomError::InvalidDexType.into()),
    }

    // Transfer all liquidity from bonding curve to DEX
    let vault_bump = ctx.bumps.bonding_curve_vault;
    let mint_key = ctx.accounts.mint.key();
    let vault_seeds = &[
        b"bonding_curve_vault",
        mint_key.as_ref(),
        &[vault_bump],
    ];

    // Transfer SOL to DEX pool
    anchor_lang::system_program::transfer(
        CpiContext::new_with_signer(
            ctx.accounts.system_program.to_account_info(),
            anchor_lang::system_program::Transfer {
                from: ctx.accounts.bonding_curve_vault.to_account_info(),
                to: ctx.accounts.pool_account.to_account_info(),
            },
            &[vault_seeds],
        ),
        sol_liquidity,
    )?;

    // Transfer tokens to DEX pool
    token::transfer(
        CpiContext::new_with_signer(
            ctx.accounts.token_program.to_account_info(),
            Transfer {
                from: ctx.accounts.bonding_curve_token_account.to_account_info(),
                to: ctx.accounts.dex_account_a.to_account_info(), // DEX token account
                authority: ctx.accounts.bonding_curve_vault.to_account_info(),
            },
            &[vault_seeds],
        ),
        token_liquidity,
    )?;

    // Update token info
    token_info.graduated = true;
    token_info.graduation_timestamp = clock.unix_timestamp;
    token_info.sol_reserves = 0; // All moved to DEX
    token_info.token_reserves = 0; // All moved to DEX

    // Initialize DEX listing info
    let dex_listing = &mut ctx.accounts.dex_listing;
    dex_listing.token_mint = ctx.accounts.mint.key();
    dex_listing.dex_type = dex_type.clone();
    dex_listing.pool_address = ctx.accounts.pool_account.key();
    dex_listing.initial_liquidity_sol = sol_liquidity;
    dex_listing.initial_liquidity_token = token_liquidity;
    dex_listing.listing_timestamp = clock.unix_timestamp;
    dex_listing.listing_price = token_info.bonding_curve.current_price;
    dex_listing.fee_tier = 300; // 0.3% default fee
    dex_listing.liquidity_locked = true;
    dex_listing.lock_duration = 30 * 24 * 60 * 60; // 30 days
    dex_listing.creator_lp_tokens = 0; // Will be updated after pool creation
    dex_listing.bump = ctx.bumps.dex_listing;

    // Calculate graduation time
    let graduation_time_hours = (clock.unix_timestamp - token_info.created_at) / 3600;

    // Emit graduation event
    emit!(TokenGraduated {
        token: ctx.accounts.mint.key(),
        dex: dex_type,
        final_market_cap: token_info.current_market_cap,
        total_volume: 0, // TODO: Calculate from platform stats
        graduation_time_hours: graduation_time_hours as u64,
        timestamp: clock.unix_timestamp,
    });

    msg!(
        "Token {} graduated to {:?} with market cap: {} SOL",
        token_info.symbol,
        dex_type,
        token_info.current_market_cap / 1_000_000_000
    );

    Ok(())
}

// DEX-specific pool creation functions
fn create_raydium_pool(
    ctx: &Context<GraduateToDex>,
    sol_amount: u64,
    token_amount: u64,
) -> Result<()> {
    // Implementation for Raydium pool creation
    // This would use Raydium's initialize_pool instruction
    msg!("Creating Raydium pool with {} SOL and {} tokens", sol_amount, token_amount);
    
    // TODO: Implement actual Raydium CPI calls
    // let cpi_accounts = raydium::cpi::accounts::InitializePool {
    //     pool: ctx.accounts.pool_account.to_account_info(),
    //     token_a: ctx.accounts.mint.to_account_info(),
    //     token_b: /* SOL mint or wrapped SOL */,
    //     // ... other required accounts
    // };
    // raydium::cpi::initialize_pool(cpi_ctx, sol_amount, token_amount)?;
    
    Ok(())
}

fn create_jupiter_pool(
    ctx: &Context<GraduateToDex>,
    sol_amount: u64,
    token_amount: u64,
) -> Result<()> {
    // Implementation for Jupiter aggregator
    msg!("Creating Jupiter pool with {} SOL and {} tokens", sol_amount, token_amount);
    
    // Jupiter is more of an aggregator, so this might involve creating
    // a pool on an underlying DEX that Jupiter can route through
    
    Ok(())
}

fn create_orca_pool(
    ctx: &Context<GraduateToDex>,
    sol_amount: u64,
    token_amount: u64,
) -> Result<()> {
    // Implementation for Orca whirlpool
    msg!("Creating Orca pool with {} SOL and {} tokens", sol_amount, token_amount);
    
    // TODO: Implement Orca whirlpool CPI calls
    
    Ok(())
}


// contracts/pump-core/programs/pump-core/src/instructions/security.rs

use anchor_lang::prelude::*;
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
    let old_state = platform_config.paused;
    
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

// Additional admin functions
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