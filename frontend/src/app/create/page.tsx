/**
 * 🎨 Страница создания токена
 * Production-ready форма для создания мемкоинов
 */

'use client'

import React, { useState } from 'react'
import { useWallet } from '@solana/wallet-adapter-react'
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui'
import { ArrowLeft, Upload, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card } from '@/components/ui/Card'
import { CreateTokenForm, CurveType } from '@/types'
import apiService from '@/services/api'
import toast from 'react-hot-toast'

interface FormErrors {
  name?: string
  symbol?: string
  description?: string
  initial_liquidity?: string
  image?: string
}

type PresetType = 'conservative' | 'balanced' | 'aggressive' | 'custom'

export default function CreateTokenPage() {
  const [mounted, setMounted] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [errors, setErrors] = useState<FormErrors>({})
  const [step, setStep] = useState(1) // 1: Form, 2: Preview, 3: Success
  const [txSignature, setTxSignature] = useState<string | null>(null)
  const [preset, setPreset] = useState<PresetType>('balanced')

  const { connected } = useWallet()

  const [formData, setFormData] = useState<CreateTokenForm>({
    name: '',
    symbol: '',
    description: '',
    initial_liquidity: '1',
    curve_type: CurveType.EXPONENTIAL,
    telegram_link: '',
    twitter_link: '',
    website_link: ''
  })

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

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {}

    if (!formData.name.trim()) {
      newErrors.name = 'Название токена обязательно'
    } else if (formData.name.length > 50) {
      newErrors.name = 'Название не может быть длиннее 50 символов'
    }

    if (!formData.symbol.trim()) {
      newErrors.symbol = 'Символ токена обязателен'
    } else if (formData.symbol.length > 10) {
      newErrors.symbol = 'Символ не может быть длиннее 10 символов'
    } else if (!/^[A-Z0-9]+$/.test(formData.symbol)) {
      newErrors.symbol = 'Символ может содержать только заглавные буквы и цифры'
    }

    if (!formData.description.trim()) {
      newErrors.description = 'Описание токена обязательно'
    } else if (formData.description.length > 500) {
      newErrors.description = 'Описание не может быть длиннее 500 символов'
    }

    const liquidity = parseFloat(formData.initial_liquidity)
    if (isNaN(liquidity) || liquidity < 0.1 || liquidity > 1000) {
      newErrors.initial_liquidity = 'Ликвидность должна быть от 0.1 до 1000 SOL'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleInputChange = (field: keyof CreateTokenForm, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    
    // Очистить ошибку при изменении поля
    if (errors[field as keyof FormErrors]) {
      setErrors(prev => ({ ...prev, [field]: undefined }))
    }
  }

  const handleImageUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      // Проверка размера файла (макс 5MB)
      if (file.size > 5 * 1024 * 1024) {
        toast.error('Размер файла не должен превышать 5MB')
        return
      }

      // Проверка типа файла
      if (!file.type.startsWith('image/')) {
        toast.error('Можно загружать только изображения')
        return
      }

      const reader = new FileReader()
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string)
      }
      reader.readAsDataURL(file)

      setFormData(prev => ({ ...prev, image: file }))
    }
  }

  const handleSubmit = async () => {
    if (!validateForm()) {
      return
    }

    setIsSubmitting(true)
    try {
      const response = await apiService.createToken(formData)
      
      if (response.success) {
        // @ts-ignore - API может не возвращать transaction_signature в зависимости от версии
        setTxSignature(response.data.transaction_signature || response.data.signature || '')
        setStep(3)
        toast.success('Токен успешно создан!')
      } else {
        throw new Error(response.message || 'Ошибка создания токена')
      }
    } catch (error: any) {
      console.error('Token creation failed:', error)
      toast.error(error.message || 'Ошибка создания токена')
    } finally {
      setIsSubmitting(false)
    }
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
                  Создать токен
                </h1>
              </div>
              
              <WalletMultiButton className="!bg-blue-600 hover:!bg-blue-700 !rounded-lg" />
            </div>
          </div>
        </header>

        <div className="max-w-2xl mx-auto px-4 py-16 text-center">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Подключите кошелек
          </h3>
          <p className="text-gray-600 mb-6">
            Для создания токена необходимо подключить Solana кошелек
          </p>
          <WalletMultiButton className="!bg-blue-600 hover:!bg-blue-700 !rounded-lg !text-white !px-6 !py-3" />
        </div>
      </div>
    )
  }

  if (step === 3 && txSignature) {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <h1 className="text-2xl font-bold text-gray-900">
                Токен создан!
              </h1>
              <WalletMultiButton className="!bg-blue-600 hover:!bg-blue-700 !rounded-lg" />
            </div>
          </div>
        </header>

        <div className="max-w-2xl mx-auto px-4 py-16 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
          
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            Поздравляем! Ваш токен создан
          </h2>
          
          <p className="text-gray-600 mb-8">
            Токен <strong>{formData.symbol}</strong> успешно создан и готов к торговле
          </p>

          <div className="bg-white rounded-lg shadow p-6 mb-8 text-left">
            <h3 className="font-semibold text-gray-900 mb-4">Детали транзакции</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Подпись транзакции:</span>
                <span className="font-mono text-gray-900 break-all">{txSignature}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Название токена:</span>
                <span className="font-semibold">{formData.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Символ:</span>
                <span className="font-semibold">{formData.symbol}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Начальная ликвидность:</span>
                <span className="font-semibold">{formData.initial_liquidity} SOL</span>
              </div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href={`/token/${formData.symbol}`}>
              <Button size="lg">
                Перейти к токену
              </Button>
            </Link>
            <Link href="/trade">
              <Button variant="outline" size="lg">
                Начать торговлю
              </Button>
            </Link>
            <Link href="/create">
              <Button 
                variant="ghost" 
                size="lg"
                onClick={() => {
                  setStep(1)
                  setFormData({
                    name: '',
                    symbol: '',
                    description: '',
                    initial_liquidity: '1',
                    curve_type: CurveType.EXPONENTIAL,
                    telegram_link: '',
                    twitter_link: '',
                    website_link: ''
                  })
                  setImagePreview(null)
                  setTxSignature(null)
                }}
              >
                Создать еще токен
              </Button>
            </Link>
          </div>
        </div>
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
                Создать токен
              </h1>
            </div>
            
            <WalletMultiButton className="!bg-blue-600 hover:!bg-blue-700 !rounded-lg" />
          </div>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-4 py-8">
        <Card className="p-8">
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Основная информация
            </h2>
            <p className="text-gray-600">
              Создайте свой мемкоин и начните торговлю на децентрализованной платформе
            </p>
          </div>

          <div className="space-y-6">
            {/* Изображение токена */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Изображение токена
              </label>
              <div className="flex items-center space-x-4">
                <div className="w-20 h-20 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center overflow-hidden">
                  {imagePreview ? (
                    <img 
                      src={imagePreview} 
                      alt="Token preview" 
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <Upload className="w-8 h-8 text-gray-400" />
                  )}
                </div>
                <div>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageUpload}
                    className="hidden"
                    id="token-image"
                  />
                  <label
                    htmlFor="token-image"
                    className="cursor-pointer bg-white border border-gray-300 rounded-md px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Загрузить изображение
                  </label>
                  <p className="text-xs text-gray-500 mt-1">
                    PNG, JPG до 5MB
                  </p>
                </div>
              </div>
              {errors.image && (
                <p className="mt-1 text-sm text-red-600">{errors.image}</p>
              )}
            </div>

            {/* Название токена */}
            <Input
              label="Название токена"
              placeholder="DogeCoin 2.0"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              error={errors.name}
              required
            />

            {/* Символ токена */}
            <Input
              label="Символ токена"
              placeholder="DOGE2"
              value={formData.symbol}
              onChange={(e) => handleInputChange('symbol', e.target.value.toUpperCase())}
              error={errors.symbol}
              helperText="Только заглавные буквы и цифры, максимум 10 символов"
              required
            />

            {/* Описание */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Описание токена *
              </label>
              <textarea
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={4}
                placeholder="Расскажите о вашем токене..."
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
              />
              <div className="flex justify-between items-center mt-1">
                {errors.description ? (
                  <p className="text-sm text-red-600">{errors.description}</p>
                ) : (
                  <span></span>
                )}
                <span className="text-xs text-gray-500">
                  {formData.description.length}/500
                </span>
              </div>
            </div>

            {/* Начальная ликвидность */}
            <Input
              label="Начальная ликвидность (SOL)"
              type="number"
              placeholder="1.0"
              value={formData.initial_liquidity}
              onChange={(e) => handleInputChange('initial_liquidity', e.target.value)}
              error={errors.initial_liquidity}
              helperText="Количество SOL для начальной ликвидности (0.1 - 1000)"
              required
            />

            {/* Тип кривой */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Тип бондинг-кривой *
              </label>
              <select
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                value={formData.curve_type}
                onChange={(e) => handleInputChange('curve_type', e.target.value as CurveType)}
              >
                <option value={CurveType.LINEAR}>
                  Линейная - Равномерный рост цены (начинающим)
                </option>
                <option value={CurveType.EXPONENTIAL}>
                  Экспоненциальная - Быстрый рост цены (популярная)
                </option>
                <option value={CurveType.SIGMOID}>
                  Сигмоидная - Плавный S-образный рост (сбалансированная)
                </option>
                <option value={CurveType.CONSTANT_PRODUCT}>
                  Constant Product - Как Uniswap (продвинутая)
                </option>
                <option value={CurveType.LOGARITHMIC}>
                  Логарифмическая - Замедляющийся рост (для стабильности)
                </option>
              </select>

              {/* Динамическое описание в зависимости от выбранной кривой */}
              <div className="mt-2 p-3 bg-blue-50 rounded-md border border-blue-100">
                <p className="text-xs text-blue-900">
                  {formData.curve_type === CurveType.LINEAR && (
                    <>
                      <strong>Линейная:</strong> Цена растет равномерно с постоянной скоростью.
                      Идеально для начинающих, предсказуемый рост без резких скачков.
                    </>
                  )}
                  {formData.curve_type === CurveType.EXPONENTIAL && (
                    <>
                      <strong>Экспоненциальная:</strong> Цена растет экспоненциально быстрее с каждой покупкой.
                      Популярный выбор для мемкоинов, обеспечивает защиту от манипуляций и создает FOMO эффект.
                    </>
                  )}
                  {formData.curve_type === CurveType.SIGMOID && (
                    <>
                      <strong>Сигмоидная:</strong> S-образная кривая - медленный старт, быстрый средний рост, плавное замедление.
                      Сбалансированный выбор для долгосрочных проектов с контролируемой волатильностью.
                    </>
                  )}
                  {formData.curve_type === CurveType.CONSTANT_PRODUCT && (
                    <>
                      <strong>Constant Product:</strong> Работает как Uniswap (x × y = k).
                      Продвинутый вариант с автоматическим балансированием ликвидности, подходит для опытных создателей.
                    </>
                  )}
                  {formData.curve_type === CurveType.LOGARITHMIC && (
                    <>
                      <strong>Логарифмическая:</strong> Быстрый рост в начале, затем постепенное замедление.
                      Идеальна для стабильных токенов с контролируемой инфляцией и защитой от pump & dump.
                    </>
                  )}
                </p>
              </div>
            </div>

            {/* Пресет параметров */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Пресет параметров *
              </label>
              <div className="grid grid-cols-3 gap-2 mb-3">
                <button
                  type="button"
                  onClick={() => setPreset('conservative')}
                  className={`px-4 py-3 rounded-lg border-2 transition-all ${
                    preset === 'conservative'
                      ? 'border-blue-500 bg-blue-50 text-blue-900'
                      : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
                  }`}
                >
                  <div className="text-sm font-semibold">Консервативный</div>
                  <div className="text-xs mt-1">Медленный рост</div>
                </button>

                <button
                  type="button"
                  onClick={() => setPreset('balanced')}
                  className={`px-4 py-3 rounded-lg border-2 transition-all ${
                    preset === 'balanced'
                      ? 'border-blue-500 bg-blue-50 text-blue-900'
                      : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
                  }`}
                >
                  <div className="text-sm font-semibold">Сбалансированный</div>
                  <div className="text-xs mt-1">Средний рост ⭐</div>
                </button>

                <button
                  type="button"
                  onClick={() => setPreset('aggressive')}
                  className={`px-4 py-3 rounded-lg border-2 transition-all ${
                    preset === 'aggressive'
                      ? 'border-blue-500 bg-blue-50 text-blue-900'
                      : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
                  }`}
                >
                  <div className="text-sm font-semibold">Агрессивный</div>
                  <div className="text-xs mt-1">Быстрый рост</div>
                </button>
              </div>

              {/* Описание пресета */}
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <p className="text-xs text-gray-700">
                  {preset === 'conservative' && (
                    <>
                      <strong>Консервативный:</strong> Низкая начальная цена, медленный рост.
                      Подходит для проектов с долгосрочной перспективой и минимальной спекуляцией.
                    </>
                  )}
                  {preset === 'balanced' && (
                    <>
                      <strong>Сбалансированный (рекомендуется):</strong> Средняя начальная цена, умеренный рост.
                      Оптимальный выбор для большинства мемкоинов - баланс между доступностью и ростом.
                    </>
                  )}
                  {preset === 'aggressive' && (
                    <>
                      <strong>Агрессивный:</strong> Высокая начальная цена, быстрый рост.
                      Для опытных создателей - создает сильный FOMO эффект, но может отпугнуть новых покупателей.
                    </>
                  )}
                </p>
              </div>
            </div>

            {/* Социальные ссылки */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-gray-900">
                Социальные ссылки (необязательно)
              </h3>
              
              <Input
                label="Telegram"
                placeholder="https://t.me/yourchannel"
                value={formData.telegram_link || ''}
                onChange={(e) => handleInputChange('telegram_link', e.target.value)}
              />
              
              <Input
                label="Twitter"
                placeholder="https://twitter.com/yourhandle"
                value={formData.twitter_link || ''}
                onChange={(e) => handleInputChange('twitter_link', e.target.value)}
              />
              
              <Input
                label="Веб-сайт"
                placeholder="https://yourwebsite.com"
                value={formData.website_link || ''}
                onChange={(e) => handleInputChange('website_link', e.target.value)}
              />
            </div>

            {/* Предупреждение */}
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-start">
                <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5 mr-2 flex-shrink-0" />
                <div className="text-sm text-yellow-800">
                  <strong>Важно:</strong> После создания токена изменить его параметры будет невозможно. 
                  Убедитесь, что вся информация указана корректно.
                </div>
              </div>
            </div>

            {/* Кнопка создания */}
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting}
              loading={isSubmitting}
              size="lg"
              fullWidth
              className="font-semibold"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Создание токена...
                </>
              ) : (
                'Создать токен'
              )}
            </Button>

            <p className="text-xs text-center text-gray-500">
              Создание токена требует подтверждения транзакции в вашем кошельке
            </p>
          </div>
        </Card>
      </div>
    </div>
  )
}