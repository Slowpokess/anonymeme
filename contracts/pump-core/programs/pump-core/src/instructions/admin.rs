/*! 
⚙️ Административные функции платформы Anonymeme
Production-ready система администрирования и управления платформой
*/

use anchor_lang::prelude::*;
use anchor_lang::system_program;
use crate::state::*;
use crate::errors::ErrorCode;

/// Контекст для обновления конфигурации платформы
#[derive(Accounts)]
pub struct UpdatePlatformConfig<'info> {
    /// Глобальная конфигурация платформы
    #[account(
        mut,
        seeds = [PlatformConfig::SEED.as_bytes()],
        bump = platform_config.bump,
        constraint = platform_config.admin == admin.key() @ ErrorCode::AdminOnly
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    /// Администратор платформы
    #[account(mut)]
    pub admin: Signer<'info>,
}

/// Обновление комиссии платформы
pub fn update_platform_fee(
    ctx: Context<UpdatePlatformConfig>,
    new_fee_rate: f64,
    reason: String,
) -> Result<()> {
    msg!("💰 Обновление комиссии платформы администратором");

    let clock = Clock::get()?;
    let platform_config = &mut ctx.accounts.platform_config;
    let old_fee = platform_config.fee_rate;
    
    // === ВАЛИДАЦИЯ НОВОЙ КОМИССИИ ===
    
    require!(
        new_fee_rate >= 0.0 && new_fee_rate <= 10.0, 
        ErrorCode::InvalidInput
    );

    require!(
        reason.len() >= 10 && reason.len() <= 200,
        ErrorCode::InvalidInput
    );

    // === ОБНОВЛЕНИЕ КОНФИГУРАЦИИ ===
    
    platform_config.fee_rate = new_fee_rate;
    platform_config.last_updated = clock.unix_timestamp;

    // === СОБЫТИЕ АДМИНИСТРАТИВНОГО ДЕЙСТВИЯ ===
    
    emit!(AdminActionEvent {
        admin: ctx.accounts.admin.key(),
        action_type: AdminActionType::FeeUpdated,
        target: platform_config.key(),
        old_value: format!("{:.2}%", old_fee),
        new_value: format!("{:.2}%", new_fee_rate),
        reason: reason.clone(),
        timestamp: clock.unix_timestamp,
    });

    msg!("✅ Комиссия платформы обновлена: {:.2}% -> {:.2}%", old_fee, new_fee_rate);
    msg!("   Причина: {}", reason);

    Ok(())
}

/// Обновление адреса казначейства платформы
pub fn update_treasury(
    ctx: Context<UpdatePlatformConfig>,
    new_treasury: Pubkey,
    reason: String,
) -> Result<()> {
    msg!("🏛️ Обновление казначейства платформы администратором");

    let clock = Clock::get()?;
    let platform_config = &mut ctx.accounts.platform_config;
    let old_treasury = platform_config.treasury;
    
    // === ВАЛИДАЦИЯ НОВОГО КАЗНАЧЕЙСТВА ===
    
    require!(
        old_treasury != new_treasury,
        ErrorCode::NoStateChange
    );

    require!(
        reason.len() >= 10 && reason.len() <= 200,
        ErrorCode::InvalidInput
    );

    // === ОБНОВЛЕНИЕ КОНФИГУРАЦИИ ===
    
    platform_config.treasury = new_treasury;
    platform_config.last_updated = clock.unix_timestamp;

    // === СОБЫТИЕ АДМИНИСТРАТИВНОГО ДЕЙСТВИЯ ===
    
    emit!(AdminActionEvent {
        admin: ctx.accounts.admin.key(),
        action_type: AdminActionType::TreasuryUpdated,
        target: new_treasury,
        old_value: old_treasury.to_string(),
        new_value: new_treasury.to_string(),
        reason: reason.clone(),
        timestamp: clock.unix_timestamp,
    });

    msg!("✅ Казначейство обновлено: {} -> {}", old_treasury, new_treasury);
    msg!("   Причина: {}", reason);

    Ok(())
}

/// Контекст для передачи прав администратора
#[derive(Accounts)]
pub struct TransferAdmin<'info> {
    /// Глобальная конфигурация платформы
    #[account(
        mut,
        seeds = [PlatformConfig::SEED.as_bytes()],
        bump = platform_config.bump,
        constraint = platform_config.admin == current_admin.key() @ ErrorCode::AdminOnly
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    /// Текущий администратор
    #[account(mut)]
    pub current_admin: Signer<'info>,

    /// CHECK: Новый администратор
    pub new_admin: AccountInfo<'info>,
}

