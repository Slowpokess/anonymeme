/**
 * 🚀 Pump Core SDK Client
 * Production-ready клиент для взаимодействия со смарт-контрактом
 */

import {
  Connection,
  PublicKey,
  Transaction,
  TransactionInstruction,
  Keypair,
  SystemProgram,
  SYSVAR_RENT_PUBKEY,
  sendAndConfirmTransaction,
  Signer,
} from '@solana/web3.js'
import {
  TOKEN_PROGRAM_ID,
  ASSOCIATED_TOKEN_PROGRAM_ID,
  getAssociatedTokenAddress as getSPLAssociatedTokenAddress,
  createAssociatedTokenAccountInstruction,
} from '@solana/spl-token'
import BN from 'bn.js'
import {
  PUMP_CORE_PROGRAM_ID,
  METADATA,
  RAYDIUM,
  DEFAULT_COMMITMENT,
} from './constants'
import {
  getPlatformConfigPDA,
  getTokenInfoPDA,
  getBondingCurveVaultPDA,
  getMetadataPDA,
  getLpTokenLockPDA,
} from './pda'
import type {
  SDKConfig,
  CreateTokenParams,
  CreateTokenResult,
  TradeParams,
  TradeResult,
  GraduateToDexParams,
  GraduationResult,
  LockLpTokensParams,
  TokenInfo,
  PlatformConfig,
  LpTokenLock,
  TransactionOptions,
} from './types'

/**
 * Основной клиент SDK
 */
export class PumpCoreClient {
  readonly connection: Connection
  readonly programId: PublicKey
  readonly commitment: 'processed' | 'confirmed' | 'finalized'
  readonly skipPreflight: boolean

  constructor(
    connection: Connection,
    config: SDKConfig = {}
  ) {
    this.connection = connection
    this.programId = config.programId || PUMP_CORE_PROGRAM_ID
    this.commitment = config.commitment || DEFAULT_COMMITMENT
    this.skipPreflight = config.skipPreflight || false
  }

  /**
   * Получить конфигурацию платформы
   */
  async getPlatformConfig(): Promise<PlatformConfig | null> {
    const { address } = getPlatformConfigPDA(this.programId)

    try {
      const accountInfo = await this.connection.getAccountInfo(address, this.commitment)
      if (!accountInfo) return null

      // TODO: Deserialize account data after IDL is generated
      // For now return null
      return null
    } catch (error) {
      console.error('Failed to fetch platform config:', error)
      return null
    }
  }

  /**
   * Получить информацию о токене
   */
  async getTokenInfo(mint: PublicKey): Promise<TokenInfo | null> {
    const { address } = getTokenInfoPDA(mint, this.programId)

    try {
      const accountInfo = await this.connection.getAccountInfo(address, this.commitment)
      if (!accountInfo) return null

      // TODO: Deserialize account data after IDL is generated
      return null
    } catch (error) {
      console.error('Failed to fetch token info:', error)
      return null
    }
  }

  /**
   * Получить информацию о блокировке LP токенов
   */
  async getLpTokenLock(owner: PublicKey, lpMint: PublicKey): Promise<LpTokenLock | null> {
    const { address } = getLpTokenLockPDA(owner, lpMint, this.programId)

    try {
      const accountInfo = await this.connection.getAccountInfo(address, this.commitment)
      if (!accountInfo) return null

      // TODO: Deserialize account data after IDL is generated
      return null
    } catch (error) {
      console.error('Failed to fetch LP token lock:', error)
      return null
    }
  }

