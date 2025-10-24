/**
 * 📊 Страница симулятора цен
 * Интерактивная визуализация бондинг-кривых
 */

'use client'

import React, { useState } from 'react'
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui'
import { ArrowLeft, Info, Lightbulb, BookOpen } from 'lucide-react'
import Link from 'next/link'
import { PriceSimulator } from '@/components/bonding-curve'
import { Card } from '@/components/ui/Card'
import { CurveType } from '@/types'

export default function SimulatorPage() {
  const [mounted, setMounted] = useState(false)

  React.useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <Link
                href="/"
                className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
              >
                <ArrowLeft className="w-5 h-5 mr-2" />
                Назад
              </Link>
              <h1 className="text-2xl font-bold text-gray-900">
                Симулятор цен
              </h1>
            </div>

            <WalletMultiButton className="!bg-blue-600 hover:!bg-blue-700 !rounded-lg" />
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Introduction */}
        <div className="mb-8">
          <Card className="p-6 bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                <Lightbulb className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  Что такое бондинг-кривая?
                </h2>
                <p className="text-gray-700 mb-4">
                  Бондинг-кривая — это математическая функция, которая определяет цену токена
                  в зависимости от его supply (количества в обращении). Когда пользователи покупают
                  токены, цена растет по заданной кривой. При продаже — снижается.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-white rounded-lg p-4 border border-blue-100">
                    <h3 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
                      <Info className="w-4 h-4" />
                      Преимущества
                    </h3>
                    <ul className="text-sm text-gray-700 space-y-1">
                      <li>✅ Автоматическое ценообразование</li>
                      <li>✅ Всегда доступная ликвидность</li>
                      <li>✅ Прозрачность и предсказуемость</li>
                      <li>✅ Защита от манипуляций</li>
                    </ul>
                  </div>
                  <div className="bg-white rounded-lg p-4 border border-blue-100">
                    <h3 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
                      <BookOpen className="w-4 h-4" />
                      Применение
                    </h3>
                    <ul className="text-sm text-gray-700 space-y-1">
                      <li>🎯 Мемкоины и токены сообществ</li>
                      <li>🎯 NFT и цифровые активы</li>
                      <li>🎯 DAO токены</li>
                      <li>🎯 Краудфандинг проекты</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* Main Simulator */}
        <PriceSimulator showComparison={false} />

        {/* Educational Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
          <Card className="p-6 hover:shadow-lg transition-shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              📈 Линейная кривая
            </h3>
            <p className="text-sm text-gray-600 mb-3">
              Цена растет с постоянной скоростью. Простая и предсказуемая,
              идеальна для начинающих.
            </p>
            <div className="bg-blue-50 rounded p-3 text-xs font-mono text-blue-900">
              price = initial + slope × supply
            </div>
          </Card>

          <Card className="p-6 hover:shadow-lg transition-shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              🚀 Экспоненциальная
            </h3>
            <p className="text-sm text-gray-600 mb-3">
              Цена растет экспоненциально быстрее. Популярна для мемкоинов,
              создает FOMO эффект.
            </p>
            <div className="bg-red-50 rounded p-3 text-xs font-mono text-red-900">
              price = initial × (factor ^ supply)
            </div>
          </Card>

          <Card className="p-6 hover:shadow-lg transition-shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              📊 Сигмоидная (S-кривая)
            </h3>
            <p className="text-sm text-gray-600 mb-3">
              Медленный старт, быстрый рост в середине, замедление в конце.
              Сбалансированный выбор.
            </p>
            <div className="bg-violet-50 rounded p-3 text-xs font-mono text-violet-900">
              price = initial + max / (1 + e^...)
            </div>
          </Card>

          <Card className="p-6 hover:shadow-lg transition-shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              💧 Constant Product
            </h3>
            <p className="text-sm text-gray-600 mb-3">
              Работает как Uniswap (x × y = k). Продвинутый вариант с
              автобалансировкой.
            </p>
            <div className="bg-green-50 rounded p-3 text-xs font-mono text-green-900">
              price = k / supply
            </div>
          </Card>

          <Card className="p-6 hover:shadow-lg transition-shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              📉 Логарифмическая
            </h3>
            <p className="text-sm text-gray-600 mb-3">
              Быстрый рост вначале, постепенное замедление. Защита от
              pump & dump.
            </p>
            <div className="bg-amber-50 rounded p-3 text-xs font-mono text-amber-900">
              price = initial + scale × log(supply)
            </div>
          </Card>

          <Card className="p-6 hover:shadow-lg transition-shadow bg-gradient-to-br from-gray-50 to-gray-100">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              💡 Нужна помощь?
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Не уверены какую кривую выбрать? Ознакомьтесь с нашей полной
              документацией.
            </p>
            <Link href="/docs/bonding-curves">
              <button className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1">
                Читать документацию
                <ArrowLeft className="w-4 h-4 rotate-180" />
              </button>
            </Link>
          </Card>
        </div>

        {/* Tips Section */}
        <Card className="p-6 mt-8 bg-yellow-50 border-yellow-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-yellow-600" />
            Советы по выбору кривой
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-700">
            <div>
              <strong className="text-gray-900">Для мемкоинов:</strong>
              <p className="mt-1">
                Используйте экспоненциальную кривую с агрессивными параметрами.
                Это создаст FOMO эффект и быстрый рост цены.
              </p>
            </div>
            <div>
              <strong className="text-gray-900">Для стабильных проектов:</strong>
              <p className="mt-1">
                Выбирайте логарифмическую или сигмоидную кривую с консервативными
                параметрами для контролируемого роста.
              </p>
            </div>
            <div>
              <strong className="text-gray-900">Для начинающих:</strong>
              <p className="mt-1">
                Начните с линейной кривой и сбалансированными параметрами.
                Это самый простой и предсказуемый вариант.
              </p>
            </div>
            <div>
              <strong className="text-gray-900">Для опытных:</strong>
              <p className="mt-1">
                Попробуйте Constant Product для имитации DEX или сигмоидную
                для плавного роста с контролируемой волатильностью.
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
