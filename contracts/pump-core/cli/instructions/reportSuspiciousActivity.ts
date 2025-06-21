import * as anchor from "@coral-xyz/anchor";
import { PublicKey, SystemProgram } from "@solana/web3.js";

export enum ReportReason {
  BotActivity = "BotActivity",
  MarketManipulation = "MarketManipulation", 
  SuspiciousVolume = "SuspiciousVolume",
  PumpAndDump = "PumpAndDump",
  Honeypot = "Honeypot",
  ScamToken = "ScamToken",
  Other = "Other"
}

export interface ReportSuspiciousActivityArgs {
  reportedUser: PublicKey;
  reason: ReportReason;
  description: string;
}

export interface ReportSuspiciousActivityAccounts {
  [key: string]: PublicKey;
  userProfile: PublicKey;
  reportedUserProfile: PublicKey;
  platformConfig: PublicKey;
  reporter: PublicKey;
  reportedUser: PublicKey;
  systemProgram: PublicKey;
}

export async function reportSuspiciousActivity(
  program: anchor.Program,
  args: ReportSuspiciousActivityArgs
): Promise<string> {
  const [reporterProfilePda] = PublicKey.findProgramAddressSync(
    [Buffer.from("user_profile"), program.provider.publicKey!.toBuffer()],
    program.programId
  );

  const [reportedUserProfilePda] = PublicKey.findProgramAddressSync(
    [Buffer.from("user_profile"), args.reportedUser.toBuffer()],
    program.programId
  );

  const [platformConfigPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("platform_config")],
    program.programId
  );

  const accounts: ReportSuspiciousActivityAccounts = {
    userProfile: reporterProfilePda,
    reportedUserProfile: reportedUserProfilePda,
    platformConfig: platformConfigPda,
    reporter: program.provider.publicKey!,
    reportedUser: args.reportedUser,
    systemProgram: SystemProgram.programId,
  };

  const tx = await program.methods
    .reportSuspiciousActivity(
      args.reportedUser,
      args.reason,
      args.description
    )
    .accounts(accounts)
    .rpc();

  console.log(`Suspicious activity reported successfully. Reason: ${args.reason}, Transaction: ${tx}`);
  return tx;
}