'use client'

/**
 * 🎯 Компонент торгового интерфейса с real-time обновлениями
 * Интегрирует торговую форму с WebSocket уведомлениями
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useWebSocket } from '@/lib/websocket'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { 
  TrendingUp, 
  TrendingDown, 
  ArrowUpDown, 
  Wallet,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  RefreshCw
} from 'lucide-react'
import RealTimeUpdates from './RealTimeUpdates'

interface Token {
  mint_address: string
  name: string
  symbol: string
  description: string
  current_price: number
  market_cap: number
  sol_reserves: number
  token_reserves: number
  volume_24h: number
  trades_24h: number
  bonding_curve_progress: number
  graduation_threshold: number
  is_graduated: boolean
}

interface TradingInterfaceProps {
  token: Token
  userWallet?: string
  userId?: string
  onTradeComplete?: (trade: any) => void
  className?: string
}

interface TradeEstimate {
  estimated_tokens?: number
  estimated_sol?: number
  price_impact: number
  slippage: number
  fees: number
  total_cost?: number
  total_received?: number
}

export default function TradingInterface({
  token,
  userWallet,
  userId,
  onTradeComplete,
  className = ''
}: TradingInterfaceProps) {
  const { client, isConnected } = useWebSocket()

  const [tradeType, setTradeType] = useState<'buy' | 'sell'>('buy')
  const [solAmount, setSolAmount] = useState('')
  const [tokenAmount, setTokenAmount] = useState('')
  const [estimate, setEstimate] = useState<TradeEstimate | null>(null)
  const [isEstimating, setIsEstimating] = useState(false)
  const [isTrading, setIsTrading] = useState(false)
  const [tradeError, setTradeError] = useState<string | null>(null)
  const [tradeSuccess, setTradeSuccess] = useState<string | null>(null)
  const [userBalance, setUserBalance] = useState<number>(0)
  const [userTokenBalance, setUserTokenBalance] = useState<number>(0)
  const [currentPrice, setCurrentPrice] = useState(token.current_price)

  // Обновление цены из WebSocket
  const handlePriceUpdate = useCallback((data: any) => {
    if (data.token_mint === token.mint_address) {
      setCurrentPrice(data.current_price)
      
      // Обновляем оценку если есть активный ввод
      if ((solAmount || tokenAmount) && !isEstimating) {
        estimateTrade()
      }
    }
  }, [token.mint_address, solAmount, tokenAmount, isEstimating])

  // Обработка завершенной торговой операции
  const handleTradeComplete = useCallback((data: any) => {
    if (data.token_mint === token.mint_address && data.user_id === userId) {
      setTradeSuccess(
        `${data.trade_type === 'buy' ? 'Купил' : 'Продал'} ${Number(data.tokens_amount).toFixed(4)} ${token.symbol} за ${Number(data.sol_amount).toFixed(4)} SOL`
      )
      setIsTrading(false)
      setSolAmount('')
      setTokenAmount('')
      setEstimate(null)
      
      // Обновляем балансы
      loadUserBalances()
      
      if (onTradeComplete) {
        onTradeComplete(data)
      }
    }
  }, [token.mint_address, token.symbol, userId, onTradeComplete])

  // Подписка на WebSocket события
  useEffect(() => {
    if (!client || !isConnected) return

    client.on('price_update', handlePriceUpdate)
    client.on('new_trade', handleTradeComplete)

    return () => {
      client.off('price_update', handlePriceUpdate)
      client.off('new_trade', handleTradeComplete)
    }
  }, [client, isConnected, handlePriceUpdate, handleTradeComplete])

  // Загрузка балансов пользователя (mock данные)
  const loadUserBalances = useCallback(async () => {
    if (!userWallet) return

    try {
      // Здесь должен быть реальный API вызов
      // const response = await fetch(`/api/v1/users/balance?wallet=${userWallet}`)
      // const data = await response.json()
      
      // Mock данные
      setUserBalance(5.2) // SOL баланс
      setUserTokenBalance(1250.5) // Баланс токенов
    } catch (error) {
      console.error('Ошибка загрузки балансов:', error)
    }
  }, [userWallet])

  // Загрузка балансов при монтировании
  useEffect(() => {
    loadUserBalances()
  }, [loadUserBalances])

  // Оценка торговой операции
  const estimateTrade = useCallback(async () => {
    if (!solAmount && !tokenAmount) {
      setEstimate(null)
      return
    }

    setIsEstimating(true)
    setTradeError(null)

    try {
      const params = new URLSearchParams({
        token_address: token.mint_address,
        ...(solAmount && { sol_amount: solAmount }),
        ...(tokenAmount && { token_amount: tokenAmount })
      })

      const response = await fetch(`/api/v1/trading/estimate?${params}`)
      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.message || 'Ошибка оценки торговой операции')
      }

      setEstimate(result.data)
    } catch (error) {
      console.error('Ошибка оценки:', error)
      setTradeError(error instanceof Error ? error.message : 'Ошибка оценки')
    } finally {
      setIsEstimating(false)
    }
  }, [token.mint_address, solAmount, tokenAmount])

  // Debounced оценка
  useEffect(() => {
    const timer = setTimeout(() => {
      estimateTrade()
    }, 500)

    return () => clearTimeout(timer)
  }, [estimateTrade])

  // Выполнение торговой операции
  const executeTrade = async () => {
    if (!userWallet || !estimate) return

    setIsTrading(true)
    setTradeError(null)
    setTradeSuccess(null)

    try {
      const endpoint = tradeType === 'buy' ? '/api/v1/trading/buy' : '/api/v1/trading/sell'
      
      const payload = tradeType === 'buy' 
        ? {
            token_address: token.mint_address,
            sol_amount: Number(solAmount),
            min_tokens_out: estimate.estimated_tokens ? estimate.estimated_tokens * 0.98 : 0, // 2% slippage
            slippage_tolerance: 2.0
          }
        : {
            token_address: token.mint_address,
            token_amount: Number(tokenAmount),
            min_sol_out: estimate.estimated_sol ? estimate.estimated_sol * 0.98 : 0, // 2% slippage
            slippage_tolerance: 2.0
          }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // Здесь должна быть авторизация
        },
        body: JSON.stringify(payload)
      })

      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.message || 'Ошибка выполнения торговой операции')
      }

      // Успех будет обработан через WebSocket
      
    } catch (error) {
      console.error('Ошибка торговли:', error)
      setTradeError(error instanceof Error ? error.message : 'Ошибка выполнения торговой операции')
      setIsTrading(false)
    }
  }

  const switchTradeType = () => {
    setTradeType(prev => prev === 'buy' ? 'sell' : 'buy')
    setSolAmount('')
    setTokenAmount('')
    setEstimate(null)
  }

  const formatBalance = (balance: number) => {
    return balance.toFixed(4)
  }

  const formatPrice = (price: number) => {
    if (price < 0.0001) {
      return price.toExponential(2)
    }
    return price.toFixed(6)
  }

  const canTrade = () => {
    if (!userWallet || !estimate || isTrading || isEstimating) return false
    
    if (tradeType === 'buy') {
      return Number(solAmount) > 0 && Number(solAmount) <= userBalance
    } else {
      return Number(tokenAmount) > 0 && Number(tokenAmount) <= userTokenBalance
    }
  }

  return (
    <div className={`grid grid-cols-1 lg:grid-cols-3 gap-6 ${className}`}>
      {/* Торговая форма */}
      <div className="lg:col-span-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span>Торговля {token.symbol}</span>
                <Badge variant="outline" className="text-xs">
                  {formatPrice(currentPrice)} SOL
                </Badge>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={switchTradeType}
                className="flex items-center gap-1"
              >
                <ArrowUpDown className="h-4 w-4" />
                {tradeType === 'buy' ? 'Купить' : 'Продать'}
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Информация о токене */}
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Market Cap:</span>
                  <span className="ml-2 font-mono">{(token.market_cap / 1000).toFixed(1)}K SOL</span>
                </div>
                <div>
                  <span className="text-gray-500">Liquidity:</span>
                  <span className="ml-2 font-mono">{token.sol_reserves.toFixed(2)} SOL</span>
                </div>
                <div>
                  <span className="text-gray-500">24h Volume:</span>
                  <span className="ml-2 font-mono">{token.volume_24h.toFixed(2)} SOL</span>
                </div>
                <div>
                  <span className="text-gray-500">Trades 24h:</span>
                  <span className="ml-2 font-mono">{token.trades_24h}</span>
                </div>
              </div>
            </div>

            {/* Прогресс до graduation */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Прогресс до DEX</span>
                <span>{token.bonding_curve_progress.toFixed(1)}%</span>
              </div>
              <Progress value={token.bonding_curve_progress} className="h-2" />
            </div>

            {/* Балансы пользователя */}
            {userWallet && (
              <div className="grid grid-cols-2 gap-4 p-3 border rounded-lg">
                <div className="flex items-center gap-2">
                  <Wallet className="h-4 w-4 text-gray-500" />
                  <div>
                    <div className="text-xs text-gray-500">SOL Баланс</div>
                    <div className="font-mono text-sm">{formatBalance(userBalance)}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div>
                    <div className="text-xs text-gray-500">{token.symbol} Баланс</div>
                    <div className="font-mono text-sm">{formatBalance(userTokenBalance)}</div>
                  </div>
                </div>
              </div>
            )}

            {/* Форма торговли */}
            <div className="space-y-4">
              {tradeType === 'buy' ? (
                <div className="space-y-2">
                  <Label htmlFor="sol-amount">Количество SOL</Label>
                  <Input
                    id="sol-amount"
                    type="number"
                    placeholder="0.0"
                    value={solAmount}
                    onChange={(e) => setSolAmount(e.target.value)}
                    disabled={isTrading}
                    max={userBalance}
                    step="0.01"
                  />
                  {estimate && (
                    <div className="text-sm text-gray-600">
                      ≈ {estimate.estimated_tokens?.toFixed(4)} {token.symbol}
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  <Label htmlFor="token-amount">Количество {token.symbol}</Label>
                  <Input
                    id="token-amount"
                    type="number"
                    placeholder="0.0"
                    value={tokenAmount}
                    onChange={(e) => setTokenAmount(e.target.value)}
                    disabled={isTrading}
                    max={userTokenBalance}
                    step="0.01"
                  />
                  {estimate && (
                    <div className="text-sm text-gray-600">
                      ≈ {estimate.estimated_sol?.toFixed(4)} SOL
                    </div>
                  )}
                </div>
              )}

              {/* Детали оценки */}
              {estimate && (
                <div className="p-3 border rounded-lg space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Price Impact:</span>
                    <span className={estimate.price_impact > 5 ? 'text-red-600' : 'text-gray-600'}>
                      {estimate.price_impact.toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Slippage:</span>
                    <span>{estimate.slippage.toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Fees:</span>
                    <span>{estimate.fees.toFixed(4)} SOL</span>
                  </div>
                  {estimate.price_impact > 10 && (
                    <Alert>
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>
                        Высокое влияние на цену! Рассмотрите меньшую сумму.
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              )}

              {/* Кнопка торговли */}
              <Button
                onClick={executeTrade}
                disabled={!canTrade()}
                className="w-full"
                size="lg"
              >
                {isTrading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Выполнение...
                  </>
                ) : isEstimating ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Оценка...
                  </>
                ) : (
                  <>
                    {tradeType === 'buy' ? (
                      <TrendingUp className="mr-2 h-4 w-4" />
                    ) : (
                      <TrendingDown className="mr-2 h-4 w-4" />
                    )}
                    {tradeType === 'buy' ? 'Купить' : 'Продать'} {token.symbol}
                  </>
                )}
              </Button>
            </div>

            {/* Сообщения об ошибках и успехе */}
            {tradeError && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{tradeError}</AlertDescription>
              </Alert>
            )}

            {tradeSuccess && (
              <Alert>
                <CheckCircle2 className="h-4 w-4" />
                <AlertDescription className="text-green-600">
                  {tradeSuccess}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Real-time обновления */}
      <div>
        <RealTimeUpdates
          tokenMint={token.mint_address}
          userId={userId}
          showTrades={true}
          showPrices={true}
          showConnection={true}
          maxTrades={5}
        />
      </div>
    </div>
  )
}