// contracts/pump-core/programs/pump-core/src/instructions/trade.rs

use anchor_lang::prelude::*;
use anchor_spl::{
    token::{self, Token, TokenAccount, Transfer, Mint},
    associated_token::AssociatedToken,
};
use crate::state::*;
use crate::errors::CustomError;
use crate::utils::bonding_curve::*;

#[derive(Accounts)]
pub struct TradeTokens<'info> {
    #[account(
        mut,
        seeds = [TokenInfo::SEED_PREFIX.as_bytes(), mint.key().as_ref()],
        bump = token_info.bump
    )]
    pub token_info: Account<'info, TokenInfo>,

    #[account(address = token_info.mint)]
    pub mint: Account<'info, Mint>,

    /// CHECK: Bonding curve vault that holds SOL
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
        init_if_needed,
        payer = trader,
        associated_token::mint = mint,
        associated_token::authority = trader,
    )]
    pub trader_token_account: Account<'info, TokenAccount>,

    #[account(
        init_if_needed,
        payer = trader,
        space = UserProfile::ACCOUNT_SIZE,
        seeds = [UserProfile::SEED_PREFIX.as_bytes(), trader.key().as_ref()],
        bump
    )]
    pub trader_profile: Account<'info, UserProfile>,

    #[account(
        mut,
        seeds = [PlatformConfig::SEED.as_bytes()],
        bump = platform_config.bump
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    /// CHECK: Platform treasury for fees
    #[account(
        mut,
        address = platform_config.treasury
    )]
    pub treasury: AccountInfo<'info>,

    #[account(mut)]
    pub trader: Signer<'info>,

    pub token_program: Program<'info, Token>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