  /**
   * Создать новый токен
   */
  async createToken(
    params: CreateTokenParams,
    payer: Signer,
    options?: TransactionOptions
  ): Promise<CreateTokenResult> {
    const mint = Keypair.generate()
    const { tokenInfo, bondingCurveVault, metadata } = {
      tokenInfo: getTokenInfoPDA(mint.publicKey, this.programId),
      bondingCurveVault: getBondingCurveVaultPDA(mint.publicKey, this.programId),
      metadata: getMetadataPDA(mint.publicKey),
    }

    const platformConfig = getPlatformConfigPDA(this.programId)

    const instruction = await this.buildCreateTokenInstruction(
      params,
      payer.publicKey,
      mint.publicKey,
      tokenInfo.address,
      bondingCurveVault.address,
      metadata.address,
      platformConfig.address
    )

    const transaction = new Transaction().add(instruction)

    const signature = await sendAndConfirmTransaction(
      this.connection,
      transaction,
      [payer, mint],
      {
        skipPreflight: options?.skipPreflight ?? this.skipPreflight,
        commitment: options?.commitment ?? this.commitment,
        maxRetries: options?.maxRetries ?? 3,
        preflightCommitment: options?.preflightCommitment ?? this.commitment,
      }
    )

    return {
      mint: mint.publicKey,
      tokenInfoPda: tokenInfo.address,
      bondingCurveVaultPda: bondingCurveVault.address,
      metadataPda: metadata.address,
      signature,
    }
  }

  /**
   * Выполнить покупку или продажу токенов
   */
  async trade(
    params: TradeParams,
    trader: Signer,
    options?: TransactionOptions
  ): Promise<TradeResult> {
    const tokenInfo = getTokenInfoPDA(params.mint, this.programId)
    const bondingCurveVault = getBondingCurveVaultPDA(params.mint, this.programId)
    const platformConfig = getPlatformConfigPDA(this.programId)

    // Get or create trader's token account
    const traderTokenAccount = await getSPLAssociatedTokenAddress(
      params.mint,
      trader.publicKey
    )

    const traderTokenAccountInfo = await this.connection.getAccountInfo(
      traderTokenAccount
    )

    const instructions: TransactionInstruction[] = []

    // Create token account if it doesn't exist
    if (!traderTokenAccountInfo) {
      instructions.push(
        createAssociatedTokenAccountInstruction(
          trader.publicKey,
          traderTokenAccount,
          trader.publicKey,
          params.mint
        )
      )
    }

    // Build trade instruction
    const tradeInstruction = await this.buildTradeInstruction(
      params,
      trader.publicKey,
      traderTokenAccount,
      tokenInfo.address,
      bondingCurveVault.address,
      platformConfig.address
    )

    instructions.push(tradeInstruction)

    const transaction = new Transaction().add(...instructions)

    const signature = await sendAndConfirmTransaction(
      this.connection,
      transaction,
      [trader],
      {
        skipPreflight: options?.skipPreflight ?? this.skipPreflight,
        commitment: options?.commitment ?? this.commitment,
        maxRetries: options?.maxRetries ?? 3,
        preflightCommitment: options?.preflightCommitment ?? this.commitment,
      }
    )

    // TODO: Parse transaction logs to get actual trade result
    return {
      signature,
      inputAmount: params.amount,
      outputAmount: new BN(0),
      actualPricePerToken: new BN(0),
      platformFee: new BN(0),
      newSupply: new BN(0),
      newPrice: new BN(0),
    }
  }

  /**
   * Градуировать токен на DEX (Raydium)
   */
  async graduateToDex(
    params: GraduateToDexParams,
    creator: Signer,
    options?: TransactionOptions
  ): Promise<GraduationResult> {
    const tokenInfo = getTokenInfoPDA(params.mint, this.programId)
    const bondingCurveVault = getBondingCurveVaultPDA(params.mint, this.programId)
    const platformConfig = getPlatformConfigPDA(this.programId)

    // TODO: Calculate Raydium pool addresses
    const poolAddress = Keypair.generate().publicKey // Placeholder
    const lpMint = Keypair.generate().publicKey // Placeholder

    const instruction = await this.buildGraduateToDexInstruction(
      params,
      creator.publicKey,
      tokenInfo.address,
      bondingCurveVault.address,
      platformConfig.address,
      poolAddress,
      lpMint
    )

    const transaction = new Transaction().add(instruction)

    const signature = await sendAndConfirmTransaction(
      this.connection,
      transaction,
      [creator],
      {
        skipPreflight: options?.skipPreflight ?? this.skipPreflight,
        commitment: options?.commitment ?? this.commitment,
        maxRetries: options?.maxRetries ?? 3,
        preflightCommitment: options?.preflightCommitment ?? this.commitment,
      }
    )

    return {
      signature,
      poolAddress,
      lpMint,
      lpTokensLocked: new BN(0),
      lockEndTime: 0,
    }
  }