/// Передача прав администратора новому пользователю
pub fn transfer_admin(
    ctx: Context<TransferAdmin>,
    reason: String,
) -> Result<()> {
    msg!("👑 Передача прав администратора платформы");

    let clock = Clock::get()?;
    let platform_config = &mut ctx.accounts.platform_config;
    let old_admin = platform_config.admin;
    let new_admin = ctx.accounts.new_admin.key();

    // === ВАЛИДАЦИЯ ПЕРЕДАЧИ ===
    
    require!(
        old_admin != new_admin, 
        ErrorCode::NoStateChange
    );

    require!(
        reason.len() >= 20 && reason.len() <= 500,
        ErrorCode::InvalidInput
    );

    // === КРИТИЧЕСКОЕ ПРЕДУПРЕЖДЕНИЕ ===
    
    msg!("⚠️ ВНИМАНИЕ: КРИТИЧЕСКОЕ ДЕЙСТВИЕ - ПЕРЕДАЧА АДМИНИСТРАТИВНЫХ ПРАВ");
    msg!("   Старый админ: {}", old_admin);
    msg!("   Новый админ: {}", new_admin);
    msg!("   Причина: {}", reason);

    // === ОБНОВЛЕНИЕ АДМИНИСТРАТОРА ===
    
    platform_config.admin = new_admin;
    platform_config.last_updated = clock.unix_timestamp;

    // === СОБЫТИЕ КРИТИЧЕСКОГО ДЕЙСТВИЯ ===
    
    emit!(AdminActionEvent {
        admin: old_admin,
        action_type: AdminActionType::AdminTransferred,
        target: new_admin,
        old_value: old_admin.to_string(),
        new_value: new_admin.to_string(),
        reason: reason.clone(),
        timestamp: clock.unix_timestamp,
    });

    msg!("✅ Административные права переданы: {} -> {}", old_admin, new_admin);
    msg!("   Причина: {}", reason);

    Ok(())
}

/// Контекст для операций с токенами
#[derive(Accounts)]
pub struct ManageToken<'info> {
    /// Информация о токене
    #[account(
        mut,
        seeds = [TokenInfo::SEED.as_bytes(), mint.key().as_ref()],
        bump = token_info.bump,
    )]
    pub token_info: Account<'info, TokenInfo>,

    /// Mint токена
    pub mint: AccountInfo<'info>,

    /// Глобальная конфигурация платформы
    #[account(
        seeds = [PlatformConfig::SEED.as_bytes()],
        bump = platform_config.bump,
        constraint = platform_config.admin == admin.key() @ ErrorCode::AdminOnly
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    /// Администратор платформы
    #[account(mut)]
    pub admin: Signer<'info>,
}

/// Блокировка токена администратором
pub fn ban_token(
    ctx: Context<ManageToken>,
    reason: String,
    is_permanent: bool,
) -> Result<()> {
    msg!("🚫 Блокировка токена администратором");

    let clock = Clock::get()?;
    let token_info = &mut ctx.accounts.token_info;

    // === ВАЛИДАЦИЯ ПАРАМЕТРОВ ===
    
    require!(
        !token_info.is_frozen,
        ErrorCode::TokenAlreadyFrozen
    );

    require!(
        reason.len() >= 10 && reason.len() <= 300,
        ErrorCode::InvalidInput
    );

    // === БЛОКИРОВКА ТОКЕНА ===
    
    token_info.is_frozen = true;
    token_info.is_tradeable = false;
    token_info.freeze_reason = reason.clone();
    token_info.frozen_at = Some(clock.unix_timestamp);
    
    if is_permanent {
        msg!("🔒 ПОСТОЯННАЯ БЛОКИРОВКА токена {}", token_info.symbol);
    } else {
        msg!("⏸️ ВРЕМЕННАЯ БЛОКИРОВКА токена {}", token_info.symbol);
    }

    // === СОБЫТИЕ БЛОКИРОВКИ ===
    
    emit!(TokenActionEvent {
        admin: ctx.accounts.admin.key(),
        token_mint: ctx.accounts.mint.key(),
        action_type: TokenActionType::TokenBanned,
        reason: reason.clone(),
        is_permanent,
        timestamp: clock.unix_timestamp,
    });

    msg!("✅ Токен {} заблокирован", token_info.symbol);
    msg!("   Причина: {}", reason);
    msg!("   Постоянно: {}", is_permanent);

    Ok(())
}

/// Разблокировка токена администратором
pub fn unban_token(
    ctx: Context<ManageToken>,
    reason: String,
) -> Result<()> {
    msg!("✅ Разблокировка токена администратором");

    let clock = Clock::get()?;
    let token_info = &mut ctx.accounts.token_info;

    // === ВАЛИДАЦИЯ СОСТОЯНИЯ ===
    
    require!(
        token_info.is_frozen,
        ErrorCode::TokenNotFrozen
    );

    require!(
        reason.len() >= 10 && reason.len() <= 300,
        ErrorCode::InvalidInput
    );

    // === РАЗБЛОКИРОВКА ТОКЕНА ===
    
    token_info.is_frozen = false;
    token_info.is_tradeable = true;
    token_info.freeze_reason = String::new();
    token_info.frozen_at = None;

    // === СОБЫТИЕ РАЗБЛОКИРОВКИ ===
    
    emit!(TokenActionEvent {
        admin: ctx.accounts.admin.key(),
        token_mint: ctx.accounts.mint.key(),
        action_type: TokenActionType::TokenUnbanned,
        reason: reason.clone(),
        is_permanent: false,
        timestamp: clock.unix_timestamp,
    });

    msg!("✅ Токен {} разблокирован", token_info.symbol);
    msg!("   Причина: {}", reason);

    Ok(())
}

