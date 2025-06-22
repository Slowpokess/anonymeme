/**
 * 💱 Панель торговли токенами
 * Production-ready компонент для покупки и продажи
 */

'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { clsx } from 'clsx'
import { ArrowUpDown, TrendingUp, TrendingDown, AlertTriangle, Info } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useWalletStore } from '@/store/wallet'
import { Token, TradeType, TradeEstimate } from '@/types'
import apiService from '@/services/api'
import toast from 'react-hot-toast'

interface TradePanelProps {
  token: Token
  className?: string
}

export function TradePanel({ token, className }: TradePanelProps) {
  const [tradeType, setTradeType] = useState<TradeType>(TradeType.BUY)
  const [amount, setAmount] = useState('')
  const [estimate, setEstimate] = useState<TradeEstimate | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isEstimating, setIsEstimating] = useState(false)
  
  const { connected, balance, user, signAndSendTransaction } = useWalletStore()

  // Получение оценки сделки
  const getTradeEstimate = useCallback(async (inputAmount: string, type: TradeType) => {
    if (!inputAmount || parseFloat(inputAmount) <= 0) {
      setEstimate(null)
      return
    }

    setIsEstimating(true)
    try {
      const response = await apiService.estimateTrade(token.id, inputAmount, type)
      if (response.success) {
        setEstimate(response.data)
      }
    } catch (error) {
      console.error('Failed to get estimate:', error)
    } finally {
      setIsEstimating(false)
    }
  }, [token.id])

  // Debounced estimate update
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (amount) {
        getTradeEstimate(amount, tradeType)
      }
    }, 500)

    return () => clearTimeout(timeoutId)
  }, [amount, tradeType, getTradeEstimate])

  // Выполнение сделки
  const executeTrade = async () => {
    if (!connected || !user || !amount || !estimate) {
      toast.error('Подключите кошелек и введите сумму')
      return
    }

    setIsLoading(true)
    try {
      // Выполнение торговой операции через API
      const response = await apiService.executeTrade({
        token_id: token.id,
        amount,
        trade_type: tradeType,
        slippage_tolerance: 5, // 5% по умолчанию
      })

      if (response.success) {
        toast.success(
          tradeType === TradeType.BUY 
            ? `Куплено ${response.data.token_amount} ${token.symbol}`
            : `Продано ${response.data.token_amount} ${token.symbol}`
        )
        
        // Очистка формы
        setAmount('')
        setEstimate(null)
        
        // Обновление баланса
        // TODO: обновить баланс через store
        
      } else {
        throw new Error(response.message || 'Trade failed')
      }
    } catch (error: any) {
      console.error('Trade execution failed:', error)
      toast.error(error.message || 'Ошибка выполнения сделки')
    } finally {
      setIsLoading(false)
    }
  }

  // Переключение типа сделки
  const toggleTradeType = () => {
    setTradeType(tradeType === TradeType.BUY ? TradeType.SELL : TradeType.BUY)
    setAmount('')
    setEstimate(null)
  }

  // Установка максимальной суммы
  const setMaxAmount = () => {
    if (!balance) return

    if (tradeType === TradeType.BUY) {
      // Для покупки - весь SOL баланс минус комиссия
      const maxSol = Math.max(0, parseFloat(balance.sol) - 0.01)
      setAmount(maxSol.toString())
    } else {
      // Для продажи - весь баланс токена
      const tokenBalance = balance.tokens.find(t => t.mint === token.mint)
      if (tokenBalance) {
        setAmount(tokenBalance.balance)
      }
    }
  }

  const isBuyType = tradeType === TradeType.BUY
  const inputCurrency = isBuyType ? 'SOL' : token.symbol
  const outputCurrency = isBuyType ? token.symbol : 'SOL'

  return (
    <div className={clsx(
      'bg-white rounded-2xl shadow-lg border border-gray-200 p-6',
      className
    )}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-gray-900">
          Торговля {token.symbol}
        </h3>
        
        <button
          onClick={toggleTradeType}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          title="Переключить тип операции"
        >
          <ArrowUpDown className="w-5 h-5 text-gray-600" />
        </button>
      </div>

      {/* Trade Type Tabs */}
      <div className="flex bg-gray-100 rounded-lg p-1 mb-6">
        <button
          onClick={() => setTradeType(TradeType.BUY)}
          className={clsx(
            'flex-1 py-2 px-4 rounded-md font-medium transition-all duration-200',
            isBuyType
              ? 'bg-green-500 text-white shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          )}
        >
          <TrendingUp className="w-4 h-4 inline mr-2" />
          Купить
        </button>
        
        <button
          onClick={() => setTradeType(TradeType.SELL)}
          className={clsx(
            'flex-1 py-2 px-4 rounded-md font-medium transition-all duration-200',
            !isBuyType
              ? 'bg-red-500 text-white shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          )}
        >
          <TrendingDown className="w-4 h-4 inline mr-2" />
          Продать
        </button>
      </div>

      {/* Amount Input */}
      <div className="space-y-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Сумма ({inputCurrency})
          </label>
          
          <div className="relative">
            <Input
              type="number"
              placeholder={`0.00 ${inputCurrency}`}
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              rightIcon={
                <button
                  onClick={setMaxAmount}
                  className="text-primary-600 hover:text-primary-700 font-medium text-sm"
                >
                  MAX
                </button>
              }
            />
          </div>
          
          {/* Balance Display */}
          {balance && (
            <div className="mt-2 text-sm text-gray-500">
              Доступно: {
                isBuyType 
                  ? `${parseFloat(balance.sol).toFixed(4)} SOL`
                  : `${balance.tokens.find(t => t.mint === token.mint)?.balance || '0'} ${token.symbol}`
              }
            </div>
          )}
        </div>
      </div>

      {/* Trade Estimate */}
      {amount && (
        <div className="bg-gray-50 rounded-lg p-4 mb-6 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Ожидаемая сумма:</span>
            <span className="font-medium">
              {isEstimating ? (
                <div className="loading-spinner" />
              ) : estimate ? (
                `${parseFloat(estimate.expected_output).toFixed(6)} ${outputCurrency}`
              ) : (
                '—'
              )}
            </span>
          </div>
          
          {estimate && (
            <>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Цена за токен:</span>
                <span className="font-medium">
                  {parseFloat(estimate.price_per_token).toFixed(8)} SOL
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Влияние на цену:</span>
                <span className={clsx(
                  'font-medium',
                  estimate.price_impact > 5 ? 'text-red-600' : 'text-gray-900'
                )}>
                  {estimate.price_impact.toFixed(2)}%
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Комиссия платформы:</span>
                <span className="font-medium">
                  {parseFloat(estimate.platform_fee).toFixed(6)} SOL
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Минимум к получению:</span>
                <span className="font-medium">
                  {parseFloat(estimate.minimum_output).toFixed(6)} {outputCurrency}
                </span>
              </div>
            </>
          )}
        </div>
      )}

      {/* Warnings */}
      {estimate && estimate.price_impact > 5 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
          <div className="flex items-start">
            <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5 mr-2 flex-shrink-0" />
            <div className="text-sm text-yellow-800">
              <strong>Высокое влияние на цену!</strong>
              <br />
              Ваша сделка значительно повлияет на цену токена. Рассмотрите уменьшение суммы.
            </div>
          </div>
        </div>
      )}

      {/* Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-6">
        <div className="flex items-start">
          <Info className="w-5 h-5 text-blue-600 mt-0.5 mr-2 flex-shrink-0" />
          <div className="text-sm text-blue-800">
            Торговля происходит по бондинг-кривой. Цена автоматически обновляется в зависимости от спроса и предложения.
          </div>
        </div>
      </div>

      {/* Execute Button */}
      <Button
        onClick={executeTrade}
        disabled={!connected || !amount || !estimate || isLoading || isEstimating}
        loading={isLoading}
        variant={isBuyType ? 'success' : 'danger'}
        size="lg"
        fullWidth
        className="font-semibold"
      >
        {!connected ? (
          'Подключите кошелек'
        ) : !amount ? (
          'Введите сумму'
        ) : isEstimating ? (
          'Расчет...'
        ) : (
          `${isBuyType ? 'Купить' : 'Продать'} ${token.symbol}`
        )}
      </Button>
    </div>
  )
}

export default TradePanel