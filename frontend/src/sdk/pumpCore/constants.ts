/**
 * 🔧 Константы для Pump Core программы
 * Production-ready константы и настройки
 */

import { PublicKey } from '@solana/web3.js'

/**
 * Program ID (будет обновлен после deployment)
 * Сейчас используется placeholder
 */
export const PUMP_CORE_PROGRAM_ID = new PublicKey(
  process.env.NEXT_PUBLIC_PUMP_CORE_PROGRAM_ID ||
  '11111111111111111111111111111111' // Placeholder
)

/**
 * Seeds для PDA (Program Derived Addresses)
 */
export const SEEDS = {
  PLATFORM_CONFIG: 'platform_config',
  TOKEN_INFO: 'token_info',
  BONDING_CURVE_VAULT: 'bonding_curve_vault',
  METADATA: 'metadata',
  LP_TOKEN_LOCK: 'lp_token_lock',
} as const

/**
 * Raydium константы
 */
export const RAYDIUM = {
  AMM_PROGRAM_ID: new PublicKey('675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8'),
  AUTHORITY_V4: new PublicKey('5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1'),
  WSOL_MINT: new PublicKey('So11111111111111111111111111111111111111112'),
} as const

/**
 * Метаданные токенов (Metaplex)
 */
export const METADATA = {
  PROGRAM_ID: new PublicKey('metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s'),
} as const

/**
 * SPL Token константы
 */
export const TOKEN = {
  PROGRAM_ID: new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'),
  ASSOCIATED_PROGRAM_ID: new PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL'),
} as const

/**
 * Лимиты и пороги
 */
export const LIMITS = {
  MIN_LOCK_DURATION: 86_400, // 1 день в секундах
  MAX_LOCK_DURATION: 31_536_000, // 365 дней в секундах
  GRADUATION_THRESHOLD: 500_000_000_000, // 500k токенов
  PLATFORM_FEE_BPS: 100, // 1% в базисных пунктах
} as const

/**
 * Decimals для SOL
 */
export const SOL_DECIMALS = 9
export const LAMPORTS_PER_SOL = 1_000_000_000

/**
 * RPC endpoints по умолчанию
 */
export const RPC_ENDPOINTS = {
  DEVNET: 'https://api.devnet.solana.com',
  TESTNET: 'https://api.testnet.solana.com',
  MAINNET: 'https://api.mainnet-beta.solana.com',
} as const

/**
 * Commitment levels
 */
export const DEFAULT_COMMITMENT = 'confirmed' as const
export const FINALIZED_COMMITMENT = 'finalized' as const
