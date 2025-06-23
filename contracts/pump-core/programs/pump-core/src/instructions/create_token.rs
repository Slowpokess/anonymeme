/*!
🏭 Создание токенов с бондинг-кривыми
Production-ready инструкция для создания мемекоинов с автоматическим ценообразованием
*/

use anchor_lang::prelude::*;
use anchor_lang::system_program;
use anchor_spl::{
    token::{self, Mint, Token, TokenAccount, MintTo},
    associated_token::AssociatedToken,
    metadata::{
        create_metadata_accounts_v3,
        CreateMetadataAccountsV3,
        Metadata,
        mpl_token_metadata::types::DataV2,
    },
};

use crate::state::*;
use crate::errors::ErrorCode;
use crate::utils::bonding_curve::{validate_curve_params, CurveCalculation};

/// Контексты для создания токена
#[derive(Accounts)]
#[instruction(name: String, symbol: String)]
pub struct CreateToken<'info> {
    /// Информация о токене (PDA)
    #[account(
        init,
        payer = creator,
        space = TokenInfo::ACCOUNT_SIZE,
        seeds = [TokenInfo::SEED.as_bytes(), mint.key().as_ref()],
        bump
    )]
    pub token_info: Account<'info, TokenInfo>,

    /// Mint токена
    #[account(
        init,
        payer = creator,
        mint::decimals = 9,
        mint::authority = bonding_curve_vault,
        mint::freeze_authority = bonding_curve_vault,
    )]
    pub mint: Account<'info, Mint>,

    /// Хранилище SOL для бондинг-кривой (PDA)
    #[account(
        mut,
        seeds = [b"bonding_curve_vault", mint.key().as_ref()],
        bump,
    )]
    /// CHECK: Проверяется как PDA в seeds constraint
    pub bonding_curve_vault: AccountInfo<'info>,

    /// Хранилище токенов для бондинг-кривой
    #[account(
        init,
        payer = creator,
        associated_token::mint = mint,
        associated_token::authority = bonding_curve_vault,
    )]
    pub bonding_curve_token_account: Account<'info, TokenAccount>,

    /// Метаданные токена
    #[account(
        mut,
        seeds = [
            b"metadata",
            metadata_program.key().as_ref(),
            mint.key().as_ref(),
        ],
        seeds::program = metadata_program.key(),
        bump,
    )]
    /// CHECK: Проверяется программой метаданных
    pub metadata: AccountInfo<'info>,

    /// Создатель токена
    #[account(mut)]
    pub creator: Signer<'info>,

    /// Глобальная конфигурация платформы
    #[account(
        mut,
        seeds = [PlatformConfig::SEED.as_bytes()],
        bump = platform_config.bump,
        constraint = !platform_config.emergency_paused @ ErrorCode::PlatformPaused,
        constraint = !platform_config.trading_paused @ ErrorCode::TradingPaused,
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    /// Программы
    pub system_program: Program<'info, System>,
    pub token_program: Program<'info, Token>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    pub metadata_program: Program<'info, Metadata>,
    pub rent: Sysvar<'info, Rent>,
}

/// Параметры для создания токена
#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct CreateTokenParams {
    /// Название токена
    pub name: String,
    /// Символ токена
    pub symbol: String,
    /// URI метаданных (JSON)
    pub uri: String,
    /// Параметры бондинг-кривой
    pub bonding_curve_params: BondingCurveParams,
    /// Начальная ликвидность от создателя (в lamports SOL)
    pub initial_liquidity: u64,
}

/// Параметры бондинг-кривой
#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct BondingCurveParams {
    /// Тип кривой
    pub curve_type: BondingCurveType,
    /// Начальная цена (в lamports за токен)
    pub initial_price: u64,
    /// Максимальный supply для выхода на DEX
    pub max_supply: u64,
    /// Дополнительные параметры (опционально)
    pub slope: Option<u64>,
    pub growth_factor: Option<u64>,
    pub max_price: Option<u64>,
    pub steepness: Option<u64>,
    pub midpoint: Option<u64>,
}

