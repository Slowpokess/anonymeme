// contracts/pump-core/programs/pump-core/src/instructions/create_token.rs

use anchor_lang::prelude::*;
use anchor_lang::system_program;
use anchor_spl::{
    token::{self, Mint, Token, TokenAccount, MintTo},
    associated_token::AssociatedToken,
};
use mpl_token_metadata::{
    ID as TokenMetadataProgramID,
    state::DataV2,
    instruction::create_metadata_accounts_v3,
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

    /// Bonding curve vault that will hold SOL - properly validated PDA
    #[account(
        mut,
        seeds = [b"bonding_curve_vault", mint.key().as_ref()],
        bump,
        constraint = bonding_curve_vault.owner == &system_program::ID @ CustomError::InvalidAccount
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
    /// CHECK: Token Metadata Program
    #[account(constraint = token_metadata_program.key() == TokenMetadataProgramID)]
    pub token_metadata_program: AccountInfo<'info>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}



pub fn create_token(
    ctx: Context<CreateToken>,
    name: String,
    symbol: String,
    uri: String,
    bonding_curve_params: crate::state::BondingCurveParams,
) -> Result<()> {
    let clock = Clock::get()?;
    
    // Быстрая валидация с ранним выходом
    require!(!ctx.accounts.platform_config.paused, CustomError::PlatformPaused);
    require!(name.len() <= 50, CustomError::NameTooLong);
    require!(symbol.len() <= 10, CustomError::SymbolTooLong);
    require!(uri.len() <= 200, CustomError::UriTooLong);
    
    // Anti-spam: Check user's last token creation time
    let user_profile = &mut ctx.accounts.user_profile;
    let security_params = &ctx.accounts.platform_config.security_params;
    
    if user_profile.last_token_creation > 0 {
        let time_since_last = clock.unix_timestamp - user_profile.last_token_creation;
        require!(
            time_since_last >= security_params.creation_cooldown.max(300), // Minimum 5 minutes
            CustomError::SpamProtection
        );
    }
    
    // Check maximum tokens per creator
    require!(
        user_profile.tokens_created < security_params.max_tokens_per_creator,
        CustomError::TooManyTokensCreated
    );
    
    // Check minimum reputation requirement
    require!(
        user_profile.reputation_score >= security_params.min_reputation_to_create,
        CustomError::InsufficientReputation
    );

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
        curve_type: bonding_curve_params.curve_type.clone(),
        initial_price: bonding_curve_params.initial_price,
        current_price: bonding_curve_params.initial_price,
        graduation_threshold: bonding_curve_params.graduation_threshold,
        slope: bonding_curve_params.slope,
        volatility_damper: bonding_curve_params.volatility_damper.unwrap_or(1.0),
        initial_supply: bonding_curve_params.initial_supply,
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

    // Создаем metadata аккаунт через CPI в mpl-token-metadata v1.13.2
    let metadata_accounts = vec![
        ctx.accounts.metadata_account.to_account_info(),
        ctx.accounts.mint.to_account_info(),
        ctx.accounts.bonding_curve_vault.to_account_info(), // mint_authority
        ctx.accounts.creator.to_account_info(), // payer
        ctx.accounts.bonding_curve_vault.to_account_info(), // update_authority
        ctx.accounts.system_program.to_account_info(),
        ctx.accounts.rent.to_account_info(),
    ];

    let metadata_data = DataV2 {
        name: name.clone(),
        symbol: symbol.clone(),
        uri: uri.clone(),
        seller_fee_basis_points: 0,
        creators: None,
        collection: None,
        uses: None,
    };

    // Создаем CPI инструкцию для metadata с правильными аргументами для v1.13.2
    let create_metadata_ix = create_metadata_accounts_v3(
        ctx.accounts.token_metadata_program.key(),  // program_id
        ctx.accounts.metadata_account.key(),        // metadata_account
        ctx.accounts.mint.key(),                    // mint
        ctx.accounts.bonding_curve_vault.key(),     // mint_authority
        ctx.accounts.creator.key(),                 // payer
        ctx.accounts.bonding_curve_vault.key(),     // update_authority
        metadata_data.name,                         // name
        metadata_data.symbol,                       // symbol  
        metadata_data.uri,                          // uri
        metadata_data.creators,                     // creators
        metadata_data.seller_fee_basis_points,      // seller_fee_basis_points
        true,                                       // update_authority_is_signer
        false,                                      // is_mutable
        metadata_data.collection,                   // collection
        metadata_data.uses,                         // uses
        None,                                       // collection_details
    );

    // Выполняем CPI вызов для создания metadata
    anchor_lang::solana_program::program::invoke_signed(
        &create_metadata_ix,
        &metadata_accounts,
        &[&vault_seeds[..]],
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
        curve_type: bonding_curve_params.curve_type,
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