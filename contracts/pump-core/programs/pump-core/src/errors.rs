// contracts/pump-core/programs/pump-core/src/errors.rs

use anchor_lang::prelude::*;

#[error_code]
pub enum CustomError {
    // === ОБЩИЕ ОШИБКИ (6000-6099) ===
    #[msg("Platform is currently paused")]
    PlatformPaused, // 6000

    #[msg("Invalid amount provided")]
    InvalidAmount, // 6001

    #[msg("Insufficient balance")]
    InsufficientBalance, // 6002

    #[msg("Insufficient liquidity")]
    InsufficientLiquidity, // 6003

    #[msg("Invalid fee rate")]
    InvalidFee, // 6004

    #[msg("Overflow or underflow occurred")]
    OverflowOrUnderflowOccurred, // 6005

    #[msg("Unauthorized access")]
    Unauthorized, // 6006

    #[msg("Invalid account provided")]
    InvalidAccount, // 6007

    #[msg("Account not initialized")]
    AccountNotInitialized, // 6008

    #[msg("Account already initialized")]
    AccountAlreadyInitialized, // 6009

    // === СОЗДАНИЕ ТОКЕНОВ (6100-6199) ===
    #[msg("Token name is too long (max 50 characters)")]
    NameTooLong, // 6100

    #[msg("Token symbol is too long (max 10 characters)")]
    SymbolTooLong, // 6101

    #[msg("Token URI is too long (max 200 characters)")]
    UriTooLong, // 6102

    #[msg("Token description is too long (max 500 characters)")]
    DescriptionTooLong, // 6103

    #[msg("Invalid bonding curve parameters")]
    InvalidBondingCurveParams, // 6104

    #[msg("Duplicate tokens are not allowed")]
    DuplicateTokenNotAllowed, // 6105

    #[msg("Token creation rate limit exceeded (spam protection)")]
    SpamProtection, // 6106

    #[msg("Insufficient reputation to create tokens")]
    InsufficientReputation, // 6107

    #[msg("Maximum tokens per creator exceeded")]
    MaxTokensPerCreatorExceeded, // 6108

    #[msg("Invalid initial supply")]
    InvalidInitialSupply, // 6109

    #[msg("Token symbol already exists")]
    SymbolAlreadyExists, // 6110

    #[msg("Creator is banned from creating tokens")]
    CreatorBanned, // 6111

    #[msg("Invalid metadata format")]
    InvalidMetadata, // 6112

    // === ТОРГОВЛЯ (6200-6299) ===
    #[msg("Trade size exceeds maximum allowed")]
    TradeSizeExceeded, // 6200

    #[msg("Slippage tolerance exceeded")]
    SlippageExceeded, // 6201

    #[msg("Invalid slippage tolerance (max 100%)")]
    InvalidSlippage, // 6202

    #[msg("Trading too fast - cooldown period not met")]
    TradingTooFast, // 6203

    #[msg("Minimum hold time not met")]
    MinHoldTimeNotMet, // 6204

    #[msg("Price impact too high")]
    PriceImpactTooHigh, // 6205

    #[msg("Daily volume limit exceeded")]
    DailyVolumeLimitExceeded, // 6206

    #[msg("Hourly trade limit exceeded")]
    HourlyTradeLimitExceeded, // 6207

    #[msg("Wallet holds too many tokens (whale protection)")]
    WhaleProtectionTriggered, // 6208

    #[msg("Circuit breaker triggered - trading temporarily halted")]
    CircuitBreakerTriggered, // 6209

    #[msg("Token is graduated - use DEX for trading")]
    TokenAlreadyGraduated, // 6210

    #[msg("Bot activity detected")]
    BotActivityDetected, // 6211

    #[msg("Honeypot token detected")]
    HoneypotDetected, // 6212

    #[msg("Market manipulation detected")]
    MarketManipulationDetected, // 6213

    #[msg("Insufficient SOL for transaction")]
    InsufficientSol, // 6214

    #[msg("Trade would exceed max wallet percentage")]
    MaxWalletPercentageExceeded, // 6215

    // === ЛИСТИНГ НА DEX (6300-6399) ===
    #[msg("Token not eligible for graduation")]
    NotEligibleForGraduation, // 6300

    #[msg("Market cap threshold not reached")]
    MarketCapThresholdNotReached, // 6301

    #[msg("Token already graduated to DEX")]
    AlreadyGraduated, // 6302

    #[msg("Invalid DEX type")]
    InvalidDexType, // 6303

