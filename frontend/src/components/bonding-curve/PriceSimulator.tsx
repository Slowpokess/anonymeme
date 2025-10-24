/**
 * 📊 Price Simulator - Интерактивный симулятор цен для бондинг-кривых
 * Production-ready компонент с поддержкой всех 5 типов кривых
 */

'use client'

import React, { useState, useMemo } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  TooltipProps
} from 'recharts'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { CurveType } from '@/types'
import {
  generatePriceData,
  calculateBuyCost,
  calculateSellRevenue,
  getCurveName,
  getCurveColor,
  CURVE_PRESETS,
  BondingCurveConfig,
  PriceDataPoint
} from '@/utils/bondingCurve'
import { Info, TrendingUp, DollarSign, BarChart3, Settings } from 'lucide-react'
import { clsx } from 'clsx'

interface PriceSimulatorProps {
  className?: string
  defaultCurveType?: CurveType
  showComparison?: boolean
}

type PresetType = 'conservative' | 'balanced' | 'aggressive' | 'custom'

export function PriceSimulator({
  className,
  defaultCurveType = CurveType.EXPONENTIAL,
  showComparison = false
}: PriceSimulatorProps) {
  const [curveType, setCurveType] = useState<CurveType>(defaultCurveType)
  const [preset, setPreset] = useState<PresetType>('balanced')
  const [maxSupply, setMaxSupply] = useState(500_000)
  const [compareMode, setCompareMode] = useState(showComparison)

  // Калькулятор
  const [currentSupply, setCurrentSupply] = useState(100_000)
  const [tradeAmount, setTradeAmount] = useState(1_000)

  // Генерация конфигурации на основе выбранного пресета
  const config: BondingCurveConfig = useMemo(() => {
    if (preset === 'custom') {
      return {
        curveType,
        initialPrice: 0.000005,
        slope: 0.000005,
        growthFactor: 1.00001,
        midpoint: 250_000,
        steepness: 0.00002,
        k: 1_000_000_000,
        base: 2,
        scaleFactor: 0.001
      }
    }

    const presetParams = CURVE_PRESETS[preset][curveType]
    return {
      curveType,
      initialPrice: 0.000005,
      ...presetParams
    }
  }, [curveType, preset])

  // Генерация данных для графика
  const chartData = useMemo(() => {
    if (compareMode) {
      // Режим сравнения - показываем все кривые
      const allCurves = Object.values(CurveType)
      const dataPoints: Record<number, any> = {}

      allCurves.forEach(type => {
        const curveConfig = {
          curveType: type,
          initialPrice: 0.000005,
          ...CURVE_PRESETS[preset][type]
        }
        const data = generatePriceData(curveConfig, maxSupply, 100)

        data.forEach(point => {
          if (!dataPoints[point.supply]) {
            dataPoints[point.supply] = { supply: point.supply }
          }
          dataPoints[point.supply][`price_${type}`] = point.price
        })
      })

      return Object.values(dataPoints)
    } else {
      // Обычный режим - только выбранная кривая
      return generatePriceData(config, maxSupply, 100)
    }
  }, [config, maxSupply, compareMode, preset])

  // Расчеты для калькулятора
  const buyCost = useMemo(() => {
    return calculateBuyCost(currentSupply, tradeAmount, config)
  }, [currentSupply, tradeAmount, config])

  const sellRevenue = useMemo(() => {
    return calculateSellRevenue(currentSupply, tradeAmount, config)
  }, [currentSupply, tradeAmount, config])

  // Кастомный тултип для графика
  const CustomTooltip = ({ active, payload, label }: TooltipProps<number, string>) => {
    if (!active || !payload || !payload.length) return null

    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
        <p className="font-semibold text-gray-900 mb-2">Supply: {label?.toLocaleString()}</p>
        {payload.map((entry, index) => (
          <div key={index} className="flex items-center gap-2 text-sm">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-gray-600">{entry.name}:</span>
            <span className="font-medium text-gray-900">
              {typeof entry.value === 'number'
                ? entry.value < 0.0001
                  ? entry.value.toExponential(4)
                  : entry.value.toFixed(8)
                : entry.value
              } SOL
            </span>
          </div>
        ))}
      </div>
    )
  }

  return (
    <Card className={clsx('p-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-blue-600" />
            Симулятор цен
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Визуализация и сравнение бондинг-кривых
          </p>
        </div>

        <Button
          variant={compareMode ? 'primary' : 'outline'}
          size="sm"
          onClick={() => setCompareMode(!compareMode)}
        >
          {compareMode ? 'Один график' : 'Сравнить все'}
        </Button>
      </div>

      {/* Controls */}
      {!compareMode && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {/* Тип кривой */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Тип кривой
            </label>
            <select
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-sm"
              value={curveType}
              onChange={(e) => setCurveType(e.target.value as CurveType)}
            >
              <option value={CurveType.LINEAR}>Линейная</option>
              <option value={CurveType.EXPONENTIAL}>Экспоненциальная</option>
              <option value={CurveType.SIGMOID}>Сигмоидная</option>
              <option value={CurveType.CONSTANT_PRODUCT}>Constant Product</option>
              <option value={CurveType.LOGARITHMIC}>Логарифмическая</option>
            </select>
          </div>

          {/* Пресет */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Пресет параметров
            </label>
            <select
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-sm"
              value={preset}
              onChange={(e) => setPreset(e.target.value as PresetType)}
            >
              <option value="conservative">Консервативный</option>
              <option value="balanced">Сбалансированный</option>
              <option value="aggressive">Агрессивный</option>
            </select>
          </div>

          {/* Max Supply */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Макс. Supply
            </label>
            <input
              type="number"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              value={maxSupply}
              onChange={(e) => setMaxSupply(parseInt(e.target.value) || 500_000)}
              min={10_000}
              max={10_000_000}
              step={10_000}
            />
          </div>
        </div>
      )}

      {compareMode && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Пресет параметров
            </label>
            <select
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-sm"
              value={preset}
              onChange={(e) => setPreset(e.target.value as PresetType)}
            >
              <option value="conservative">Консервативный</option>
              <option value="balanced">Сбалансированный</option>
              <option value="aggressive">Агрессивный</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Макс. Supply
            </label>
            <input
              type="number"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              value={maxSupply}
              onChange={(e) => setMaxSupply(parseInt(e.target.value) || 500_000)}
              min={10_000}
              max={10_000_000}
              step={10_000}
            />
          </div>
        </div>
      )}

      {/* Chart */}
      <div className="bg-gray-50 rounded-lg p-4 mb-6">
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="supply"
              stroke="#6b7280"
              fontSize={12}
              tickFormatter={(value) => `${(value / 1000).toFixed(0)}K`}
            />
            <YAxis
              stroke="#6b7280"
              fontSize={12}
              tickFormatter={(value) =>
                value < 0.0001 ? value.toExponential(1) : value.toFixed(6)
              }
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: '14px' }} />

            {compareMode ? (
              // Режим сравнения - все кривые
              Object.values(CurveType).map((type) => (
                <Line
                  key={type}
                  type="monotone"
                  dataKey={`price_${type}`}
                  name={getCurveName(type)}
                  stroke={getCurveColor(type)}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 6 }}
                />
              ))
            ) : (
              // Обычный режим - одна кривая
              <Line
                type="monotone"
                dataKey="price"
                name={`Цена (${getCurveName(curveType)})`}
                stroke={getCurveColor(curveType)}
                strokeWidth={3}
                dot={false}
                activeDot={{ r: 8 }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Calculator */}
      {!compareMode && (
        <div className="border-t border-gray-200 pt-6">
          <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-green-600" />
            Калькулятор стоимости
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Inputs */}
            <div className="space-y-4">
              <Input
                label="Текущий Supply"
                type="number"
                value={currentSupply}
                onChange={(e) => setCurrentSupply(parseInt(e.target.value) || 0)}
                helperText="Текущее количество токенов в обращении"
              />

              <Input
                label="Количество токенов"
                type="number"
                value={tradeAmount}
                onChange={(e) => setTradeAmount(parseInt(e.target.value) || 0)}
                helperText="Сколько токенов купить/продать"
              />
            </div>

            {/* Results */}
            <div className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-green-900">
                    <TrendingUp className="w-4 h-4 inline mr-1" />
                    Стоимость покупки
                  </span>
                </div>
                <p className="text-2xl font-bold text-green-700">
                  {buyCost < 0.0001 ? buyCost.toExponential(4) : buyCost.toFixed(6)} SOL
                </p>
                <p className="text-xs text-green-600 mt-1">
                  ~${(buyCost * 100).toFixed(2)} USD (при $100/SOL)
                </p>
              </div>

              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-red-900">
                    <TrendingUp className="w-4 h-4 inline mr-1 rotate-180" />
                    Выручка от продажи
                  </span>
                </div>
                <p className="text-2xl font-bold text-red-700">
                  {sellRevenue < 0.0001 ? sellRevenue.toExponential(4) : sellRevenue.toFixed(6)} SOL
                </p>
                <p className="text-xs text-red-600 mt-1">
                  ~${(sellRevenue * 100).toFixed(2)} USD (при $100/SOL)
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-6">
        <div className="flex items-start gap-2">
          <Info className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-900">
            <strong>Как работает симулятор:</strong>
            <ul className="list-disc list-inside mt-2 space-y-1">
              <li>График показывает как изменяется цена токена при росте supply</li>
              <li>Калькулятор использует интегральный метод для точного расчета стоимости</li>
              <li>Режим сравнения позволяет увидеть разницу между всеми типами кривых</li>
              <li>Пресеты (Conservative/Balanced/Aggressive) задают разные параметры роста</li>
            </ul>
          </div>
        </div>
      </div>
    </Card>
  )
}

export default PriceSimulator
