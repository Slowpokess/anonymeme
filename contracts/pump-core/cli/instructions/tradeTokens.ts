import * as anchor from "@coral-xyz/anchor";
import { PublicKey, SystemProgram, SYSVAR_RENT_PUBKEY } from "@solana/web3.js";
import { 
  TOKEN_PROGRAM_ID, 
  ASSOCIATED_TOKEN_PROGRAM_ID,
  getAssociatedTokenAddress 
} from "@solana/spl-token";

export interface BuyTokensArgs {
  solAmount: anchor.BN;
  minTokensOut: anchor.BN;
  slippageTolerance: number;
}

export interface SellTokensArgs {
  tokenAmount: anchor.BN;
  minSolOut: anchor.BN;
  slippageTolerance: number;
}

export interface BuyTokensAccounts {
  [key: string]: PublicKey;
  tokenInfo: PublicKey;
  mint: PublicKey;
  bondingCurveVault: PublicKey;
  bondingCurveTokenAccount: PublicKey;
  traderTokenAccount: PublicKey;
  traderProfile: PublicKey;
  platformConfig: PublicKey;
  treasury: PublicKey;
  trader: PublicKey;
  tokenProgram: PublicKey;
  associatedTokenProgram: PublicKey;
  systemProgram: PublicKey;
  rent: PublicKey;
}

export interface SellTokensAccounts {
  [key: string]: PublicKey;
  tokenInfo: PublicKey;
  mint: PublicKey;
  bondingCurveVault: PublicKey; 
  bondingCurveTokenAccount: PublicKey;
  traderTokenAccount: PublicKey;
  traderProfile: PublicKey;
  platformConfig: PublicKey;
  treasury: PublicKey;
  trader: PublicKey;
  tokenProgram: PublicKey;
  associatedTokenProgram: PublicKey;
  systemProgram: PublicKey;
  rent: PublicKey;
}

export async function buyTokens(
  program: any,
  mint: PublicKey,
  args: BuyTokensArgs
): Promise<string> {
  const [tokenInfoPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("token_info"), mint.toBuffer()],
    program.programId
  );

  const [bondingCurveVault] = PublicKey.findProgramAddressSync(
    [Buffer.from("bonding_curve_vault"), mint.toBuffer()],
    program.programId
  );

  const [userProfilePda] = PublicKey.findProgramAddressSync(
    [Buffer.from("user_profile"), program.provider.publicKey!.toBuffer()],
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

  const userTokenAccount = await getAssociatedTokenAddress(
    mint,
    program.provider.publicKey!
  );

  // Get treasury address from platform config
  const platformConfig = await program.account.platformConfig.fetch(platformConfigPda);
  const treasury = (platformConfig as any).treasury;

  const accounts: BuyTokensAccounts = {
    tokenInfo: tokenInfoPda,
    mint,
    bondingCurveVault,
    bondingCurveTokenAccount,
    traderTokenAccount: userTokenAccount,
    traderProfile: userProfilePda,
    platformConfig: platformConfigPda,
    treasury,
    trader: program.provider.publicKey!,
    tokenProgram: TOKEN_PROGRAM_ID,
    associatedTokenProgram: ASSOCIATED_TOKEN_PROGRAM_ID,
    systemProgram: SystemProgram.programId,
    rent: SYSVAR_RENT_PUBKEY,
  };

  const tx = await program.methods
    .buyTokens(
      args.solAmount,
      args.minTokensOut,
      args.slippageTolerance
    )
    .accounts(accounts)
    .rpc();

  console.log(`Tokens bought successfully. Transaction: ${tx}`);
  return tx;
}

export async function sellTokens(
  program: any,
  mint: PublicKey,
  args: SellTokensArgs
): Promise<string> {
  const [tokenInfoPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("token_info"), mint.toBuffer()],
    program.programId
  );

  const [bondingCurveVault] = PublicKey.findProgramAddressSync(
    [Buffer.from("bonding_curve_vault"), mint.toBuffer()],
    program.programId
  );

  const [userProfilePda] = PublicKey.findProgramAddressSync(
    [Buffer.from("user_profile"), program.provider.publicKey!.toBuffer()],
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

  const userTokenAccount = await getAssociatedTokenAddress(
    mint,
    program.provider.publicKey!
  );

  // Get treasury address from platform config
  const platformConfig = await program.account.platformConfig.fetch(platformConfigPda);
  const treasury = (platformConfig as any).treasury;

  const accounts: SellTokensAccounts = {
    tokenInfo: tokenInfoPda,
    mint,
    bondingCurveVault,
    bondingCurveTokenAccount,
    traderTokenAccount: userTokenAccount,
    traderProfile: userProfilePda,
    platformConfig: platformConfigPda,
    treasury,
    trader: program.provider.publicKey!,
    tokenProgram: TOKEN_PROGRAM_ID,
    associatedTokenProgram: ASSOCIATED_TOKEN_PROGRAM_ID,
    systemProgram: SystemProgram.programId,
    rent: SYSVAR_RENT_PUBKEY,
  };

  const tx = await program.methods
    .sellTokens(
      args.tokenAmount,
      args.minSolOut,
      args.slippageTolerance
    )
    .accounts(accounts)
    .rpc();

  console.log(`Tokens sold successfully. Transaction: ${tx}`);
  return tx;
}