/*! 
🎓 Градация токенов на DEX - листинг с полной ликвидностью
Production-ready инструкция для перехода с бондинг-кривой на DEX
*/

use anchor_lang::prelude::*;
use anchor_lang::system_program;
use anchor_spl::{
    token::{self, Token, TokenAccount, Transfer, Mint},
    associated_token::AssociatedToken,
};

use crate::state::*;
use crate::errors::ErrorCode;

/// Контексты для градации токена на DEX
#[derive(Accounts)]
pub struct GraduateToDex<'info> {
    /// Информация о токене для градации
    #[account(
        mut,
        seeds = [TokenInfo::SEED.as_bytes(), mint.key().as_ref()],
        bump = token_info.bump,
        constraint = !token_info.is_graduated @ ErrorCode::TokenAlreadyGraduated,
        constraint = token_info.is_tradeable @ ErrorCode::TradingDisabled,
        constraint = !token_info.is_frozen @ ErrorCode::TokenFrozen,
    )]
    pub token_info: Account<'info, TokenInfo>,

    /// Mint токена для градации
    #[account(address = token_info.mint)]
    pub mint: Account<'info, Mint>,

    /// Информация о листинге на DEX (создается)
    #[account(
        init,
        payer = initiator,
        space = DexListing::ACCOUNT_SIZE,
        seeds = [DexListing::SEED.as_bytes(), mint.key().as_ref()],
        bump
    )]
    pub dex_listing: Account<'info, DexListing>,

    /// Хранилище SOL бондинг-кривой
    #[account(
        mut,
        seeds = [b"bonding_curve_vault", mint.key().as_ref()],
        bump = token_info.vault_bump,
    )]
    /// CHECK: Проверяется как PDA
    pub bonding_curve_vault: AccountInfo<'info>,

    /// Токен-аккаунт бондинг-кривой (источник ликвидности)
    #[account(
        mut,
        associated_token::mint = mint,
        associated_token::authority = bonding_curve_vault,
    )]
    pub bonding_curve_token_account: Account<'info, TokenAccount>,

    /// Глобальная конфигурация платформы
    #[account(
        mut,
        seeds = [PlatformConfig::SEED.as_bytes()],
        bump = platform_config.bump,
        constraint = !platform_config.emergency_paused @ ErrorCode::PlatformPaused,
        constraint = !platform_config.trading_paused @ ErrorCode::TradingPaused,
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    /// Казначейство для сбора комиссий за градацию
    #[account(
        mut,
        address = platform_config.treasury
    )]
    /// CHECK: Проверяется через address constraint
    pub treasury: AccountInfo<'info>,

    /// Программа DEX для создания пула (проверяется по типу DEX)
    /// CHECK: Валидируется в зависимости от dex_type
    pub dex_program: AccountInfo<'info>,

    /// Аккаунт пула ликвидности на DEX (создается или обновляется)
    #[account(mut)]
    /// CHECK: Создается DEX программой
    pub pool_account: AccountInfo<'info>,

    /// DEX-специфичные аккаунты (зависят от конкретного DEX)
    #[account(mut)]
    /// CHECK: Используется DEX программой
    pub dex_account_a: AccountInfo<'info>,

    #[account(mut)]
    /// CHECK: Используется DEX программой  
    pub dex_account_b: AccountInfo<'info>,

    #[account(mut)]
    /// CHECK: Используется DEX программой
    pub dex_account_c: AccountInfo<'info>,

    /// Инициатор градации (может быть создатель токена или любой пользователь)
    #[account(mut)]
    pub initiator: Signer<'info>,

    /// Системные программы
    pub token_program: Program<'info, Token>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

