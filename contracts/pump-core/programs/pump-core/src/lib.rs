use anchor_lang::prelude::*;

pub mod state;
pub mod instructions;
pub mod errors;
pub mod utils;

use crate::instructions::*;
use crate::state::*;

declare_id!("7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb");

#[program]
pub mod pump_core {
    use super::*;

    /// 🎯 Инициализация платформы с администратором и конфигурацией
    pub fn initialize_platform(
        ctx: Context<InitializePlatform>,
        fee_rate: u16, // В базисных пунктах (10000 = 100%)
        treasury: Pubkey,
        security_params: SecurityParams,
    ) -> Result<()> {
        instructions::initialize_platform(ctx, fee_rate, treasury, security_params)
    }

    /// 🏭 Создание нового токена с бондинг-кривой
    pub fn create_token(
        ctx: Context<CreateToken>,
        params: crate::instructions::create_token::CreateTokenParams,
    ) -> Result<()> {
        instructions::create_token(ctx, params)
    }

    /// 💰 Покупка токенов за SOL (следует бондинг-кривой)
    pub fn buy_tokens(
        ctx: Context<BuyTokens>,
        sol_amount: u64,
        min_tokens_out: u64,
        slippage_tolerance: u16, // В базисных пунктах (100 = 1%)
    ) -> Result<()> {
        instructions::buy_tokens(ctx, sol_amount, min_tokens_out, slippage_tolerance)
    }

    /// 💸 Продажа токенов за SOL (следует бондинг-кривой)
    pub fn sell_tokens(
        ctx: Context<SellTokens>,
        token_amount: u64,
        min_sol_out: u64,
        slippage_tolerance: u16,
    ) -> Result<()> {
        instructions::sell_tokens(ctx, token_amount, min_sol_out, slippage_tolerance)
    }

    /// 📊 Автоматический листинг токена на DEX при завершении кривой
    pub fn graduate_to_dex(
        ctx: Context<GraduateToDex>,
        dex_type: DexType,
        minimum_liquidity_sol: u64,
    ) -> Result<()> {
        instructions::graduate_to_dex(ctx, dex_type, minimum_liquidity_sol)
    }

    /// 🛡️ Обновление параметров безопасности (только админ)
    pub fn update_security_params(
        ctx: Context<UpdateSecurity>,
        new_params: SecurityParams,
    ) -> Result<()> {
        instructions::update_security_params(ctx, new_params)
    }

    /// ⏸️ Экстренная пауза/возобновление торговли (только админ)
    pub fn emergency_pause_platform(
        ctx: Context<EmergencyControl>,
        pause: bool,
        reason: String,
    ) -> Result<()> {
        instructions::emergency_pause_platform(ctx, pause, reason)
    }

    /// 📈 Получение текущей цены токена из бондинг-кривой
    pub fn get_token_price(
        ctx: Context<ViewTokenInfo>,
    ) -> Result<u64> {
        instructions::get_token_price(ctx)
    }

    /// 🔄 Обновление репутации пользователя на основе торгового поведения
    pub fn update_user_reputation(
        ctx: Context<UpdateUserReputation>,
        reputation_delta: i32,
        reason: String,
    ) -> Result<()> {
        instructions::update_user_reputation(ctx, reputation_delta, reason)
    }

    /// 🚨 Сообщение о подозрительной активности (модерация сообщества)
    pub fn report_suspicious_activity(
        ctx: Context<ReportActivity>,
        reported_user: Pubkey,
        reason: ReportReason,
        description: String,
    ) -> Result<()> {
        instructions::report_suspicious_activity(ctx, reported_user, reason, description)
    }

    /// 💼 Обновление комиссии платформы (только админ)
    pub fn update_platform_fee(
        ctx: Context<UpdatePlatformConfig>,
        new_fee_rate: u16, // В базисных пунктах (10000 = 100%)
        reason: String,
    ) -> Result<()> {
        instructions::update_platform_fee(ctx, new_fee_rate, reason)
    }

    /// 🏦 Обновление адреса казны (только админ)
    pub fn update_treasury(
        ctx: Context<UpdatePlatformConfig>,
        new_treasury: Pubkey,
        reason: String,
    ) -> Result<()> {
        instructions::update_treasury(ctx, new_treasury, reason)
    }

    /// 👑 Передача прав администратора (только текущий админ)
    pub fn transfer_admin(
        ctx: Context<TransferAdmin>,
        reason: String,
    ) -> Result<()> {
        instructions::transfer_admin(ctx, reason)
    }

    // === LP TOKEN LOCK МЕХАНИЗМ ===

    /// 🔒 Блокировка LP токенов с таймлоком для защиты от rug pulls
    pub fn lock_lp_tokens(
        ctx: Context<LockLpTokens>,
        lp_amount: u64,
        lock_duration: i64,
        enable_vesting: bool,
    ) -> Result<()> {
        instructions::lock_lp_tokens(ctx, lp_amount, lock_duration, enable_vesting)
    }

    /// 🔓 Разблокировка LP токенов после истечения срока блокировки
    pub fn unlock_lp_tokens(
        ctx: Context<UnlockLpTokens>,
        amount: u64,
    ) -> Result<()> {
        instructions::unlock_lp_tokens(ctx, amount)
    }

    /// ⏱️ Продление срока блокировки LP токенов
    pub fn extend_lock(
        ctx: Context<ExtendLock>,
        additional_duration: i64,
    ) -> Result<()> {
        instructions::extend_lock(ctx, additional_duration)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_program_id() {
        let expected_id = "7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb";
        assert_eq!(id().to_string(), expected_id);
    }
}