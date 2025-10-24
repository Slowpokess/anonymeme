/*!
🔒 LP Token Lock - Механизм блокировки ликвидности с таймлоком

Этот модуль реализует безопасную блокировку LP (Liquidity Provider) токенов
для защиты инвесторов от rug pulls и преждевременного удаления ликвидности.

## Основные возможности:

1. **Автоматическая блокировка** - LP токены автоматически блокируются при градации на DEX
2. **Настраиваемый период** - Длительность блокировки от 1 дня до 365 дней
3. **Безопасное хранение** - LP токены хранятся в PDA под контролем программы
4. **Разблокировка по времени** - Разблокировка возможна только после истечения срока
5. **Частичная разблокировка** - Возможность разблокировать частями (vesting)
6. **Продление блокировки** - Создатель может продлить срок блокировки

## Безопасность:

- ✅ LP токены хранятся в PDA (Program Derived Address)
- ✅ Только владелец может разблокировать после истечения срока
- ✅ Невозможно обойти таймлок
- ✅ Checked arithmetic для всех операций
- ✅ Events для мониторинга

## Формула vesting (опционально):

При включенном vesting токены разблокируются постепенно:
```
unlockable_amount = total_locked * (current_time - lock_start) / lock_duration
```

*/

use anchor_lang::prelude::*;
use anchor_spl::{
    token::{self, Token, TokenAccount, Transfer, Mint},
    associated_token::AssociatedToken,
};

use crate::state::*;
use crate::errors::ErrorCode;

/// Минимальный период блокировки (1 день в секундах)
pub const MIN_LOCK_DURATION: i64 = 86_400; // 24 * 60 * 60

/// Максимальный период блокировки (365 дней в секундах)
pub const MAX_LOCK_DURATION: i64 = 31_536_000; // 365 * 24 * 60 * 60

/// Контексты для блокировки LP токенов
#[derive(Accounts)]
#[instruction(lock_duration: i64)]
pub struct LockLpTokens<'info> {
    /// Информация о блокировке LP токенов (создается)
    #[account(
        init,
        payer = owner,
        space = LpTokenLock::ACCOUNT_SIZE,
        seeds = [LpTokenLock::SEED.as_bytes(), lp_mint.key().as_ref(), owner.key().as_ref()],
        bump
    )]
    pub lp_lock: Account<'info, LpTokenLock>,

    /// Mint LP токенов (созданный при градации на DEX)
    pub lp_mint: Account<'info, Mint>,

    /// Токен мемкоина (для связи с градацией)
    pub token_mint: Account<'info, Mint>,

    /// Информация о листинге на DEX
    #[account(
        seeds = [DexListing::SEED.as_bytes(), token_mint.key().as_ref()],
        bump = dex_listing.bump,
        constraint = dex_listing.liquidity_locked @ ErrorCode::LiquidityNotLocked,
    )]
    pub dex_listing: Account<'info, DexListing>,

    /// Хранилище заблокированных LP токенов (PDA)
    #[account(
        init,
        payer = owner,
        seeds = [b"lp_vault", lp_mint.key().as_ref(), owner.key().as_ref()],
        bump,
        token::mint = lp_mint,
        token::authority = lp_vault,
    )]
    pub lp_vault: Account<'info, TokenAccount>,

    /// Аккаунт владельца с LP токенами (источник)
    #[account(
        mut,
        constraint = owner_lp_account.mint == lp_mint.key(),
        constraint = owner_lp_account.owner == owner.key(),
        constraint = owner_lp_account.amount >= lp_amount @ ErrorCode::InsufficientBalance,
    )]
    pub owner_lp_account: Account<'info, TokenAccount>,

    /// Владелец LP токенов (создатель токена)
    #[account(mut)]
    pub owner: Signer<'info>,

    /// Системные программы
    pub token_program: Program<'info, Token>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