pub fn buy_tokens(
    ctx: Context<TradeTokens>,
    sol_amount: u64,
    min_tokens_out: u64,
    slippage_tolerance: u16, // In basis points (100 = 1%)
) -> Result<()> {
    let clock = Clock::get()?;
    
    // Validations
    require!(!ctx.accounts.platform_config.paused, CustomError::PlatformPaused);
    require!(!ctx.accounts.platform_config.trading_locked, CustomError::PlatformPaused); // Reentrancy protection
    require!(!ctx.accounts.token_info.graduated, CustomError::TokenAlreadyGraduated);
    require!(sol_amount > 0, CustomError::InvalidAmount);
    require!(slippage_tolerance <= 10000, CustomError::InvalidSlippage); // Max 100%
    
    // Lock trading to prevent reentrancy
    ctx.accounts.platform_config.trading_locked = true;

    // Security checks
    let security_params = &ctx.accounts.platform_config.security_params;
    require!(
        sol_amount <= security_params.max_trade_size,
        CustomError::TradeSizeExceeded
    );

    // Anti-bot protection: check minimum time between trades
    let trader_profile = &mut ctx.accounts.trader_profile;
    if trader_profile.last_trade_time > 0 {
        let time_since_last_trade = clock.unix_timestamp - trader_profile.last_trade_time;
        require!(
            time_since_last_trade >= 1, // 1 second minimum
            CustomError::TradingTooFast
        );
    }

    // Calculate platform fee
    let platform_fee = (sol_amount as f64 * ctx.accounts.platform_config.fee_rate / 100.0) as u64;
    let sol_amount_after_fee = sol_amount.saturating_sub(platform_fee);

    // Calculate tokens to receive based on bonding curve
    let token_info = &mut ctx.accounts.token_info;
    
    // Кэшируем часто используемые значения
    let current_sol_reserves = token_info.sol_reserves;
    let current_token_reserves = token_info.token_reserves;
    let curve = &token_info.bonding_curve;
    
    let tokens_to_receive = calculate_buy_amount(
        curve,
        current_sol_reserves,
        current_token_reserves,
        sol_amount_after_fee,
    )?;

    // Проверяем slippage и ликвидность
    require!(tokens_to_receive >= min_tokens_out, CustomError::SlippageExceeded);
    require!(tokens_to_receive <= current_token_reserves, CustomError::InsufficientLiquidity);

    // Предвычисляем новые резервы для использования в нескольких местах
    let new_sol_reserves = current_sol_reserves.saturating_add(sol_amount_after_fee);
    let new_token_reserves = current_token_reserves.saturating_sub(tokens_to_receive);
    let new_price = calculate_current_price(curve, new_sol_reserves, new_token_reserves)?;

    // Оптимизированное вычисление price impact
    let current_price = curve.current_price;
    let price_impact = if current_price > 0 {
        // Используем целочисленную арифметику где возможно
        let price_diff = if new_price > current_price {
            new_price - current_price
        } else {
            current_price - new_price
        };
        (price_diff as f64) / (current_price as f64)
    } else {
        0.0
    };

    if price_impact > security_params.circuit_breaker_threshold {
        // Apply whale tax
        let whale_tax = (sol_amount_after_fee as f64 * security_params.whale_tax_rate) as u64;
        let final_sol_amount = sol_amount_after_fee.saturating_sub(whale_tax);
        
        // Recalculate with reduced amount
        let _tokens_to_receive = calculate_buy_amount(
            &token_info.bonding_curve,
            token_info.sol_reserves,
            token_info.token_reserves,
            final_sol_amount,
        )?;

        // Transfer whale tax to treasury
        if whale_tax > 0 {
            transfer_sol_to_treasury(
                &ctx.accounts.trader.to_account_info(),
                &ctx.accounts.treasury,
                whale_tax,
                &ctx.accounts.system_program,
            )?;
        }
    }

    // Transfer SOL from trader to bonding curve vault
    transfer_sol_from_user(
        &ctx.accounts.trader.to_account_info(),
        &ctx.accounts.bonding_curve_vault,
        sol_amount_after_fee,
        &ctx.accounts.system_program,
    )?;

    // Transfer platform fee to treasury
    if platform_fee > 0 {
        transfer_sol_to_treasury(
            &ctx.accounts.trader.to_account_info(),
            &ctx.accounts.treasury,
            platform_fee,
            &ctx.accounts.system_program,
        )?;
    }

    // Transfer tokens from bonding curve to trader
    let vault_bump = ctx.bumps.bonding_curve_vault;
    let mint_key = ctx.accounts.mint.key();
    let vault_seeds = &[
        b"bonding_curve_vault",
        mint_key.as_ref(),
        &[vault_bump],
    ];
    let vault_signer = &[&vault_seeds[..]];

    let transfer_ctx = CpiContext::new(
        ctx.accounts.token_program.to_account_info(),
        Transfer {
            from: ctx.accounts.bonding_curve_token_account.to_account_info(),
            to: ctx.accounts.trader_token_account.to_account_info(),
            authority: ctx.accounts.bonding_curve_vault.to_account_info(),
        },
    );

    token::transfer(transfer_ctx.with_signer(vault_signer), tokens_to_receive)?;

    // Update token info
    token_info.sol_reserves = new_sol_reserves;
    token_info.token_reserves = new_token_reserves;
    token_info.bonding_curve.current_price = new_price;
    token_info.last_trade_at = clock.unix_timestamp;
    token_info.trade_count = token_info.trade_count.saturating_add(1);
    // Оптимизированное вычисление market cap с переиспользованием new_price
    let circulating_supply = token_info.total_supply.saturating_sub(new_token_reserves);
    token_info.current_market_cap = if circulating_supply > 0 {
        // Используем уже вычисленную цену вместо пересчета
        ((new_price as u128 * circulating_supply as u128) / 1_000_000_000).min(u64::MAX as u128) as u64
    } else {
        0
    };

    // Check if token should graduate to DEX
    if token_info.current_market_cap >= token_info.bonding_curve.graduation_threshold {
        token_info.graduation_eligible = true;
    }

    // Update trader profile
    if trader_profile.user == Pubkey::default() {
        trader_profile.user = ctx.accounts.trader.key();
        trader_profile.reputation_score = 50.0; // Starting reputation
        trader_profile.bump = ctx.bumps.trader_profile;
    }
    
    trader_profile.total_volume_traded = trader_profile.total_volume_traded.saturating_add(sol_amount);
    trader_profile.last_trade_time = clock.unix_timestamp;

    // Update platform stats
    ctx.accounts.platform_config.total_volume = 
        ctx.accounts.platform_config.total_volume.saturating_add(sol_amount);

    // Unlock trading after successful completion
    ctx.accounts.platform_config.trading_locked = false;

    // Emit event
    emit!(TokenTraded {
        token: ctx.accounts.mint.key(),
        trader: ctx.accounts.trader.key(),
        is_buy: true,
        sol_amount,
        token_amount: tokens_to_receive,
        new_price,
        new_market_cap: token_info.current_market_cap,
        price_impact,
        timestamp: clock.unix_timestamp,
    });

    msg!(
        "Buy executed: {} SOL -> {} tokens, New price: {}, Market cap: {}",
        sol_amount,
        tokens_to_receive,
        new_price,
        token_info.current_market_cap
    );

    Ok(())
}