    #[msg("Insufficient liquidity for DEX listing")]
    InsufficientLiquidityForDex, // 6304

    #[msg("DEX listing failed")]
    DexListingFailed, // 6305

    #[msg("Invalid pool parameters")]
    InvalidPoolParameters, // 6306

    #[msg("Liquidity lock period too short")]
    LiquidityLockTooShort, // 6307

    #[msg("Creator must provide minimum liquidity")]
    InsufficientCreatorLiquidity, // 6308

    #[msg("Graduation fee not paid")]
    GraduationFeeNotPaid, // 6309

    // === БЕЗОПАСНОСТЬ И АДМИНИСТРИРОВАНИЕ (6400-6499) ===
    #[msg("Only admin can perform this action")]
    AdminOnly, // 6400

    #[msg("User is banned")]
    UserBanned, // 6401

    #[msg("Token is flagged as suspicious")]
    TokenFlagged, // 6402

    #[msg("KYC required for this action")]
    KYCRequired, // 6403

    #[msg("Verification required")]
    VerificationRequired, // 6404

    #[msg("Security score too low")]
    SecurityScoreTooLow, // 6405

    #[msg("Suspicious activity detected")]
    SuspiciousActivity, // 6406

    #[msg("Account locked due to security concerns")]
    AccountLocked, // 6407

    #[msg("Invalid security parameters")]
    InvalidSecurityParams, // 6408

    #[msg("Emergency mode activated")]
    EmergencyMode, // 6409

    #[msg("Rate limit exceeded")]
    RateLimitExceeded, // 6410

    #[msg("Invalid admin signature")]
    InvalidAdminSignature, // 6411

    #[msg("Security cooldown period active")]
    SecurityCooldownActive, // 6412

    // === ПОЛЬЗОВАТЕЛЬСКИЕ ПРОФИЛИ (6500-6599) ===
    #[msg("User profile not found")]
    UserProfileNotFound, // 6500

    #[msg("Invalid reputation score")]
    InvalidReputationScore, // 6501

    #[msg("Profile creation failed")]
    ProfileCreationFailed, // 6502

    #[msg("Profile update failed")]
    ProfileUpdateFailed, // 6503

    #[msg("User level too low")]
    UserLevelTooLow, // 6504

    #[msg("Insufficient experience points")]
    InsufficientExperiencePoints, // 6505

    #[msg("Achievement already unlocked")]
    AchievementAlreadyUnlocked, // 6506

    #[msg("Achievement requirements not met")]
    AchievementRequirementsNotMet, // 6507

    #[msg("Invalid referral code")]
    InvalidReferralCode, // 6508

    #[msg("Self-referral not allowed")]
    SelfReferralNotAllowed, // 6509

    // === МАТЕМАТИЧЕСКИЕ ОШИБКИ (6600-6699) ===
    #[msg("Division by zero")]
    DivisionByZero, // 6600

    #[msg("Mathematical overflow")]
    MathematicalOverflow, // 6601

    #[msg("Mathematical underflow")]
    MathematicalUnderflow, // 6602

    #[msg("Invalid curve calculation")]
    InvalidCurveCalculation, // 6603

    #[msg("Price calculation failed")]
    PriceCalculationFailed, // 6604

    #[msg("Market cap calculation failed")]
    MarketCapCalculationFailed, // 6605

    #[msg("Invalid percentage value")]
    InvalidPercentage, // 6606

    #[msg("Square root of negative number")]
    SqrtNegativeNumber, // 6607

    #[msg("Logarithm of zero or negative number")]
    LogNonPositiveNumber, // 6608

    #[msg("Exponential overflow")]
    ExponentialOverflow, // 6609

    // === ВРЕМЕННЫЕ ОШИБКИ (6700-6799) ===
    #[msg("Invalid timestamp")]
    InvalidTimestamp, // 6700

    #[msg("Event too old")]
    EventTooOld, // 6701

    #[msg("Event too far in future")]
    EventTooFuture, // 6702

    #[msg("Cooldown period not elapsed")]
    CooldownNotElapsed, // 6703

    #[msg("Deadline exceeded")]
    DeadlineExceeded, // 6704

    #[msg("Lock period not expired")]
    LockPeriodNotExpired, // 6705

    #[msg("Grace period expired")]
    GracePeriodExpired, // 6706

    #[msg("Invalid time window")]
    InvalidTimeWindow, // 6707

