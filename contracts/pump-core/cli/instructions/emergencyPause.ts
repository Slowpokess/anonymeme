import * as anchor from "@coral-xyz/anchor";
import { PublicKey, SystemProgram } from "@solana/web3.js";

export interface EmergencyPauseArgs {
  pause: boolean;
  reason: string;
}

export interface EmergencyPauseAccounts {
  [key: string]: PublicKey;
  platformConfig: PublicKey;
  admin: PublicKey;
  systemProgram: PublicKey;
}

export async function emergencyPause(
  program: anchor.Program,
  args: EmergencyPauseArgs
): Promise<string> {
  const [platformConfigPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("platform_config")],
    program.programId
  );

  const accounts: EmergencyPauseAccounts = {
    platformConfig: platformConfigPda,
    admin: program.provider.publicKey!,
    systemProgram: SystemProgram.programId,
  };

  const tx = await program.methods
    .emergencyPausePlatform(args.pause, args.reason)
    .accounts(accounts)
    .rpc();

  console.log(`Platform ${args.pause ? 'paused' : 'unpaused'} successfully. Transaction: ${tx}`);
  return tx;
}

export interface TradingPauseArgs {
  pause: boolean;
  reason: string;
}

export interface TradingPauseAccounts {
  [key: string]: PublicKey;
  platformConfig: PublicKey;
  admin: PublicKey;
  systemProgram: PublicKey;
}

export async function pauseTrading(
  program: anchor.Program,
  args: TradingPauseArgs
): Promise<string> {
  const [platformConfigPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("platform_config")],
    program.programId
  );

  const accounts: TradingPauseAccounts = {
    platformConfig: platformConfigPda,
    admin: program.provider.publicKey!,
    systemProgram: SystemProgram.programId,
  };

  const tx = await program.methods
    .pauseTradingOnly(args.pause, args.reason)
    .accounts(accounts)
    .rpc();

  console.log(`Trading ${args.pause ? 'paused' : 'resumed'} successfully. Transaction: ${tx}`);
  return tx;
}