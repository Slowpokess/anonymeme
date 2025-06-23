/**
 * 💱 Страница торговли токенами
 * Основной интерфейс для торговли мемкоинами
 */

'use client'

import React, { useState, useEffect } from 'react'
import { useWallet } from '@solana/wallet-adapter-react'
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui'
import { Search, TrendingUp, TrendingDown, Filter, ArrowLeft, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card } from '@/components/ui/Card'
import TradingInterface from '@/components/TradingInterface'
import RealTimeUpdates from '@/components/RealTimeUpdates'
import { Token, TradeType, TokenStatus, CurveType, PaginatedResponse } from '@/types'
import { apiService } from '@/services/api'
import toast from 'react-hot-toast'

// Функция для вычисления дополнительных свойств токена для совместимости
const enrichToken = (token: Token): Token => ({
  ...token,
  price: parseFloat(token.current_price),
  bonding_curve_progress: Math.min((parseFloat(token.market_cap) / parseFloat(token.graduation_threshold)) * 100, 100),
  holders: token.holders_count,
  liquidity: parseFloat(token.sol_reserves)
})

export default function TradePage() {
  const [mounted, setMounted] = useState(false)
  const [selectedToken, setSelectedToken] = useState<Token | null>(null)
  const [tokens, setTokens] = useState<Token[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<'market_cap' | 'volume_24h' | 'price_change_24h'>('market_cap')
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
    total: 0,
    pages: 0,
    has_next: false,
    has_prev: false
  })
  
  const { connected, publicKey } = useWallet()

  // Загрузка токенов
  useEffect(() => {
    const loadTokens = async () => {
      try {
        setLoading(true)
        const response = await apiService.getTokens({
          page: pagination.page,
          limit: pagination.limit,
          search: searchQuery || undefined,
          sort_by: sortBy,
          order: 'desc',
          status: 'active'
        })

        const enrichedTokens = response.data.map(enrichToken)
        setTokens(enrichedTokens)
        setPagination(response.pagination)

        // Выбираем первый токен по умолчанию
        if (enrichedTokens.length > 0 && !selectedToken) {
          setSelectedToken(enrichedTokens[0])
        }
      } catch (error) {
        console.error('Failed to load tokens:', error)
        toast.error('Ошибка загрузки токенов')
      } finally {
        setLoading(false)
      }
    }

    if (mounted) {
      loadTokens()
    }
  }, [mounted, pagination.page, sortBy, searchQuery])

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  // Поиск с debounce
  const [searchDebounced, setSearchDebounced] = useState('')
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchDebounced(searchQuery)
    }, 500)
    
    return () => clearTimeout(timer)
  }, [searchQuery])

  // Перезагрузка при изменении поискового запроса
  useEffect(() => {
    if (mounted) {
      setPagination(prev => ({ ...prev, page: 1 }))
    }
  }, [searchDebounced])

  const displayedTokens = tokens

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <Link href="/" className="flex items-center text-gray-600 hover:text-gray-900">
                <ArrowLeft className="w-5 h-5 mr-2" />
                Назад
              </Link>
              <h1 className="text-2xl font-bold text-gray-900">
                Торговля
              </h1>
            </div>
            
            <WalletMultiButton className="!bg-blue-600 hover:!bg-blue-700 !rounded-lg" />
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {!connected ? (
          // Сообщение о необходимости подключения кошелька
          <div className="text-center py-16">
            <div className="max-w-md mx-auto">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Подключите кошелек
              </h3>
              <p className="text-gray-600 mb-6">
                Для начала торговли необходимо подключить Solana кошелек
              </p>
              <WalletMultiButton className="!bg-blue-600 hover:!bg-blue-700 !rounded-lg !text-white !px-6 !py-3" />
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Список токенов */}
            <div className="lg:col-span-1">
              <Card className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-gray-900">
                    Токены
                  </h2>
                  <Button variant="outline" size="sm">
                    <Filter className="w-4 h-4 mr-2" />
                    Фильтр
                  </Button>
                </div>

                {/* Поиск */}
                <div className="mb-6">
                  <Input
                    placeholder="Поиск токенов..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    leftIcon={<Search className="w-4 h-4" />}
                  />
                </div>

                {/* Сортировка */}
                <div className="mb-6">
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as any)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="market_cap">По капитализации</option>
                    <option value="volume_24h">По объему</option>
                    <option value="price_change_24h">По изменению цены</option>
                  </select>
                </div>

                {/* Список токенов */}
                <div className="space-y-3">
                  {loading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
                    </div>
                  ) : displayedTokens.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      {searchQuery ? 'Токены не найдены' : 'Нет доступных токенов'}
                    </div>
                  ) : (
                    displayedTokens.map((token) => (
                      <div
                      key={token.id}
                      onClick={() => setSelectedToken(token)}
                      className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                        selectedToken?.id === token.id
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-3">
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
                        <div className={`flex items-center ${
                          token.price_change_24h >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {token.price_change_24h >= 0 ? (
                            <TrendingUp className="w-4 h-4 mr-1" />
                          ) : (
                            <TrendingDown className="w-4 h-4 mr-1" />
                          )}
                          {Math.abs(token.price_change_24h).toFixed(1)}%
                        </div>
                      </div>
                      
                      <div className="text-sm text-gray-600 space-y-1">
                        <div className="flex justify-between">
                          <span>Цена:</span>
                          <span className="font-medium">${token.price.toFixed(8)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Капитализация:</span>
                          <span className="font-medium">${(Number(token.market_cap) / 1000).toFixed(1)}K</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Объем 24ч:</span>
                          <span className="font-medium">${(Number(token.volume_24h) / 1000).toFixed(1)}K</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Прогресс кривой:</span>
                          <span className="font-medium">{token.bonding_curve_progress.toFixed(1)}%</span>
                        </div>
                      </div>
                      </div>
                    ))
                  )}
                  
                  {/* Пагинация */}
                  {pagination.has_next && (
                    <div className="mt-4">
                      <Button 
                        variant="outline" 
                        onClick={() => setPagination(prev => ({ ...prev, page: prev.page + 1 }))}
                        disabled={loading}
                        className="w-full"
                      >
                        {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                        Загрузить еще
                      </Button>
                    </div>
                  )}
                </div>
              </Card>
            </div>

            {/* Панель торговли */}
            <div className="lg:col-span-2">
              {selectedToken ? (
                <div className="space-y-6">
                  {/* Информация о токене */}
                  <Card className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center space-x-4">
                        <span className="text-4xl">{selectedToken.image}</span>
                        <div>
                          <h1 className="text-2xl font-bold text-gray-900">
                            {selectedToken.name} ({selectedToken.symbol})
                          </h1>
                          <p className="text-gray-600 mt-1">
                            {selectedToken.description}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-gray-900">
                          ${selectedToken.price.toFixed(8)}
                        </div>
                        <div className={`flex items-center justify-end ${
                          selectedToken.price_change_24h >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {selectedToken.price_change_24h >= 0 ? (
                            <TrendingUp className="w-4 h-4 mr-1" />
                          ) : (
                            <TrendingDown className="w-4 h-4 mr-1" />
                          )}
                          {selectedToken.price_change_24h.toFixed(2)}%
                        </div>
                      </div>
                    </div>

                    {/* Прогресс-бар бондинг кривой */}
                    <div className="mb-4">
                      <div className="flex justify-between text-sm text-gray-600 mb-2">
                        <span>Прогресс бондинг-кривой</span>
                        <span>{selectedToken.bonding_curve_progress.toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${selectedToken.bonding_curve_progress}%` }}
                        />
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        При достижении 100% токен будет выведен на DEX
                      </div>
                    </div>

                    {/* Статистика */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <div className="text-gray-600">Капитализация</div>
                        <div className="font-semibold">${(Number(selectedToken.market_cap) / 1000).toFixed(1)}K</div>
                      </div>
                      <div>
                        <div className="text-gray-600">Объем 24ч</div>
                        <div className="font-semibold">${(Number(selectedToken.volume_24h) / 1000).toFixed(1)}K</div>
                      </div>
                      <div>
                        <div className="text-gray-600">Держатели</div>
                        <div className="font-semibold">{selectedToken.holders}</div>
                      </div>
                      <div>
                        <div className="text-gray-600">Ликвидность</div>
                        <div className="font-semibold">${(selectedToken.liquidity / 1000).toFixed(1)}K</div>
                      </div>
                    </div>
                  </Card>

                  {/* Торговая панель с WebSocket */}
                  <TradingInterface 
                    token={{
                      ...selectedToken,
                      mint_address: selectedToken.mint,
                      sol_reserves: selectedToken.liquidity,
                      token_reserves: Number(selectedToken.total_supply) || 1000000,
                      trades_24h: Number(selectedToken.trades_count) || 0,
                      bonding_curve_progress: selectedToken.bonding_curve_progress,
                      graduation_threshold: Number(selectedToken.graduation_threshold) || 69000,
                      is_graduated: selectedToken.bonding_curve_progress >= 100
                    }}
                    userWallet={publicKey?.toString()}
                    userId={publicKey?.toString()} // В реальном приложении нужен настоящий user_id
                    onTradeComplete={(trade) => {
                      console.log('Торговая операция завершена:', trade)
                      toast.success(`Торговля завершена: ${trade.transaction_signature}`)
                      // Перезагрузка токенов для обновления данных
                      setPagination(prev => ({ ...prev, page: 1 }))
                    }}
                  />
                </div>
              ) : (
                <Card className="p-12 text-center">
                  <div className="text-gray-400 mb-4">
                    <TrendingUp className="w-16 h-16 mx-auto" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Выберите токен для торговли
                  </h3>
                  <p className="text-gray-600">
                    Выберите токен из списка слева для начала торговли
                  </p>
                </Card>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}