    // === СЕТЬ И СОЕДИНЕНИЯ (6800-6899) ===
    #[msg("Network congestion - try again later")]
    NetworkCongestion, // 6800

    #[msg("RPC timeout")]
    RpcTimeout, // 6801

    #[msg("Invalid network configuration")]
    InvalidNetworkConfig, // 6802

    #[msg("Cross-program invocation failed")]
    CpiFailure, // 6803

    #[msg("Account rent not paid")]
    RentNotPaid, // 6804

    #[msg("Program account mismatch")]
    ProgramAccountMismatch, // 6805

    #[msg("Invalid program ID")]
    InvalidProgramId, // 6806

    #[msg("Instruction not allowed")]
    InstructionNotAllowed, // 6807

    // === СПЕЦИФИЧЕСКИЕ ДЛЯ БИЗНЕС-ЛОГИКИ (6900-6999) ===
    #[msg("Token launch window closed")]
    LaunchWindowClosed, // 6900

    #[msg("Presale already ended")]
    PresaleEnded, // 6901

    #[msg("Minimum investment not met")]
    MinimumInvestmentNotMet, // 6902

    #[msg("Maximum investment exceeded")]
    MaximumInvestmentExceeded, // 6903

    #[msg("Whitelist verification failed")]
    WhitelistVerificationFailed, // 6904

    #[msg("Token vesting not started")]
    VestingNotStarted, // 6905

    #[msg("Token still vesting")]
    TokenStillVesting, // 6906

    #[msg("Rewards already claimed")]
    RewardsAlreadyClaimed, // 6907

    #[msg("No rewards available")]
    NoRewardsAvailable, // 6908

    #[msg("Staking period not completed")]
    StakingPeriodNotCompleted, // 6909

    #[msg("Invalid governance proposal")]
    InvalidGovernanceProposal, // 6910

    #[msg("Voting period ended")]
    VotingPeriodEnded, // 6911

    #[msg("Already voted")]
    AlreadyVoted, // 6912

    #[msg("Governance threshold not met")]
    GovernanceThresholdNotMet, // 6913

    #[msg("Token burn not allowed")]
    TokenBurnNotAllowed, // 6914

    #[msg("Mint authority required")]
    MintAuthorityRequired, // 6915
}

impl CustomError {
    /// Возвращает является ли ошибка критической (требует немедленного внимания)
    pub fn is_critical(&self) -> bool {
        matches!(
            self,
            CustomError::OverflowOrUnderflowOccurred
                | CustomError::CircuitBreakerTriggered
                | CustomError::BotActivityDetected
                | CustomError::MarketManipulationDetected
                | CustomError::HoneypotDetected
                | CustomError::EmergencyMode
                | CustomError::SecurityScoreTooLow
                | CustomError::SuspiciousActivity
        )
    }

    /// Возвращает является ли ошибка связанной с безопасностью
    pub fn is_security_related(&self) -> bool {
        matches!(
            self,
            CustomError::BotActivityDetected
                | CustomError::MarketManipulationDetected
                | CustomError::HoneypotDetected
                | CustomError::SuspiciousActivity
                | CustomError::AccountLocked
                | CustomError::UserBanned
                | CustomError::TokenFlagged
                | CustomError::SecurityScoreTooLow
                | CustomError::WhaleProtectionTriggered
                | CustomError::SpamProtection
        )
    }

    /// Возвращает категорию ошибки для логирования
    pub fn get_category(&self) -> ErrorCategory {
        let error_code = *self as u32;
        match error_code {
            6000..=6099 => ErrorCategory::General,
            6100..=6199 => ErrorCategory::TokenCreation,
            6200..=6299 => ErrorCategory::Trading,
            6300..=6399 => ErrorCategory::DexListing,
            6400..=6499 => ErrorCategory::Security,
            6500..=6599 => ErrorCategory::UserProfile,
            6600..=6699 => ErrorCategory::Mathematical,
            6700..=6799 => ErrorCategory::Temporal,
            6800..=6899 => ErrorCategory::Network,
            6900..=6999 => ErrorCategory::BusinessLogic,
            _ => ErrorCategory::Unknown,
        }
    }

    /// Возвращает приоритет ошибки для системы мониторинга
    pub fn get_priority(&self) -> ErrorPriority {
        if self.is_critical() {
            ErrorPriority::Critical
        } else if self.is_security_related() {
            ErrorPriority::High
        } else {
            match self {
                CustomError::NetworkCongestion
                | CustomError::RpcTimeout
                | CustomError::TradingTooFast
                | CustomError::SlippageExceeded => ErrorPriority::Medium,
                _ => ErrorPriority::Low,
            }
        }
    }

