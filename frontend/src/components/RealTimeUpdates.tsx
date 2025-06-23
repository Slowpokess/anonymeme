'use client'

/**
 * 🔄 Компонент для real-time обновлений
 * Отображает live цены, торги и другие события через WebSocket
 */

import React, { useEffect, useState, useCallback } from 'react'
import { useWebSocket, WebSocketMessage } from '@/lib/websocket'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  Users, 
  Wifi, 
  WifiOff,
  AlertCircle,
  Check 
} from 'lucide-react'

interface PriceUpdate {
  token_mint: string
  token_name: string
  token_symbol: string
  current_price: number
  previous_price: number
  market_cap: number
  price_change_24h: number
  volume_24h: number
  trade_count: number
  last_trade_at: string
}

interface TradeUpdate {
  trade_id: string
  token_mint: string
  token_name: string
  token_symbol: string
  trade_type: 'buy' | 'sell'
  user_wallet: string
  sol_amount: number
  tokens_amount: number
  price_per_token: number
  market_cap_after: number
  price_impact: number
  transaction_signature: string
  timestamp: string
  is_profitable?: boolean
}

interface ConnectionStatus {
  isConnected: boolean
  reconnectAttempts: number
  lastConnected: Date | null
}

interface RealTimeUpdatesProps {
  tokenMint?: string  // Если указан, подписываемся на конкретный токен
  userId?: string     // Если указан, подписываемся на события пользователя
  showTrades?: boolean
  showPrices?: boolean
  showConnection?: boolean
  maxTrades?: number
  className?: string
}

