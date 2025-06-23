import * as anchor from "@coral-xyz/anchor";
import { PublicKey, SystemProgram } from "@solana/web3.js";
import { TOKEN_PROGRAM_ID } from "@solana/spl-token";

export interface UpdatePlatformFeeArgs {
  newFeeRate: number;
  reason: string;
}

export interface UpdateTreasuryArgs {
  newTreasury: PublicKey;
  reason: string;
}

export interface TransferAdminArgs {
  newAdmin: PublicKey;
  reason: string;
}

export interface BanTokenArgs {
  tokenMint: PublicKey;
  reason: string;
  isPermanent: boolean;
}

export interface CollectFeesArgs {
  // No additional args needed
}

export interface AdminAccounts {
  [key: string]: PublicKey;
  platformConfig: PublicKey;
  admin: PublicKey;
  systemProgram: PublicKey;
}

export interface ManageTokenAccounts {
  [key: string]: PublicKey;
  tokenInfo: PublicKey;
  mint: PublicKey;
  platformConfig: PublicKey;
  admin: PublicKey;
  systemProgram: PublicKey;
}

export interface CollectFeesAccounts {
  [key: string]: PublicKey;
  platformConfig: PublicKey;
  treasury: PublicKey;
  feeAccumulator: PublicKey;
  admin: PublicKey;
  systemProgram: PublicKey;
}

export async function updatePlatformFee(
  program: anchor.Program,
  args: UpdatePlatformFeeArgs
): Promise<string> {
  const [platformConfigPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("platform_config")],
    program.programId
  );

  const accounts: AdminAccounts = {
    platformConfig: platformConfigPda,
    admin: program.provider.publicKey!,
    systemProgram: SystemProgram.programId,
  };

  const tx = await program.methods
    .updatePlatformFee(args.newFeeRate, args.reason)
    .accounts(accounts)
    .rpc();

  console.log(`Platform fee updated to ${args.newFeeRate}%. Transaction: ${tx}`);
  return tx;
}

export async function updateTreasury(
  program: anchor.Program,
  args: UpdateTreasuryArgs
): Promise<string> {
  const [platformConfigPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("platform_config")],
    program.programId
  );

  const accounts: AdminAccounts = {
    platformConfig: platformConfigPda,
    admin: program.provider.publicKey!,
    systemProgram: SystemProgram.programId,
  };

  const tx = await program.methods
    .updateTreasury(args.newTreasury, args.reason)
    .accounts(accounts)
    .rpc();

  console.log(`Treasury updated to ${args.newTreasury.toString()}. Transaction: ${tx}`);
  return tx;
}

export async function transferAdmin(
  program: anchor.Program,
  args: TransferAdminArgs
): Promise<string> {
  const [platformConfigPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("platform_config")],
    program.programId
  );

  const accounts = {
    platformConfig: platformConfigPda,
    currentAdmin: program.provider.publicKey!,
    newAdmin: args.newAdmin,
    systemProgram: SystemProgram.programId,
  };

  const tx = await program.methods
    .transferAdmin(args.reason)
    .accounts(accounts)
    .rpc();

  console.log(`Admin transferred to ${args.newAdmin.toString()}. Transaction: ${tx}`);
  return tx;
}

export async function banToken(
  program: anchor.Program,
  args: BanTokenArgs
): Promise<string> {
  const [tokenInfoPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("token_info"), args.tokenMint.toBuffer()],
    program.programId
  );

  const [platformConfigPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("platform_config")],
    program.programId
  );

  const accounts: ManageTokenAccounts = {
    tokenInfo: tokenInfoPda,
    mint: args.tokenMint,
    platformConfig: platformConfigPda,
    admin: program.provider.publicKey!,
    systemProgram: SystemProgram.programId,
  };

  const tx = await program.methods
    .banToken(args.reason, args.isPermanent)
    .accounts(accounts)
    .rpc();

  console.log(`Token ${args.tokenMint.toString()} banned. Transaction: ${tx}`);
  return tx;
}

export async function unbanToken(
  program: anchor.Program,
  tokenMint: PublicKey,
  reason: string
): Promise<string> {
  const [tokenInfoPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("token_info"), tokenMint.toBuffer()],
    program.programId
  );

  const [platformConfigPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("platform_config")],
    program.programId
  );

  const accounts: ManageTokenAccounts = {
    tokenInfo: tokenInfoPda,
    mint: tokenMint,
    platformConfig: platformConfigPda,
    admin: program.provider.publicKey!,
    systemProgram: SystemProgram.programId,
  };

  const tx = await program.methods
    .unbanToken(reason)
    .accounts(accounts)
    .rpc();

  console.log(`Token ${tokenMint.toString()} unbanned. Transaction: ${tx}`);
  return tx;
}

export async function collectPlatformFees(
  program: anchor.Program
): Promise<string> {
  const [platformConfigPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("platform_config")],
    program.programId
  );

  const [feeAccumulatorPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("fee_accumulator")],
    program.programId
  );

  // Get platform config to get treasury address
  const platformConfig = await program.account.platformConfig.fetch(platformConfigPda);
  const treasury = (platformConfig as any).treasury;

  const accounts: CollectFeesAccounts = {
    platformConfig: platformConfigPda,
    treasury,
    feeAccumulator: feeAccumulatorPda,
    admin: program.provider.publicKey!,
    systemProgram: SystemProgram.programId,
  };

  const tx = await program.methods
    .collectPlatformFees()
    .accounts(accounts)
    .rpc();

  console.log(`Platform fees collected. Transaction: ${tx}`);
  return tx;
}