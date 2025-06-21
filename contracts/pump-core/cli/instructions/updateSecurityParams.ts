import * as anchor from "@coral-xyz/anchor";
import { PublicKey, SystemProgram } from "@solana/web3.js";

export interface UpdateSecurityParamsArgs {
  newParams: {
    maxTradeAmount: anchor.BN;
    minHoldTime: anchor.BN;
    maxSlippage: number;
    whaleProtectionThreshold: anchor.BN;
    botDetectionEnabled: boolean;
    dailyVolumeLimit: anchor.BN;
    hourlyTradeLimit: number;
    priceImpactLimit: number;
    circuitBreakerThreshold: number;
    emergencyPauseEnabled: boolean;
  };
}

export interface UpdateSecurityParamsAccounts {
  [key: string]: PublicKey;
  platformConfig: PublicKey;
  admin: PublicKey;
  systemProgram: PublicKey;
}

export async function updateSecurityParams(
  program: anchor.Program,
  args: UpdateSecurityParamsArgs
): Promise<string> {
  const [platformConfigPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("platform_config")],
    program.programId
  );

  const accounts: UpdateSecurityParamsAccounts = {
    platformConfig: platformConfigPda,
    admin: program.provider.publicKey!,
    systemProgram: SystemProgram.programId,
  };

  const tx = await program.methods
    .updateSecurityParams(args.newParams)
    .accounts(accounts)
    .rpc();

  console.log(`Security parameters updated successfully. Transaction: ${tx}`);
  return tx;
}