import * as anchor from "@coral-xyz/anchor";
import { PublicKey, SystemProgram } from "@solana/web3.js";

export interface ToggleEmergencyPauseArgs {
  pause: boolean;
}

export interface ToggleEmergencyPauseAccounts {
  [key: string]: PublicKey;
  platformConfig: PublicKey;
  admin: PublicKey;
  systemProgram: PublicKey;
}

export async function toggleEmergencyPause(
  program: anchor.Program,
  args: ToggleEmergencyPauseArgs
): Promise<string> {
  const [platformConfigPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("platform_config")],
    program.programId
  );

  const accounts: ToggleEmergencyPauseAccounts = {
    platformConfig: platformConfigPda,
    admin: program.provider.publicKey!,
    systemProgram: SystemProgram.programId,
  };

  const tx = await program.methods
    .toggleEmergencyPause(args.pause)
    .accounts(accounts)
    .rpc();

  const action = args.pause ? "paused" : "resumed";
  console.log(`Platform ${action} successfully. Transaction: ${tx}`);
  return tx;
}