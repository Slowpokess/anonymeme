// contracts/pump-core/programs/pump-core/src/state.rs

use anchor_lang::prelude::*;

// 🏛️ Глобальная конфигурация платформы
#[account]
pub struct PlatformConfig {
    pub admin: Pubkey,                      // Админ платформы
    pub treasury: Pubkey,                   // Казна платформы
    pub fee_rate: u16,                      // Комиссия платформы (в базисных пунктах, 10000 = 100%)
    pub emergency_paused: bool,             // Экстренная пауза платформы
    pub trading_paused: bool,               // Пауза торгов
    pub reentrancy_guard: bool,             // Защита от реентрантности
    pub total_tokens_created: u64,          // Всего токенов создано
    pub total_volume_sol: u64,              // Общий объем торгов в SOL
    pub total_fees_collected: u64,          // Всего собрано комиссий
    pub total_trades: u64,                  // Всего сделок
    pub total_graduated_tokens: u64,        // Всего токенов выпущено на DEX
    pub total_liquidity_moved: u64,         // Всего ликвидности перемещено на DEX
    pub security_params: SecurityParams,    // Параметры безопасности
    pub graduation_fee: u64,                // Комиссия за листинг на DEX
    pub min_initial_liquidity: u64,         // Мин начальная ликвидность
    pub max_initial_supply: u64,            // Макс начальное предложение
    pub min_token_name_length: u8,          // Минимальная длина имени токена
    pub max_token_name_length: u8,          // Максимальная длина имени токена
    pub platform_version: u8,              // Версия платформы
    pub emergency_contacts: [Pubkey; 3],    // Экстренные контакты
    pub initialized_at: i64,                // Время инициализации
    pub last_updated: i64,                  // Последнее обновление
    pub last_fee_collection: i64,           // Последний сбор комиссий
    pub bump: u8,
}

// 🪙 Полная информация о токене
#[account]
pub struct TokenInfo {
    // Основная информация
    pub creator: Pubkey,                    // Создатель токена
    pub mint: Pubkey,                       // Mint адрес токена
    pub name: String,                       // Имя токена (макс 50 символов)
    pub symbol: String,                     // Символ токена (макс 10 символов)
    pub uri: String,                        // Метаданные URI (макс 200 символов)
    pub description: String,                // Описание (макс 500 символов)

    // Бондинг-кривая
    pub bonding_curve: BondingCurve,        // Параметры бондинг-кривой
    pub sol_reserves: u64,                  // Резервы SOL в lamports
    pub token_reserves: u64,                // Резервы токенов
    pub current_supply: u64,                // Текущее предложение (для расчетов на кривой)
    pub circulating_supply: u64,            // Циркулирующее предложение (у пользователей)
    pub total_supply: u64,                  // Общее предложение
    pub initial_supply: u64,                // Начальное предложение для кривой

    // Рыночные данные
    pub market_cap: u64,                    // Текущая рыночная капитализация
    pub all_time_high_price: u64,          // Максимальная цена за всё время
    pub all_time_high_market_cap: u64,      // Максимальная капитализация
    pub graduation_eligible: bool,          // Может ли быть листингован
    pub is_graduated: bool,                 // Листингован ли на DEX
    pub graduated_at: Option<i64>,          // Время листинга

    // Статистика
    pub created_at: i64,                    // Время создания
    pub last_trade_at: i64,                 // Последняя сделка
    pub total_volume_sol: u64,              // Общий объем торгов в SOL
    pub total_trades: u64,                  // Количество сделок
    pub unique_traders: u32,                // Уникальных трейдеров
    pub holders_count: u32,                 // Количество держателей
    pub volume_24h: u64,                    // Объем за 24 часа
    pub trades_24h: u32,                    // Сделки за 24 часа

    // Безопасность и репутация
    pub creator_reputation_at_creation: f64, // Репутация создателя при создании
    pub security_score: f64,                // Счет безопасности (0-100)
    pub community_rating: f64,              // Рейтинг сообщества (0-5)
    pub verified: bool,                     // Верифицирован
    pub flagged: bool,                      // Помечен как подозрительный
    pub rug_pull_risk_score: f64,          // Риск rug pull (0-100)

