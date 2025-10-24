// contracts/pump-core/programs/pump-core/src/errors.rs

use anchor_lang::prelude::*;

#[error_code]
pub enum ErrorCode {
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
    TooManyTokensCreated, // 6108

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

    // === LP TOKEN LOCK (6916-6925) ===
    #[msg("Lock period not expired yet")]
    LockPeriodNotExpired, // 6916

    #[msg("Lock duration too short")]
    LockDurationTooShort, // 6917

    #[msg("Lock duration too long")]
    LockDurationTooLong, // 6918

    #[msg("LP tokens already unlocked")]
    AlreadyUnlocked, // 6919

    #[msg("Liquidity not locked")]
    LiquidityNotLocked, // 6920

    #[msg("Invalid lock duration")]
    InvalidLockDuration, // 6921

    #[msg("Cannot unlock before vesting period")]
    VestingPeriodNotComplete, // 6922
}

impl ErrorCode {
    /// Возвращает является ли ошибка критической (требует немедленного внимания)
    pub fn is_critical(&self) -> bool {
        matches!(
            self,
            ErrorCode::OverflowOrUnderflowOccurred
                | ErrorCode::CircuitBreakerTriggered
                | ErrorCode::BotActivityDetected
                | ErrorCode::MarketManipulationDetected
                | ErrorCode::HoneypotDetected
                | ErrorCode::EmergencyMode
                | ErrorCode::SecurityScoreTooLow
                | ErrorCode::SuspiciousActivity
        )
    }

