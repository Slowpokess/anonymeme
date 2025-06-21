/**
 * 🏗️ Шапка приложения с навигацией и кошельком
 * Production-ready header с адаптивным дизайном
 */

import React from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'
import { clsx } from 'clsx'
import { 
  Menu, 
  X, 
  TrendingUp, 
  BarChart3, 
  Wallet,
  User,
  Settings,
  LogOut,
  Bell
} from 'lucide-react'
import { Button } from '@/components/ui/Button'

interface HeaderProps {
  onWalletConnect: () => void
  walletAddress?: string
  isWalletConnected: boolean
  isWalletConnecting: boolean
  onWalletDisconnect: () => void
}

export function Header({
  onWalletConnect,
  walletAddress,
  isWalletConnected,
  isWalletConnecting,
  onWalletDisconnect
}: HeaderProps) {
  const router = useRouter()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false)
  const [isProfileMenuOpen, setIsProfileMenuOpen] = React.useState(false)

  const navigation = [
    { name: 'Торговля', href: '/trade', icon: TrendingUp },
    { name: 'Аналитика', href: '/analytics', icon: BarChart3 },
    { name: 'Портфолио', href: '/portfolio', icon: Wallet },
  ]

  const formatWalletAddress = (address: string) => {
    return `${address.slice(0, 4)}...${address.slice(-4)}`
  }

  const isActiveRoute = (href: string) => {
    return router.pathname === href || router.pathname.startsWith(href)
  }

  return (
    <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-r from-primary-500 to-secondary-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">A</span>
              </div>
              <span className="text-xl font-bold text-gray-900">Anonymeme</span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex space-x-8">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = isActiveRoute(item.href)
              
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={clsx(
                    'flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                    isActive
                      ? 'text-primary-600 bg-primary-50'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.name}</span>
                </Link>
              )
            })}
          </nav>

          {/* Right side - Wallet & Profile */}
          <div className="flex items-center space-x-4">
            {/* Notifications */}
            {isWalletConnected && (
              <button className="p-2 text-gray-400 hover:text-gray-500 hover:bg-gray-100 rounded-md transition-colors">
                <Bell className="w-5 h-5" />
              </button>
            )}

            {/* Wallet Connection */}
            {!isWalletConnected ? (
              <Button
                onClick={onWalletConnect}
                loading={isWalletConnecting}
                variant="primary"
                size="sm"
                leftIcon={<Wallet className="w-4 h-4" />}
              >
                Подключить кошелек
              </Button>
            ) : (
              <div className="relative">
                <button
                  onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
                  className="flex items-center space-x-2 p-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
                >
                  <div className="w-8 h-8 bg-gradient-to-r from-primary-500 to-secondary-500 rounded-full flex items-center justify-center">
                    <User className="w-4 h-4 text-white" />
                  </div>
                  <span className="hidden sm:block font-medium">
                    {formatWalletAddress(walletAddress!)}
                  </span>
                </button>

                {/* Profile Dropdown */}
                {isProfileMenuOpen && (
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 border border-gray-200">
                    <Link
                      href="/profile"
                      className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <User className="w-4 h-4 mr-3" />
                      Профиль
                    </Link>
                    <Link
                      href="/settings"
                      className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <Settings className="w-4 h-4 mr-3" />
                      Настройки
                    </Link>
                    <hr className="my-1 border-gray-200" />
                    <button
                      onClick={onWalletDisconnect}
                      className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <LogOut className="w-4 h-4 mr-3" />
                      Отключить кошелек
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Mobile menu button */}
            <button
              className="md:hidden p-2 text-gray-400 hover:text-gray-500 hover:bg-gray-100 rounded-md"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              {isMobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Navigation */}
      {isMobileMenuOpen && (
        <div className="md:hidden">
          <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3 bg-white border-t border-gray-200">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = isActiveRoute(item.href)
              
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={clsx(
                    'flex items-center space-x-3 px-3 py-2 rounded-md text-base font-medium transition-colors',
                    isActive
                      ? 'text-primary-600 bg-primary-50'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  )}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.name}</span>
                </Link>
              )
            })}
          </div>
        </div>
      )}

      {/* Click outside to close dropdowns */}
      {(isProfileMenuOpen || isMobileMenuOpen) && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => {
            setIsProfileMenuOpen(false)
            setIsMobileMenuOpen(false)
          }}
        />
      )}
    </header>
  )
}

export default Header