pub fn sell_tokens(
    ctx: Context<TradeTokens>,
    token_amount: u64,
    min_sol_out: u64,
    slippage_tolerance: u16,
) -> Result<()> {
    let clock = Clock::get()?;
    
    // Validations
    require!(!ctx.accounts.platform_config.paused, CustomError::PlatformPaused);
    require!(!ctx.accounts.platform_config.trading_locked, CustomError::PlatformPaused); // Reentrancy protection
    require!(!ctx.accounts.token_info.graduated, CustomError::TokenAlreadyGraduated);
    require!(token_amount > 0, CustomError::InvalidAmount);
    require!(slippage_tolerance <= 10000, CustomError::InvalidSlippage);
    
    // Lock trading to prevent reentrancy
    ctx.accounts.platform_config.trading_locked = true;

    // Check if trader has enough tokens
    require!(
        ctx.accounts.trader_token_account.amount >= token_amount,
        CustomError::InsufficientBalance
    );

    // Anti-dumping protection: check holding time
    let security_params = &ctx.accounts.platform_config.security_params;
    let trader_profile = &mut ctx.accounts.trader_profile;
    
    if trader_profile.last_trade_time > 0 {
        let holding_time = clock.unix_timestamp - trader_profile.last_trade_time;
        require!(
            holding_time >= security_params.min_hold_time,
            CustomError::MinHoldTimeNotMet
        );
    }

    // Calculate SOL to receive based on bonding curve
    let token_info = &mut ctx.accounts.token_info;
    let sol_to_receive = calculate_sell_amount(
        &token_info.bonding_curve,
        token_info.sol_reserves,
        token_info.token_reserves,
        token_amount,
    )?;

    // Calculate platform fee
    let platform_fee = (sol_to_receive as f64 * ctx.accounts.platform_config.fee_rate / 100.0) as u64;
    let sol_after_fee = sol_to_receive.saturating_sub(platform_fee);

    // Check slippage
    require!(
        sol_after_fee >= min_sol_out,
        CustomError::SlippageExceeded
    );

    // Check if vault has enough SOL
    require!(
        ctx.accounts.bonding_curve_vault.lamports() >= sol_to_receive,
        CustomError::InsufficientLiquidity
    );

    // Transfer tokens from trader to bonding curve
    let transfer_ctx = CpiContext::new(
        ctx.accounts.token_program.to_account_info(),
        Transfer {
            from: ctx.accounts.trader_token_account.to_account_info(),
            to: ctx.accounts.bonding_curve_token_account.to_account_info(),
            authority: ctx.accounts.trader.to_account_info(),
        },
    );

    token::transfer(transfer_ctx, token_amount)?;

    // Transfer SOL from vault to trader
    let vault_bump = ctx.bumps.bonding_curve_vault;
    let mint_key = ctx.accounts.mint.key();
    let vault_seeds = &[
        b"bonding_curve_vault",
        mint_key.as_ref(),
        &[vault_bump],
    ];

    transfer_sol_from_vault(
        &ctx.accounts.bonding_curve_vault,
        &ctx.accounts.trader.to_account_info(),
        sol_after_fee,
        &ctx.accounts.system_program,
        vault_seeds,
    )?;

    // Transfer platform fee to treasury
    if platform_fee > 0 {
        transfer_sol_from_vault(
            &ctx.accounts.bonding_curve_vault,
            &ctx.accounts.treasury,
            platform_fee,
            &ctx.accounts.system_program,
            vault_seeds,
        )?;
    }

    // Update reserves and price
    let new_sol_reserves = token_info.sol_reserves.saturating_sub(sol_to_receive);
    let new_token_reserves = token_info.token_reserves.saturating_add(token_amount);
    let new_price = calculate_current_price(
        &token_info.bonding_curve,
        new_sol_reserves,
        new_token_reserves,
    )?;

    // Calculate price impact for event
    let price_impact = if token_info.bonding_curve.current_price > 0 {
        ((token_info.bonding_curve.current_price as f64 - new_price as f64) / 
         token_info.bonding_curve.current_price as f64).abs()
    } else {
        0.0
    };

    // Update token info
    token_info.sol_reserves = new_sol_reserves;
    token_info.token_reserves = new_token_reserves;
    token_info.bonding_curve.current_price = new_price;
    token_info.last_trade_at = clock.unix_timestamp;
    token_info.trade_count = token_info.trade_count.saturating_add(1);
    token_info.current_market_cap = calculate_market_cap(
        &token_info.bonding_curve,
        new_sol_reserves,
        new_token_reserves,
        token_info.total_supply,
    )?;

    // Update trader profile
    trader_profile.total_volume_traded = trader_profile.total_volume_traded.saturating_add(sol_to_receive);
    trader_profile.last_trade_time = clock.unix_timestamp;

    // Update platform stats
    ctx.accounts.platform_config.total_volume = 
        ctx.accounts.platform_config.total_volume.saturating_add(sol_to_receive);

    // Unlock trading after successful completion
    ctx.accounts.platform_config.trading_locked = false;

    // Emit event
    emit!(TokenTraded {
        token: ctx.accounts.mint.key(),
        trader: ctx.accounts.trader.key(),
        is_buy: false,
        sol_amount: sol_to_receive,
        token_amount,
        new_price,
        new_market_cap: token_info.current_market_cap,
        price_impact,
        timestamp: clock.unix_timestamp,
    });

    msg!(
        "Sell executed: {} tokens -> {} SOL, New price: {}, Market cap: {}",
        token_amount,
        sol_to_receive,
        new_price,
        token_info.current_market_cap
    );

    Ok(())
}