/// Основная функция создания токена
pub fn create_token(
    ctx: Context<CreateToken>,
    params: CreateTokenParams,
) -> Result<()> {
    msg!("🏭 Создание нового токена: {}", params.name);

    let clock = Clock::get()?;
    let platform_config = &mut ctx.accounts.platform_config;

    // === ВАЛИДАЦИЯ ПАРАМЕТРОВ ===
    validate_token_params(&params, platform_config)?;

    // === СОЗДАНИЕ МЕТАДАННЫХ ===
    create_token_metadata(
        &ctx,
        &params.name,
        &params.symbol,
        &params.uri,
    )?;

    // === ИНИЦИАЛИЗАЦИЯ БОНДИНГ-КРИВОЙ ===
    let bonding_curve = BondingCurve {
        curve_type: params.bonding_curve_params.curve_type,
        initial_price: params.bonding_curve_params.initial_price,
        max_supply: params.bonding_curve_params.max_supply,
        slope: params.bonding_curve_params.slope,
        growth_factor: params.bonding_curve_params.growth_factor,
        max_price: params.bonding_curve_params.max_price,
        steepness: params.bonding_curve_params.steepness,
        midpoint: params.bonding_curve_params.midpoint,
    };

    // Валидация параметров кривой
    validate_curve_params(&bonding_curve)?;

    // === MINT НАЧАЛЬНОГО SUPPLY ===
    let initial_supply = params.bonding_curve_params.max_supply;
    mint_initial_supply(&ctx, initial_supply)?;

    // === ИНИЦИАЛИЗАЦИЯ ТОКЕНА ===
    let token_info = &mut ctx.accounts.token_info;
    
    token_info.mint = ctx.accounts.mint.key();
    token_info.creator = ctx.accounts.creator.key();
    token_info.name = params.name.clone();
    token_info.symbol = params.symbol.clone();
    token_info.uri = params.uri.clone();
    token_info.bonding_curve = bonding_curve;
    
    // Статистика
    token_info.current_supply = initial_supply;
    token_info.circulating_supply = 0; // Все токены в бондинг-кривой
    token_info.total_volume_sol = 0;
    token_info.total_trades = 0;
    token_info.holders_count = 0;
    
    // Состояние
    token_info.is_graduated = false;
    token_info.is_frozen = false;
    token_info.is_tradeable = true;
    
    // Временные метки
    token_info.created_at = clock.unix_timestamp;
    token_info.last_trade_at = 0;
    token_info.graduated_at = None;
    
    // Бампы для PDA
    token_info.bump = ctx.bumps.token_info;
    token_info.vault_bump = ctx.bumps.bonding_curve_vault;

    // === ОБРАБОТКА НАЧАЛЬНОЙ ЛИКВИДНОСТИ ===
    if params.initial_liquidity > 0 {
        handle_initial_liquidity(&ctx, &mut token_info, params.initial_liquidity)?;
    }

    // === ОБНОВЛЕНИЕ ПЛАТФОРМЫ ===
    platform_config.total_tokens_created = platform_config
        .total_tokens_created
        .checked_add(1)
        .ok_or(ErrorCode::MathOverflow)?;
    
    platform_config.last_updated = clock.unix_timestamp;

    // === СОБЫТИЯ ===
    emit!(TokenCreatedEvent {
        mint: ctx.accounts.mint.key(),
        creator: ctx.accounts.creator.key(),
        name: params.name,
        symbol: params.symbol,
        uri: params.uri,
        bonding_curve_type: params.bonding_curve_params.curve_type,
        initial_price: params.bonding_curve_params.initial_price,
        max_supply: params.bonding_curve_params.max_supply,
        initial_liquidity: params.initial_liquidity,
        timestamp: clock.unix_timestamp,
    });

    msg!("✅ Токен {} ({}) создан успешно!", params.name, params.symbol);
    msg!("   Mint: {}", ctx.accounts.mint.key());
    msg!("   Creator: {}", ctx.accounts.creator.key());
    msg!("   Max Supply: {}", params.bonding_curve_params.max_supply);
    msg!("   Initial Price: {} lamports", params.bonding_curve_params.initial_price);

    Ok(())
}

/// Валидация параметров токена
fn validate_token_params(
    params: &CreateTokenParams,
    platform_config: &PlatformConfig,
) -> Result<()> {
    // Проверка длины названия
    require!(
        params.name.len() >= platform_config.min_token_name_length as usize,
        ErrorCode::TokenNameTooShort
    );
    require!(
        params.name.len() <= platform_config.max_token_name_length as usize,
        ErrorCode::TokenNameTooLong
    );

    // Проверка символа (1-10 символов, только буквы и цифры)
    require!(
        params.symbol.len() >= 1 && params.symbol.len() <= 10,
        ErrorCode::InvalidTokenSymbol
    );
    require!(
        params.symbol.chars().all(|c| c.is_alphanumeric()),
        ErrorCode::InvalidTokenSymbol
    );

    // Проверка URI
    require!(
        params.uri.len() <= 200,
        ErrorCode::TokenUriTooLong
    );

    // Проверка начальной цены
    require!(
        params.bonding_curve_params.initial_price > 0,
        ErrorCode::InvalidInitialPrice
    );

    // Проверка максимального supply
    require!(
        params.bonding_curve_params.max_supply > 0,
        ErrorCode::InvalidMaxSupply
    );
    require!(
        params.bonding_curve_params.max_supply <= platform_config.max_initial_supply,
        ErrorCode::MaxSupplyExceeded
    );

    // Проверка начальной ликвидности
    if params.initial_liquidity > 0 {
        require!(
            params.initial_liquidity >= platform_config.min_initial_liquidity,
            ErrorCode::InsufficientInitialLiquidity
        );
    }

    Ok(())
}