    // Состояние токена
    pub is_tradeable: bool,                 // Можно ли торговать
    pub is_frozen: bool,                    // Заморожен ли токен
    pub freeze_reason: String,              // Причина заморозки (макс 300 символов)
    pub frozen_at: Option<i64>,             // Время заморозки
    pub locked_liquidity: bool,             // Заблокирована ли ликвидность
    pub fair_launch: bool,                  // Честный запуск (без премайна)
    pub doxxed_creator: bool,               // Деанонимизированный создатель
    pub audited: bool,                      // Прошел аудит

    // Социальные функции
    pub telegram_url: String,               // Telegram группа (макс 100 символов)
    pub twitter_url: String,                // Twitter профиль (макс 100 символов)
    pub website_url: String,                // Веб-сайт (макс 100 символов)

    // PDA bumps
    pub bump: u8,                           // Bump для token_info PDA
    pub vault_bump: u8,                     // Bump для bonding_curve_vault PDA
}

// 📈 Расширенные параметры бондинг-кривой
#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct BondingCurve {
    pub curve_type: CurveType,              // Тип кривой
    pub initial_price: u64,                 // Начальная цена в lamports за токен
    pub current_price: u64,                 // Текущая цена
    pub graduation_threshold: u64,          // Порог рыночной капы для листинга
    pub slope: f64,                         // Наклон кривой
    pub volatility_damper: f64,             // Демпфер волатильности (0.1-2.0)
    pub initial_supply: u64,                // Начальное предложение для кривой
}

// 🎯 Параметры для создания бондинг-кривой (используется в инструкциях)
#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct BondingCurveParams {
    pub curve_type: CurveType,              // Тип кривой
    pub initial_supply: u64,                // Начальное предложение
    pub initial_price: u64,                 // Начальная цена
    pub graduation_threshold: u64,          // Порог для листинга
    pub slope: f64,                         // Наклон кривой
    pub volatility_damper: Option<f64>,     // Демпфер волатильности (опционально)
}

// 📊 Типы бондинг-кривых
#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq, Debug)]
pub enum CurveType {
    Linear,                                 // y = mx + b
    Exponential,                            // y = ae^(bx)
    Logarithmic,                            // y = a + b*ln(x)
    Sigmoid,                                // y = L/(1 + e^(-k(x-x0)))
    ConstantProduct,                        // xy = k (Uniswap style)
}

// 🛡️ Расширенные параметры безопасности
#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct SecurityParams {
    // Торговые лимиты
    pub max_trade_size_sol: u64,            // Макс размер сделки в SOL
    pub max_wallet_percentage: f64,         // Макс % от supply для одного кошелька
    pub daily_volume_limit: u64,            // Дневной лимит объема
    pub hourly_trade_limit: u32,            // Лимит сделок в час на кошелек

    // Налоги и комиссии
    pub whale_threshold_sol: u64,           // Порог для whale tax в SOL
    pub whale_tax_bps: u16,                 // Налог на крупные сделки (в базисных пунктах)
    pub early_sell_tax: f64,                // Налог на раннюю продажу (%)
    pub liquidity_tax: f64,                 // Налог на ликвидность (%)

    // Временные ограничения
    pub min_hold_time: i64,                 // Мин время удержания в секундах
    pub cooldown_period_seconds: u32,       // Задержка между сделками (cooldown)
    pub creation_cooldown: i64,             // Задержка между созданием токенов
    pub rate_limit_per_minute: u32,         // Лимит сделок в минуту

    // Защитные механизмы
    pub circuit_breaker_threshold: f64,     // Порог остановки торгов (% изменения цены)
    pub max_price_impact: f64,              // Макс влияние на цену (%)
    pub max_slippage_bps: u16,              // Максимальный slippage (в базисных пунктах)
    pub anti_bot_enabled: bool,             // Включена ли защита от ботов
    pub honeypot_detection: bool,           // Детекция honeypot

    // Верификация
    pub require_kyc_for_large_trades: bool, // KYC для крупных сделок
    pub min_reputation_to_create: f64,      // Мин репутация для создания
    pub max_tokens_per_creator: u32,        // Макс токенов на создателя
}

