// contracts/pump-core/programs/pump-core/src/instructions/create_token.rs

use anchor_lang::prelude::*;
use anchor_spl::{
    token::{self, Mint, Token, TokenAccount, MintTo},
    metadata::{create_metadata_accounts_v3, CreateMetadataAccountsV3, Metadata},
    associated_token::AssociatedToken,
};
use crate::state::*;
use crate::errors::CustomError;

#[derive(Accounts)]
#[instruction(name: String, symbol: String)]
pub struct CreateToken<'info> {
    #[account(
        init,
        payer = creator,
        space = TokenInfo::ACCOUNT_SIZE,
        seeds = [TokenInfo::SEED_PREFIX.as_bytes(), mint.key().as_ref()],
        bump
    )]
    pub token_info: Account<'info, TokenInfo>,

    #[account(
        init,
        payer = creator,
        mint::decimals = 9,
        mint::authority = bonding_curve_vault,
        mint::freeze_authority = bonding_curve_vault,
    )]
    pub mint: Account<'info, Mint>,

    /// CHECK: This is the bonding curve vault that will hold SOL
    #[account(
        mut,
        seeds = [b"bonding_curve_vault", mint.key().as_ref()],
        bump
    )]
    pub bonding_curve_vault: AccountInfo<'info>,

    #[account(
        init,
        payer = creator,
        associated_token::mint = mint,
        associated_token::authority = bonding_curve_vault,
    )]
    pub bonding_curve_token_account: Account<'info, TokenAccount>,

    #[account(
        init_if_needed,
        payer = creator,
        space = UserProfile::ACCOUNT_SIZE,
        seeds = [UserProfile::SEED_PREFIX.as_bytes(), creator.key().as_ref()],
        bump
    )]
    pub user_profile: Account<'info, UserProfile>,

    #[account(
        mut,
        seeds = [PlatformConfig::SEED.as_bytes()],
        bump = platform_config.bump
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    #[account(mut)]
    pub creator: Signer<'info>,

    /// CHECK: Metadata account for the token
    #[account(mut)]
    pub metadata_account: AccountInfo<'info>,

    pub token_program: Program<'info, Token>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    pub token_metadata_program: Program<'info, Metadata>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