// Helper functions for SOL transfers
fn transfer_sol_from_user<'a>(
    from: &AccountInfo<'a>,
    to: &AccountInfo<'a>,
    amount: u64,
    system_program: &Program<'a, System>,
) -> Result<()> {
    let transfer_instruction = anchor_lang::system_program::Transfer {
        from: from.to_account_info(),
        to: to.to_account_info(),
    };
    
    let cpi_ctx = CpiContext::new(system_program.to_account_info(), transfer_instruction);
    anchor_lang::system_program::transfer(cpi_ctx, amount)
}

fn transfer_sol_from_vault<'a>(
    from: &AccountInfo<'a>,
    to: &AccountInfo<'a>,
    amount: u64,
    system_program: &Program<'a, System>,
    vault_seeds: &[&[u8]],
) -> Result<()> {
    // Check vault has sufficient balance before transfer
    require!(
        from.lamports() >= amount,
        CustomError::InsufficientBalance
    );
    
    // Additional safety check
    require!(amount > 0, CustomError::InvalidAmount);
    
    let transfer_instruction = anchor_lang::system_program::Transfer {
        from: from.to_account_info(),
        to: to.to_account_info(),
    };
    
    let cpi_ctx = CpiContext::new(system_program.to_account_info(), transfer_instruction);
    anchor_lang::system_program::transfer(cpi_ctx.with_signer(&[vault_seeds]), amount)
}

fn transfer_sol_to_treasury<'a>(
    from: &AccountInfo<'a>,
    to: &AccountInfo<'a>,
    amount: u64,
    system_program: &Program<'a, System>,
) -> Result<()> {
    transfer_sol_from_user(from, to, amount, system_program)
}