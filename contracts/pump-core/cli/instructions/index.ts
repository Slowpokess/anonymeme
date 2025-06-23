// Новые инструкции для Anonymeme Platform
export { initializePlatform } from "./initializePlatform"
export type { 
  InitializePlatformArgs, 
  InitializePlatformAccounts,
  SecurityParams 
} from "./initializePlatform"

export { createToken } from "./createToken"
export type { 
  CreateTokenArgs, 
  CreateTokenAccounts,
  BondingCurveParams,
  CurveType 
} from "./createToken"

export { buyTokens, sellTokens } from "./tradeTokens"
export type { 
  BuyTokensArgs, 
  BuyTokensAccounts,
  SellTokensArgs,
  SellTokensAccounts 
} from "./tradeTokens"

export { graduateToDex } from "./graduateToDex"
export type {
  GraduateToDexArgs,
  GraduateToDexAccounts,
  DexType
} from "./graduateToDex"

export { updateSecurityParams } from "./updateSecurityParams"
export type {
  UpdateSecurityParamsArgs,
  UpdateSecurityParamsAccounts
} from "./updateSecurityParams"

export { toggleEmergencyPause } from "./toggleEmergencyPause"
export type {
  ToggleEmergencyPauseArgs,
  ToggleEmergencyPauseAccounts
} from "./toggleEmergencyPause"

export { getTokenPrice } from "./getTokenPrice"
export type {
  GetTokenPriceArgs,
  GetTokenPriceAccounts
} from "./getTokenPrice"

export { updateUserReputation } from "./updateUserReputation"
export type {
  UpdateUserReputationArgs,
  UpdateUserReputationAccounts
} from "./updateUserReputation"

export { reportSuspiciousActivity } from "./reportSuspiciousActivity"
export type {
  ReportSuspiciousActivityArgs,
  ReportSuspiciousActivityAccounts,
  ReportReason
} from "./reportSuspiciousActivity"

export { emergencyPause, pauseTrading } from "./emergencyPause"
export type {
  EmergencyPauseArgs,
  EmergencyPauseAccounts,
  TradingPauseArgs,
  TradingPauseAccounts
} from "./emergencyPause"

export { 
  updatePlatformFee, 
  updateTreasury, 
  transferAdmin, 
  banToken, 
  unbanToken, 
  collectPlatformFees 
} from "./adminFunctions"
export type {
  UpdatePlatformFeeArgs,
  UpdateTreasuryArgs,
  TransferAdminArgs,
  BanTokenArgs,
  CollectFeesArgs,
  AdminAccounts,
  ManageTokenAccounts,
  CollectFeesAccounts
} from "./adminFunctions"

// Старые инструкции (оставлены для совместимости)
export { initialize } from "./initialize"
export type { InitializeArgs, InitializeAccounts } from "./initialize"
export { addLiquidity } from "./addLiquidity"
export type { AddLiquidityArgs, AddLiquidityAccounts } from "./addLiquidity"
export { removeLiquidity } from "./removeLiquidity"
export type {
  RemoveLiquidityArgs,
  RemoveLiquidityAccounts,
} from "./removeLiquidity"
export { swap } from "./swap"
export type { SwapArgs, SwapAccounts } from "./swap"
export { createRaydiumPool } from "./createRaydiumPool"
export type {
  CreateRaydiumPoolArgs,
  CreateRaydiumPoolAccounts,
} from "./createRaydiumPool"
