import * as anchor from "@coral-xyz/anchor";
import { PublicKey, SystemProgram } from "@solana/web3.js";

export interface UpdateUserReputationArgs {
  reputationDelta: number;
}

export interface UpdateUserReputationAccounts {
  [key: string]: PublicKey;
  userProfile: PublicKey;
  platformConfig: PublicKey;
  admin: PublicKey;
  targetUser: PublicKey;
  systemProgram: PublicKey;
}

export async function updateUserReputation(
  program: anchor.Program,
  targetUser: PublicKey,
  args: UpdateUserReputationArgs
): Promise<string> {
  const [userProfilePda] = PublicKey.findProgramAddressSync(
    [Buffer.from("user_profile"), targetUser.toBuffer()],
    program.programId
  );

  const [platformConfigPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("platform_config")],
    program.programId
  );

  const accounts: UpdateUserReputationAccounts = {
    userProfile: userProfilePda,
    platformConfig: platformConfigPda,
    admin: program.provider.publicKey!,
    targetUser,
    systemProgram: SystemProgram.programId,
  };

  const tx = await program.methods
    .updateUserReputation(args.reputationDelta)
    .accounts(accounts)
    .rpc();

  const change = args.reputationDelta > 0 ? "increased" : "decreased";
  console.log(`User reputation ${change} by ${Math.abs(args.reputationDelta)} points. Transaction: ${tx}`);
  return tx;
}