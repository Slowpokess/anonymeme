/**
 * 💰 Wallet Provider для интеграции с Solana кошельками
 * Production-ready провайдер с поддержкой Phantom, Solflare и других
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
      // Phantom - самый популярный кошелек
      new PhantomWalletAdapter(),
      
      // Solflare - официальный кошелек Solana
      new SolflareWalletAdapter({ network }),
      
      // Torus - web-based кошелек
      new TorusWalletAdapter(),
      
      // Ledger - аппаратный кошелек
      new LedgerWalletAdapter(),
      
      // Другие популярные кошельки
      new MathWalletAdapter(),
      new Coin98WalletAdapter(),
      new TrustWalletAdapter(),
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
    'Torus': '🌀',
    'Ledger': '🔒',
    'Sollet': '💼',
    'MathWallet': '📊',
    'Coin98': '🪙',
    'Slope': '📈',
    'Trust Wallet': '🛡️',
  }
  
  return icons[walletName] || '💰'
}

export const getWalletDisplayName = (walletName: string): string => {
  const displayNames: Record<string, string> = {
    'Phantom': 'Phantom',
    'Solflare': 'Solflare',
    'Torus': 'Torus',
    'Ledger': 'Ledger',
    'Sollet': 'Sollet',
    'Sollet Extension': 'Sollet (Extension)',
    'MathWallet': 'Math Wallet',
    'Coin98': 'Coin98',
    'Slope': 'Slope',
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