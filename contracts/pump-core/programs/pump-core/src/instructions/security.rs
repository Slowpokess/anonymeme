/*!
🛡️ Инструкции безопасности и защиты
Production-ready система защиты от мошенничества и управления рисками
*/

use anchor_lang::prelude::*;
use anchor_spl::token::Mint;
use crate::state::*;
use crate::errors::ErrorCode;

/// Контексты для обновления параметров безопасности
#[derive(Accounts)]
pub struct UpdateSecurity<'info> {
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

/// Обновление параметров безопасности платформы
pub fn update_security_params(
    ctx: Context<UpdateSecurity>,
    new_params: SecurityParams,
) -> Result<()> {
    msg!("🛡️ Обновление параметров безопасности администратором");

    let clock = Clock::get()?;
    let platform_config = &mut ctx.accounts.platform_config;

    // === ВАЛИДАЦИЯ НОВЫХ ПАРАМЕТРОВ ===

    // Проверка максимального размера сделки (не более 1000 SOL)
    require!(
        new_params.max_trade_size_sol > 0 && new_params.max_trade_size_sol <= 1000_000_000_000,
        ErrorCode::InvalidSecurityParams
    );

    // Проверка налога на китов (не более 50% = 5000 базисных пунктов)
    require!(
        new_params.whale_tax_bps <= 5000,
        ErrorCode::InvalidSecurityParams
    );

    // Проверка максимального slippage (не более 50%)
    require!(
        new_params.max_slippage_bps <= 5000,
        ErrorCode::InvalidSecurityParams
    );

    // Проверка порога для определения китов
    require!(
        new_params.whale_threshold_sol > 0 && new_params.whale_threshold_sol <= 100_000_000_000,
        ErrorCode::InvalidSecurityParams
    );

    // Проверка rate limiting (от 1 до 1000 запросов в минуту)
    require!(
        new_params.rate_limit_per_minute >= 1 && new_params.rate_limit_per_minute <= 1000,
        ErrorCode::InvalidSecurityParams
    );

    // Проверка cooldown периода (максимум 1 час)
    require!(
        new_params.cooldown_period_seconds <= 3600,
        ErrorCode::InvalidSecurityParams
    );

    // === СОХРАНЕНИЕ СТАРЫХ ПАРАМЕТРОВ ДЛЯ ЛОГИРОВАНИЯ ===
    
    let old_params = platform_config.security_params;
    
    // === ПРИМЕНЕНИЕ НОВЫХ ПАРАМЕТРОВ ===
    
    platform_config.security_params = new_params;
    platform_config.last_updated = clock.unix_timestamp;

    // === СОБЫТИЕ БЕЗОПАСНОСТИ ===
    
    emit!(SecurityUpdateEvent {
        admin: ctx.accounts.admin.key(),
        old_max_trade_size: old_params.max_trade_size_sol,
        new_max_trade_size: new_params.max_trade_size_sol,
        old_whale_tax: old_params.whale_tax_bps,
        new_whale_tax: new_params.whale_tax_bps,
        timestamp: clock.unix_timestamp,
    });

    // === ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ ИЗМЕНЕНИЙ ===
    
    msg!("✅ Параметры безопасности обновлены администратором: {}", ctx.accounts.admin.key());
    msg!("   Максимальный размер сделки: {} -> {} lamports", 
         old_params.max_trade_size_sol, 
         new_params.max_trade_size_sol);
    msg!("   Налог на китов: {} -> {} базисных пунктов", 
         old_params.whale_tax_bps, 
         new_params.whale_tax_bps);
    msg!("   Максимальный slippage: {} -> {} базисных пунктов", 
         old_params.max_slippage_bps, 
         new_params.max_slippage_bps);
    msg!("   Rate limiting: {} -> {} запросов/минуту", 
         old_params.rate_limit_per_minute, 
         new_params.rate_limit_per_minute);

    Ok(())
}

/// Контексты для экстренного управления платформой
#[derive(Accounts)]
pub struct EmergencyControl<'info> {
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

