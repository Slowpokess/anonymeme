/**
 * 🏠 Главная страница Anonymeme
 * Landing page с обзором платформы и токенов
 */

'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { TrendingUp, Shield, Zap, Users, ArrowRight, Play } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useWallet } from '@solana/wallet-adapter-react'
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui'
import { useWalletStore } from '@/store/wallet'

export default function HomePage() {
  const [mounted, setMounted] = useState(false)
  const { connected, publicKey } = useWallet()
  const { balance, user } = useWalletStore()

  // Избегаем SSR проблем
  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-500"></div>
      </div>
    )
  }
  const features = [
    {
      icon: <Shield className="w-8 h-8" />,
      title: 'Анонимная торговля',
      description: 'Торгуйте без раскрытия личности с помощью Solana кошельков'
    },
    {
      icon: <Zap className="w-8 h-8" />,
      title: 'Мгновенные сделки',
      description: 'Быстрые транзакции и низкие комиссии на Solana блокчейне'
    },
    {
      icon: <TrendingUp className="w-8 h-8" />,
      title: 'Бондинг-кривые',
      description: 'Справедливое ценообразование через алгоритмические кривые'
    },
    {
      icon: <Users className="w-8 h-8" />,
      title: 'Сообщество',
      description: 'Создавайте и торгуйте токенами вместе с сообществом'
    }
  ]

  const stats = [
    { label: 'Токенов создано', value: '1,234' },
    { label: 'Общий объем', value: '₿12.5K SOL' },
    { label: 'Активных трейдеров', value: '5,678' },
    { label: 'Сделок за 24ч', value: '890' }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900">
      {/* Header */}
      <header className="relative z-10 px-4 py-6 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-r from-primary-500 to-secondary-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">A</span>
            </div>
            <span className="text-xl font-bold text-white">Anonymeme</span>
          </div>
          
          <nav className="hidden md:flex space-x-8">
            <Link href="/trade" className="text-gray-300 hover:text-white transition-colors">
              Торговля
            </Link>
            <Link href="/create" className="text-gray-300 hover:text-white transition-colors">
              Создать токен
            </Link>
            <Link href="/analytics" className="text-gray-300 hover:text-white transition-colors">
              Аналитика
            </Link>
          </nav>
          
          <WalletMultiButton className="!bg-gradient-to-r !from-primary-500 !to-secondary-500 !rounded-lg" />
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative px-4 py-20 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center">
          <h1 className="text-4xl sm:text-6xl font-bold text-white mb-6">
            Анонимная торговля
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-primary-400 to-secondary-400">
              мемекоинами
            </span>
          </h1>
          
          <p className="text-xl text-gray-300 mb-8 max-w-3xl mx-auto">
            Создавайте, торгуйте и зарабатывайте на мемекоинах в полностью децентрализованной 
            и анонимной среде на блокчейне Solana
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
            {connected ? (
              <div className="flex flex-col sm:flex-row gap-4">
                <Link href="/trade">
                  <Button 
                    size="lg" 
                    className="bg-gradient-to-r from-primary-500 to-secondary-500 text-white px-8 py-4"
                    rightIcon={<ArrowRight className="w-5 h-5" />}
                  >
                    Начать торговлю
                  </Button>
                </Link>
                <Link href="/create">
                  <Button 
                    variant="outline" 
                    size="lg"
                    className="border-white/20 text-white hover:bg-white/10 px-8 py-4"
                  >
                    Создать токен
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="flex flex-col sm:flex-row gap-4">
                <WalletMultiButton className="!bg-gradient-to-r !from-primary-500 !to-secondary-500 !text-white !px-8 !py-4 !text-lg !rounded-lg" />
                <Button 
                  variant="outline" 
                  size="lg"
                  className="border-white/20 text-white hover:bg-white/10 px-8 py-4"
                  leftIcon={<Play className="w-5 h-5" />}
                >
                  Смотреть демо
                </Button>
              </div>
            )}
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 mb-20">
            {stats.map((stat, index) => (
              <div key={index} className="text-center">
                <div className="text-3xl font-bold text-white mb-2">{stat.value}</div>
                <div className="text-gray-400">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="relative px-4 py-20 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">
              Почему Anonymeme?
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Мы предоставляем самую продвинутую платформу для торговли мемекоинами 
              с полной анонимностью и безопасностью
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div 
                key={index}
                className="p-6 rounded-2xl bg-white/5 backdrop-blur border border-white/10 hover:bg-white/10 transition-all duration-300"
              >
                <div className="text-primary-400 mb-4">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-400">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative px-4 py-20 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <div className="p-8 rounded-3xl bg-gradient-to-r from-primary-500/20 to-secondary-500/20 backdrop-blur border border-white/20">
            <h2 className="text-3xl font-bold text-white mb-4">
              Готовы начать?
            </h2>
            <p className="text-gray-300 mb-8">
              Подключите кошелек и начните торговать мемекоинами уже сегодня
            </p>
            {connected ? (
              <Link href="/trade">
                <Button 
                  size="lg"
                  className="bg-gradient-to-r from-primary-500 to-secondary-500 text-white px-8 py-4"
                >
                  Начать торговлю
                </Button>
              </Link>
            ) : (
              <WalletMultiButton className="!bg-gradient-to-r !from-primary-500 !to-secondary-500 !text-white !px-8 !py-4 !text-lg !rounded-lg" />
            )}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative px-4 py-12 sm:px-6 lg:px-8 border-t border-white/10">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center space-x-2 mb-4 md:mb-0">
              <div className="w-6 h-6 bg-gradient-to-r from-primary-500 to-secondary-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-xs">A</span>
              </div>
              <span className="text-white font-semibold">Anonymeme</span>
            </div>
            
            <div className="flex space-x-6 text-gray-400 text-sm">
              <Link href="/terms" className="hover:text-white transition-colors">
                Условия использования
              </Link>
              <Link href="/privacy" className="hover:text-white transition-colors">
                Политика конфиденциальности
              </Link>
              <Link href="/docs" className="hover:text-white transition-colors">
                Документация
              </Link>
            </div>
          </div>
          
          <div className="mt-8 pt-8 border-t border-white/10 text-center text-gray-400 text-sm">
            © 2024 Anonymeme. Все права защищены.
          </div>
        </div>
      </footer>
    </div>
  )
}