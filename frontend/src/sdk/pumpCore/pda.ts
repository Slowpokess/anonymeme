/**
 * 🔑 PDA (Program Derived Address) Helpers
 * Функции для расчета всех PDA адресов программы
 */

import { PublicKey } from '@solana/web3.js'
import { PUMP_CORE_PROGRAM_ID, SEEDS, METADATA as METADATA_CONSTANTS } from './constants'

/**
 * Результат расчета PDA
 */
export interface PDAResult {
  address: PublicKey
  bump: number
}

/**
 * Получить PDA для конфигурации платформы
 */
export function getPlatformConfigPDA(programId: PublicKey = PUMP_CORE_PROGRAM_ID): PDAResult {
  const [address, bump] = PublicKey.findProgramAddressSync(
    [Buffer.from(SEEDS.PLATFORM_CONFIG)],
    programId
  )

  return { address, bump }
}

/**
 * Получить PDA для информации о токене
 */
export function getTokenInfoPDA(
  mint: PublicKey,
  programId: PublicKey = PUMP_CORE_PROGRAM_ID
): PDAResult {
  const [address, bump] = PublicKey.findProgramAddressSync(
    [Buffer.from(SEEDS.TOKEN_INFO), mint.toBuffer()],
    programId
  )

  return { address, bump }
}

/**
 * Получить PDA для хранилища бондинг-кривой
 */
export function getBondingCurveVaultPDA(
  mint: PublicKey,
  programId: PublicKey = PUMP_CORE_PROGRAM_ID
): PDAResult {
  const [address, bump] = PublicKey.findProgramAddressSync(
    [Buffer.from(SEEDS.BONDING_CURVE_VAULT), mint.toBuffer()],
    programId
  )

  return { address, bump }
}

/**
 * Получить PDA для метаданных токена (Metaplex)
 */
export function getMetadataPDA(mint: PublicKey): PDAResult {
  const [address, bump] = PublicKey.findProgramAddressSync(
    [
      Buffer.from('metadata'),
      METADATA_CONSTANTS.PROGRAM_ID.toBuffer(),
      mint.toBuffer(),
    ],
    METADATA_CONSTANTS.PROGRAM_ID
  )

  return { address, bump }
}

/**
 * Получить PDA для блокировки LP токенов
 */
export function getLpTokenLockPDA(
  owner: PublicKey,
  lpMint: PublicKey,
  programId: PublicKey = PUMP_CORE_PROGRAM_ID
): PDAResult {
  const [address, bump] = PublicKey.findProgramAddressSync(
    [Buffer.from(SEEDS.LP_TOKEN_LOCK), owner.toBuffer(), lpMint.toBuffer()],
    programId
  )

  return { address, bump }
}

/**
 * Получить Associated Token Address
 */
export async function getAssociatedTokenAddress(
  mint: PublicKey,
  owner: PublicKey,
  allowOwnerOffCurve = false,
  programId: PublicKey = new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'),
  associatedTokenProgramId: PublicKey = new PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL')
): Promise<PublicKey> {
  if (!allowOwnerOffCurve && !PublicKey.isOnCurve(owner.toBuffer())) {
    throw new Error('Owner is not on curve')
  }

  const [address] = await PublicKey.findProgramAddress(
    [owner.toBuffer(), programId.toBuffer(), mint.toBuffer()],
    associatedTokenProgramId
  )

  return address
}

/**
 * Получить все PDA для токена одним вызовом
 */
export interface TokenPDAs {
  tokenInfo: PDAResult
  bondingCurveVault: PDAResult
  metadata: PDAResult
}

export function getTokenPDAs(
  mint: PublicKey,
  programId: PublicKey = PUMP_CORE_PROGRAM_ID
): TokenPDAs {
  return {
    tokenInfo: getTokenInfoPDA(mint, programId),
    bondingCurveVault: getBondingCurveVaultPDA(mint, programId),
    metadata: getMetadataPDA(mint),
  }
}

/**
 * Проверка корректности PDA
 */
export async function verifyPDA(
  pda: PublicKey,
  seeds: Buffer[],
  programId: PublicKey
): Promise<boolean> {
  try {
    const [derivedPDA] = await PublicKey.findProgramAddress(seeds, programId)
    return derivedPDA.equals(pda)
  } catch {
    return false
  }
}

/**
 * Batch расчет нескольких PDA
 */
export function batchCalculatePDAs<T extends Record<string, () => PDAResult>>(
  calculators: T
): { [K in keyof T]: PublicKey } {
  const result: any = {}

  for (const [key, calculator] of Object.entries(calculators)) {
    result[key] = calculator().address
  }

  return result
}
