// contracts/pump-core/programs/pump-core/src/state.rs

use anchor_lang::prelude::*;

// 🏛️ Глобальная конфигурация платформы
#[account]
pub struct PlatformConfig {
    pub admin: Pubkey,                      // Админ платформы
    pub treasury: Pubkey,                   // Казна платформы
    pub fee_rate: f64,                      // Комиссия платформы (%)
    pub paused: bool,                       // Пауза торгов
    pub total_tokens_created: u64,          // Всего токенов создано
    pub total_volume: u64,                  // Общий объем торгов в SOL
    pub total_fees_collected: u64,          // Всего собрано комиссий
    pub security_params: SecurityParams,    // Параметры безопасности
    pub graduation_fee: u64,                // Комиссия за листинг на DEX
    pub min_initial_liquidity: u64,         // Мин начальная ликвидность
    pub platform_version: u8,              // Версия платформы
    pub emergency_contacts: [Pubkey; 3],    // Экстренные контакты
    pub trading_locked: bool,                // Флаг для защиты от reentrancy
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
    pub total_supply: u64,                  // Общее предложение
    pub initial_supply: u64,                // Начальное предложение для кривой
    
    // Рыночные данные
    pub current_market_cap: u64,            // Текущая рыночная капитализация
    pub all_time_high_price: u64,          // Максимальная цена за всё время
    pub all_time_high_market_cap: u64,      // Максимальная капитализация
    pub graduation_eligible: bool,          // Может ли быть листингован
    pub graduated: bool,                    // Листингован ли на DEX
    pub graduation_timestamp: i64,          // Время листинга
    
    // Статистика
    pub created_at: i64,                    // Время создания
    pub last_trade_at: i64,                 // Последняя сделка
    pub trade_count: u64,                   // Количество сделок
    pub unique_traders: u32,                // Уникальных трейдеров
    pub holder_count: u32,                  // Количество держателей
    pub volume_24h: u64,                    // Объем за 24 часа
    pub trades_24h: u32,                    // Сделки за 24 часа
    
    // Безопасность и репутация
    pub creator_reputation_at_creation: f64, // Репутация создателя при создании
    pub security_score: f64,                // Счет безопасности (0-100)
    pub community_rating: f64,              // Рейтинг сообщества (0-5)
    pub verified: bool,                     // Верифицирован
    pub flagged: bool,                      // Помечен как подозрительный
    pub rug_pull_risk_score: f64,          // Риск rug pull (0-100)
    
    // Дополнительные флаги
    pub locked_liquidity: bool,             // Заблокирована ли ликвидность
    pub fair_launch: bool,                  // Честный запуск (без премайна)
    pub doxxed_creator: bool,               // Деанонимизированный создатель
    pub audited: bool,                      // Прошел аудит
    
    // Социальные функции
    pub telegram_url: String,               // Telegram группа (макс 100 символов)
    pub twitter_url: String,                // Twitter профиль (макс 100 символов)
    pub website_url: String,                // Веб-сайт (макс 100 символов)
    
    pub bump: u8,
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
    pub max_trade_size: u64,                // Макс размер сделки в SOL
    pub max_wallet_percentage: f64,         // Макс % от supply для одного кошелька
    pub daily_volume_limit: u64,            // Дневной лимит объема
    pub hourly_trade_limit: u32,            // Лимит сделок в час на кошелек
    
    // Налоги и комиссии
    pub whale_tax_threshold: u64,           // Порог для whale tax в SOL
    pub whale_tax_rate: f64,                // Налог на крупные сделки (%)
    pub early_sell_tax: f64,                // Налог на раннюю продажу (%)
    pub liquidity_tax: f64,                 // Налог на ликвидность (%)
    
    // Временные ограничения
    pub min_hold_time: i64,                 // Мин время удержания в секундах
    pub trade_cooldown: i64,                // Задержка между сделками
    pub creation_cooldown: i64,             // Задержка между созданием токенов
    
    // Защитные механизмы
    pub circuit_breaker_threshold: f64,     // Порог остановки торгов (% изменения цены)
    pub max_price_impact: f64,              // Макс влияние на цену (%)
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
    pub total_volume_traded: u64,           // Общий объем торгов в SOL
    pub total_trades: u64,                  // Общее количество сделок
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
    pub warning_count: u32,                 // Количество предупреждений
    pub ban_reason: String,                 // Причина блокировки (макс 200 символов)
    
    // Временные метки
    pub created_at: i64,                    // Время создания профиля
    pub last_activity: i64,                 // Последняя активность
    pub last_token_creation: i64,           // Последнее создание токена
    pub last_trade_time: i64,               // Последняя сделка
    
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
    pub const ACCOUNT_SIZE: usize = 8 + // discriminator
        32 + 32 + // creator + mint
        60 + 20 + 250 + 550 + // strings (name, symbol, uri, description)
        200 + // bonding_curve
        8 + 8 + 8 + 8 + // reserves and supply
        8 + 8 + 8 + // market data
        1 + 1 + 8 + // graduation flags
        8 + 8 + 8 + 4 + 4 + 8 + 4 + // timestamps and counts
        8 + 8 + 8 + // reputation scores
        1 + 1 + 1 + 1 + // boolean flags
        110 + 110 + 110 + // social urls
        1; // bump

    pub const MAX_NAME_LEN: usize = 50;
    pub const MAX_SYMBOL_LEN: usize = 10;
    pub const MAX_URI_LEN: usize = 200;
    pub const MAX_DESCRIPTION_LEN: usize = 500;
    pub const MAX_URL_LEN: usize = 100;
}

impl UserProfile {
    pub const SEED_PREFIX: &'static str = "user_profile";
    pub const ACCOUNT_SIZE: usize = 8 + // discriminator
        32 + // user
        4 + 4 + 4 + 8 + 8 + // token creation stats
        8 + 8 + 8 + 8 + 8 + 8 + // trading stats
        8 + 8 + 8 + 4 + 4 + // reputation
        1 + 1 + 1 + 4 + 210 + // verification and bans
        8 + 8 + 8 + 8 + // timestamps
        4 + 4 + 4 + // anti-spam
        4 + 32 + 8 + // referrals
        4 + 8 + 400 + // achievements (estimated)
        1; // bump
}

impl SuspiciousActivityReport {
    pub const SEED_PREFIX: &'static str = "report";
    pub const ACCOUNT_SIZE: usize = 8 + 32 + 32 + 1 + 510 + 210 + 8 + 1 + 32 + 210 + 1;
}

impl DexListing {
    pub const SEED_PREFIX: &'static str = "dex_listing";
    pub const ACCOUNT_SIZE: usize = 8 + 32 + 50 + 32 + 8 + 8 + 8 + 8 + 2 + 1 + 8 + 8 + 1;
}

impl PriceHistory {
    pub const SEED_PREFIX: &'static str = "price_history";
    pub const ACCOUNT_SIZE: usize = 8 + 32 + 8 + 8 + 8 + 8 + 4 + 8 + 1 + 1;
}