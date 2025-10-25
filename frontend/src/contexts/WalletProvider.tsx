/**
 * 💰 Wallet Provider для интеграции с Solana кошельками
 * Production-ready провайдер с поддержкой 13 популярных кошельков
 *
 * Поддерживаемые кошельки:
 * - Phantom (самый популярный)
 * - Solflare (официальный кошелек Solana)
 * - Backpack (xNFT поддержка)
 * - Glow (фокус на безопасность)
 * - Slope (мобильный + десктоп)
 * - Exodus (мультивалютный)
 * - Torus (web-based, OAuth)
 * - Sollet & Sollet Extension (классический)
 * - Ledger (аппаратный кошелек)
 * - MathWallet, Coin98, TrustWallet
 */

'use client'

import React, { FC, ReactNode, useMemo, useCallback } from 'react'
import { ConnectionProvider, WalletProvider } from '@solana/wallet-adapter-react'
import { WalletAdapterNetwork } from '@solana/wallet-adapter-base'
import { WalletModalProvider } from '@solana/wallet-adapter-react-ui'
import {
  PhantomWalletAdapter,
  SolflareWalletAdapter,
  TorusWalletAdapter,
  LedgerWalletAdapter,
  MathWalletAdapter,
  Coin98WalletAdapter,
  TrustWalletAdapter,
  BackpackWalletAdapter,
  GlowWalletAdapter,
  SlopeWalletAdapter,
  ExodusWalletAdapter,
  SolletExtensionWalletAdapter,
  SolletWalletAdapter,
} from '@solana/wallet-adapter-wallets'
import { clusterApiUrl } from '@solana/web3.js'
import toast from 'react-hot-toast'

// Импорт стилей для кошельков
require('@solana/wallet-adapter-react-ui/styles.css')

interface WalletContextProviderProps {
  children: ReactNode
}

export const WalletContextProvider: FC<WalletContextProviderProps> = ({ children }) => {
  // Определение сети на основе переменных окружения
  const network = useMemo(() => {
    const networkEnv = process.env.NEXT_PUBLIC_SOLANA_NETWORK as string
    
    switch (networkEnv) {
      case 'mainnet-beta':
        return WalletAdapterNetwork.Mainnet
      case 'testnet':
        return WalletAdapterNetwork.Testnet
      case 'devnet':
      default:
        return WalletAdapterNetwork.Devnet
    }
  }, [])

  // RPC endpoint
  const endpoint = useMemo(() => {
    const customRPC = process.env.NEXT_PUBLIC_SOLANA_RPC_URL
    return customRPC || clusterApiUrl(network)
  }, [network])

  // Конфигурация поддерживаемых кошельков
  const wallets = useMemo(
    () => [
      // ТОП-2 самых популярных кошелька
      new PhantomWalletAdapter(), // Самый популярный
      new SolflareWalletAdapter({ network }), // Официальный кошелек Solana

      // Современные популярные кошельки
      new BackpackWalletAdapter(), // Новый популярный кошелек от Coral (xNFT)
      new GlowWalletAdapter(), // Кошелек с фокусом на безопасность
      new SlopeWalletAdapter(), // Мобильный + десктоп
      new ExodusWalletAdapter(), // Мультивалютный кошелек

      // Web-based и расширения
      new TorusWalletAdapter(), // Web-based кошелек (OAuth)
      new SolletWalletAdapter({ network }), // Классический web кошелек
      new SolletExtensionWalletAdapter({ network }), // Расширение браузера

      // Аппаратный кошелек
      new LedgerWalletAdapter(), // Ledger hardware wallet

      // Другие кошельки
      new MathWalletAdapter(), // Math Wallet
      new Coin98WalletAdapter(), // Coin98
      new TrustWalletAdapter(), // Trust Wallet
    ],
    [network]
  )

  // Обработчики ошибок
  const onError = useCallback((error: any) => {
    console.error('Wallet error:', error)
    
    // Типизированная обработка ошибок
    let message = 'Произошла ошибка с кошельком'
    
    if (error?.message) {
      if (error.message.includes('User rejected')) {
        message = 'Подключение отклонено пользователем'
      } else if (error.message.includes('not found')) {
        message = 'Кошелек не найден. Установите расширение'
      } else if (error.message.includes('already pending')) {
        message = 'Дождитесь завершения текущей операции'
      } else if (error.message.includes('Wallet not ready')) {
        message = 'Кошелек не готов. Попробуйте еще раз'
      } else {
        message = error.message
      }
    }
    
    toast.error(message)
  }, [])

  // Autoconnect только если пользователь ранее подключался
  const autoConnect = useMemo(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('wallet-auto-connect') === 'true'
    }
    return false
  }, [])

  return (
    <ConnectionProvider 
      endpoint={endpoint}
      config={{
        commitment: 'confirmed',
        confirmTransactionInitialTimeout: 60000,
      }}
    >
      <WalletProvider 
        wallets={wallets} 
        onError={onError}
        autoConnect={autoConnect}
      >
        <WalletModalProvider>
          {children}
        </WalletModalProvider>
      </WalletProvider>
    </ConnectionProvider>
  )
}

// Дополнительные утилиты для работы с кошельками
export const getWalletIcon = (walletName: string): string => {
  const icons: Record<string, string> = {
    'Phantom': '👻',
    'Solflare': '🔥',
    'Backpack': '🎒',
    'Glow': '✨',
    'Slope': '📈',
    'Exodus': '🚀',
    'Torus': '🌀',
    'Sollet': '💼',
    'Sollet Extension': '💼',
    'Ledger': '🔒',
    'MathWallet': '📊',
    'Coin98': '🪙',
    'Trust Wallet': '🛡️',
  }

  return icons[walletName] || '💰'
}

export const getWalletDisplayName = (walletName: string): string => {
  const displayNames: Record<string, string> = {
    'Phantom': 'Phantom',
    'Solflare': 'Solflare',
    'Backpack': 'Backpack',
    'Glow': 'Glow',
    'Slope': 'Slope',
    'Exodus': 'Exodus',
    'Torus': 'Torus',
    'Sollet': 'Sollet',
    'Sollet Extension': 'Sollet Extension',
    'Ledger': 'Ledger',
    'MathWallet': 'Math Wallet',
    'Coin98': 'Coin98',
    'Trust Wallet': 'Trust Wallet',
  }

  return displayNames[walletName] || walletName
}

export const saveAutoConnectPreference = (shouldAutoConnect: boolean) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem('wallet-auto-connect', shouldAutoConnect.toString())
  }
}

export default WalletContextProvider