export default function RealTimeUpdates({
  tokenMint,
  userId,
  showTrades = true,
  showPrices = true,
  showConnection = true,
  maxTrades = 10,
  className = ''
}: RealTimeUpdatesProps) {
  const { client, isConnected, connect, disconnect, on, off } = useWebSocket()
  
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    isConnected: false,
    reconnectAttempts: 0,
    lastConnected: null
  })
  
  const [recentTrades, setRecentTrades] = useState<TradeUpdate[]>([])
  const [priceUpdates, setPriceUpdates] = useState<Map<string, PriceUpdate>>(new Map())
  const [isInitialized, setIsInitialized] = useState(false)

  // Обработчики WebSocket событий
  const handleConnection = useCallback(() => {
    setConnectionStatus(prev => ({
      ...prev,
      isConnected: true,
      lastConnected: new Date(),
      reconnectAttempts: 0
    }))
  }, [])

  const handleDisconnection = useCallback(() => {
    setConnectionStatus(prev => ({
      ...prev,
      isConnected: false
    }))
  }, [])

  const handleNewTrade = useCallback((data: TradeUpdate) => {
    console.log('📈 Новая торговая операция:', data)
    
    setRecentTrades(prev => {
      const newTrades = [data, ...prev].slice(0, maxTrades)
      return newTrades
    })
  }, [maxTrades])

  const handlePriceUpdate = useCallback((data: PriceUpdate) => {
    console.log('💰 Обновление цены:', data)
    
    setPriceUpdates(prev => {
      const newMap = new Map(prev)
      newMap.set(data.token_mint, data)
      return newMap
    })
  }, [])

  const handleError = useCallback((data: any) => {
    console.error('❌ WebSocket ошибка:', data)
  }, [])

  // Инициализация WebSocket подключения
  useEffect(() => {
    if (!client || isInitialized) return

    // Подписка на события
    on('connected', handleConnection)
    on('disconnected', handleDisconnection)
    on('new_trade', handleNewTrade)
    on('price_update', handlePriceUpdate)
    on('error', handleError)

    // Подключение
    connect(undefined, 'global', userId)
      .then(() => {
        setIsInitialized(true)
        console.log('✅ WebSocket подключен')

        // Подписка на конкретный токен
        if (tokenMint && client) {
          client.subscribeToToken(tokenMint)
        }

        // Подписка на события пользователя
        if (userId && client) {
          client.subscribeToUser(userId)
        }
      })
      .catch(error => {
        console.error('❌ Ошибка подключения WebSocket:', error)
      })

    return () => {
      off('connected', handleConnection)
      off('disconnected', handleDisconnection)
      off('new_trade', handleNewTrade)
      off('price_update', handlePriceUpdate)
      off('error', handleError)
    }
  }, [client, isInitialized, tokenMint, userId, connect, on, off, handleConnection, handleDisconnection, handleNewTrade, handlePriceUpdate, handleError])

  // Обновление статуса подключения
  useEffect(() => {
    setConnectionStatus(prev => ({
      ...prev,
      isConnected
    }))
  }, [isConnected])

  // Очистка при размонтировании
  useEffect(() => {
    return () => {
      if (client) {
        disconnect()
      }
    }
  }, [client, disconnect])

  const formatPrice = (price: number) => {
    if (price < 0.0001) {
      return price.toExponential(2)
    }
    return price.toFixed(6)
  }

  const formatSOL = (amount: number) => {
    return amount.toFixed(4)
  }

  const formatTimeAgo = (timestamp: string) => {
    const now = new Date()
    const then = new Date(timestamp)
    const diffMs = now.getTime() - then.getTime()
    const diffSec = Math.floor(diffMs / 1000)
    
    if (diffSec < 60) return `${diffSec}с назад`
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}м назад`
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}ч назад`
    return `${Math.floor(diffSec / 86400)}д назад`
  }

  const getTradeTypeColor = (tradeType: 'buy' | 'sell') => {
    return tradeType === 'buy' ? 'text-green-600' : 'text-red-600'
  }

  const getPriceChangeColor = (current: number, previous: number) => {
    if (current > previous) return 'text-green-600'
    if (current < previous) return 'text-red-600'
    return 'text-gray-600'
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Статус подключения */}
      {showConnection && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              {connectionStatus.isConnected ? (
                <>
                  <Wifi className="h-4 w-4 text-green-600" />
                  <span className="text-green-600">Real-time подключен</span>
                </>
              ) : (
                <>
                  <WifiOff className="h-4 w-4 text-red-600" />
                  <span className="text-red-600">Подключение...</span>
                </>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>
                {connectionStatus.lastConnected 
                  ? `Последнее подключение: ${connectionStatus.lastConnected.toLocaleTimeString()}`
                  : 'Не подключен'
                }
              </span>
              {connectionStatus.reconnectAttempts > 0 && (
                <Badge variant="secondary" className="text-xs">
                  Попытка {connectionStatus.reconnectAttempts}
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Обновления цен */}
      {showPrices && priceUpdates.size > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Live цены токенов
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Array.from(priceUpdates.values()).map((update) => (
                <div key={update.token_mint} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                  <div className="flex-1">
                    <div className="font-medium text-sm">{update.token_symbol}</div>
                    <div className="text-xs text-gray-500">{update.token_name}</div>
                  </div>
                  <div className="text-right">
                    <div className={`font-mono text-sm ${getPriceChangeColor(update.current_price, update.previous_price)}`}>
                      {formatPrice(update.current_price)} SOL
                    </div>
                    <div className="text-xs text-gray-500">
                      MC: {(update.market_cap / 1000).toFixed(1)}K SOL
                    </div>
                  </div>
                  <div className="ml-2">
                    {update.current_price > update.previous_price ? (
                      <TrendingUp className="h-4 w-4 text-green-600" />
                    ) : update.current_price < update.previous_price ? (
                      <TrendingDown className="h-4 w-4 text-red-600" />
                    ) : (
                      <Activity className="h-4 w-4 text-gray-400" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Последние торги */}
      {showTrades && recentTrades.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Live торги ({recentTrades.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {recentTrades.map((trade) => (
                <div key={trade.trade_id} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Badge 
                        variant={trade.trade_type === 'buy' ? 'default' : 'secondary'}
                        className={`text-xs ${getTradeTypeColor(trade.trade_type)}`}
                      >
                        {trade.trade_type === 'buy' ? '🟢 BUY' : '🔴 SELL'}
                      </Badge>
                      <span className="font-medium text-sm">{trade.token_symbol}</span>
                      {trade.is_profitable !== undefined && (
                        <Badge variant={trade.is_profitable ? 'default' : 'destructive'} className="text-xs">
                          {trade.is_profitable ? <Check className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
                        </Badge>
                      )}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {trade.user_wallet.slice(0, 8)}...{trade.user_wallet.slice(-4)} • {formatTimeAgo(trade.timestamp)}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono text-sm">
                      {formatSOL(trade.sol_amount)} SOL
                    </div>
                    <div className="text-xs text-gray-500">
                      @ {formatPrice(trade.price_per_token)}
                    </div>
                    {trade.price_impact !== null && Math.abs(trade.price_impact) > 1 && (
                      <div className="text-xs text-orange-600">
                        Impact: {trade.price_impact.toFixed(1)}%
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Сообщение когда нет данных */}
      {showTrades && recentTrades.length === 0 && connectionStatus.isConnected && (
        <Alert>
          <Activity className="h-4 w-4" />
          <AlertDescription>
            Ожидание live торгов... Подключение активно.
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}