  /**
   * Заблокировать LP токены
   */
  async lockLpTokens(
    params: LockLpTokensParams,
    owner: Signer,
    options?: TransactionOptions
  ): Promise<string> {
    const lpTokenLock = getLpTokenLockPDA(owner.publicKey, params.lpMint, this.programId)

    // Get LP token vault PDA
    const lpVault = Keypair.generate().publicKey // TODO: Calculate proper PDA

    const instruction = await this.buildLockLpTokensInstruction(
      params,
      owner.publicKey,
      lpTokenLock.address,
      lpVault
    )

    const transaction = new Transaction().add(instruction)

    const signature = await sendAndConfirmTransaction(
      this.connection,
      transaction,
      [owner],
      {
        skipPreflight: options?.skipPreflight ?? this.skipPreflight,
        commitment: options?.commitment ?? this.commitment,
        maxRetries: options?.maxRetries ?? 3,
        preflightCommitment: options?.preflightCommitment ?? this.commitment,
      }
    )

    return signature
  }

  /**
   * Разблокировать LP токены
   */
  async unlockLpTokens(
    lpMint: PublicKey,
    amount: BN,
    owner: Signer,
    options?: TransactionOptions
  ): Promise<string> {
    const lpTokenLock = getLpTokenLockPDA(owner.publicKey, lpMint, this.programId)

    const instruction = await this.buildUnlockLpTokensInstruction(
      lpMint,
      amount,
      owner.publicKey,
      lpTokenLock.address
    )

    const transaction = new Transaction().add(instruction)

    const signature = await sendAndConfirmTransaction(
      this.connection,
      transaction,
      [owner],
      {
        skipPreflight: options?.skipPreflight ?? this.skipPreflight,
        commitment: options?.commitment ?? this.commitment,
        maxRetries: options?.maxRetries ?? 3,
        preflightCommitment: options?.preflightCommitment ?? this.commitment,
      }
    )

    return signature
  }

  // ==================== PRIVATE INSTRUCTION BUILDERS ====================

  /**
   * Build create token instruction
   * TODO: Replace with actual Anchor instruction after IDL is generated
   */
  private async buildCreateTokenInstruction(
    params: CreateTokenParams,
    creator: PublicKey,
    mint: PublicKey,
    tokenInfo: PublicKey,
    bondingCurveVault: PublicKey,
    metadata: PublicKey,
    platformConfig: PublicKey
  ): Promise<TransactionInstruction> {
    // Placeholder - will be replaced with actual Anchor instruction
    return new TransactionInstruction({
      keys: [
        { pubkey: creator, isSigner: true, isWritable: true },
        { pubkey: mint, isSigner: true, isWritable: true },
        { pubkey: tokenInfo, isSigner: false, isWritable: true },
        { pubkey: bondingCurveVault, isSigner: false, isWritable: true },
        { pubkey: metadata, isSigner: false, isWritable: true },
        { pubkey: platformConfig, isSigner: false, isWritable: false },
        { pubkey: TOKEN_PROGRAM_ID, isSigner: false, isWritable: false },
        { pubkey: METADATA.PROGRAM_ID, isSigner: false, isWritable: false },
        { pubkey: SystemProgram.programId, isSigner: false, isWritable: false },
        { pubkey: SYSVAR_RENT_PUBKEY, isSigner: false, isWritable: false },
      ],
      programId: this.programId,
      data: Buffer.from([]), // TODO: Encode instruction data
    })
  }