// 👤 Профиль пользователя с расширенной аналитикой
#[account]
pub struct UserProfile {
    pub user: Pubkey,                       // Пользователь

    // Статистика создания токенов
    pub tokens_created: u32,                // Токенов создано
    pub successful_launches: u32,           // Успешных запусков (достигли листинга)
    pub failed_launches: u32,               // Неудачных запусков
    pub total_tokens_initial_value: u64,    // Общая начальная стоимость созданных токенов
    pub total_tokens_current_value: u64,    // Общая текущая стоимость

    // Статистика торговли
    pub total_volume_sol: u64,              // Общий объем торгов в SOL
    pub total_trades: u64,                  // Общее количество сделок
    pub total_tokens_bought: u64,           // Всего токенов куплено
    pub total_tokens_sold: u64,             // Всего токенов продано
    pub profitable_trades: u64,             // Прибыльных сделок
    pub total_profit_loss: i64,             // Общая прибыль/убыток в lamports
    pub largest_trade: u64,                 // Крупнейшая сделка
    pub avg_trade_size: u64,                // Средний размер сделки

    // Репутация и рейтинги
    pub reputation_score: f64,              // Репутация (0-100)
    pub creator_rating: f64,                // Рейтинг как создателя (0-5)
    pub trader_rating: f64,                 // Рейтинг как трейдера (0-5)
    pub community_votes_positive: u32,      // Положительные голоса сообщества
    pub community_votes_negative: u32,      // Отрицательные голоса

    // Верификация и безопасность
    pub verified: bool,                     // Верифицирован
    pub kyc_completed: bool,                // Прошел KYC
    pub banned: bool,                       // Заблокирован
    pub banned_at: Option<i64>,             // Время блокировки
    pub warning_count: u32,                 // Количество предупреждений
    pub ban_reason: String,                 // Причина блокировки (макс 200 символов)

    // Временные метки
    pub created_at: i64,                    // Время создания профиля
    pub last_activity: i64,                 // Последняя активность
    pub last_token_creation: i64,           // Последнее создание токена
    pub last_trade_timestamp: i64,          // Последняя сделка
    pub last_reputation_update: i64,        // Последнее обновление репутации

    // Rate limiting
    pub trades_last_minute: u32,            // Сделки за последнюю минуту (для rate limiting)

    // Анти-спам
    pub anti_spam_score: u32,               // Анти-спам счетчик
    pub failed_trade_attempts: u32,         // Неудачных попыток торговли
    pub suspicious_activity_flags: u32,     // Флаги подозрительной активности

    // Социальная активность
    pub referrals_count: u32,               // Количество рефералов
    pub referred_by: Pubkey,                // Кем приглашен
    pub total_referral_volume: u64,         // Объем по рефералам

    // Достижения и уровни
    pub level: u32,                         // Уровень пользователя (1-100)
    pub experience_points: u64,             // Очки опыта
    pub achievements: Vec<Achievement>,     // Достижения

    pub bump: u8,
}

// 🏆 Система достижений
#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct Achievement {
    pub id: u32,                            // ID достижения
    pub unlocked_at: i64,                   // Время разблокировки
    pub tier: u8,                           // Уровень достижения (1-5)
}

// 📋 Типы DEX для листинга
#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq, Debug)]
pub enum DexType {
    Raydium,
    Jupiter,
    Orca,
    Serum,
    Meteora,
    Custom { program_id: Pubkey },
}

// 🚨 Типы отчетов о подозрительной активности
#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq, Debug)]
pub enum ReportReason {
    Spam,
    Scam,
    RugPull,
    MarketManipulation,
    FakeMetadata,
    Impersonation,
    Other,
}