/// Контексты для разблокировки LP токенов
#[derive(Accounts)]
pub struct UnlockLpTokens<'info> {
    /// Информация о блокировке LP токенов
    #[account(
        mut,
        seeds = [LpTokenLock::SEED.as_bytes(), lp_mint.key().as_ref(), owner.key().as_ref()],
        bump = lp_lock.bump,
        constraint = lp_lock.owner == owner.key() @ ErrorCode::Unauthorized,
        constraint = lp_lock.is_locked @ ErrorCode::AlreadyUnlocked,
    )]
    pub lp_lock: Account<'info, LpTokenLock>,

    /// Mint LP токенов
    pub lp_mint: Account<'info, Mint>,

    /// Хранилище заблокированных LP токенов (PDA)
    #[account(
        mut,
        seeds = [b"lp_vault", lp_mint.key().as_ref(), owner.key().as_ref()],
        bump,
        token::mint = lp_mint,
        token::authority = lp_vault,
    )]
    pub lp_vault: Account<'info, TokenAccount>,

    /// Целевой аккаунт для получения LP токенов
    #[account(
        mut,
        constraint = destination_lp_account.mint == lp_mint.key(),
        constraint = destination_lp_account.owner == owner.key(),
    )]
    pub destination_lp_account: Account<'info, TokenAccount>,

    /// Владелец LP токенов
    #[account(mut)]
    pub owner: Signer<'info>,

    /// Системные программы
    pub token_program: Program<'info, Token>,
}

/// Контексты для продления блокировки
#[derive(Accounts)]
pub struct ExtendLock<'info> {
    /// Информация о блокировке LP токенов
    #[account(
        mut,
        seeds = [LpTokenLock::SEED.as_bytes(), lp_mint.key().as_ref(), owner.key().as_ref()],
        bump = lp_lock.bump,
        constraint = lp_lock.owner == owner.key() @ ErrorCode::Unauthorized,
        constraint = lp_lock.is_locked @ ErrorCode::AlreadyUnlocked,
    )]
    pub lp_lock: Account<'info, LpTokenLock>,

    /// Mint LP токенов
    pub lp_mint: Account<'info, Mint>,

    /// Владелец LP токенов
    pub owner: Signer<'info>,
}

/// Блокировка LP токенов с таймлоком
pub fn lock_lp_tokens(
    ctx: Context<LockLpTokens>,
    lp_amount: u64,
    lock_duration: i64,
    enable_vesting: bool,
) -> Result<()> {
    msg!("🔒 Блокировка LP токенов...");
    msg!("   💰 Количество: {}", lp_amount);
    msg!("   ⏱️ Длительность: {} дней", lock_duration / 86_400);
    msg!("   📊 Vesting: {}", if enable_vesting { "Включен" } else { "Выключен" });

    let clock = Clock::get()?;

    // === ВАЛИДАЦИЯ ===

    require!(lp_amount > 0, ErrorCode::InvalidAmount);
    require!(
        lock_duration >= MIN_LOCK_DURATION,
        ErrorCode::LockDurationTooShort
    );
    require!(
        lock_duration <= MAX_LOCK_DURATION,
        ErrorCode::LockDurationTooLong
    );

    // === ПЕРЕВОД LP ТОКЕНОВ В ХРАНИЛИЩЕ ===

    msg!("📦 Перевод LP токенов в защищенное хранилище...");

    token::transfer(
        CpiContext::new(
            ctx.accounts.token_program.to_account_info(),
            Transfer {
                from: ctx.accounts.owner_lp_account.to_account_info(),
                to: ctx.accounts.lp_vault.to_account_info(),
                authority: ctx.accounts.owner.to_account_info(),
            },
        ),
        lp_amount,
    )?;

    // === ИНИЦИАЛИЗАЦИЯ БЛОКИРОВКИ ===

    let lp_lock = &mut ctx.accounts.lp_lock;
    lp_lock.owner = ctx.accounts.owner.key();
    lp_lock.lp_mint = ctx.accounts.lp_mint.key();
    lp_lock.token_mint = ctx.accounts.token_mint.key();
    lp_lock.lp_vault = ctx.accounts.lp_vault.key();
    lp_lock.locked_amount = lp_amount;
    lp_lock.unlocked_amount = 0;
    lp_lock.lock_start = clock.unix_timestamp;
    lp_lock.lock_end = clock.unix_timestamp
        .checked_add(lock_duration)
        .ok_or(ErrorCode::MathOverflow)?;
    lp_lock.is_locked = true;
    lp_lock.vesting_enabled = enable_vesting;
    lp_lock.last_unlock_time = clock.unix_timestamp;
    lp_lock.bump = ctx.bumps.lp_lock;

    // === СОБЫТИЕ БЛОКИРОВКИ ===

    emit!(LpTokensLockedEvent {
        owner: ctx.accounts.owner.key(),
        lp_mint: ctx.accounts.lp_mint.key(),
        token_mint: ctx.accounts.token_mint.key(),
        locked_amount: lp_amount,
        lock_start: lp_lock.lock_start,
        lock_end: lp_lock.lock_end,
        vesting_enabled: enable_vesting,
        timestamp: clock.unix_timestamp,
    });

    msg!("✅ LP токены успешно заблокированы!");
    msg!("   🔐 Vault: {}", ctx.accounts.lp_vault.key());
    msg!("   📅 Разблокировка: {} (Unix timestamp)", lp_lock.lock_end);

    let unlock_date_days = lock_duration / 86_400;
    msg!("   ⏰ Через {} дней", unlock_date_days);

    Ok(())
}