    /// Возвращает рекомендуемое действие для пользователя
    pub fn get_user_action(&self) -> &'static str {
        match self {
            CustomError::SlippageExceeded => "Increase slippage tolerance or try again later",
            CustomError::TradingTooFast => "Wait a moment before next trade",
            CustomError::NetworkCongestion => "Network is busy, please try again in a few minutes",
            CustomError::InsufficientBalance => "Add more funds to your wallet",
            CustomError::SpamProtection => "Wait 5 minutes before creating another token",
            CustomError::TradeSizeExceeded => "Reduce trade size or split into smaller trades",
            CustomError::MinHoldTimeNotMet => "Wait before selling (minimum hold time required)",
            CustomError::TokenAlreadyGraduated => "Trade this token on the DEX instead",
            CustomError::KYCRequired => "Complete KYC verification to continue",
            CustomError::UserBanned => "Contact support - your account is banned",
            _ => "Check transaction details and try again",
        }
    }

    /// Возвращает должна ли ошибка быть залогирована
    pub fn should_log(&self) -> bool {
        !matches!(
            self,
            CustomError::SlippageExceeded
                | CustomError::TradingTooFast
                | CustomError::InvalidAmount
                | CustomError::InsufficientBalance
        )
    }

    /// Возвращает нужно ли отправлять уведомление администратору
    pub fn should_notify_admin(&self) -> bool {
        self.is_critical() || matches!(
            self,
            CustomError::BotActivityDetected
                | CustomError::MarketManipulationDetected
                | CustomError::SuspiciousActivity
                | CustomError::DexListingFailed
        )
    }
}

#[derive(Debug, Clone)]
pub enum ErrorCategory {
    General,
    TokenCreation,
    Trading,
    DexListing,
    Security,
    UserProfile,
    Mathematical,
    Temporal,
    Network,
    BusinessLogic,
    Unknown,
}

#[derive(Debug, Clone, PartialEq, PartialOrd)]
pub enum ErrorPriority {
    Low,
    Medium,
    High,
    Critical,
}

// Вспомогательные макросы для быстрого создания ошибок с контекстом
#[macro_export]
macro_rules! require_gte {
    ($left:expr, $right:expr, $error:expr) => {
        if $left < $right {
            return Err($error.into());
        }
    };
}

#[macro_export]
macro_rules! require_lte {
    ($left:expr, $right:expr, $error:expr) => {
        if $left > $right {
            return Err($error.into());
        }
    };
}

#[macro_export]
macro_rules! require_gt {
    ($left:expr, $right:expr, $error:expr) => {
        if $left <= $right {
            return Err($error.into());
        }
    };
}

#[macro_export]
macro_rules! require_lt {
    ($left:expr, $right:expr, $error:expr) => {
        if $left >= $right {
            return Err($error.into());
        }
    };
}

#[macro_export]
macro_rules! require_not_zero {
    ($value:expr, $error:expr) => {
        if $value == 0 {
            return Err($error.into());
        }
    };
}

#[macro_export]
macro_rules! require_non_empty {
    ($string:expr, $error:expr) => {
        if $string.trim().is_empty() {
            return Err($error.into());
        }
    };
}

// Тестовые функции для проверки ошибок
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_categorization() {
        assert_eq!(
            CustomError::TokenAlreadyGraduated.get_category() as u8,
            ErrorCategory::Trading as u8
        );
        assert!(CustomError::BotActivityDetected.is_security_related());
        assert!(CustomError::CircuitBreakerTriggered.is_critical());
    }

    #[test]
    fn test_error_priorities() {
        assert_eq!(
            CustomError::EmergencyMode.get_priority(),
            ErrorPriority::Critical
        );
        assert_eq!(
            CustomError::BotActivityDetected.get_priority(),
            ErrorPriority::High
        );
        assert_eq!(
            CustomError::SlippageExceeded.get_priority(),
            ErrorPriority::Medium
        );
    }

    #[test]
    fn test_notification_requirements() {
        assert!(CustomError::MarketManipulationDetected.should_notify_admin());
        assert!(!CustomError::SlippageExceeded.should_notify_admin());
        assert!(CustomError::SuspiciousActivity.should_log());
        assert!(!CustomError::TradingTooFast.should_log());
    }
}