// 📊 Отчет о подозрительной активности
#[account]
pub struct SuspiciousActivityReport {
    pub reporter: Pubkey,                   // Кто сообщил
    pub reported_user: Pubkey,              // На кого жалоба
    pub reason: ReportReason,               // Причина
    pub description: String,                // Описание (макс 500 символов)
    pub evidence_uri: String,               // Ссылка на доказательства
    pub created_at: i64,                    // Время создания
    pub reviewed: bool,                     // Рассмотрен ли
    pub reviewer: Pubkey,                   // Кто рассматривал
    pub action_taken: String,               // Принятые меры
    pub bump: u8,
}

// 💎 Информация о листинге на DEX
#[account]
pub struct DexListing {
    pub token_mint: Pubkey,                 // Токен
    pub dex_type: DexType,                  // Тип DEX
    pub pool_address: Pubkey,               // Адрес пула
    pub initial_liquidity_sol: u64,         // Начальная ликвидность SOL
    pub initial_liquidity_token: u64,       // Начальная ликвидность токенов
    pub listing_timestamp: i64,             // Время листинга
    pub listing_price: u64,                 // Цена листинга
    pub fee_tier: u16,                      // Комиссия пула (в базисных пунктах)
    pub liquidity_locked: bool,             // Заблокирована ли ликвидность
    pub lock_duration: i64,                 // Длительность блокировки
    pub pool_lp_supply: u64,                // Общее предложение LP токенов
    pub creator_lp_tokens: u64,             // LP токены создателя
    pub bump: u8,
}

// 📈 Исторические данные цен (для графиков)
#[account]
pub struct PriceHistory {
    pub token_mint: Pubkey,                 // Токен
    pub timestamp: i64,                     // Время
    pub price: u64,                         // Цена в lamports
    pub volume: u64,                        // Объем за период
    pub market_cap: u64,                    // Рыночная капитализация
    pub trades_count: u32,                  // Количество сделок
    pub price_change_percent: f64,          // Изменение цены в %
    pub period: PricePeriod,                // Период (1m, 5m, 1h, 1d)
    pub bump: u8,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq, Debug)]
pub enum PricePeriod {
    OneMinute,
    FiveMinutes,
    FifteenMinutes,
    OneHour,
    FourHours,
    OneDay,
}

// 🎯 События для аналитики и мониторинга
#[event]
pub struct TokenCreated {
    pub token: Pubkey,
    pub creator: Pubkey,
    pub name: String,
    pub symbol: String,
    pub initial_supply: u64,
    pub initial_price: u64,
    pub curve_type: CurveType,
    pub timestamp: i64,
}

#[event]
pub struct TokenTraded {
    pub token: Pubkey,
    pub trader: Pubkey,
    pub is_buy: bool,
    pub sol_amount: u64,
    pub token_amount: u64,
    pub new_price: u64,
    pub new_market_cap: u64,
    pub price_impact: f64,
    pub timestamp: i64,
}

#[event]
pub struct TokenGraduated {
    pub token: Pubkey,
    pub dex: DexType,
    pub final_market_cap: u64,
    pub total_volume: u64,
    pub graduation_time_hours: u64,
    pub timestamp: i64,
}

#[event]
pub struct SuspiciousActivityDetected {
    pub user: Pubkey,
    pub activity_type: String,
    pub risk_score: f64,
    pub auto_flagged: bool,
    pub timestamp: i64,
}

#[event]
pub struct EmergencyAction {
    pub admin: Pubkey,
    pub action: String,
    pub target: Pubkey,
    pub reason: String,
    pub timestamp: i64,
}

// 🔧 Константы и размеры аккаунтов
impl PlatformConfig {
    pub const SEED: &'static str = "platform_config";
    pub const ACCOUNT_SIZE: usize = 8 + // discriminator
        32 + 32 + // admin + treasury
        8 + 1 + // fee_rate + paused
        8 + 8 + 8 + // counters
        200 + // security_params (estimated)
        8 + 8 + 1 + // graduation_fee + min_initial_liquidity + platform_version
        96 + // emergency_contacts
        1 + // trading_locked
        1; // bump
}

