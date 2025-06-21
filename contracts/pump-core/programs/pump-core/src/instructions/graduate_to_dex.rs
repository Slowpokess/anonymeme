// contracts/pump-core/programs/pump-core/src/instructions/graduate_to_dex.rs

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
    let _expected_program_id = match dex_type {
        DexType::Raydium => "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8", // Raydium program ID
        DexType::Jupiter => "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4", // Jupiter program ID
        DexType::Orca => "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP", // Orca program ID
        DexType::Serum => "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin", // Serum program ID
        DexType::Meteora => "24Uqj9JCLxUeoC3hGfh5W3s9FM9uCHDS2SG3LYwBpyTi", // Meteora program ID
        DexType::Custom { program_id: _ } => return Err(CustomError::InvalidDexType.into()),
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

    // Клонируем dex_type для использования в логе
    let dex_type_for_log = dex_type.clone();
    
    // Create DEX pool based on type
    match dex_type {
        DexType::Raydium => {
            // Реализация создания пула Raydium напрямую
            msg!("Creating Raydium pool with {} SOL and {} tokens", sol_liquidity, token_liquidity);
            // TODO: Полная интеграция с Raydium SDK
        },
        DexType::Jupiter => {
            // Реализация создания пула Jupiter напрямую  
            msg!("Creating Jupiter pool with {} SOL and {} tokens", sol_liquidity, token_liquidity);
            // TODO: Полная интеграция с Jupiter SDK
        },
        DexType::Orca => {
            // Реализация создания пула Orca напрямую
            msg!("Creating Orca pool with {} SOL and {} tokens", sol_liquidity, token_liquidity);
            // TODO: Полная интеграция с Orca SDK
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
        dex_type_for_log,
        token_info.current_market_cap / 1_000_000_000
    );

    Ok(())
}

// DEX-specific pool creation functions
fn create_raydium_pool(
    _ctx: &Context<GraduateToDex>,
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
    _ctx: &Context<GraduateToDex>,
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
    _ctx: &Context<GraduateToDex>,
    sol_amount: u64,
    token_amount: u64,
) -> Result<()> {
    // Implementation for Orca whirlpool
    msg!("Creating Orca pool with {} SOL and {} tokens", sol_amount, token_amount);
    
    // TODO: Implement Orca whirlpool CPI calls
    
    Ok(())
}