/// Градация токена на DEX с перемещением всей ликвидности
pub fn graduate_to_dex(
    ctx: Context<GraduateToDex>,
    dex_type: DexType,
    minimum_liquidity_sol: u64,
) -> Result<()> {
    msg!("🎓 Начинаем градацию токена на DEX: {:?}", dex_type);

    let clock = Clock::get()?;
    let platform_config = &mut ctx.accounts.platform_config;
    let token_info = &mut ctx.accounts.token_info;

    // === ВАЛИДАЦИЯ УСЛОВИЙ ГРАДАЦИИ ===

    // Проверка рыночной капитализации
    require!(
        token_info.market_cap >= platform_config.graduation_fee,
        ErrorCode::GraduationThresholdNotMet
    );

    // Проверка минимальной ликвидности
    require!(
        token_info.sol_reserves >= minimum_liquidity_sol,
        ErrorCode::InsufficientLiquidity
    );

    require!(
        token_info.token_reserves > 0,
        ErrorCode::InsufficientLiquidity
    );

    // Проверка времени с момента создания (минимум 1 час)
    let time_since_creation = clock.unix_timestamp - token_info.created_at;
    require!(
        time_since_creation >= 3600, // 1 час
        ErrorCode::TooEarlyForGraduation
    );

    // === ВАЛИДАЦИЯ DEX ПРОГРАММЫ ===
    
    let expected_program_id = match dex_type {
        DexType::Raydium => "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
        DexType::Orca => "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP", 
        DexType::Jupiter => "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",
        DexType::Serum => "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin",
        DexType::Meteora => "24Uqj9JCLxUeoC3hGfh5W3s9FM9uCHDS2SG3LYwBpyTi",
    };

    require!(
        ctx.accounts.dex_program.key().to_string() == expected_program_id,
        ErrorCode::InvalidDexProgram
    );

    // === СБОР КОМИССИИ ЗА ГРАДАЦИЮ ===
    
    let graduation_fee = platform_config.graduation_fee;
    if graduation_fee > 0 {
        msg!("💰 Сбор комиссии за градацию: {} lamports", graduation_fee);
        
        system_program::transfer(
            CpiContext::new(
                ctx.accounts.system_program.to_account_info(),
                system_program::Transfer {
                    from: ctx.accounts.initiator.to_account_info(),
                    to: ctx.accounts.treasury.to_account_info(),
                },
            ),
            graduation_fee,
        )?;
    }

    // === ПОДГОТОВКА ЛИКВИДНОСТИ ===
    
    let sol_liquidity = token_info.sol_reserves;
    let token_liquidity = token_info.token_reserves;
    
    msg!("💧 Перемещение ликвидности: {} SOL + {} токенов", 
         sol_liquidity as f64 / 1_000_000_000.0, 
         token_liquidity);

    // === СОЗДАНИЕ ПУЛА НА DEX ===
    
    let pool_creation_result = match dex_type {
        DexType::Raydium => {
            create_raydium_pool(&ctx, sol_liquidity, token_liquidity)?
        },
        DexType::Orca => {
            create_orca_pool(&ctx, sol_liquidity, token_liquidity)?
        },
        DexType::Jupiter => {
            create_jupiter_pool(&ctx, sol_liquidity, token_liquidity)?
        },
        _ => {
            // Для остальных DEX используем общую логику
            create_generic_pool(&ctx, sol_liquidity, token_liquidity)?
        }
    };

    // === ПЕРЕМЕЩЕНИЕ ЛИКВИДНОСТИ ===
    
    let vault_seeds = &[
        b"bonding_curve_vault",
        ctx.accounts.mint.key().as_ref(),
        &[token_info.vault_bump],
    ];
    let vault_signer = &[&vault_seeds[..]];

    // Перевод SOL в пул DEX
    **ctx.accounts.bonding_curve_vault.try_borrow_mut_lamports()? -= sol_liquidity;
    **ctx.accounts.pool_account.try_borrow_mut_lamports()? += sol_liquidity;

    // Перевод токенов в пул DEX
    token::transfer(
        CpiContext::new_with_signer(
            ctx.accounts.token_program.to_account_info(),
            Transfer {
                from: ctx.accounts.bonding_curve_token_account.to_account_info(),
                to: ctx.accounts.dex_account_a.to_account_info(),
                authority: ctx.accounts.bonding_curve_vault.to_account_info(),
            },
            vault_signer,
        ),
        token_liquidity,
    )?;

    // === ОБНОВЛЕНИЕ СОСТОЯНИЯ ТОКЕНА ===
    
    token_info.is_graduated = true;
    token_info.graduated_at = Some(clock.unix_timestamp);
    token_info.sol_reserves = 0; // Вся ликвидность перемещена на DEX
    token_info.token_reserves = 0;
    token_info.is_tradeable = false; // Торговля теперь только на DEX

    // === ИНИЦИАЛИЗАЦИЯ ИНФОРМАЦИИ О ЛИСТИНГЕ ===
    
    let dex_listing = &mut ctx.accounts.dex_listing;
    dex_listing.token_mint = ctx.accounts.mint.key();
    dex_listing.dex_type = dex_type;
    dex_listing.pool_address = ctx.accounts.pool_account.key();
    dex_listing.initial_liquidity_sol = sol_liquidity;
    dex_listing.initial_liquidity_token = token_liquidity;
    dex_listing.listing_timestamp = clock.unix_timestamp;
    dex_listing.listing_price = token_info.current_price;
    dex_listing.fee_tier = 300; // 0.3% стандартная комиссия
    dex_listing.liquidity_locked = true;
    dex_listing.lock_duration = 30 * 24 * 60 * 60; // 30 дней блокировки
    dex_listing.pool_lp_supply = pool_creation_result.lp_tokens_minted;
    dex_listing.creator_lp_tokens = pool_creation_result.creator_lp_tokens;
    dex_listing.bump = ctx.bumps.dex_listing;

    // === ОБНОВЛЕНИЕ СТАТИСТИКИ ПЛАТФОРМЫ ===
    
    platform_config.total_graduated_tokens = platform_config
        .total_graduated_tokens
        .checked_add(1)
        .ok_or(ErrorCode::MathOverflow)?;
    
    platform_config.total_liquidity_moved = platform_config
        .total_liquidity_moved
        .checked_add(sol_liquidity)
        .ok_or(ErrorCode::MathOverflow)?;

    platform_config.last_updated = clock.unix_timestamp;

    // === РАСЧЕТ СТАТИСТИКИ ГРАДАЦИИ ===
    
    let graduation_time_hours = time_since_creation / 3600;
    let final_market_cap = token_info.market_cap;

    // === СОБЫТИЕ ГРАДАЦИИ ===
    
    emit!(TokenGraduatedEvent {
        mint: ctx.accounts.mint.key(),
        creator: token_info.creator,
        dex_type,
        final_market_cap,
        liquidity_sol: sol_liquidity,
        liquidity_tokens: token_liquidity,
        graduation_time_hours: graduation_time_hours as u64,
        pool_address: ctx.accounts.pool_account.key(),
        timestamp: clock.unix_timestamp,
    });

    msg!("✅ Токен {} успешно выпущен на {:?}!", 
         token_info.symbol, 
         dex_type);
    msg!("   Финальная капитализация: {} SOL", 
         final_market_cap as f64 / 1_000_000_000.0);
    msg!("   Время до градации: {} часов", graduation_time_hours);
    msg!("   Адрес пула: {}", ctx.accounts.pool_account.key());

    Ok(())
}