/// Контекст для сбора комиссий
#[derive(Accounts)]
pub struct CollectFees<'info> {
    /// Глобальная конфигурация платформы
    #[account(
        mut,
        seeds = [PlatformConfig::SEED.as_bytes()],
        bump = platform_config.bump,
        constraint = platform_config.admin == admin.key() @ ErrorCode::AdminOnly
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    /// Казначейство платформы (получатель комиссий)
    #[account(
        mut,
        address = platform_config.treasury
    )]
    /// CHECK: Проверяется через address constraint
    pub treasury: AccountInfo<'info>,

    /// Аккумулятор комиссий (источник)
    #[account(
        mut,
        seeds = [b"fee_accumulator"],
        bump,
    )]
    /// CHECK: Проверяется как PDA
    pub fee_accumulator: AccountInfo<'info>,

    /// Администратор платформы
    #[account(mut)]
    pub admin: Signer<'info>,

    /// Системная программа
    pub system_program: Program<'info, System>,
}

/// Сбор накопленных комиссий в казначейство
pub fn collect_platform_fees(
    ctx: Context<CollectFees>,
) -> Result<()> {
    msg!("💰 Сбор платформенных комиссий в казначейство");

    let clock = Clock::get()?;
    let fee_accumulator = &ctx.accounts.fee_accumulator;
    let treasury = &ctx.accounts.treasury;
    let platform_config = &mut ctx.accounts.platform_config;

    // === ПРОВЕРКА БАЛАНСА КОМИССИЙ ===
    
    let fee_balance = fee_accumulator.lamports();
    
    require!(
        fee_balance > 0,
        ErrorCode::InsufficientFunds
    );

    // === ПЕРЕВОД КОМИССИЙ В КАЗНАЧЕЙСТВО ===
    
    **fee_accumulator.try_borrow_mut_lamports()? -= fee_balance;
    **treasury.try_borrow_mut_lamports()? += fee_balance;

    // === ОБНОВЛЕНИЕ СТАТИСТИКИ ===
    
    platform_config.total_fees_collected = platform_config
        .total_fees_collected
        .checked_add(fee_balance)
        .ok_or(ErrorCode::MathOverflow)?;

    platform_config.last_fee_collection = clock.unix_timestamp;
    platform_config.last_updated = clock.unix_timestamp;

    // === СОБЫТИЕ СБОРА КОМИССИЙ ===
    
    emit!(AdminActionEvent {
        admin: ctx.accounts.admin.key(),
        action_type: AdminActionType::FeesCollected,
        target: treasury.key(),
        old_value: "0".to_string(),
        new_value: (fee_balance as f64 / 1_000_000_000.0).to_string(),
        reason: "Routine fee collection".to_string(),
        timestamp: clock.unix_timestamp,
    });

    msg!("✅ Комиссии собраны: {} SOL переведено в казначейство", 
         fee_balance as f64 / 1_000_000_000.0);
    msg!("   Всего собрано комиссий: {} SOL", 
         platform_config.total_fees_collected as f64 / 1_000_000_000.0);

    Ok(())
}

// === СОБЫТИЯ АДМИНИСТРАТИВНЫХ ДЕЙСТВИЙ ===

/// Тип административного действия
#[derive(AnchorSerialize, AnchorDeserialize, Clone, Debug, PartialEq)]
pub enum AdminActionType {
    FeeUpdated,
    TreasuryUpdated,
    AdminTransferred,
    FeesCollected,
    ConfigUpdated,
}

/// Событие административного действия
#[event]
pub struct AdminActionEvent {
    /// Администратор, выполнивший действие
    pub admin: Pubkey,
    /// Тип действия
    pub action_type: AdminActionType,
    /// Цель действия
    pub target: Pubkey,
    /// Старое значение
    pub old_value: String,
    /// Новое значение
    pub new_value: String,
    /// Причина действия
    pub reason: String,
    /// Временная метка
    pub timestamp: i64,
}

/// Тип действия с токеном
#[derive(AnchorSerialize, AnchorDeserialize, Clone, Debug, PartialEq)]
pub enum TokenActionType {
    TokenBanned,
    TokenUnbanned,
    MetadataUpdated,
}

/// Событие действия с токеном
#[event]
pub struct TokenActionEvent {
    /// Администратор, выполнивший действие
    pub admin: Pubkey,
    /// Mint токена
    pub token_mint: Pubkey,
    /// Тип действия
    pub action_type: TokenActionType,
    /// Причина действия
    pub reason: String,
    /// Является ли действие постоянным
    pub is_permanent: bool,
    /// Временная метка
    pub timestamp: i64,
}