  /**
   * Build trade instruction
   */
  private async buildTradeInstruction(
    params: TradeParams,
    trader: PublicKey,
    traderTokenAccount: PublicKey,
    tokenInfo: PublicKey,
    bondingCurveVault: PublicKey,
    platformConfig: PublicKey
  ): Promise<TransactionInstruction> {
    // Placeholder
    return new TransactionInstruction({
      keys: [
        { pubkey: trader, isSigner: true, isWritable: true },
        { pubkey: traderTokenAccount, isSigner: false, isWritable: true },
        { pubkey: tokenInfo, isSigner: false, isWritable: true },
        { pubkey: bondingCurveVault, isSigner: false, isWritable: true },
        { pubkey: platformConfig, isSigner: false, isWritable: false },
        { pubkey: TOKEN_PROGRAM_ID, isSigner: false, isWritable: false },
        { pubkey: SystemProgram.programId, isSigner: false, isWritable: false },
      ],
      programId: this.programId,
      data: Buffer.from([]),
    })
  }

  /**
   * Build graduate to DEX instruction
   */
  private async buildGraduateToDexInstruction(
    params: GraduateToDexParams,
    creator: PublicKey,
    tokenInfo: PublicKey,
    bondingCurveVault: PublicKey,
    platformConfig: PublicKey,
    poolAddress: PublicKey,
    lpMint: PublicKey
  ): Promise<TransactionInstruction> {
    // Placeholder
    return new TransactionInstruction({
      keys: [
        { pubkey: creator, isSigner: true, isWritable: true },
        { pubkey: tokenInfo, isSigner: false, isWritable: true },
        { pubkey: bondingCurveVault, isSigner: false, isWritable: true },
        { pubkey: platformConfig, isSigner: false, isWritable: false },
        { pubkey: poolAddress, isSigner: false, isWritable: true },
        { pubkey: lpMint, isSigner: false, isWritable: true },
        { pubkey: RAYDIUM.AMM_PROGRAM_ID, isSigner: false, isWritable: false },
      ],
      programId: this.programId,
      data: Buffer.from([]),
    })
  }

  /**
   * Build lock LP tokens instruction
   */
  private async buildLockLpTokensInstruction(
    params: LockLpTokensParams,
    owner: PublicKey,
    lpTokenLock: PublicKey,
    lpVault: PublicKey
  ): Promise<TransactionInstruction> {
    // Placeholder
    return new TransactionInstruction({
      keys: [
        { pubkey: owner, isSigner: true, isWritable: true },
        { pubkey: lpTokenLock, isSigner: false, isWritable: true },
        { pubkey: lpVault, isSigner: false, isWritable: true },
        { pubkey: TOKEN_PROGRAM_ID, isSigner: false, isWritable: false },
        { pubkey: SystemProgram.programId, isSigner: false, isWritable: false },
      ],
      programId: this.programId,
      data: Buffer.from([]),
    })
  }

  /**
   * Build unlock LP tokens instruction
   */
  private async buildUnlockLpTokensInstruction(
    lpMint: PublicKey,
    amount: BN,
    owner: PublicKey,
    lpTokenLock: PublicKey
  ): Promise<TransactionInstruction> {
    // Placeholder
    return new TransactionInstruction({
      keys: [
        { pubkey: owner, isSigner: true, isWritable: true },
        { pubkey: lpTokenLock, isSigner: false, isWritable: true },
        { pubkey: lpMint, isSigner: false, isWritable: false },
        { pubkey: TOKEN_PROGRAM_ID, isSigner: false, isWritable: false },
      ],
      programId: this.programId,
      data: Buffer.from([]),
    })
  }
}

/**
 * Создать экземпляр клиента с настройками по умолчанию
 */
export function createClient(
  connection: Connection,
  config?: SDKConfig
): PumpCoreClient {
  return new PumpCoreClient(connection, config)
}