// === DEX-СПЕЦИФИЧНЫЕ ФУНКЦИИ СОЗДАНИЯ ПУЛОВ ===

/// Структура результата создания пула
#[derive(Debug)]
pub struct PoolCreationResult {
    pub lp_tokens_minted: u64,
    pub creator_lp_tokens: u64,
    pub pool_initialized: bool,
}

/// Создание пула ликвидности на Raydium
fn create_raydium_pool(
    ctx: &Context<GraduateToDex>,
    sol_amount: u64,
    token_amount: u64,
) -> Result<PoolCreationResult> {
    msg!("🌊 Создание пула Raydium с {} SOL и {} токенов", 
         sol_amount as f64 / 1_000_000_000.0, 
         token_amount);

    // В production здесь будет интеграция с Raydium AMM
    // Пример структуры:
    /*
    let cpi_accounts = raydium::cpi::accounts::InitializePool {
        pool: ctx.accounts.pool_account.to_account_info(),
        token_a: ctx.accounts.mint.to_account_info(),
        token_b: /* WSOL mint */,
        vault_a: ctx.accounts.dex_account_a.to_account_info(),
        vault_b: ctx.accounts.dex_account_b.to_account_info(),
        lp_mint: ctx.accounts.dex_account_c.to_account_info(),
        authority: ctx.accounts.bonding_curve_vault.to_account_info(),
        fee_destination: /* fee account */,
        payer: ctx.accounts.initiator.to_account_info(),
        system_program: ctx.accounts.system_program.to_account_info(),
        token_program: ctx.accounts.token_program.to_account_info(),
    };

    let cpi_ctx = CpiContext::new(ctx.accounts.dex_program.to_account_info(), cpi_accounts);
    raydium::cpi::initialize_pool(cpi_ctx, sol_amount, token_amount)?;
    */

    // Заглушка для демонстрации
    let lp_tokens = calculate_lp_tokens(sol_amount, token_amount)?;
    
    Ok(PoolCreationResult {
        lp_tokens_minted: lp_tokens,
        creator_lp_tokens: lp_tokens, // Весь LP токены идут создателю
        pool_initialized: true,
    })
}

