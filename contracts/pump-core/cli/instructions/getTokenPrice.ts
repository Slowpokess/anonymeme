import * as anchor from "@coral-xyz/anchor";
import { PublicKey } from "@solana/web3.js";

export interface GetTokenPriceArgs {
  // No additional args needed for price lookup
}

export interface GetTokenPriceAccounts {
  [key: string]: PublicKey;
  tokenInfo: PublicKey;
  mint: PublicKey;
  platformConfig: PublicKey;
  user: PublicKey;
}

export async function getTokenPrice(
  program: anchor.Program,
  mint: PublicKey
): Promise<{ signature: string; price: anchor.BN }> {
  const [tokenInfoPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("token_info"), mint.toBuffer()],
    program.programId
  );

  const [platformConfigPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("platform_config")],
    program.programId
  );

  const accounts: GetTokenPriceAccounts = {
    tokenInfo: tokenInfoPda,
    mint,
    platformConfig: platformConfigPda,
    user: program.provider.publicKey!,
  };

  const tx = await program.methods
    .getTokenPrice()
    .accounts(accounts)
    .rpc();

  // Note: In a real implementation, this would return the price from the transaction logs
  // For now, we'll fetch it from the token info account
  const tokenInfo = await program.account.tokenInfo.fetch(tokenInfoPda);
  const currentPrice = (tokenInfo as any).bondingCurve.currentPrice;

  console.log(`Token price retrieved successfully. Current price: ${currentPrice.toString()}, Transaction: ${tx}`);
  return { signature: tx, price: currentPrice };
}