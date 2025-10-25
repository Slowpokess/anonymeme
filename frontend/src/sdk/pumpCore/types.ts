/**
 * 📝 Типы данных для Pump Core SDK
 * Production-ready TypeScript types
 */

import { PublicKey } from '@solana/web3.js'
import BN from 'bn.js'

/**
 * Типы бондинг-кривых
 */
export enum CurveType {
  Linear = 'Linear',
  Exponential = 'Exponential',
  Sigmoid = 'Sigmoid',
  ConstantProduct = 'ConstantProduct',
  Logarithmic = 'Logarithmic',
}

/**
 * Параметры бондинг-кривой
 */
export interface BondingCurveParams {
  curveType: CurveType
  initialPrice: BN
  slope?: BN
  growthFactor?: BN
  midpoint?: BN
  steepness?: BN
  k?: BN
  base?: BN
  scaleFactor?: BN
}

/**
 * Информация о токене
 */
export interface TokenInfo {
  creator: PublicKey
  mint: PublicKey
  bondingCurve: BondingCurveParams
  currentSupply: BN
  currentPrice: BN
  solReserves: BN
  tokenReserves: BN
  graduated: boolean
  graduatedAt?: number
  dexPoolAddress?: PublicKey
  lpMint?: PublicKey
  totalTrades: BN
  volume24h: BN
  createdAt: number
  lastTradeAt: number
  isFlagged: boolean
  flaggedReason?: string
}

/**
 * Конфигурация платформы
 */
export interface PlatformConfig {
  authority: PublicKey
  feeRecipient: PublicKey
  platformFeeBps: number
  graduationThreshold: BN
  isPaused: boolean
  totalTokensCreated: BN
  totalVolumeAllTime: BN
}

/**
 * Блокировка LP токенов
 */
export interface LpTokenLock {
  owner: PublicKey
  lpMint: PublicKey
  tokenMint: PublicKey
  lpVault: PublicKey
  lockedAmount: BN
  unlockedAmount: BN
  lockStart: number
  lockEnd: number
  isLocked: boolean
  vestingEnabled: boolean
  lastUnlockTime: number
}

/**
 * Результат оценки трейда
 */
export interface TradeEstimate {
  inputAmount: BN
  expectedOutput: BN
  pricePerToken: BN
  priceImpact: number // в процентах
  platformFee: BN
  minimumOutput: BN
  slippage: number // в процентах
}

/**
 * Параметры для создания токена
 */
export interface CreateTokenParams {
  name: string
  symbol: string
  uri: string // Metadata URI
  bondingCurve: BondingCurveParams
  decimals?: number
}

/**
 * Параметры для трейда
 */
export interface TradeParams {
  mint: PublicKey
  amount: BN
  isBuy: boolean
  slippageBps: number // Slippage в базисных пунктах (100 = 1%)
  minAmountOut?: BN
}

/**
 * Параметры для градуации на DEX
 */
export interface GraduateToDexParams {
  mint: PublicKey
  lockDuration: number // В секундах
  enableVesting: boolean
}

/**
 * Параметры для блокировки LP токенов
 */
export interface LockLpTokensParams {
  lpMint: PublicKey
  tokenMint: PublicKey
  amount: BN
  lockDuration: number // В секундах
  enableVesting: boolean
}

/**
 * Результат создания токена
 */
export interface CreateTokenResult {
  mint: PublicKey
  tokenInfoPda: PublicKey
  bondingCurveVaultPda: PublicKey
  metadataPda: PublicKey
  signature: string
}

/**
 * Результат трейда
 */
export interface TradeResult {
  signature: string
  inputAmount: BN
  outputAmount: BN
  actualPricePerToken: BN
  platformFee: BN
  newSupply: BN
  newPrice: BN
}

/**
 * Результат градуации
 */
export interface GraduationResult {
  signature: string
  poolAddress: PublicKey
  lpMint: PublicKey
  lpTokensLocked: BN
  lockEndTime: number
}

/**
 * События программы
 */
export interface TokenCreatedEvent {
  creator: PublicKey
  mint: PublicKey
  name: string
  symbol: string
  curveType: CurveType
  timestamp: number
}

export interface TradeExecutedEvent {
  trader: PublicKey
  mint: PublicKey
  isBuy: boolean
  solAmount: BN
  tokenAmount: BN
  newPrice: BN
  timestamp: number
}

export interface TokenGraduatedEvent {
  mint: PublicKey
  poolAddress: PublicKey
  lpMint: PublicKey
  lpTokensLocked: BN
  timestamp: number
}

export interface LpTokensLockedEvent {
  owner: PublicKey
  lpMint: PublicKey
  amount: BN
  lockEnd: number
  vestingEnabled: boolean
  timestamp: number
}

/**
 * Ошибки программы
 */
export enum PumpCoreError {
  InsufficientBalance = 6000,
  InsufficientLiquidity = 6001,
  TokenAlreadyGraduated = 6002,
  GraduationThresholdNotReached = 6003,
  InvalidBondingCurve = 6004,
  SlippageExceeded = 6005,
  PlatformPaused = 6006,
  Unauthorized = 6007,
  InvalidAmount = 6008,
  TokenNotGraduated = 6009,
  AlreadyGraduated = 6010,
  InvalidParameters = 6011,
  OverflowError = 6012,
  UnderflowError = 6013,
  DivisionByZero = 6014,
  InvalidCurveType = 6015,
  LockPeriodNotExpired = 6916,
  LockDurationTooShort = 6917,
  LockDurationTooLong = 6918,
  AlreadyUnlocked = 6919,
  LiquidityNotLocked = 6920,
  InvalidLockDuration = 6921,
  VestingPeriodNotComplete = 6922,
}

/**
 * Опции для транзакций
 */
export interface TransactionOptions {
  skipPreflight?: boolean
  commitment?: 'processed' | 'confirmed' | 'finalized'
  maxRetries?: number
  preflightCommitment?: 'processed' | 'confirmed' | 'finalized'
}

/**
 * Конфигурация SDK
 */
export interface SDKConfig {
  programId?: PublicKey
  commitment?: 'processed' | 'confirmed' | 'finalized'
  rpcUrl?: string
  skipPreflight?: boolean
}