pub fn create_token(
    ctx: Context<CreateToken>,
    name: String,
    symbol: String,
    uri: String,
    bonding_curve_params: BondingCurveParams,
) -> Result<()> {
    let clock = Clock::get()?;
    
    // Validation
    require!(!ctx.accounts.platform_config.paused, CustomError::PlatformPaused);
    require!(name.len() <= 50, CustomError::NameTooLong);
    require!(symbol.len() <= 10, CustomError::SymbolTooLong);
    require!(uri.len() <= 200, CustomError::UriTooLong);
    
    // Anti-spam: Check user's last token creation time
    let user_profile = &mut ctx.accounts.user_profile;
    if user_profile.last_token_creation > 0 {
        let time_since_last = clock.unix_timestamp - user_profile.last_token_creation;
        require!(
            time_since_last >= 300, // 5 minutes minimum
            CustomError::SpamProtection
        );
    }

    // Validate bonding curve parameters
    require!(
        bonding_curve_params.initial_price > 0,
        CustomError::InvalidBondingCurveParams
    );
    require!(
        bonding_curve_params.graduation_threshold > bonding_curve_params.initial_price,
        CustomError::InvalidBondingCurveParams
    );

    // Initialize token info
    let token_info = &mut ctx.accounts.token_info;
    token_info.creator = ctx.accounts.creator.key();
    token_info.mint = ctx.accounts.mint.key();
    token_info.name = name.clone();
    token_info.symbol = symbol.clone();
    token_info.uri = uri.clone();
    token_info.bonding_curve = BondingCurve {
        curve_type: bonding_curve_params.curve_type,
        initial_price: bonding_curve_params.initial_price,
        current_price: bonding_curve_params.initial_price,
        graduation_threshold: bonding_curve_params.graduation_threshold,
        slope: bonding_curve_params.slope,
        volatility_damper: bonding_curve_params.volatility_damper.unwrap_or(1.0),
    };
    token_info.sol_reserves = 0;
    token_info.token_reserves = bonding_curve_params.initial_supply;
    token_info.total_supply = bonding_curve_params.initial_supply;
    token_info.current_market_cap = 0;
    token_info.graduated = false;
    token_info.created_at = clock.unix_timestamp;
    token_info.last_trade_at = 0;
    token_info.trade_count = 0;
    token_info.holder_count = 0;
    token_info.creator_reputation_at_creation = user_profile.reputation_score;
    token_info.bump = ctx.bumps.token_info;

    // Update user profile
    user_profile.user = ctx.accounts.creator.key();
    user_profile.tokens_created = user_profile.tokens_created.saturating_add(1);
    user_profile.last_token_creation = clock.unix_timestamp;
    
    // Increment anti-spam score (decreases over time in other functions)
    user_profile.anti_spam_score = user_profile.anti_spam_score.saturating_add(1);
    
    if user_profile.tokens_created == 1 {
        user_profile.reputation_score = 50.0; // Starting reputation
        user_profile.bump = ctx.bumps.user_profile;
    }

    // Mint initial supply to bonding curve
    let mint_to_ctx = CpiContext::new(
        ctx.accounts.token_program.to_account_info(),
        MintTo {
            mint: ctx.accounts.mint.to_account_info(),
            to: ctx.accounts.bonding_curve_token_account.to_account_info(),
            authority: ctx.accounts.bonding_curve_vault.to_account_info(),
        },
    );

    let vault_bump = ctx.bumps.bonding_curve_vault;
    let mint_key = ctx.accounts.mint.key();
    let vault_seeds = &[
        b"bonding_curve_vault",
        mint_key.as_ref(),
        &[vault_bump],
    ];
    let vault_signer = &[&vault_seeds[..]];

    token::mint_to(
        mint_to_ctx.with_signer(vault_signer),
        bonding_curve_params.initial_supply,
    )?;

    // Create metadata account
    let metadata_ctx = CpiContext::new(
        ctx.accounts.token_metadata_program.to_account_info(),
        CreateMetadataAccountsV3 {
            metadata: ctx.accounts.metadata_account.to_account_info(),
            mint: ctx.accounts.mint.to_account_info(),
            mint_authority: ctx.accounts.bonding_curve_vault.to_account_info(),
            update_authority: ctx.accounts.bonding_curve_vault.to_account_info(),
            payer: ctx.accounts.creator.to_account_info(),
            system_program: ctx.accounts.system_program.to_account_info(),
            rent: ctx.accounts.rent.to_account_info(),
        },
    );

    create_metadata_accounts_v3(
        metadata_ctx.with_signer(vault_signer),
        mpl_token_metadata::state::DataV2 {
            name: name.clone(),
            symbol: symbol.clone(),
            uri: uri.clone(),
            seller_fee_basis_points: 0,
            creators: None,
            collection: None,
            uses: None,
        },
        false, // is_mutable
        true,  // update_authority_is_signer
        None,  // collection_details
    )?;

    // Update platform stats
    ctx.accounts.platform_config.total_tokens_created = 
        ctx.accounts.platform_config.total_tokens_created.saturating_add(1);

    // Emit event
    emit!(TokenCreated {
        token: ctx.accounts.mint.key(),
        creator: ctx.accounts.creator.key(),
        name,
        symbol,
        initial_supply: bonding_curve_params.initial_supply,
        initial_price: bonding_curve_params.initial_price,
        timestamp: clock.unix_timestamp,
    });

    msg!(
        "Token created successfully: {} ({}), Initial supply: {}, Initial price: {}",
        token_info.name,
        token_info.symbol,
        token_info.total_supply,
        token_info.bonding_curve.initial_price
    );

    Ok(())
}

// Helper struct for bonding curve parameters
#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct BondingCurveParams {
    pub curve_type: CurveType,
    pub initial_supply: u64,              // Initial token supply (e.g., 1,000,000,000)
    pub initial_price: u64,               // Initial price in lamports per token
    pub graduation_threshold: u64,        // Market cap threshold for DEX listing
    pub slope: f64,                       // Price increase rate
    pub volatility_damper: Option<f64>,   // Optional volatility control
}

#[event]
pub struct TokenCreated {
    pub token: Pubkey,
    pub creator: Pubkey,
    pub name: String,
    pub symbol: String,
    pub initial_supply: u64,
    pub initial_price: u64,
    pub timestamp: i64,
}