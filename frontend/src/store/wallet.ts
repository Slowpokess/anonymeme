/**
 * 💰 Zustand store для управления состоянием кошелька
 * Production-ready state management с TypeScript
 */

import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { Connection, PublicKey, Transaction } from '@solana/web3.js'
import type { WalletAdapter } from '@solana/wallet-adapter-base'
import { WalletInfo, WalletBalance, User } from '@/types'
import apiService from '@/services/api'

interface WalletState {
  // Connection state
  connected: boolean
  connecting: boolean
  disconnecting: boolean
  
  // Wallet info
  publicKey: PublicKey | null
  walletAdapter: WalletAdapter | null
  balance: WalletBalance | null
  
  // User data
  user: User | null
  isAuthenticated: boolean
  authToken: string | null
  
  // Solana connection
  connection: Connection | null
  
  // Error handling
  error: string | null
  
  // Actions
  connect: (adapter: WalletAdapter) => Promise<void>
  disconnect: () => Promise<void>
  authenticateUser: () => Promise<void>
  updateBalance: () => Promise<void>
  signAndSendTransaction: (transaction: Transaction) => Promise<string>
  setError: (error: string | null) => void
  clearError: () => void
}

export const useWalletStore = create<WalletState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        connected: false,
        connecting: false,
        disconnecting: false,
        publicKey: null,
        walletAdapter: null,
        balance: null,
        user: null,
        isAuthenticated: false,
        authToken: null,
        connection: null,
        error: null,

        // Connect wallet
        connect: async (adapter: WalletAdapter) => {
          set({ connecting: true, error: null })
          
          try {
            // Connect to wallet
            await adapter.connect()
            
            if (!adapter.publicKey) {
              throw new Error('Wallet connection failed')
            }

            // Initialize Solana connection
            const connection = new Connection(
              process.env.NEXT_PUBLIC_SOLANA_RPC_URL || 'https://api.devnet.solana.com',
              'confirmed'
            )

            set({
              connected: true,
              connecting: false,
              publicKey: adapter.publicKey,
              walletAdapter: adapter,
              connection,
            })

            // Get initial balance
            await get().updateBalance()
            
            // Authenticate user
            await get().authenticateUser()

            console.log('✅ Wallet connected successfully')
            
          } catch (error) {
            console.error('❌ Wallet connection failed:', error)
            set({
              connecting: false,
              error: error instanceof Error ? error.message : 'Failed to connect wallet'
            })
            throw error
          }
        },

        // Disconnect wallet
        disconnect: async () => {
          set({ disconnecting: true })
          
          try {
            const { walletAdapter } = get()
            
            if (walletAdapter) {
              await walletAdapter.disconnect()
            }
            
            // Clear auth token
            apiService.clearAuthToken()
            
            set({
              connected: false,
              disconnecting: false,
              publicKey: null,
              walletAdapter: null,
              balance: null,
              user: null,
              isAuthenticated: false,
              authToken: null,
              connection: null,
              error: null,
            })

            console.log('✅ Wallet disconnected successfully')
            
          } catch (error) {
            console.error('❌ Wallet disconnection failed:', error)
            set({
              disconnecting: false,
              error: error instanceof Error ? error.message : 'Failed to disconnect wallet'
            })
          }
        },

        // Authenticate user with wallet signature
        authenticateUser: async () => {
          const { publicKey, walletAdapter } = get()
          
          if (!publicKey || !walletAdapter) {
            throw new Error('Wallet not connected')
          }

          try {
            // Create message to sign
            const message = `Sign this message to authenticate with Anonymeme platform.\n\nWallet: ${publicKey.toBase58()}\nTimestamp: ${Date.now()}`
            const messageBytes = new TextEncoder().encode(message)
            
            // Sign message
            const signature = await walletAdapter.signMessage!(messageBytes)
            
            // Authenticate with backend
            const response = await apiService.authenticateWallet(
              publicKey.toBase58(),
              Buffer.from(signature).toString('base64')
            )
            
            if (response.success) {
              const { token, user } = response.data
              
              // Store auth token
              apiService.setAuthToken(token)
              
              set({
                user,
                isAuthenticated: true,
                authToken: token,
              })
              
              console.log('✅ User authenticated successfully')
            } else {
              throw new Error('Authentication failed')
            }
            
          } catch (error) {
            console.error('❌ User authentication failed:', error)
            set({
              error: error instanceof Error ? error.message : 'Authentication failed'
            })
            throw error
          }
        },

        // Update wallet balance
        updateBalance: async () => {
          const { connection, publicKey } = get()
          
          if (!connection || !publicKey) {
            return
          }

          try {
            // Get SOL balance
            const solBalance = await connection.getBalance(publicKey)
            const solBalanceFormatted = (solBalance / 1_000_000_000).toString()

            // Get token accounts
            const tokenAccounts = await connection.getTokenAccountsByOwner(publicKey, {
              programId: new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
            })

            const tokens = await Promise.all(
              tokenAccounts.value.map(async (account) => {
                try {
                  const accountInfo = await connection.getAccountInfo(account.pubkey)
                  if (!accountInfo) return null

                  // Parse token account data (simplified)
                  // In production, use @solana/spl-token for proper parsing
                  return {
                    mint: 'unknown',
                    balance: '0',
                    decimals: 9,
                    symbol: 'UNKNOWN'
                  }
                } catch {
                  return null
                }
              })
            )

            const balance: WalletBalance = {
              sol: solBalanceFormatted,
              tokens: tokens.filter(Boolean) as any[]
            }

            set({ balance })
            
          } catch (error) {
            console.error('❌ Failed to update balance:', error)
          }
        },

        // Sign and send transaction
        signAndSendTransaction: async (transaction: Transaction) => {
          const { walletAdapter, connection } = get()
          
          if (!walletAdapter || !connection) {
            throw new Error('Wallet not connected')
          }

          try {
            // Get recent blockhash
            const { blockhash } = await connection.getLatestBlockhash()
            transaction.recentBlockhash = blockhash
            transaction.feePayer = walletAdapter.publicKey!

            // Sign transaction
            const signedTransaction = await walletAdapter.signTransaction!(transaction)
            
            // Send transaction
            const signature = await connection.sendRawTransaction(signedTransaction.serialize())
            
            // Confirm transaction
            await connection.confirmTransaction(signature, 'confirmed')
            
            // Update balance after successful transaction
            await get().updateBalance()
            
            return signature
            
          } catch (error) {
            console.error('❌ Transaction failed:', error)
            throw error
          }
        },

        // Set error
        setError: (error: string | null) => {
          set({ error })
        },

        // Clear error
        clearError: () => {
          set({ error: null })
        },
      }),
      {
        name: 'wallet-storage',
        partialize: (state) => ({
          // Only persist non-sensitive data
          isAuthenticated: state.isAuthenticated,
          user: state.user,
        }),
      }
    ),
    {
      name: 'wallet-store',
    }
  )
)

// Computed selectors
export const useWalletInfo = (): WalletInfo => {
  const { connected, connecting, disconnecting, publicKey, walletAdapter } = useWalletStore()
  
  return {
    publicKey: publicKey?.toBase58() || '',
    connected,
    connecting,
    disconnecting,
    wallet: walletAdapter ? {
      adapter: {
        name: walletAdapter.name,
        icon: walletAdapter.icon,
        url: walletAdapter.url,
      }
    } : undefined,
  }
}

export const useWalletBalance = () => {
  return useWalletStore((state) => state.balance)
}

export const useWalletUser = () => {
  return useWalletStore((state) => ({
    user: state.user,
    isAuthenticated: state.isAuthenticated,
  }))
}

export const useWalletActions = () => {
  return useWalletStore((state) => ({
    connect: state.connect,
    disconnect: state.disconnect,
    updateBalance: state.updateBalance,
    signAndSendTransaction: state.signAndSendTransaction,
    setError: state.setError,
    clearError: state.clearError,
  }))
}

export const useWalletError = () => {
  return useWalletStore((state) => state.error)
}