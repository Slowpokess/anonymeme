use anchor_lang::prelude::*;

pub mod state;
pub mod instructions;
pub mod errors;
pub mod utils;

use crate::instructions::*;
use crate::state::*;
use crate::errors::CustomError;

declare_id!("7wUQXRQtBzTmyp9kcrmok9FKcc4RSYXxPYN9FGDLnqxb");

#[program]
pub mod pump_core {
    use super::*;

    /// 🎯 Initialize the platform with admin and configuration
    pub fn initialize_platform(
        ctx: Context<InitializePlatform>, 
        fee_rate: f64,
        treasury: Pubkey,
        security_params: SecurityParams,
    ) -> Result<()> {
        instructions::initialize_platform(ctx, fee_rate, treasury, security_params)
    }

    /// 🏭 Create a new token with bonding curve
    pub fn create_token(
        ctx: Context<CreateToken>,
        name: String,
        symbol: String,
        uri: String,
        bonding_curve_params: BondingCurveParams,
    ) -> Result<()> {
        instructions::create_token(ctx, name, symbol, uri, bonding_curve_params)
    }

    /// 💰 Buy tokens using SOL (follows bonding curve)
    pub fn buy_tokens(
        ctx: Context<TradeTokens>,
        sol_amount: u64,
        min_tokens_out: u64,
        slippage_tolerance: u16, // In basis points (100 = 1%)
    ) -> Result<()> {
        instructions::buy_tokens(ctx, sol_amount, min_tokens_out, slippage_tolerance)
    }

    /// 💸 Sell tokens for SOL (follows bonding curve)
    pub fn sell_tokens(
        ctx: Context<TradeTokens>,
        token_amount: u64,
        min_sol_out: u64,
        slippage_tolerance: u16,
    ) -> Result<()> {
        instructions::sell_tokens(ctx, token_amount, min_sol_out, slippage_tolerance)
    }

    /// 📊 Automatically list token on DEX when curve is completed
    pub fn graduate_to_dex(
        ctx: Context<GraduateToDex>,
        dex_type: DexType,
        initial_liquidity: u64,
    ) -> Result<()> {
        instructions::graduate_to_dex(ctx, dex_type, initial_liquidity)
    }

    /// 🛡️ Update security parameters (admin only)
    pub fn update_security_params(
        ctx: Context<UpdateSecurity>,
        new_params: SecurityParams,
    ) -> Result<()> {
        instructions::update_security_params(ctx, new_params)
    }

    /// ⏸️ Emergency pause/unpause trading (admin only)
    pub fn toggle_emergency_pause(
        ctx: Context<EmergencyControl>,
        pause: bool,
    ) -> Result<()> {
        instructions::toggle_emergency_pause(ctx, pause)
    }

    /// 📈 Get current token price from bonding curve
    pub fn get_token_price(
        ctx: Context<ViewTokenInfo>,
    ) -> Result<u64> {
        instructions::get_token_price(ctx)
    }

    /// 🔄 Update user reputation based on trading behavior
    pub fn update_user_reputation(
        ctx: Context<UpdateUserReputation>,
        reputation_delta: i32,
    ) -> Result<()> {
        instructions::update_user_reputation(ctx, reputation_delta)
    }

    /// 🚨 Report suspicious activity (community moderation)
    pub fn report_suspicious_activity(
        ctx: Context<ReportActivity>,
        reported_user: Pubkey,
        reason: ReportReason,
        description: String,
    ) -> Result<()> {
        instructions::report_suspicious_activity(ctx, reported_user, reason, description)
    }
}