impl TokenInfo {
    pub const SEED_PREFIX: &'static str = "token_info";
    pub const SEED: &'static str = "token_info"; // Alias для совместимости с инструкциями
    pub const ACCOUNT_SIZE: usize = 8 + // discriminator
        32 + 32 + // creator + mint
        60 + 20 + 250 + 550 + // strings (name, symbol, uri, description)
        200 + // bonding_curve
        8 + 8 + 8 + 8 + 8 + 8 + // reserves and supply (6 fields)
        8 + 8 + 8 + // market data
        1 + 1 + 8 + // graduation flags
        8 + 8 + 8 + 8 + 4 + 4 + 8 + 4 + // timestamps and counts
        8 + 8 + 8 + // reputation scores
        1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + // boolean flags (8 flags)
        310 + 8 + // freeze_reason + frozen_at option
        110 + 110 + 110 + // social urls
        1 + 1; // bump + vault_bump

    pub const MAX_NAME_LEN: usize = 50;
    pub const MAX_SYMBOL_LEN: usize = 10;
    pub const MAX_URI_LEN: usize = 200;
    pub const MAX_DESCRIPTION_LEN: usize = 500;
    pub const MAX_URL_LEN: usize = 100;
}

impl UserProfile {
    pub const SEED_PREFIX: &'static str = "user_profile";
    pub const SEED: &'static str = "user_profile"; // Alias для совместимости с инструкциями
    pub const ACCOUNT_SIZE: usize = 8 + // discriminator
        32 + // user
        4 + 4 + 4 + 8 + 8 + // token creation stats
        8 + 8 + 8 + 8 + 8 + 8 + 8 + 8 + // trading stats (8 fields)
        8 + 8 + 8 + 4 + 4 + // reputation
        1 + 1 + 1 + 8 + 4 + 210 + // verification and bans (with banned_at)
        8 + 8 + 8 + 8 + 8 + // timestamps (5 fields)
        4 + // trades_last_minute
        4 + 4 + 4 + // anti-spam
        4 + 32 + 8 + // referrals
        4 + 8 + 400 + // achievements (estimated)
        1; // bump
}

impl SuspiciousActivityReport {
    pub const SEED_PREFIX: &'static str = "report";
    pub const SEED: &'static str = "report"; // Alias для совместимости
    pub const ACCOUNT_SIZE: usize = 8 + 32 + 32 + 1 + 510 + 210 + 8 + 1 + 32 + 210 + 1 + 1;

    pub fn auto_flagged(&self) -> bool {
        // Автоматическая отметка для high-risk репортов
        matches!(self.reason, ReportReason::RugPull | ReportReason::Scam)
    }
}

impl DexListing {
    pub const SEED_PREFIX: &'static str = "dex_listing";
    pub const SEED: &'static str = "dex_listing"; // Alias для совместимости
    pub const ACCOUNT_SIZE: usize = 8 + 32 + 50 + 32 + 8 + 8 + 8 + 8 + 2 + 1 + 8 + 8 + 8 + 1;
}

impl PriceHistory {
    pub const SEED_PREFIX: &'static str = "price_history";
    pub const ACCOUNT_SIZE: usize = 8 + 32 + 8 + 8 + 8 + 8 + 4 + 8 + 1 + 1;
}