/// Экстренная пауза/возобновление работы платформы
pub fn emergency_pause_platform(
    ctx: Context<EmergencyControl>,
    pause: bool,
    reason: String,
) -> Result<()> {
    msg!("🚨 Экстренное управление платформой: {}", 
         if pause { "ПАУЗА" } else { "ВОЗОБНОВЛЕНИЕ" });

    let clock = Clock::get()?;
    let platform_config = &mut ctx.accounts.platform_config;
    let old_state = platform_config.emergency_paused;

    // Проверка валидности причины
    require!(
        reason.len() >= 10 && reason.len() <= 500,
        ErrorCode::InvalidInput
    );

    // Проверка что состояние действительно меняется
    require!(
        old_state != pause,
        ErrorCode::NoStateChange
    );

    // === ОБНОВЛЕНИЕ СОСТОЯНИЯ ===
    
    platform_config.emergency_paused = pause;
    platform_config.last_updated = clock.unix_timestamp;

    // === СОБЫТИЯ БЕЗОПАСНОСТИ ===
    
    emit!(EmergencyActionEvent {
        admin: ctx.accounts.admin.key(),
        action_type: if pause { 
            EmergencyActionType::EmergencyPause 
        } else { 
            EmergencyActionType::EmergencyUnpause 
        },
        target: platform_config.key(),
        reason: reason.clone(),
        timestamp: clock.unix_timestamp,
    });

    // === ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ ===
    
    if pause {
        msg!("🔴 ПЛАТФОРМА ПРИОСТАНОВЛЕНА");
        msg!("   Администратор: {}", ctx.accounts.admin.key());
        msg!("   Причина: {}", reason);
        msg!("   Все торговые операции заблокированы");
    } else {
        msg!("🟢 ПЛАТФОРМА ВОЗОБНОВЛЕНА");
        msg!("   Администратор: {}", ctx.accounts.admin.key());
        msg!("   Причина: {}", reason);
        msg!("   Торговые операции восстановлены");
    }

    Ok(())
}

/// Приостановка торговли (не полная пауза платформы)
pub fn pause_trading_only(
    ctx: Context<EmergencyControl>,
    pause: bool,
    reason: String,
) -> Result<()> {
    msg!("⏸️ Управление торговлей: {}", 
         if pause { "ПАУЗА" } else { "ВОЗОБНОВЛЕНИЕ" });

    let clock = Clock::get()?;
    let platform_config = &mut ctx.accounts.platform_config;

    // Валидация причины
    require!(
        reason.len() >= 5 && reason.len() <= 200,
        ErrorCode::InvalidInput
    );

    platform_config.trading_paused = pause;
    platform_config.last_updated = clock.unix_timestamp;

    emit!(TradingStatusEvent {
        admin: ctx.accounts.admin.key(),
        trading_paused: pause,
        reason: reason.clone(),
        timestamp: clock.unix_timestamp,
    });

    msg!("🔄 Торговля {}: {}", 
         if pause { "приостановлена" } else { "возобновлена" },
         reason);

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
        constraint = platform_config.admin == admin.key() @ ErrorCode::AdminOnly
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    #[account(mut)]
    pub admin: Signer<'info>,
}

