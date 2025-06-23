/**
 * 📊 Страница аналитики
 * Production-ready отображение статистики торговли и рынка
 */

'use client'

import React, { useState, useEffect } from 'react'
import { useWallet } from '@solana/wallet-adapter-react'
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui'
import { 
  ArrowLeft, TrendingUp, TrendingDown, BarChart3, 
  DollarSign, Activity, Users, RefreshCw, Calendar,
  PieChart, LineChart, Target, Award
} from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import apiService from '@/services/api'
import toast from 'react-hot-toast'

interface TradingStats {
  period: string
  total_trades: number
  total_volume_sol: number
  total_fees_paid: number
  buy_trades: number
  sell_trades: number
  average_slippage: number
  largest_trade_sol: number
  trades_per_day: number
}

interface MarketOverview {
  total_tokens: number
  active_tokens: number
  total_market_cap: number
  total_volume_24h: number
  total_trades_24h: number
  average_price_change_24h: number
}

interface TopToken {
  id: string
  name: string
  symbol: string
  image: string
  current_price: number
  market_cap: number
  volume_24h: number
  price_change_24h: number
  trades_24h: number
}

export default function AnalyticsPage() {
  const [mounted, setMounted] = useState(false)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [period, setPeriod] = useState<'1h' | '24h' | '7d' | '30d'>('24h')
  
  const [tradingStats, setTradingStats] = useState<TradingStats | null>(null)
  const [marketOverview, setMarketOverview] = useState<MarketOverview | null>(null)
  const [topTokens, setTopTokens] = useState<TopToken[]>([])
  
  const { connected } = useWallet()

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (mounted) {
      loadAnalytics()
    }
  }, [mounted, period])

  const loadAnalytics = async () => {
    try {
      setLoading(true)

      // Параллельная загрузка данных
      const promises = [
        // Рыночные данные доступны всем
        loadMarketOverview(),
        loadTopTokens()
      ]

      // Статистика торговли только для авторизованных пользователей
      if (connected) {
        promises.push(loadTradingStats())
      }

      await Promise.all(promises)
    } catch (error: any) {
      console.error('Failed to load analytics:', error)
      toast.error('Ошибка загрузки аналитики')
    } finally {
      setLoading(false)
    }
  }

  const loadTradingStats = async () => {
    try {
      const response = await apiService.getTradingStats(period)
      if (response.success) {
        setTradingStats(response.data)
      }
    } catch (error) {
      console.error('Failed to load trading stats:', error)
    }
  }

  const loadMarketOverview = async () => {
    try {
      const response = await apiService.getMarketOverview()
      if (response.success) {
        const overview: MarketOverview = {
          total_tokens: response.data.total_tokens,
          active_tokens: response.data.total_tokens, // Предполагаем что все активные
          total_market_cap: parseFloat(response.data.total_market_cap || '0'),
          total_volume_24h: parseFloat(response.data.total_volume_24h || '0'),
          total_trades_24h: response.data.total_trades_24h,
          average_price_change_24h: response.data.average_price_change_24h || 0
        }
        setMarketOverview(overview)
      }
    } catch (error) {
      console.error('Failed to load market overview:', error)
      // Fallback к мок-данным при ошибке
      const mockOverview: MarketOverview = {
        total_tokens: 0,
        active_tokens: 0,
        total_market_cap: 0,
        total_volume_24h: 0,
        total_trades_24h: 0,
        average_price_change_24h: 0
      }
      setMarketOverview(mockOverview)
    }
  }

  const loadTopTokens = async () => {
    try {
      const response = await apiService.getTrendingTokens()
      if (response.success) {
        const tokens: TopToken[] = response.data.slice(0, 10).map(token => ({
          id: token.id,
          name: token.name,
          symbol: token.symbol,
          image: token.image || '🪙',
          current_price: parseFloat(token.current_price),
          market_cap: parseFloat(token.market_cap),
          volume_24h: parseFloat(token.volume_24h),
          price_change_24h: token.price_change_24h,
          trades_24h: token.total_trades
        }))
        setTopTokens(tokens)
      }
    } catch (error) {
      console.error('Failed to load top tokens:', error)
      // Fallback к пустому массиву при ошибке
      setTopTokens([])
    }
  }

  const refreshAnalytics = async () => {
    try {
      setRefreshing(true)
      await loadAnalytics()
      toast.success('Аналитика обновлена')
    } catch (error) {
      // Error already handled in loadAnalytics
    } finally {
      setRefreshing(false)
    }
  }

  const formatNumber = (num: number, decimals: number = 2): string => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(decimals)}M`
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(decimals)}K`
    }
    return num.toFixed(decimals)
  }

  const formatSOL = (amount: number): string => {
    return `${formatNumber(amount, 4)} SOL`
  }

  if (!mounted) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

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
                Аналитика
              </h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <Button
                variant="outline"
                onClick={refreshAnalytics}
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
            {/* Рыночная статистика */}
            <div className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                <BarChart3 className="w-6 h-6 mr-2" />
                Обзор рынка
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <Card className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600">Всего токенов</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {marketOverview?.total_tokens.toLocaleString() || '0'}
                      </p>
                      <p className="text-xs text-gray-500">
                        {marketOverview?.active_tokens} активных
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
                      <p className="text-sm text-gray-600">Общий объем 24ч</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {formatSOL(marketOverview?.total_volume_24h || 0)}
                      </p>
                    </div>
                    <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                      <DollarSign className="w-6 h-6 text-green-600" />
                    </div>
                  </div>
                </Card>

                <Card className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600">Сделок 24ч</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {marketOverview?.total_trades_24h.toLocaleString() || '0'}
                      </p>
                    </div>
                    <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                      <Activity className="w-6 h-6 text-purple-600" />
                    </div>
                  </div>
                </Card>

                <Card className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600">Общий Market Cap</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {formatSOL(marketOverview?.total_market_cap || 0)}
                      </p>
                    </div>
                    <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                      <Target className="w-6 h-6 text-yellow-600" />
                    </div>
                  </div>
                </Card>
              </div>
            </div>

            {/* Статистика торговли пользователя */}
            {connected && tradingStats && (
              <div className="mb-8">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-gray-900 flex items-center">
                    <LineChart className="w-6 h-6 mr-2" />
                    Ваша торговая статистика
                  </h2>
                  
                  <div className="flex items-center space-x-2">
                    <Calendar className="w-4 h-4 text-gray-500" />
                    <select
                      value={period}
                      onChange={(e) => setPeriod(e.target.value as any)}
                      className="px-3 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="1h">1 час</option>
                      <option value="24h">24 часа</option>
                      <option value="7d">7 дней</option>
                      <option value="30d">30 дней</option>
                    </select>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <Card className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-600">Всего сделок</p>
                        <p className="text-2xl font-bold text-gray-900">
                          {tradingStats.total_trades}
                        </p>
                        <p className="text-xs text-gray-500">
                          {tradingStats.buy_trades} покупок / {tradingStats.sell_trades} продаж
                        </p>
                      </div>
                      <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center">
                        <Activity className="w-6 h-6 text-indigo-600" />
                      </div>
                    </div>
                  </Card>

                  <Card className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-600">Объем торгов</p>
                        <p className="text-2xl font-bold text-gray-900">
                          {formatSOL(tradingStats.total_volume_sol)}
                        </p>
                      </div>
                      <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                        <DollarSign className="w-6 h-6 text-green-600" />
                      </div>
                    </div>
                  </Card>

                  <Card className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-600">Комиссии</p>
                        <p className="text-2xl font-bold text-gray-900">
                          {formatSOL(tradingStats.total_fees_paid)}
                        </p>
                      </div>
                      <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center">
                        <Target className="w-6 h-6 text-red-600" />
                      </div>
                    </div>
                  </Card>

                  <Card className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-600">Средний слиппаж</p>
                        <p className="text-2xl font-bold text-gray-900">
                          {tradingStats.average_slippage.toFixed(2)}%
                        </p>
                      </div>
                      <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                        <BarChart3 className="w-6 h-6 text-orange-600" />
                      </div>
                    </div>
                  </Card>
                </div>
              </div>
            )}

            {/* Подключение кошелька для авторизованных данных */}
            {!connected && (
              <Card className="p-8 mb-8 text-center">
                <Users className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Подключите кошелек
                </h3>
                <p className="text-gray-600 mb-6">
                  Для просмотра персональной статистики торговли подключите Solana кошелек
                </p>
                <WalletMultiButton className="!bg-blue-600 hover:!bg-blue-700 !rounded-lg !text-white !px-6 !py-3" />
              </Card>
            )}

            {/* Топ токены */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-gray-900 flex items-center">
                  <Award className="w-6 h-6 mr-2" />
                  Топ токены по объему
                </h2>
              </div>

              {topTokens.length === 0 ? (
                <div className="text-center py-12">
                  <BarChart3 className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Данные недоступны
                  </h3>
                  <p className="text-gray-600">
                    Токены появятся после начала торговли
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {topTokens.map((token, index) => (
                    <div
                      key={token.id}
                      className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
                    >
                      <div className="flex items-center space-x-4">
                        <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center font-semibold text-sm">
                          {index + 1}
                        </div>
                        <span className="text-2xl">{token.image}</span>
                        <div>
                          <div className="font-semibold text-gray-900">
                            {token.symbol}
                          </div>
                          <div className="text-sm text-gray-600">
                            {token.name}
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-right">
                        <div>
                          <div className="text-sm text-gray-600">Цена</div>
                          <div className="font-semibold">
                            ${token.current_price.toFixed(8)}
                          </div>
                        </div>

                        <div>
                          <div className="text-sm text-gray-600">Market Cap</div>
                          <div className="font-semibold">
                            {formatSOL(token.market_cap)}
                          </div>
                        </div>

                        <div>
                          <div className="text-sm text-gray-600">Объем 24ч</div>
                          <div className="font-semibold">
                            {formatSOL(token.volume_24h)}
                          </div>
                        </div>

                        <div>
                          <div className="text-sm text-gray-600">Изменение 24ч</div>
                          <div className={`font-semibold flex items-center ${
                            token.price_change_24h >= 0 ? 'text-green-600' : 'text-red-600'
                          }`}>
                            {token.price_change_24h >= 0 ? (
                              <TrendingUp className="w-4 h-4 mr-1" />
                            ) : (
                              <TrendingDown className="w-4 h-4 mr-1" />
                            )}
                            {token.price_change_24h >= 0 ? '+' : ''}
                            {token.price_change_24h.toFixed(2)}%
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </>
        )}
      </div>
    </div>
  )
}