/// Разблокировка LP токенов после истечения срока
pub fn unlock_lp_tokens(ctx: Context<UnlockLpTokens>, amount: u64) -> Result<()> {
    msg!("🔓 Разблокировка LP токенов...");
    msg!("   💰 Запрошено: {}", amount);

    let clock = Clock::get()?;
    let lp_lock = &mut ctx.accounts.lp_lock;

    // === ВАЛИДАЦИЯ ===

    require!(amount > 0, ErrorCode::InvalidAmount);

    // Проверка что срок блокировки истек
    let current_time = clock.unix_timestamp;

    // === РАСЧЕТ ДОСТУПНОГО КОЛИЧЕСТВА ===

    let available_amount = if lp_lock.vesting_enabled {
        // Vesting: постепенная разблокировка
        calculate_vested_amount(lp_lock, current_time)?
    } else {
        // Без vesting: разблокировка только после полного истечения срока
        require!(
            current_time >= lp_lock.lock_end,
            ErrorCode::LockPeriodNotExpired
        );
        lp_lock.locked_amount
    };

    msg!("   ✅ Доступно для разблокировки: {}", available_amount);

    require!(amount <= available_amount, ErrorCode::InsufficientBalance);

    // === ПЕРЕВОД LP ТОКЕНОВ ВЛАДЕЛЬЦУ ===

    msg!("📤 Перевод LP токенов владельцу...");

    let lp_mint_key = ctx.accounts.lp_mint.key();
    let owner_key = ctx.accounts.owner.key();
    let vault_seeds = &[
        b"lp_vault",
        lp_mint_key.as_ref(),
        owner_key.as_ref(),
        &[ctx.bumps.lp_vault],
    ];
    let vault_signer = &[&vault_seeds[..]];

    token::transfer(
        CpiContext::new_with_signer(
            ctx.accounts.token_program.to_account_info(),
            Transfer {
                from: ctx.accounts.lp_vault.to_account_info(),
                to: ctx.accounts.destination_lp_account.to_account_info(),
                authority: ctx.accounts.lp_vault.to_account_info(),
            },
            vault_signer,
        ),
        amount,
    )?;

    // === ОБНОВЛЕНИЕ СОСТОЯНИЯ ===

    lp_lock.locked_amount = lp_lock.locked_amount
        .checked_sub(amount)
        .ok_or(ErrorCode::MathOverflow)?;

    lp_lock.unlocked_amount = lp_lock.unlocked_amount
        .checked_add(amount)
        .ok_or(ErrorCode::MathOverflow)?;

    lp_lock.last_unlock_time = current_time;

    // Если разблокировали все токены
    if lp_lock.locked_amount == 0 {
        lp_lock.is_locked = false;
        msg!("🎉 Все LP токены разблокированы!");
    }

    // === СОБЫТИЕ РАЗБЛОКИРОВКИ ===

    emit!(LpTokensUnlockedEvent {
        owner: ctx.accounts.owner.key(),
        lp_mint: ctx.accounts.lp_mint.key(),
        unlocked_amount: amount,
        remaining_locked: lp_lock.locked_amount,
        timestamp: current_time,
    });

    msg!("✅ Разблокировка завершена!");
    msg!("   📊 Осталось заблокировано: {}", lp_lock.locked_amount);

    Ok(())
}