/// Создание метаданных токена
fn create_token_metadata(
    ctx: &Context<CreateToken>,
    name: &str,
    symbol: &str,
    uri: &str,
) -> Result<()> {
    let metadata_seeds = &[
        b"bonding_curve_vault",
        ctx.accounts.mint.key().as_ref(),
        &[ctx.bumps.bonding_curve_vault],
    ];
    
    let metadata_signer = &[&metadata_seeds[..]];

    let metadata_ctx = CpiContext::new_with_signer(
        ctx.accounts.metadata_program.to_account_info(),
        CreateMetadataAccountsV3 {
            metadata: ctx.accounts.metadata.to_account_info(),
            mint: ctx.accounts.mint.to_account_info(),
            mint_authority: ctx.accounts.bonding_curve_vault.to_account_info(),
            update_authority: ctx.accounts.bonding_curve_vault.to_account_info(),
            payer: ctx.accounts.creator.to_account_info(),
            system_program: ctx.accounts.system_program.to_account_info(),
            rent: ctx.accounts.rent.to_account_info(),
        },
        metadata_signer,
    );

    let metadata_data = DataV2 {
        name: name.to_string(),
        symbol: symbol.to_string(),
        uri: uri.to_string(),
        seller_fee_basis_points: 0,
        creators: None,
        collection: None,
        uses: None,
    };

    create_metadata_accounts_v3(
        metadata_ctx,
        metadata_data,
        true,  // is_mutable
        true,  // update_authority_is_signer
        None,  // collection_details
    )?;

    msg!("📄 Метаданные токена созданы");
    Ok(())
}

/// Mint начального supply в хранилище бондинг-кривой
fn mint_initial_supply(
    ctx: &Context<CreateToken>,
    initial_supply: u64,
) -> Result<()> {
    let seeds = &[
        b"bonding_curve_vault",
        ctx.accounts.mint.key().as_ref(),
        &[ctx.bumps.bonding_curve_vault],
    ];
    let signer = &[&seeds[..]];

    let cpi_ctx = CpiContext::new_with_signer(
        ctx.accounts.token_program.to_account_info(),
        MintTo {
            mint: ctx.accounts.mint.to_account_info(),
            to: ctx.accounts.bonding_curve_token_account.to_account_info(),
            authority: ctx.accounts.bonding_curve_vault.to_account_info(),
        },
        signer,
    );

    token::mint_to(cpi_ctx, initial_supply)?;

    msg!("🪙 Создано {} токенов в бондинг-кривой", initial_supply);
    Ok(())
}

/// Обработка начальной ликвидности от создателя
fn handle_initial_liquidity(
    ctx: &Context<CreateToken>,
    token_info: &mut TokenInfo,
    liquidity_amount: u64,
) -> Result<()> {
    // Перевод SOL от создателя в хранилище
    let transfer_ctx = CpiContext::new(
        ctx.accounts.system_program.to_account_info(),
        system_program::Transfer {
            from: ctx.accounts.creator.to_account_info(),
            to: ctx.accounts.bonding_curve_vault.to_account_info(),
        },
    );

    system_program::transfer(transfer_ctx, liquidity_amount)?;

    // Обновление статистики
    token_info.total_volume_sol = token_info
        .total_volume_sol
        .checked_add(liquidity_amount)
        .ok_or(ErrorCode::MathOverflow)?;

    msg!("💧 Добавлена начальная ликвидность: {} SOL", liquidity_amount as f64 / 1_000_000_000.0);
    Ok(())
}

/// Событие создания токена
#[event]
pub struct TokenCreatedEvent {
    /// Адрес mint токена
    pub mint: Pubkey,
    /// Создатель токена
    pub creator: Pubkey,
    /// Название токена
    pub name: String,
    /// Символ токена
    pub symbol: String,
    /// URI метаданных
    pub uri: String,
    /// Тип бондинг-кривой
    pub bonding_curve_type: BondingCurveType,
    /// Начальная цена
    pub initial_price: u64,
    /// Максимальный supply
    pub max_supply: u64,
    /// Начальная ликвидность
    pub initial_liquidity: u64,
    /// Время создания
    pub timestamp: i64,
}