// Implementation methods для создания дефолтных структур
impl Default for SecurityParams {
    fn default() -> Self {
        Self {
            max_trade_size_sol: 100_000_000_000, // 100 SOL
            max_wallet_percentage: 5.0, // 5%
            daily_volume_limit: 1_000_000_000_000, // 1000 SOL
            hourly_trade_limit: 10,
            whale_threshold_sol: 10_000_000_000, // 10 SOL
            whale_tax_bps: 200, // 2% (200 базисных пунктов)
            early_sell_tax: 1.0, // 1%
            liquidity_tax: 0.5, // 0.5%
            min_hold_time: 300, // 5 минут
            cooldown_period_seconds: 10, // 10 секунд
            creation_cooldown: 3600, // 1 час
            rate_limit_per_minute: 10, // 10 сделок в минуту
            circuit_breaker_threshold: 50.0, // 50%
            max_price_impact: 10.0, // 10%
            max_slippage_bps: 1000, // 10% (1000 базисных пунктов)
            anti_bot_enabled: true,
            honeypot_detection: true,
            require_kyc_for_large_trades: false,
            min_reputation_to_create: 0.0,
            max_tokens_per_creator: 5,
        }
    }
}

impl BondingCurve {
    pub fn new(
        curve_type: CurveType,
        initial_price: u64,
        graduation_threshold: u64,
        slope: f64,
        initial_supply: u64,
    ) -> Self {
        Self {
            curve_type,
            initial_price,
            current_price: initial_price,
            graduation_threshold,
            slope,
            volatility_damper: 1.0,
            initial_supply,
        }
    }
}

