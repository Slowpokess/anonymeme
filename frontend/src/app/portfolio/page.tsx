/**
 * 💼 Страница портфолио пользователя
 * Production-ready отображение позиций и P&L
 */

'use client'

import React, { useState, useEffect } from 'react'
import { useWallet } from '@solana/wallet-adapter-react'
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui'
import { 
  ArrowLeft, TrendingUp, TrendingDown, RefreshCw, 
  PieChart, BarChart3, Eye, EyeOff, Download 
} from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { useWalletStore } from '@/store/wallet'
import apiService from '@/services/api'
import toast from 'react-hot-toast'

interface PortfolioPosition {
  token: {
    id: string
    symbol: string
    name: string
    image: string
    mint: string
    current_price: string
  }
  balance: number
  avg_buy_price: number | null
  current_price: number
  current_value_sol: number
  unrealized_pnl: number
  realized_pnl: number
  total_pnl: number
  total_bought: number
  total_sold: number
  first_trade_at: string
  last_trade_at: string
}

interface PortfolioData {
  total_value_sol: number
  total_value_usd: number | null
  total_pnl: number
  total_pnl_percent: number
  positions: PortfolioPosition[]
}

export default function PortfolioPage() {
  const [mounted, setMounted] = useState(false)
  const [portfolioData, setPortfolioData] = useState<PortfolioData | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [showBalances, setShowBalances] = useState(true)
  const [sortBy, setSortBy] = useState<'value' | 'pnl' | 'pnl_percent'>('value')
  
  const { connected } = useWallet()
  const { balance } = useWalletStore()

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (connected && mounted) {
      loadPortfolio()
    }
  }, [connected, mounted])

  const loadPortfolio = async () => {
    try {
      setLoading(true)
      const response = await apiService.getUserPortfolio()
      
      if (response.success) {
        setPortfolioData(response.data)
      } else {
        throw new Error(response.message || 'Ошибка загрузки портфолио')
      }
    } catch (error: any) {
      console.error('Failed to load portfolio:', error)
      toast.error(error.message || 'Ошибка загрузки портфолио')
    } finally {
      setLoading(false)
    }
  }

  const refreshPortfolio = async () => {
    try {
      setRefreshing(true)
      await loadPortfolio()
      toast.success('Портфолио обновлено')
    } catch (error) {
      // Error already handled in loadPortfolio
    } finally {
      setRefreshing(false)
    }
  }

  const exportPortfolio = () => {
    if (!portfolioData) return

    const exportData = {
      export_date: new Date().toISOString(),
      total_value_sol: portfolioData.total_value_sol,
      total_pnl: portfolioData.total_pnl,
      total_pnl_percent: portfolioData.total_pnl_percent,
      positions: portfolioData.positions.map(pos => ({
        token_symbol: pos.token.symbol,
        token_name: pos.token.name,
        balance: pos.balance,
        current_value_sol: pos.current_value_sol,
        total_pnl: pos.total_pnl,
        avg_buy_price: pos.avg_buy_price,
        current_price: pos.current_price
      }))
    }

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `portfolio_${new Date().toISOString().split('T')[0]}.json`
    a.click()
    URL.revokeObjectURL(url)
    
    toast.success('Портфолио экспортировано')
  }

  if (!mounted) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!connected) {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center space-x-4">
                <Link href="/" className="flex items-center text-gray-600 hover:text-gray-900">
                  <ArrowLeft className="w-5 h-5 mr-2" />
                  Назад
                </Link>
                <h1 className="text-2xl font-bold text-gray-900">
                  Портфолио
                </h1>
              </div>
              
              <WalletMultiButton className="!bg-blue-600 hover:!bg-blue-700 !rounded-lg" />
            </div>
          </div>
        </header>

        <div className="max-w-2xl mx-auto px-4 py-16 text-center">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <PieChart className="w-8 h-8 text-blue-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Подключите кошелек
          </h3>
          <p className="text-gray-600 mb-6">
            Для просмотра портфолио необходимо подключить Solana кошелек
          </p>
          <WalletMultiButton className="!bg-blue-600 hover:!bg-blue-700 !rounded-lg !text-white !px-6 !py-3" />
        </div>
      </div>
    )
  }

  const sortedPositions = portfolioData?.positions.sort((a, b) => {
    switch (sortBy) {
      case 'value':
        return b.current_value_sol - a.current_value_sol
      case 'pnl':
        return b.total_pnl - a.total_pnl
      case 'pnl_percent':
        const aPnlPercent = a.avg_buy_price ? (a.total_pnl / (a.balance * a.avg_buy_price)) * 100 : 0
        const bPnlPercent = b.avg_buy_price ? (b.total_pnl / (b.balance * b.avg_buy_price)) * 100 : 0
        return bPnlPercent - aPnlPercent
      default:
        return 0
    }
  }) || []

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <Link href="/" className="flex items-center text-gray-600 hover:text-gray-900">
                <ArrowLeft className="w-5 h-5 mr-2" />
                Назад
              </Link>
              <h1 className="text-2xl font-bold text-gray-900">
                Портфолио
              </h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <Button
                variant="outline"
                onClick={() => setShowBalances(!showBalances)}
                leftIcon={showBalances ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              >
                {showBalances ? 'Скрыть' : 'Показать'} балансы
              </Button>
              
              <Button
                variant="outline"
                onClick={refreshPortfolio}
                disabled={refreshing}
                leftIcon={<RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />}
              >
                Обновить
              </Button>
              
              <WalletMultiButton className="!bg-blue-600 hover:!bg-blue-700 !rounded-lg" />
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <>
            {/* Общая статистика */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
              <Card className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Общая стоимость</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {showBalances ? `${portfolioData?.total_value_sol.toFixed(4)} SOL` : '••••'}
                    </p>
                  </div>
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <PieChart className="w-6 h-6 text-blue-600" />
                  </div>
                </div>
              </Card>

              <Card className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">SOL баланс</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {showBalances ? `${balance ? parseFloat(balance.sol).toFixed(4) : '0'} SOL` : '••••'}
                    </p>
                  </div>
                  <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                    <span className="text-purple-600 font-bold">SOL</span>
                  </div>
                </div>
              </Card>

              <Card className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Общий P&L</p>
                    <p className={`text-2xl font-bold ${
                      (portfolioData?.total_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {showBalances ? (
                        <>
                          {(portfolioData?.total_pnl || 0) >= 0 ? '+' : ''}
                          {portfolioData?.total_pnl.toFixed(4)} SOL
                        </>
                      ) : '••••'}
                    </p>
                  </div>
                  <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                    (portfolioData?.total_pnl || 0) >= 0 ? 'bg-green-100' : 'bg-red-100'
                  }`}>
                    {(portfolioData?.total_pnl || 0) >= 0 ? (
                      <TrendingUp className="w-6 h-6 text-green-600" />
                    ) : (
                      <TrendingDown className="w-6 h-6 text-red-600" />
                    )}
                  </div>
                </div>
              </Card>

              <Card className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">P&L %</p>
                    <p className={`text-2xl font-bold ${
                      (portfolioData?.total_pnl_percent || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {showBalances ? (
                        <>
                          {(portfolioData?.total_pnl_percent || 0) >= 0 ? '+' : ''}
                          {portfolioData?.total_pnl_percent.toFixed(2)}%
                        </>
                      ) : '••••'}
                    </p>
                  </div>
                  <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center">
                    <BarChart3 className="w-6 h-6 text-gray-600" />
                  </div>
                </div>
              </Card>
            </div>

            {/* Позиции */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-gray-900">
                  Позиции ({sortedPositions.length})
                </h2>
                
                <div className="flex items-center space-x-4">
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as any)}
                    className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="value">По стоимости</option>
                    <option value="pnl">По P&L</option>
                    <option value="pnl_percent">По P&L %</option>
                  </select>
                  
                  <Button
                    variant="outline"
                    onClick={exportPortfolio}
                    leftIcon={<Download className="w-4 h-4" />}
                  >
                    Экспорт
                  </Button>
                </div>
              </div>

              {sortedPositions.length === 0 ? (
                <div className="text-center py-12">
                  <PieChart className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Портфолио пуст
                  </h3>
                  <p className="text-gray-600 mb-6">
                    У вас пока нет позиций по токенам
                  </p>
                  <Link href="/trade">
                    <Button>
                      Начать торговлю
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-4">
                  {sortedPositions.map((position) => {
                    const pnlPercent = position.avg_buy_price 
                      ? (position.total_pnl / (position.balance * position.avg_buy_price)) * 100 
                      : 0

                    return (
                      <div
                        key={position.token.id}
                        className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
                      >
                        <div className="grid grid-cols-1 md:grid-cols-6 gap-4 items-center">
                          {/* Токен */}
                          <div className="flex items-center space-x-3">
                            <span className="text-2xl">{position.token.image}</span>
                            <div>
                              <div className="font-semibold text-gray-900">
                                {position.token.symbol}
                              </div>
                              <div className="text-sm text-gray-600">
                                {position.token.name}
                              </div>
                            </div>
                          </div>

                          {/* Баланс */}
                          <div className="text-center">
                            <div className="text-sm text-gray-600">Баланс</div>
                            <div className="font-semibold">
                              {showBalances ? position.balance.toLocaleString() : '••••'}
                            </div>
                          </div>

                          {/* Текущая цена */}
                          <div className="text-center">
                            <div className="text-sm text-gray-600">Цена</div>
                            <div className="font-semibold">
                              {showBalances ? `$${position.current_price.toFixed(8)}` : '••••'}
                            </div>
                          </div>

                          {/* Стоимость */}
                          <div className="text-center">
                            <div className="text-sm text-gray-600">Стоимость</div>
                            <div className="font-semibold">
                              {showBalances ? `${position.current_value_sol.toFixed(4)} SOL` : '••••'}
                            </div>
                          </div>

                          {/* P&L */}
                          <div className="text-center">
                            <div className="text-sm text-gray-600">P&L</div>
                            <div className={`font-semibold ${
                              position.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                            }`}>
                              {showBalances ? (
                                <>
                                  {position.total_pnl >= 0 ? '+' : ''}
                                  {position.total_pnl.toFixed(4)}
                                </>
                              ) : '••••'}
                            </div>
                          </div>

                          {/* P&L % */}
                          <div className="text-center">
                            <div className="text-sm text-gray-600">P&L %</div>
                            <div className={`font-semibold ${
                              pnlPercent >= 0 ? 'text-green-600' : 'text-red-600'
                            }`}>
                              {showBalances ? (
                                <>
                                  {pnlPercent >= 0 ? '+' : ''}
                                  {pnlPercent.toFixed(2)}%
                                </>
                              ) : '••••'}
                            </div>
                          </div>
                        </div>

                        {/* Дополнительная информация */}
                        <div className="mt-4 pt-4 border-t border-gray-100 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <span className="text-gray-600">Средняя цена: </span>
                            <span className="font-medium">
                              {showBalances && position.avg_buy_price 
                                ? `$${position.avg_buy_price.toFixed(8)}` 
                                : '••••'
                              }
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-600">Куплено: </span>
                            <span className="font-medium">
                              {showBalances ? position.total_bought.toLocaleString() : '••••'}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-600">Продано: </span>
                            <span className="font-medium">
                              {showBalances ? position.total_sold.toLocaleString() : '••••'}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-600">Первая сделка: </span>
                            <span className="font-medium">
                              {new Date(position.first_trade_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </Card>
          </>
        )}
      </div>
    </div>
  )
}