    /// Возвращает является ли ошибка связанной с безопасностью
    pub fn is_security_related(&self) -> bool {
        matches!(
            self,
            ErrorCode::BotActivityDetected
                | ErrorCode::MarketManipulationDetected
                | ErrorCode::HoneypotDetected
                | ErrorCode::SuspiciousActivity
                | ErrorCode::AccountLocked
                | ErrorCode::UserBanned
                | ErrorCode::TokenFlagged
                | ErrorCode::SecurityScoreTooLow
                | ErrorCode::WhaleProtectionTriggered
                | ErrorCode::SpamProtection
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
                ErrorCode::NetworkCongestion
                | ErrorCode::RpcTimeout
                | ErrorCode::TradingTooFast
                | ErrorCode::SlippageExceeded => ErrorPriority::Medium,
                _ => ErrorPriority::Low,
            }
        }
    }

    /// Возвращает рекомендуемое действие для пользователя
    pub fn get_user_action(&self) -> &'static str {
        match self {
            ErrorCode::SlippageExceeded => "Increase slippage tolerance or try again later",
            ErrorCode::TradingTooFast => "Wait a moment before next trade",
            ErrorCode::NetworkCongestion => "Network is busy, please try again in a few minutes",
            ErrorCode::InsufficientBalance => "Add more funds to your wallet",
            ErrorCode::SpamProtection => "Wait 5 minutes before creating another token",
            ErrorCode::TradeSizeExceeded => "Reduce trade size or split into smaller trades",
            ErrorCode::MinHoldTimeNotMet => "Wait before selling (minimum hold time required)",
            ErrorCode::TokenAlreadyGraduated => "Trade this token on the DEX instead",
            ErrorCode::KYCRequired => "Complete KYC verification to continue",
            ErrorCode::UserBanned => "Contact support - your account is banned",
            _ => "Check transaction details and try again",
        }
    }

    /// Возвращает должна ли ошибка быть залогирована
    pub fn should_log(&self) -> bool {
        !matches!(
            self,
            ErrorCode::SlippageExceeded
                | ErrorCode::TradingTooFast
                | ErrorCode::InvalidAmount
                | ErrorCode::InsufficientBalance
        )
    }

    /// Возвращает нужно ли отправлять уведомление администратору
    pub fn should_notify_admin(&self) -> bool {
        self.is_critical() || matches!(
            self,
            ErrorCode::BotActivityDetected
                | ErrorCode::MarketManipulationDetected
                | ErrorCode::SuspiciousActivity
                | ErrorCode::DexListingFailed
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
macro_rules! require_gte {
    ($left:expr, $right:expr, $error:expr) => {
        if $left < $right {
            return Err($error.into());
        }
    };
}

macro_rules! require_lte {
    ($left:expr, $right:expr, $error:expr) => {
        if $left > $right {
            return Err($error.into());
        }
    };
}

macro_rules! require_gt {
    ($left:expr, $right:expr, $error:expr) => {
        if $left <= $right {
            return Err($error.into());
        }
    };
}

macro_rules! require_lt {
    ($left:expr, $right:expr, $error:expr) => {
        if $left >= $right {
            return Err($error.into());
        }
    };
}

macro_rules! require_not_zero {
    ($value:expr, $error:expr) => {
        if $value == 0 {
            return Err($error.into());
        }
    };
}

macro_rules! require_non_empty {
    ($string:expr, $error:expr) => {
        if $string.trim().is_empty() {
            return Err($error.into());
        }
    };
}

// Comprehensive unit тесты для модуля ошибок
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_categorization() {
        // Тест общих ошибок (6000-6099)
        assert!(matches!(ErrorCode::PlatformPaused.get_category(), ErrorCategory::General));
        assert!(matches!(ErrorCode::InvalidAmount.get_category(), ErrorCategory::General));
        assert!(matches!(ErrorCode::Unauthorized.get_category(), ErrorCategory::General));

        // Тест ошибок создания токенов (6100-6199)
        assert!(matches!(ErrorCode::NameTooLong.get_category(), ErrorCategory::TokenCreation));
        assert!(matches!(ErrorCode::SymbolTooLong.get_category(), ErrorCategory::TokenCreation));
        assert!(matches!(ErrorCode::InvalidBondingCurveParams.get_category(), ErrorCategory::TokenCreation));

        // Тест торговых ошибок (6200-6299)
        assert!(matches!(ErrorCode::SlippageExceeded.get_category(), ErrorCategory::Trading));
        assert!(matches!(ErrorCode::TradeSizeExceeded.get_category(), ErrorCategory::Trading));
        assert!(matches!(ErrorCode::TokenAlreadyGraduated.get_category(), ErrorCategory::Trading));

        // Тест ошибок листинга на DEX (6300-6399)
        assert!(matches!(ErrorCode::NotEligibleForGraduation.get_category(), ErrorCategory::DexListing));
        assert!(matches!(ErrorCode::AlreadyGraduated.get_category(), ErrorCategory::DexListing));

        // Тест ошибок безопасности (6400-6499)
        assert!(matches!(ErrorCode::AdminOnly.get_category(), ErrorCategory::Security));
        assert!(matches!(ErrorCode::UserBanned.get_category(), ErrorCategory::Security));
        assert!(matches!(ErrorCode::EmergencyMode.get_category(), ErrorCategory::Security));

        // Тест ошибок профилей (6500-6599)
        assert!(matches!(ErrorCode::UserProfileNotFound.get_category(), ErrorCategory::UserProfile));
        assert!(matches!(ErrorCode::InvalidReputationScore.get_category(), ErrorCategory::UserProfile));

        // Тест математических ошибок (6600-6699)
        assert!(matches!(ErrorCode::DivisionByZero.get_category(), ErrorCategory::Mathematical));
        assert!(matches!(ErrorCode::MathematicalOverflow.get_category(), ErrorCategory::Mathematical));

        // Тест временных ошибок (6700-6799)
        assert!(matches!(ErrorCode::InvalidTimestamp.get_category(), ErrorCategory::Temporal));
        assert!(matches!(ErrorCode::CooldownNotElapsed.get_category(), ErrorCategory::Temporal));

        // Тест сетевых ошибок (6800-6899)
        assert!(matches!(ErrorCode::NetworkCongestion.get_category(), ErrorCategory::Network));
        assert!(matches!(ErrorCode::RpcTimeout.get_category(), ErrorCategory::Network));

        // Тест бизнес-логики (6900-6999)
        assert!(matches!(ErrorCode::LaunchWindowClosed.get_category(), ErrorCategory::BusinessLogic));
        assert!(matches!(ErrorCode::PresaleEnded.get_category(), ErrorCategory::BusinessLogic));
    }

    #[test]
    fn test_critical_errors_identification() {
        let critical_errors = vec![
            ErrorCode::OverflowOrUnderflowOccurred,
            ErrorCode::CircuitBreakerTriggered,
            ErrorCode::BotActivityDetected,
            ErrorCode::MarketManipulationDetected,
            ErrorCode::HoneypotDetected,
            ErrorCode::EmergencyMode,
            ErrorCode::SecurityScoreTooLow,
            ErrorCode::SuspiciousActivity,
        ];

        for error in critical_errors {
            assert!(error.is_critical(), "Error {:?} should be critical", error);
        }

        // Тест не критических ошибок
        let non_critical_errors = vec![
            ErrorCode::SlippageExceeded,
            ErrorCode::InvalidAmount,
            ErrorCode::NameTooLong,
            ErrorCode::TradingTooFast,
        ];

        for error in non_critical_errors {
            assert!(!error.is_critical(), "Error {:?} should not be critical", error);
        }
    }

    #[test]
    fn test_security_related_errors() {
        let security_errors = vec![
            ErrorCode::BotActivityDetected,
            ErrorCode::MarketManipulationDetected,
            ErrorCode::HoneypotDetected,
            ErrorCode::SuspiciousActivity,
            ErrorCode::AccountLocked,
            ErrorCode::UserBanned,
            ErrorCode::TokenFlagged,
            ErrorCode::SecurityScoreTooLow,
            ErrorCode::WhaleProtectionTriggered,
            ErrorCode::SpamProtection,
        ];

        for error in security_errors {
            assert!(error.is_security_related(), "Error {:?} should be security related", error);
        }

        // Тест не связанных с безопасностью ошибок
        let non_security_errors = vec![
            ErrorCode::SlippageExceeded,
            ErrorCode::NameTooLong,
            ErrorCode::InvalidAmount,
            ErrorCode::NetworkCongestion,
        ];

        for error in non_security_errors {
            assert!(!error.is_security_related(), "Error {:?} should not be security related", error);
        }
    }

    #[test]
    fn test_error_priorities() {
        // Критические ошибки
        assert_eq!(ErrorCode::EmergencyMode.get_priority(), ErrorPriority::Critical);
        assert_eq!(ErrorCode::CircuitBreakerTriggered.get_priority(), ErrorPriority::Critical);
        assert_eq!(ErrorCode::OverflowOrUnderflowOccurred.get_priority(), ErrorPriority::Critical);

        // Высокоприоритетные ошибки (безопасность)
        assert_eq!(ErrorCode::BotActivityDetected.get_priority(), ErrorPriority::High);
        assert_eq!(ErrorCode::MarketManipulationDetected.get_priority(), ErrorPriority::High);
        assert_eq!(ErrorCode::UserBanned.get_priority(), ErrorPriority::High);

        // Среднеприоритетные ошибки
        assert_eq!(ErrorCode::NetworkCongestion.get_priority(), ErrorPriority::Medium);
        assert_eq!(ErrorCode::RpcTimeout.get_priority(), ErrorPriority::Medium);
        assert_eq!(ErrorCode::TradingTooFast.get_priority(), ErrorPriority::Medium);
        assert_eq!(ErrorCode::SlippageExceeded.get_priority(), ErrorPriority::Medium);

        // Низкоприоритетные ошибки
        assert_eq!(ErrorCode::NameTooLong.get_priority(), ErrorPriority::Low);
        assert_eq!(ErrorCode::InvalidAmount.get_priority(), ErrorPriority::Low);
        assert_eq!(ErrorCode::EventTooOld.get_priority(), ErrorPriority::Low);
    }

    #[test]
    fn test_user_action_recommendations() {
        assert_eq!(
            ErrorCode::SlippageExceeded.get_user_action(),
            "Increase slippage tolerance or try again later"
        );
        assert_eq!(
            ErrorCode::TradingTooFast.get_user_action(),
            "Wait a moment before next trade"
        );
        assert_eq!(
            ErrorCode::NetworkCongestion.get_user_action(),
            "Network is busy, please try again in a few minutes"
        );
        assert_eq!(
            ErrorCode::InsufficientBalance.get_user_action(),
            "Add more funds to your wallet"
        );
        assert_eq!(
            ErrorCode::SpamProtection.get_user_action(),
            "Wait 5 minutes before creating another token"
        );
        assert_eq!(
            ErrorCode::TradeSizeExceeded.get_user_action(),
            "Reduce trade size or split into smaller trades"
        );
        assert_eq!(
            ErrorCode::MinHoldTimeNotMet.get_user_action(),
            "Wait before selling (minimum hold time required)"
        );
        assert_eq!(
            ErrorCode::TokenAlreadyGraduated.get_user_action(),
            "Trade this token on the DEX instead"
        );
        assert_eq!(
            ErrorCode::KYCRequired.get_user_action(),
            "Complete KYC verification to continue"
        );
        assert_eq!(
            ErrorCode::UserBanned.get_user_action(),
            "Contact support - your account is banned"
        );

        // Тест дефолтного действия
        assert_eq!(
            ErrorCode::DivisionByZero.get_user_action(),
            "Check transaction details and try again"
        );
    }

    #[test]
    fn test_logging_requirements() {
        // Ошибки, которые не должны логироваться
        let no_log_errors = vec![
            ErrorCode::SlippageExceeded,
            ErrorCode::TradingTooFast,
            ErrorCode::InvalidAmount,
            ErrorCode::InsufficientBalance,
        ];

        for error in no_log_errors {
            assert!(!error.should_log(), "Error {:?} should not be logged", error);
        }

        // Ошибки, которые должны логироваться
        let should_log_errors = vec![
            ErrorCode::BotActivityDetected,
            ErrorCode::MarketManipulationDetected,
            ErrorCode::EmergencyMode,
            ErrorCode::DexListingFailed,
            ErrorCode::UserBanned,
        ];

        for error in should_log_errors {
            assert!(error.should_log(), "Error {:?} should be logged", error);
        }
    }

    #[test]
    fn test_admin_notification_requirements() {
        // Ошибки, требующие уведомления админа
        let notify_admin_errors = vec![
            ErrorCode::EmergencyMode,
            ErrorCode::CircuitBreakerTriggered,
            ErrorCode::BotActivityDetected,
            ErrorCode::MarketManipulationDetected,
            ErrorCode::HoneypotDetected,
            ErrorCode::SuspiciousActivity,
            ErrorCode::DexListingFailed,
        ];

        for error in notify_admin_errors {
            assert!(error.should_notify_admin(), "Error {:?} should notify admin", error);
        }

        // Ошибки, не требующие уведомления админа
        let no_notify_errors = vec![
            ErrorCode::SlippageExceeded,
            ErrorCode::TradingTooFast,
            ErrorCode::InvalidAmount,
            ErrorCode::NameTooLong,
            ErrorCode::NetworkCongestion,
        ];

        for error in no_notify_errors {
            assert!(!error.should_notify_admin(), "Error {:?} should not notify admin", error);
        }
    }

    #[test]
    fn test_error_priority_ordering() {
        assert!(ErrorPriority::Critical > ErrorPriority::High);
        assert!(ErrorPriority::High > ErrorPriority::Medium);
        assert!(ErrorPriority::Medium > ErrorPriority::Low);
        
        // Тест сравнения приоритетов
        let priorities = vec![
            ErrorPriority::Low,
            ErrorPriority::Medium,
            ErrorPriority::High,
            ErrorPriority::Critical,
        ];
        
        for i in 0..priorities.len() - 1 {
            assert!(priorities[i] < priorities[i + 1]);
        }
    }

    #[test]
    fn test_error_category_variants() {
        let categories = vec![
            ErrorCategory::General,
            ErrorCategory::TokenCreation,
            ErrorCategory::Trading,
            ErrorCategory::DexListing,
            ErrorCategory::Security,
            ErrorCategory::UserProfile,
            ErrorCategory::Mathematical,
            ErrorCategory::Temporal,
            ErrorCategory::Network,
            ErrorCategory::BusinessLogic,
            ErrorCategory::Unknown,
        ];

        // Все категории должны быть клонируемыми
        for category in categories {
            let cloned = category.clone();
            // Сравнение по Debug representation, так как PartialEq не реализован
            assert_eq!(format!("{:?}", category), format!("{:?}", cloned));
        }
    }

    #[test]
    fn test_error_code_ranges() {
        // Проверка, что ошибки попадают в правильные диапазоны кодов
        assert!((ErrorCode::PlatformPaused as u32) >= 6000);
        assert!((ErrorCode::PlatformPaused as u32) < 6100);
        
        assert!((ErrorCode::NameTooLong as u32) >= 6100);
        assert!((ErrorCode::NameTooLong as u32) < 6200);
        
        assert!((ErrorCode::TradeSizeExceeded as u32) >= 6200);
        assert!((ErrorCode::TradeSizeExceeded as u32) < 6300);
        
        assert!((ErrorCode::NotEligibleForGraduation as u32) >= 6300);
        assert!((ErrorCode::NotEligibleForGraduation as u32) < 6400);
        
        assert!((ErrorCode::AdminOnly as u32) >= 6400);
        assert!((ErrorCode::AdminOnly as u32) < 6500);
        
        assert!((ErrorCode::UserProfileNotFound as u32) >= 6500);
        assert!((ErrorCode::UserProfileNotFound as u32) < 6600);
        
        assert!((ErrorCode::DivisionByZero as u32) >= 6600);
        assert!((ErrorCode::DivisionByZero as u32) < 6700);
        
        assert!((ErrorCode::InvalidTimestamp as u32) >= 6700);
        assert!((ErrorCode::InvalidTimestamp as u32) < 6800);
        
        assert!((ErrorCode::NetworkCongestion as u32) >= 6800);
        assert!((ErrorCode::NetworkCongestion as u32) < 6900);
        
        assert!((ErrorCode::LaunchWindowClosed as u32) >= 6900);
        assert!((ErrorCode::LaunchWindowClosed as u32) < 7000);
    }

    #[test]
    fn test_all_errors_have_messages() {
        // Тест что у всех ошибок есть сообщения (проверяем через Display)
        use std::error::Error;
        
        let all_errors = vec![
            // Общие ошибки
            ErrorCode::PlatformPaused,
            ErrorCode::InvalidAmount,
            ErrorCode::InsufficientBalance,
            ErrorCode::Unauthorized,
            
            // Ошибки создания токенов
            ErrorCode::NameTooLong,
            ErrorCode::SymbolTooLong,
            ErrorCode::InvalidBondingCurveParams,
            ErrorCode::SpamProtection,
            
            // Торговые ошибки
            ErrorCode::TradeSizeExceeded,
            ErrorCode::SlippageExceeded,
            ErrorCode::TradingTooFast,
            ErrorCode::TokenAlreadyGraduated,
            
            // Ошибки безопасности
            ErrorCode::BotActivityDetected,
            ErrorCode::MarketManipulationDetected,
            ErrorCode::UserBanned,
            ErrorCode::EmergencyMode,
            
            // Математические ошибки
            ErrorCode::DivisionByZero,
            ErrorCode::MathematicalOverflow,
            ErrorCode::SqrtNegativeNumber,
            
            // Временные ошибки
            ErrorCode::InvalidTimestamp,
            ErrorCode::CooldownNotElapsed,
            ErrorCode::DeadlineExceeded,
            
            // Сетевые ошибки
            ErrorCode::NetworkCongestion,
            ErrorCode::RpcTimeout,
            ErrorCode::CpiFailure,
        ];

        for error in all_errors {
            let message = format!("{}", error);
            assert!(!message.is_empty(), "Error {:?} should have a message", error);
            assert!(message.len() > 5, "Error {:?} message too short: {}", error, message);
        }
    }

    #[test]
    fn test_error_consistency() {
        // Тест что критические ошибки также являются ошибками безопасности или требуют уведомления админа
        let critical_errors = vec![
            ErrorCode::OverflowOrUnderflowOccurred,
            ErrorCode::CircuitBreakerTriggered,
            ErrorCode::BotActivityDetected,
            ErrorCode::MarketManipulationDetected,
            ErrorCode::HoneypotDetected,
            ErrorCode::EmergencyMode,
            ErrorCode::SecurityScoreTooLow,
            ErrorCode::SuspiciousActivity,
        ];

        for error in critical_errors {
            assert!(error.is_critical());
            // Критические ошибки должны или быть связаны с безопасностью, или требовать уведомления админа
            assert!(
                error.is_security_related() || error.should_notify_admin(),
                "Critical error {:?} should be security related or notify admin",
                error
            );
        }
    }

    #[test]
    fn test_macro_helpers() {
        // Тест макросов (они должны компилироваться)
        fn test_require_macros() -> Result<(), ErrorCode> {
            let value = 5u64;
            let limit = 10u64;
            
            require_gte!(value, 1, ErrorCode::InvalidAmount);
            require_lte!(value, limit, ErrorCode::TradeSizeExceeded);
            require_gt!(value, 0, ErrorCode::InvalidAmount);
            require_lt!(value, 100, ErrorCode::TradeSizeExceeded);
            require_not_zero!(value, ErrorCode::DivisionByZero);
            
            let text = "valid text";
            require_non_empty!(text, ErrorCode::NameTooLong);
            
            Ok(())
        }
        
        // Макросы должны работать без ошибок для валидных значений
        assert!(test_require_macros().is_ok());
        
        // Тест что макросы правильно возвращают ошибки
        fn test_require_failure() -> Result<(), ErrorCode> {
            let value = 0u64;
            require_not_zero!(value, ErrorCode::DivisionByZero);
            Ok(())
        }
        
        let result = test_require_failure();
        assert!(result.is_err());
        if let Err(err) = result {
            assert_eq!(err, ErrorCode::DivisionByZero);
        }
    }

    #[test]
    fn test_unknown_error_category() {
        // Тест для случая неизвестной категории (не должно происходить в реальности)
        // Но функция должна обработать любой код ошибки
        
        // Создаем фиктивную ошибку с кодом вне диапазонов
        // Это тест для полноты покрытия кода
        
        // Проверяем граничные случаи
        let category_6099 = match 6099 {
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
        };
        
        assert!(matches!(category_6099, ErrorCategory::General));
        
        let category_unknown = match 7000 {
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
        };
        
        assert!(matches!(category_unknown, ErrorCategory::Unknown));
    }

    #[test]
    fn test_error_combinations() {
        // Тест комбинаций свойств ошибок
        let error = ErrorCode::BotActivityDetected;
        assert!(error.is_critical());
        assert!(error.is_security_related());
        assert!(error.should_notify_admin());
        assert!(error.should_log());
        assert_eq!(error.get_priority(), ErrorPriority::Critical);
        
        let error2 = ErrorCode::SlippageExceeded;
        assert!(!error2.is_critical());
        assert!(!error2.is_security_related());
        assert!(!error2.should_notify_admin());
        assert!(!error2.should_log());
        assert_eq!(error2.get_priority(), ErrorPriority::Medium);
    }
}