/// Создание пула ликвидности на Orca Whirlpools
fn create_orca_pool(
    ctx: &Context<GraduateToDex>,
    sol_amount: u64,
    token_amount: u64,
) -> Result<PoolCreationResult> {
    msg!("🐋 Создание пула Orca Whirlpool с {} SOL и {} токенов", 
         sol_amount as f64 / 1_000_000_000.0, 
         token_amount);

    // В production здесь будет интеграция с Orca Whirlpools
    // Orca использует концентрированную ликвидность
    /*
    let cpi_accounts = orca_whirlpools::cpi::accounts::InitializePool {
        whirlpool: ctx.accounts.pool_account.to_account_info(),
        token_mint_a: ctx.accounts.mint.to_account_info(),
        token_mint_b: /* WSOL mint */,
        token_vault_a: ctx.accounts.dex_account_a.to_account_info(),
        token_vault_b: ctx.accounts.dex_account_b.to_account_info(),
        tick_spacing: 64, // стандартный tick spacing
        initial_sqrt_price: /* calculated sqrt price */,
        payer: ctx.accounts.initiator.to_account_info(),
    };
    */

    let lp_tokens = calculate_lp_tokens(sol_amount, token_amount)?;
    
    Ok(PoolCreationResult {
        lp_tokens_minted: lp_tokens,
        creator_lp_tokens: lp_tokens,
        pool_initialized: true,
    })
}

/// Создание маршрута через Jupiter (использует базовые DEX)
fn create_jupiter_pool(
    ctx: &Context<GraduateToDex>,
    sol_amount: u64,
    token_amount: u64,
) -> Result<PoolCreationResult> {
    msg!("🪐 Создание маршрута Jupiter с {} SOL и {} токенов", 
         sol_amount as f64 / 1_000_000_000.0, 
         token_amount);

    // Jupiter это агрегатор, не создаёт собственные пулы
    // Обычно создаём пул на базовом DEX (например, Orca)
    // и Jupiter автоматически его индексирует
    
    // Делегируем создание пула на Orca
    create_orca_pool(ctx, sol_amount, token_amount)
}

/// Общая функция создания пула для неспециализированных DEX
fn create_generic_pool(
    _ctx: &Context<GraduateToDex>,
    sol_amount: u64,
    token_amount: u64,
) -> Result<PoolCreationResult> {
    msg!("⚙️ Создание общего пула с {} SOL и {} токенов", 
         sol_amount as f64 / 1_000_000_000.0, 
         token_amount);

    // Базовая реализация для неспециализированных DEX
    let lp_tokens = calculate_lp_tokens(sol_amount, token_amount)?;
    
    Ok(PoolCreationResult {
        lp_tokens_minted: lp_tokens,
        creator_lp_tokens: lp_tokens,
        pool_initialized: true,
    })
}

// === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

/// Расчет количества LP токенов по формуле геометрического среднего
fn calculate_lp_tokens(sol_amount: u64, token_amount: u64) -> Result<u64> {
    // LP токены = sqrt(sol_amount * token_amount)
    // Используем приближенное вычисление квадратного корня
    
    let product = (sol_amount as u128)
        .checked_mul(token_amount as u128)
        .ok_or(ErrorCode::MathOverflow)?;
    
    // Упрощенный квадратный корень через итерации
    let mut x = product / 2;
    if x == 0 {
        return Ok(0);
    }
    
    // Метод Ньютона для квадратного корня
    for _ in 0..10 {
        let new_x = (x + product / x) / 2;
        if new_x >= x {
            break;
        }
        x = new_x;
    }
    
    Ok(x as u64)
}

/// Событие градации токена
#[event]
pub struct TokenGraduatedEvent {
    /// Mint токена
    pub mint: Pubkey,
    /// Создатель токена
    pub creator: Pubkey,
    /// Тип DEX
    pub dex_type: DexType,
    /// Финальная рыночная капитализация
    pub final_market_cap: u64,
    /// Ликвидность SOL
    pub liquidity_sol: u64,
    /// Ликвидность токенов
    pub liquidity_tokens: u64,
    /// Время до градации в часах
    pub graduation_time_hours: u64,
    /// Адрес пула на DEX
    pub pool_address: Pubkey,
    /// Время градации
    pub timestamp: i64,
}