/// Продление срока блокировки
pub fn extend_lock(ctx: Context<ExtendLock>, additional_duration: i64) -> Result<()> {
    msg!("⏱️ Продление блокировки LP токенов...");
    msg!("   ➕ Дополнительное время: {} дней", additional_duration / 86_400);

    let clock = Clock::get()?;
    let lp_lock = &mut ctx.accounts.lp_lock;

    // === ВАЛИДАЦИЯ ===

    require!(
        additional_duration > 0,
        ErrorCode::InvalidLockDuration
    );

    let new_lock_end = lp_lock.lock_end
        .checked_add(additional_duration)
        .ok_or(ErrorCode::MathOverflow)?;

    // Проверка что новый срок не превышает максимум
    let total_duration = new_lock_end - lp_lock.lock_start;
    require!(
        total_duration <= MAX_LOCK_DURATION,
        ErrorCode::LockDurationTooLong
    );

    // === ОБНОВЛЕНИЕ СРОКА ===

    let old_lock_end = lp_lock.lock_end;
    lp_lock.lock_end = new_lock_end;

    // === СОБЫТИЕ ПРОДЛЕНИЯ ===

    emit!(LockExtendedEvent {
        owner: ctx.accounts.owner.key(),
        lp_mint: ctx.accounts.lp_mint.key(),
        old_lock_end,
        new_lock_end,
        additional_days: additional_duration / 86_400,
        timestamp: clock.unix_timestamp,
    });

    msg!("✅ Блокировка продлена!");
    msg!("   📅 Старый срок: {} (Unix timestamp)", old_lock_end);
    msg!("   📅 Новый срок: {} (Unix timestamp)", new_lock_end);

    Ok(())
}

// === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

/// Расчет количества токенов, доступных для разблокировки при vesting
fn calculate_vested_amount(lp_lock: &LpTokenLock, current_time: i64) -> Result<u64> {
    // Если еще не началась разблокировка
    if current_time < lp_lock.lock_start {
        return Ok(0);
    }

    // Если срок блокировки истек полностью
    if current_time >= lp_lock.lock_end {
        return Ok(lp_lock.locked_amount);
    }

    // Линейный vesting: unlockable = total * (time_passed / total_duration)
    let time_passed = current_time - lp_lock.lock_start;
    let total_duration = lp_lock.lock_end - lp_lock.lock_start;

    let initial_total = lp_lock.locked_amount
        .checked_add(lp_lock.unlocked_amount)
        .ok_or(ErrorCode::MathOverflow)?;

    let vested_amount = (initial_total as u128)
        .checked_mul(time_passed as u128)
        .ok_or(ErrorCode::MathOverflow)?
        .checked_div(total_duration as u128)
        .ok_or(ErrorCode::MathOverflow)? as u64;

    // Вычитаем уже разблокированное
    let available = vested_amount
        .checked_sub(lp_lock.unlocked_amount)
        .ok_or(ErrorCode::MathOverflow)?;

    Ok(available)
}

// === СОБЫТИЯ ===

/// Событие блокировки LP токенов
#[event]
pub struct LpTokensLockedEvent {
    pub owner: Pubkey,
    pub lp_mint: Pubkey,
    pub token_mint: Pubkey,
    pub locked_amount: u64,
    pub lock_start: i64,
    pub lock_end: i64,
    pub vesting_enabled: bool,
    pub timestamp: i64,
}

/// Событие разблокировки LP токенов
#[event]
pub struct LpTokensUnlockedEvent {
    pub owner: Pubkey,
    pub lp_mint: Pubkey,
    pub unlocked_amount: u64,
    pub remaining_locked: u64,
    pub timestamp: i64,
}

/// Событие продления блокировки
#[event]
pub struct LockExtendedEvent {
    pub owner: Pubkey,
    pub lp_mint: Pubkey,
    pub old_lock_end: i64,
    pub new_lock_end: i64,
    pub additional_days: i64,
    pub timestamp: i64,
}
