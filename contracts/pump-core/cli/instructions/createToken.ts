import * as anchor from "@coral-xyz/anchor";
import { PublicKey, SystemProgram, SYSVAR_RENT_PUBKEY, Keypair } from "@solana/web3.js";
import { 
  TOKEN_PROGRAM_ID, 
  ASSOCIATED_TOKEN_PROGRAM_ID,
  getAssociatedTokenAddress 
} from "@solana/spl-token";

export enum CurveType {
  Linear = "Linear",
  Exponential = "Exponential", 
  Logarithmic = "Logarithmic",
  Sigmoid = "Sigmoid",
  ConstantProduct = "ConstantProduct"
}

export interface BondingCurveParams {
  curveType: CurveType;
  initialSupply: anchor.BN;
  initialPrice: anchor.BN;
  graduationThreshold: anchor.BN;
  slope: number;
  volatilityDamper: number | null;
}

export interface CreateTokenArgs {
  name: string;
  symbol: string;
  uri: string;
  bondingCurveParams: BondingCurveParams;
}

export interface CreateTokenAccounts {
  [key: string]: PublicKey;
  tokenInfo: PublicKey;
  mint: PublicKey;
  bondingCurveVault: PublicKey;
  bondingCurveTokenAccount: PublicKey;
  userProfile: PublicKey;
  platformConfig: PublicKey;
  creator: PublicKey;
  metadataAccount: PublicKey;
  tokenProgram: PublicKey;
  associatedTokenProgram: PublicKey;
  tokenMetadataProgram: PublicKey;
  systemProgram: PublicKey;
  rent: PublicKey;
}

export async function createToken(
  program: any,
  args: CreateTokenArgs,
  mintKeypair?: Keypair
): Promise<{ signature: string; mint: PublicKey }> {
  const mint = mintKeypair || Keypair.generate();

  const [tokenInfoPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("token_info"), mint.publicKey.toBuffer()],
    program.programId
  );

  const [bondingCurveVault] = PublicKey.findProgramAddressSync(
    [Buffer.from("bonding_curve_vault"), mint.publicKey.toBuffer()],
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
    mint.publicKey,
    bondingCurveVault,
    true
  );

  // Metadata account PDA
  const TOKEN_METADATA_PROGRAM_ID = new PublicKey(
    "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
  );
  
  const [metadataAccount] = PublicKey.findProgramAddressSync(
    [
      Buffer.from("metadata"),
      TOKEN_METADATA_PROGRAM_ID.toBuffer(),
      mint.publicKey.toBuffer(),
    ],
    TOKEN_METADATA_PROGRAM_ID
  );

  const accounts: CreateTokenAccounts = {
    tokenInfo: tokenInfoPda,
    mint: mint.publicKey,
    bondingCurveVault,
    bondingCurveTokenAccount,
    userProfile: userProfilePda,
    platformConfig: platformConfigPda,
    creator: program.provider.publicKey!,
    metadataAccount,
    tokenProgram: TOKEN_PROGRAM_ID,
    associatedTokenProgram: ASSOCIATED_TOKEN_PROGRAM_ID,
    tokenMetadataProgram: TOKEN_METADATA_PROGRAM_ID,
    systemProgram: SystemProgram.programId,
    rent: SYSVAR_RENT_PUBKEY,
  };

  const tx = await program.methods
    .createToken(
      args.name,
      args.symbol,
      args.uri,
      args.bondingCurveParams
    )
    .accounts(accounts)
    .signers([mint])
    .rpc();

  console.log(`Token created successfully. Mint: ${mint.publicKey.toString()}, Transaction: ${tx}`);
  return { signature: tx, mint: mint.publicKey };
}