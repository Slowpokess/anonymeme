/**
 * 🔷 Общие типы для Anonymeme Frontend
 * Production-ready TypeScript определения
 */

export interface Token {
  id: string
  mint: string
  name: string
  symbol: string
  description?: string
  image?: string
  creator: string
  created_at: string
  updated_at: string
  status: TokenStatus
  supply: string
  decimals: number
  curve_type: CurveType
  bonding_curve_params: BondingCurveParams
  current_price: string
  market_cap: string
  sol_reserves: string
  token_reserves: string
  graduation_threshold: string
  graduated: boolean
  dex_listing?: DexListing
  metadata_uri?: string
  telegram_link?: string
  twitter_link?: string
  website_link?: string
  is_flagged: boolean
  flagged_reason?: string
  total_trades: number
  volume_24h: string
  price_change_24h: number
  holders_count: number
}

export interface User {
  id: string
  wallet_address: string
  username?: string
  avatar_url?: string
  bio?: string
  created_at: string
  updated_at: string
  status: UserStatus
  role: UserRole
  total_trades: number
  total_volume: string
  tokens_created: number
  reputation_score: number
  is_verified: boolean
  settings: UserSettings
}

export interface Trade {
  id: string
  user_id: string
  token_id: string
  trade_type: TradeType
  sol_amount: string
  token_amount: string
  price_per_token: string
  transaction_signature: string
  created_at: string
  slippage: number
  platform_fee: string
  success: boolean
  error_message?: string
}

export interface Portfolio {
  user_id: string
  tokens: PortfolioToken[]
  total_value_sol: string
  total_value_usd: string
  pnl_24h: string
  pnl_percentage: number
  updated_at: string
}

export interface PortfolioToken {
  token: Token
  balance: string
  value_sol: string
  value_usd: string
  avg_buy_price: string
  pnl: string
  pnl_percentage: number
}

// === ENUMS ===

export enum TokenStatus {
  ACTIVE = 'active',
  PAUSED = 'paused',
  FLAGGED = 'flagged',
  GRADUATED = 'graduated'
}

export enum CurveType {
  LINEAR = 'linear',
  EXPONENTIAL = 'exponential',
  LOGARITHMIC = 'logarithmic',
  SIGMOID = 'sigmoid',
  CONSTANT_PRODUCT = 'constant_product'
}

export enum TradeType {
  BUY = 'buy',
  SELL = 'sell'
}

export enum UserStatus {
  ACTIVE = 'active',
  SUSPENDED = 'suspended',
  BANNED = 'banned'
}

export enum UserRole {
  USER = 'user',
  MODERATOR = 'moderator',
  ADMIN = 'admin',
  SUPER_ADMIN = 'super_admin'
}

// === СТРУКТУРЫ ДАННЫХ ===

export interface BondingCurveParams {
  initial_price: string
  max_price: string
  curve_steepness: number
  liquidity_threshold: string
}

export interface DexListing {
  dex_type: string
  pool_address: string
  listed_at: string
  initial_liquidity: string
}

export interface UserSettings {
  theme: 'light' | 'dark' | 'system'
  notifications: {
    email: boolean
    push: boolean
    trades: boolean
    price_alerts: boolean
  }
  privacy: {
    show_portfolio: boolean
    show_trades: boolean
  }
}

// === API RESPONSES ===

export interface ApiResponse<T> {
  success: boolean
  data: T
  message?: string
  error?: string
  timestamp: string
}

export interface PaginatedResponse<T> {
  data: T[]
  pagination: {
    page: number
    limit: number
    total: number
    pages: number
    has_next: boolean
    has_prev: boolean
  }
}

export interface TradeEstimate {
  input_amount: string
  expected_output: string
  price_per_token: string
  price_impact: number
  estimated_slippage: number
  platform_fee: string
  minimum_output: string
}

// === WEBSOCKET СОБЫТИЯ ===

export interface WSPriceUpdate {
  token_id: string
  price: string
  volume_24h: string
  price_change_24h: number
  market_cap: string
  timestamp: string
}

export interface WSTradeUpdate {
  trade: Trade
  token: Token
  user: Partial<User>
  timestamp: string
}

export interface WSTokenUpdate {
  token: Token
  event_type: 'created' | 'updated' | 'graduated'
  timestamp: string
}

// === FORM ТИПЫ ===

export interface CreateTokenForm {
  name: string
  symbol: string
  description: string
  image?: File
  telegram_link?: string
  twitter_link?: string
  website_link?: string
  initial_liquidity: string
  curve_type: CurveType
}

export interface TradeForm {
  token_id: string
  amount: string
  trade_type: TradeType
  slippage_tolerance: number
}

export interface ProfileForm {
  username: string
  bio: string
  avatar?: File
  settings: UserSettings
}

// === UTILS ТИПЫ ===

export interface ChartDataPoint {
  timestamp: number
  price: number
  volume: number
  market_cap: number
}

export interface PriceAlert {
  id: string
  user_id: string
  token_id: string
  target_price: string
  condition: 'above' | 'below'
  is_active: boolean
  created_at: string
}

export interface Analytics {
  tokens_created_24h: number
  total_volume_24h: string
  active_traders_24h: number
  top_tokens: Token[]
  trending_tokens: Token[]
  recent_trades: Trade[]
}

// === ERROR ТИПЫ ===

export interface ApiError {
  error: boolean
  message: string
  error_code?: string
  details?: Record<string, any>
  timestamp: string
  path: string
}

export class AppError extends Error {
  code: string
  details?: Record<string, any>

  constructor(message: string, code: string = 'UNKNOWN_ERROR', details?: Record<string, any>) {
    super(message)
    this.name = 'AppError'
    this.code = code
    this.details = details
  }
}

// === WALLET ТИПЫ ===

export interface WalletInfo {
  publicKey: string
  connected: boolean
  connecting: boolean
  disconnecting: boolean
  wallet?: {
    adapter: {
      name: string
      icon: string
      url: string
    }
  }
}

export interface WalletBalance {
  sol: string
  tokens: Array<{
    mint: string
    balance: string
    decimals: number
    symbol?: string
  }>
}

// === CONSTANTS ===

export const LAMPORTS_PER_SOL = 1_000_000_000
export const SOL_DECIMALS = 9

export const ERROR_CODES = {
  INSUFFICIENT_BALANCE: 'INSUFFICIENT_BALANCE',
  SLIPPAGE_EXCEEDED: 'SLIPPAGE_EXCEEDED',
  TOKEN_NOT_FOUND: 'TOKEN_NOT_FOUND',
  WALLET_NOT_CONNECTED: 'WALLET_NOT_CONNECTED',
  TRANSACTION_FAILED: 'TRANSACTION_FAILED',
  NETWORK_ERROR: 'NETWORK_ERROR',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  UNAUTHORIZED: 'UNAUTHORIZED',
  RATE_LIMITED: 'RATE_LIMITED',
} as const

export type ErrorCode = typeof ERROR_CODES[keyof typeof ERROR_CODES]