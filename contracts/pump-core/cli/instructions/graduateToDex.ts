import * as anchor from "@coral-xyz/anchor";
import { PublicKey, SystemProgram } from "@solana/web3.js";
import { 
  TOKEN_PROGRAM_ID, 
  ASSOCIATED_TOKEN_PROGRAM_ID,
  getAssociatedTokenAddress 
} from "@solana/spl-token";

export enum DexType {
  Raydium = "Raydium",
  Jupiter = "Jupiter", 
  Orca = "Orca"
}

export interface GraduateToDexArgs {
  dexType: DexType;
  initialLiquidity: anchor.BN;
}

export interface GraduateToDexAccounts {
  [key: string]: PublicKey;
  tokenInfo: PublicKey;
  mint: PublicKey;
  bondingCurveVault: PublicKey;
  bondingCurveTokenAccount: PublicKey;
  platformConfig: PublicKey;
  creator: PublicKey;
  treasury: PublicKey;
  tokenProgram: PublicKey;
  associatedTokenProgram: PublicKey;
  systemProgram: PublicKey;
  // DEX-specific accounts would be added here dynamically
}

export async function graduateToDex(
  program: anchor.Program,
  mint: PublicKey,
  args: GraduateToDexArgs
): Promise<string> {
  const [tokenInfoPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("token_info"), mint.toBuffer()],
    program.programId
  );

  const [bondingCurveVault] = PublicKey.findProgramAddressSync(
    [Buffer.from("bonding_curve_vault"), mint.toBuffer()],
    program.programId
  );

  const [platformConfigPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("platform_config")],
    program.programId
  );

  const bondingCurveTokenAccount = await getAssociatedTokenAddress(
    mint,
    bondingCurveVault,
    true
  );

  // Get platform config to get treasury and creator info
  const platformConfig = await program.account.platformConfig.fetch(platformConfigPda);
  const treasury = (platformConfig as any).treasury;

  // Get token info to get creator
  const tokenInfo = await program.account.tokenInfo.fetch(tokenInfoPda);
  const creator = (tokenInfo as any).creator;

  const accounts: GraduateToDexAccounts = {
    tokenInfo: tokenInfoPda,
    mint,
    bondingCurveVault,
    bondingCurveTokenAccount,
    platformConfig: platformConfigPda,
    creator,
    treasury,
    tokenProgram: TOKEN_PROGRAM_ID,
    associatedTokenProgram: ASSOCIATED_TOKEN_PROGRAM_ID,
    systemProgram: SystemProgram.programId,
  };

  const tx = await program.methods
    .graduateToDex(
      args.dexType,
      args.initialLiquidity
    )
    .accounts(accounts)
    .rpc();

  console.log(`Token graduated to ${args.dexType} successfully. Transaction: ${tx}`);
  return tx;
}