/// Обновление репутации пользователя администратором
pub fn update_user_reputation(
    ctx: Context<UpdateUserReputation>,
    reputation_delta: i32,
    reason: String,
) -> Result<()> {
    msg!("🔄 Обновление репутации пользователя администратором");

    let clock = Clock::get()?;
    let user_profile = &mut ctx.accounts.user_profile;
    let old_reputation = user_profile.reputation_score;

    // === ВАЛИДАЦИЯ ПАРАМЕТРОВ ===
    
    require!(
        reason.len() >= 5 && reason.len() <= 200,
        ErrorCode::InvalidInput
    );

    require!(
        reputation_delta.abs() <= 50, // Максимальное изменение за раз
        ErrorCode::InvalidInput
    );

    // === ПРИМЕНЕНИЕ ИЗМЕНЕНИЯ РЕПУТАЦИИ ===

    let new_reputation = if reputation_delta > 0 {
        (user_profile.reputation_score + reputation_delta as f64).min(100.0)
    } else {
        (user_profile.reputation_score + reputation_delta as f64).max(0.0)
    };

    user_profile.reputation_score = new_reputation;
    user_profile.last_reputation_update = clock.unix_timestamp;

    // === ПРОВЕРКА АВТОМАТИЧЕСКОЙ БЛОКИРОВКИ ===
    
    if user_profile.reputation_score < 10.0 && !user_profile.banned {
        user_profile.banned = true;
        user_profile.ban_reason = format!("Автоматическая блокировка: репутация слишком низкая ({})", user_profile.reputation_score);
        user_profile.banned_at = Some(clock.unix_timestamp);
        
        msg!("🚫 Пользователь автоматически заблокирован из-за низкой репутации");
    } else if user_profile.reputation_score >= 10.0 && user_profile.banned && user_profile.ban_reason.contains("репутация слишком низкая") {
        // Автоматическая разблокировка если репутация восстановилась
        user_profile.banned = false;
        user_profile.ban_reason = String::new();
        user_profile.banned_at = None;
        
        msg!("✅ Пользователь автоматически разблокирован: репутация восстановлена");
    }

    // === СОБЫТИЕ ОБНОВЛЕНИЯ РЕПУТАЦИИ ===
    
    emit!(ReputationUpdatedEvent {
        user: ctx.accounts.user.key(),
        admin: ctx.accounts.admin.key(),
        old_reputation,
        new_reputation,
        delta: reputation_delta,
        reason: reason.clone(),
        auto_banned: user_profile.banned && user_profile.ban_reason.contains("репутация"),
        timestamp: clock.unix_timestamp,
    });

    msg!("✅ Репутация пользователя {} обновлена: {} -> {} (изменение: {})",
         ctx.accounts.user.key(),
         old_reputation,
         new_reputation,
         reputation_delta);
    msg!("   Причина: {}", reason);

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

/// Подача жалобы на подозрительную активность пользователя
pub fn report_suspicious_activity(
    ctx: Context<ReportActivity>,
    reported_user: Pubkey,
    reason: ReportReason,
    description: String,
) -> Result<()> {
    msg!("🚨 Подача жалобы на подозрительную активность");

    // === ВАЛИДАЦИЯ ПАРАМЕТРОВ ===
    
    require!(
        description.len() >= 10 && description.len() <= 500, 
        ErrorCode::InvalidInput
    );
    
    require!(
        ctx.accounts.reporter.key() != reported_user, 
        ErrorCode::InvalidAccount
    );

    let clock = Clock::get()?;
    let report = &mut ctx.accounts.report;

    // === ЗАПОЛНЕНИЕ ОТЧЕТА ===
    
    report.reporter = ctx.accounts.reporter.key();
    report.reported_user = reported_user;
    report.reason = reason.clone();
    report.description = description.clone();
    report.evidence_uri = String::new(); // Может быть добавлено позже
    report.created_at = clock.unix_timestamp;
    report.reviewed = false;
    report.reviewer = Pubkey::default();
    report.action_taken = String::new();
    report.bump = ctx.bumps.report;

    // === ВЫЧИСЛЕНИЕ УРОВНЯ РИСКА ===
    
    let risk_score = calculate_risk_score(&reason);
    let is_high_risk = risk_score >= 80.0;

    // === АВТОМАТИЧЕСКАЯ ОБРАБОТКА ДЛЯ ВЫСОКОГО РИСКА ===
    
    if is_high_risk {
        report.auto_flagged = true;
        msg!("⚠️ ВЫСОКИЙ РИСК: Автоматическая отметка для проверки модераторами");
    }

    // === СОБЫТИЕ ПОДОЗРИТЕЛЬНОЙ АКТИВНОСТИ ===
    
    emit!(SuspiciousActivityDetected {
        user: reported_user,
        reporter: ctx.accounts.reporter.key(),
        activity_type: format!("{:?}", reason),
        risk_score,
        auto_flagged: is_high_risk,
        description: description.clone(),
        timestamp: clock.unix_timestamp,
    });

    msg!("✅ Жалоба подана: {} сообщил о {} по причине {:?}",
         ctx.accounts.reporter.key(),
         reported_user,
         reason);
    msg!("   Уровень риска: {}/100", risk_score);
    msg!("   Описание: {}", description);

    Ok(())
}

/// Вспомогательная функция расчета уровня риска на основе причины жалобы
fn calculate_risk_score(reason: &ReportReason) -> f64 {
    match reason {
        ReportReason::RugPull => 95.0,           // Критический риск
        ReportReason::Scam => 90.0,              // Очень высокий риск  
        ReportReason::MarketManipulation => 85.0, // Высокий риск
        ReportReason::Impersonation => 75.0,     // Средне-высокий риск
        ReportReason::FakeMetadata => 70.0,      // Средний риск
        ReportReason::Spam => 40.0,              // Низкий риск
        ReportReason::Other => 50.0,             // Базовый риск
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

// === СОБЫТИЯ БЕЗОПАСНОСТИ ===

/// Событие обновления репутации пользователя
#[event]
pub struct ReputationUpdatedEvent {
    /// Пользователь, чья репутация изменена
    pub user: Pubkey,
    /// Администратор, выполнивший изменение
    pub admin: Pubkey,
    /// Старое значение репутации
    pub old_reputation: f64,
    /// Новое значение репутации
    pub new_reputation: f64,
    /// Изменение репутации
    pub delta: i32,
    /// Причина изменения
    pub reason: String,
    /// Автоматически заблокирован
    pub auto_banned: bool,
    /// Временная метка
    pub timestamp: i64,
}

/// Событие обнаружения подозрительной активности
#[event]
pub struct SuspiciousActivityDetected {
    /// Пользователь, на которого подается жалоба
    pub user: Pubkey,
    /// Пользователь, подающий жалобу
    pub reporter: Pubkey,
    /// Тип активности
    pub activity_type: String,
    /// Уровень риска (0-100)
    pub risk_score: f64,
    /// Автоматически отмечено для проверки
    pub auto_flagged: bool,
    /// Описание проблемы
    pub description: String,
    /// Временная метка
    pub timestamp: i64,
}