impl Achievement {
    pub fn new(id: u32, tier: u8) -> Self {
        Self {
            id,
            unlocked_at: Clock::get().unwrap().unix_timestamp,
            tier,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_security_params_default() {
        let params = SecurityParams::default();
        assert_eq!(params.max_trade_size, 100_000_000_000);
        assert_eq!(params.max_wallet_percentage, 5.0);
        assert!(params.anti_bot_enabled);
        assert!(params.honeypot_detection);
        assert_eq!(params.max_tokens_per_creator, 5);
    }

    #[test]
    fn test_bonding_curve_creation() {
        let curve = BondingCurve::new(
            CurveType::Linear,
            1000, // initial_price
            50_000_000_000_000, // graduation_threshold (50 SOL)
            0.000001, // slope
            1_000_000_000_000_000, // initial_supply (1 млрд)
        );

        assert_eq!(curve.curve_type, CurveType::Linear);
        assert_eq!(curve.initial_price, 1000);
        assert_eq!(curve.current_price, 1000);
        assert_eq!(curve.graduation_threshold, 50_000_000_000_000);
        assert_eq!(curve.slope, 0.000001);
        assert_eq!(curve.volatility_damper, 1.0);
        assert_eq!(curve.initial_supply, 1_000_000_000_000_000);
    }

    #[test]
    fn test_achievement_creation() {
        let achievement = Achievement::new(1, 3);
        assert_eq!(achievement.id, 1);
        assert_eq!(achievement.tier, 3);
        assert!(achievement.unlocked_at > 0);
    }

    #[test]
    fn test_curve_type_variants() {
        let types = vec![
            CurveType::Linear,
            CurveType::Exponential,
            CurveType::Logarithmic,
            CurveType::Sigmoid,
            CurveType::ConstantProduct,
        ];

        for curve_type in types {
            // Все типы должны быть валидными
            let curve = BondingCurve::new(
                curve_type.clone(),
                1000,
                50_000_000_000_000,
                0.000001,
                1_000_000_000_000_000,
            );
            assert_eq!(curve.curve_type, curve_type);
        }
    }

    #[test]
    fn test_dex_type_variants() {
        let dex_types = vec![
            DexType::Raydium,
            DexType::Jupiter,
            DexType::Orca,
            DexType::Serum,
            DexType::Meteora,
        ];

        for dex_type in dex_types {
            // Все типы DEX должны быть валидными
            match dex_type {
                DexType::Raydium => assert_eq!(dex_type, DexType::Raydium),
                DexType::Jupiter => assert_eq!(dex_type, DexType::Jupiter),
                DexType::Orca => assert_eq!(dex_type, DexType::Orca),
                DexType::Serum => assert_eq!(dex_type, DexType::Serum),
                DexType::Meteora => assert_eq!(dex_type, DexType::Meteora),
                _ => {}
            }
        }
    }

    #[test]
    fn test_custom_dex_type() {
        let custom_program_id = Pubkey::new_unique();
        let custom_dex = DexType::Custom { program_id: custom_program_id };
        
        if let DexType::Custom { program_id } = custom_dex {
            assert_eq!(program_id, custom_program_id);
        } else {
            panic!("Expected Custom DexType");
        }
    }

    #[test]
    fn test_report_reason_variants() {
        let reasons = vec![
            ReportReason::Spam,
            ReportReason::Scam,
            ReportReason::RugPull,
            ReportReason::MarketManipulation,
            ReportReason::FakeMetadata,
            ReportReason::Impersonation,
            ReportReason::Other,
        ];

        assert_eq!(reasons.len(), 7);
        assert!(reasons.contains(&ReportReason::RugPull));
        assert!(reasons.contains(&ReportReason::Scam));
    }

    #[test]
    fn test_price_period_variants() {
        let periods = vec![
            PricePeriod::OneMinute,
            PricePeriod::FiveMinutes,
            PricePeriod::FifteenMinutes,
            PricePeriod::OneHour,
            PricePeriod::FourHours,
            PricePeriod::OneDay,
        ];

        assert_eq!(periods.len(), 6);
        assert!(periods.contains(&PricePeriod::OneHour));
        assert!(periods.contains(&PricePeriod::OneDay));
    }

    #[test]
    fn test_bonding_curve_params_creation() {
        let params = BondingCurveParams {
            curve_type: CurveType::Exponential,
            initial_supply: 1_000_000_000_000_000,
            initial_price: 1000,
            graduation_threshold: 50_000_000_000_000,
            slope: 0.000001,
            volatility_damper: Some(1.5),
        };

        assert_eq!(params.curve_type, CurveType::Exponential);
        assert_eq!(params.initial_supply, 1_000_000_000_000_000);
        assert_eq!(params.initial_price, 1000);
        assert_eq!(params.graduation_threshold, 50_000_000_000_000);
        assert_eq!(params.slope, 0.000001);
        assert_eq!(params.volatility_damper, Some(1.5));
    }

    #[test]
    fn test_security_params_validation() {
        let mut params = SecurityParams::default();
        
        // Валидные параметры
        assert!(params.max_trade_size > 0);
        assert!(params.max_wallet_percentage > 0.0 && params.max_wallet_percentage <= 100.0);
        assert!(params.daily_volume_limit > 0);
        assert!(params.circuit_breaker_threshold > 0.0);
        assert!(params.max_price_impact > 0.0);
        
        // Тест edge cases
        params.max_wallet_percentage = 0.1; // 0.1%
        assert!(params.max_wallet_percentage >= 0.0);
        
        params.circuit_breaker_threshold = 100.0; // 100%
        assert!(params.circuit_breaker_threshold <= 100.0);
    }

    #[test]
    fn test_account_size_constants() {
        // Проверка, что константы размеров аккаунтов разумны
        assert!(PlatformConfig::ACCOUNT_SIZE > 0);
        assert!(PlatformConfig::ACCOUNT_SIZE < 10000); // Разумный лимит
        
        assert!(TokenInfo::ACCOUNT_SIZE > 0);
        assert!(TokenInfo::ACCOUNT_SIZE < 10000);
        
        assert!(UserProfile::ACCOUNT_SIZE > 0);
        assert!(UserProfile::ACCOUNT_SIZE < 10000);
        
        assert!(SuspiciousActivityReport::ACCOUNT_SIZE > 0);
        assert!(DexListing::ACCOUNT_SIZE > 0);
        assert!(PriceHistory::ACCOUNT_SIZE > 0);
    }

    #[test]
    fn test_string_length_constants() {
        // Проверка констант максимальной длины строк
        assert_eq!(TokenInfo::MAX_NAME_LEN, 50);
        assert_eq!(TokenInfo::MAX_SYMBOL_LEN, 10);
        assert_eq!(TokenInfo::MAX_URI_LEN, 200);
        assert_eq!(TokenInfo::MAX_DESCRIPTION_LEN, 500);
        assert_eq!(TokenInfo::MAX_URL_LEN, 100);
        
        // Проверка, что лимиты разумны
        assert!(TokenInfo::MAX_NAME_LEN > 0 && TokenInfo::MAX_NAME_LEN <= 100);
        assert!(TokenInfo::MAX_SYMBOL_LEN > 0 && TokenInfo::MAX_SYMBOL_LEN <= 20);
        assert!(TokenInfo::MAX_URI_LEN > 0 && TokenInfo::MAX_URI_LEN <= 500);
    }

    #[test]
    fn test_seed_constants() {
        // Проверка seed константы для PDA
        assert_eq!(PlatformConfig::SEED, "platform_config");
        assert_eq!(TokenInfo::SEED_PREFIX, "token_info");
        assert_eq!(UserProfile::SEED_PREFIX, "user_profile");
        assert_eq!(SuspiciousActivityReport::SEED_PREFIX, "report");
        assert_eq!(DexListing::SEED_PREFIX, "dex_listing");
        assert_eq!(PriceHistory::SEED_PREFIX, "price_history");
        
        // Все seeds должны быть непустыми и разумной длины
        assert!(!PlatformConfig::SEED.is_empty());
        assert!(PlatformConfig::SEED.len() <= 32);
        assert!(!TokenInfo::SEED_PREFIX.is_empty());
        assert!(TokenInfo::SEED_PREFIX.len() <= 32);
    }

    #[test]
    fn test_enum_clone_and_partial_eq() {
        // Тест что enums поддерживают Clone и PartialEq
        let curve1 = CurveType::Linear;
        let curve2 = curve1.clone();
        assert_eq!(curve1, curve2);
        
        let dex1 = DexType::Raydium;
        let dex2 = dex1.clone();
        assert_eq!(dex1, dex2);
        
        let reason1 = ReportReason::Scam;
        let reason2 = reason1.clone();
        assert_eq!(reason1, reason2);
        
        let period1 = PricePeriod::OneHour;
        let period2 = period1.clone();
        assert_eq!(period1, period2);
    }

    #[test]
    fn test_struct_clone() {
        // Тест клонирования структур
        let original_curve = BondingCurve::new(
            CurveType::Linear,
            1000,
            50_000_000_000_000,
            0.000001,
            1_000_000_000_000_000,
        );
        
        let cloned_curve = original_curve.clone();
        assert_eq!(original_curve.curve_type, cloned_curve.curve_type);
        assert_eq!(original_curve.initial_price, cloned_curve.initial_price);
        assert_eq!(original_curve.slope, cloned_curve.slope);
        
        let original_params = SecurityParams::default();
        let cloned_params = original_params.clone();
        assert_eq!(original_params.max_trade_size, cloned_params.max_trade_size);
        assert_eq!(original_params.anti_bot_enabled, cloned_params.anti_bot_enabled);
        
        let original_achievement = Achievement::new(1, 3);
        let cloned_achievement = original_achievement.clone();
        assert_eq!(original_achievement.id, cloned_achievement.id);
        assert_eq!(original_achievement.tier, cloned_achievement.tier);
    }

    #[test]
    fn test_bonding_curve_params_with_optional_damper() {
        // Тест с volatility_damper = None
        let params_none = BondingCurveParams {
            curve_type: CurveType::Linear,
            initial_supply: 1_000_000_000_000_000,
            initial_price: 1000,
            graduation_threshold: 50_000_000_000_000,
            slope: 0.000001,
            volatility_damper: None,
        };
        assert_eq!(params_none.volatility_damper, None);
        
        // Тест с volatility_damper = Some(value)
        let params_some = BondingCurveParams {
            curve_type: CurveType::Linear,
            initial_supply: 1_000_000_000_000_000,
            initial_price: 1000,
            graduation_threshold: 50_000_000_000_000,
            slope: 0.000001,
            volatility_damper: Some(2.0),
        };
        assert_eq!(params_some.volatility_damper, Some(2.0));
    }
}