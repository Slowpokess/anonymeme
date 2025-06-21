import * as anchor from "@coral-xyz/anchor";
import { PublicKey, SystemProgram, SYSVAR_RENT_PUBKEY } from "@solana/web3.js";

export interface SecurityParams {
  // Торговые лимиты
  maxTradeSize: anchor.BN;
  maxWalletPercentage: number;
  dailyVolumeLimit: anchor.BN;
  hourlyTradeLimit: number;
  
  // Налоги и комиссии
  whaleTaxThreshold: anchor.BN;
  whaleTaxRate: number;
  earlySellTax: number;
  liquidityTax: number;
  
  // Временные ограничения
  minHoldTime: anchor.BN;
  tradeCooldown: anchor.BN;
  creationCooldown: anchor.BN;
  
  // Защитные механизмы
  circuitBreakerThreshold: number;
  maxPriceImpact: number;
  antiBotEnabled: boolean;
  honeypotDetection: boolean;
  
  // Верификация
  requireKycForLargeTrades: boolean;
  minReputationToCreate: number;
  maxTokensPerCreator: number;
}

export interface InitializePlatformArgs {
  feeRate: number;
  treasury: PublicKey;
  securityParams: SecurityParams;
}

export interface InitializePlatformAccounts {
  [key: string]: PublicKey;
  platformConfig: PublicKey;
  admin: PublicKey;
  systemProgram: PublicKey;
  rent: PublicKey;
}

export async function initializePlatform(
  program: any,
  args: InitializePlatformArgs
): Promise<string> {
  const [platformConfigPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("platform_config")],
    program.programId
  );

  const accounts: InitializePlatformAccounts = {
    platformConfig: platformConfigPda,
    admin: program.provider.publicKey!,
    systemProgram: SystemProgram.programId,
    rent: SYSVAR_RENT_PUBKEY,
  };

  const tx = await program.methods
    .initializePlatform(
      args.feeRate,
      args.treasury,
      args.securityParams
    )
    .accounts(accounts)
    .rpc();

  console.log("Platform initialized successfully. Transaction:", tx);
  return tx;
}