/**
 * 📊 Утилиты для расчета цен по бондинг-кривым
 * Production-ready математические функции
 */

import { CurveType } from '@/types'

export interface BondingCurveConfig {
  curveType: CurveType
  initialPrice: number // Начальная цена в SOL
  slope?: number // Для Linear
  growthFactor?: number // Для Exponential (например, 1.00001)
  midpoint?: number // Для Sigmoid (точка перегиба)
  steepness?: number // Для Sigmoid (крутизна S-кривой)
  k?: number // Для Constant Product (константа пула)
  base?: number // Для Logarithmic (основание логарифма)
  scaleFactor?: number // Для Logarithmic (масштабирование)
}

/**
 * Расчет цены токена при заданном supply для любой кривой
 */
export function calculatePrice(supply: number, config: BondingCurveConfig): number {
  const { curveType, initialPrice } = config

  switch (curveType) {
    case CurveType.LINEAR:
      return calculateLinearPrice(supply, initialPrice, config.slope || 0.00001)

    case CurveType.EXPONENTIAL:
      return calculateExponentialPrice(supply, initialPrice, config.growthFactor || 1.00001)

    case CurveType.SIGMOID:
      return calculateSigmoidPrice(
        supply,
        initialPrice,
        config.midpoint || 250_000,
        config.steepness || 0.00002
      )

    case CurveType.CONSTANT_PRODUCT:
      return calculateConstantProductPrice(supply, config.k || 1_000_000_000)

    case CurveType.LOGARITHMIC:
      return calculateLogarithmicPrice(
        supply,
        initialPrice,
        config.base || 2,
        config.scaleFactor || 0.001
      )

    default:
      return initialPrice
  }
}

/**
 * Линейная кривая: price = initial_price + slope × supply
 */
function calculateLinearPrice(supply: number, initialPrice: number, slope: number): number {
  return initialPrice + slope * supply
}

/**
 * Экспоненциальная кривая: price = initial_price × (growth_factor ^ supply)
 */
function calculateExponentialPrice(
  supply: number,
  initialPrice: number,
  growthFactor: number
): number {
  return initialPrice * Math.pow(growthFactor, supply)
}

/**
 * Сигмоидная кривая: price = initial_price + (max_price - initial_price) / (1 + e^(-steepness × (supply - midpoint)))
 */
function calculateSigmoidPrice(
  supply: number,
  initialPrice: number,
  midpoint: number,
  steepness: number
): number {
  const maxPrice = initialPrice * 100 // Максимальная цена в 100 раз больше начальной
  const sigmoid = 1 / (1 + Math.exp(-steepness * (supply - midpoint)))
  return initialPrice + (maxPrice - initialPrice) * sigmoid
}

/**
 * Constant Product: price = k / supply (как в Uniswap)
 */
function calculateConstantProductPrice(supply: number, k: number): number {
  if (supply === 0) return 0
  return k / supply
}

/**
 * Логарифмическая кривая: price = initial_price + scale_factor × log_base(supply + 1)
 */
function calculateLogarithmicPrice(
  supply: number,
  initialPrice: number,
  base: number,
  scaleFactor: number
): number {
  if (supply === 0) return initialPrice
  return initialPrice + scaleFactor * Math.log(supply + 1) / Math.log(base)
}

/**
 * Генерация точек данных для графика
 */
export interface PriceDataPoint {
  supply: number
  price: number
  marketCap: number
}

export function generatePriceData(
  config: BondingCurveConfig,
  maxSupply: number = 500_000,
  points: number = 100
): PriceDataPoint[] {
  const dataPoints: PriceDataPoint[] = []
  const step = maxSupply / points

  for (let i = 0; i <= points; i++) {
    const supply = i * step
    const price = calculatePrice(supply, config)
    const marketCap = supply * price

    dataPoints.push({
      supply: Math.round(supply),
      price: parseFloat(price.toFixed(10)),
      marketCap: parseFloat(marketCap.toFixed(4))
    })
  }

  return dataPoints
}

/**
 * Расчет стоимости покупки токенов (интеграл под кривой)
 */
export function calculateBuyCost(
  fromSupply: number,
  tokensAmount: number,
  config: BondingCurveConfig
): number {
  const steps = 1000
  const stepSize = tokensAmount / steps
  let totalCost = 0

  for (let i = 0; i < steps; i++) {
    const currentSupply = fromSupply + i * stepSize
    const price = calculatePrice(currentSupply, config)
    totalCost += price * stepSize
  }

  return totalCost
}

/**
 * Расчет выручки от продажи токенов
 */
export function calculateSellRevenue(
  fromSupply: number,
  tokensAmount: number,
  config: BondingCurveConfig
): number {
  const steps = 1000
  const stepSize = tokensAmount / steps
  let totalRevenue = 0

  for (let i = 0; i < steps; i++) {
    const currentSupply = fromSupply - i * stepSize
    if (currentSupply < 0) break
    const price = calculatePrice(currentSupply, config)
    totalRevenue += price * stepSize
  }

  return totalRevenue
}

/**
 * Получить название кривой на русском
 */
export function getCurveName(curveType: CurveType): string {
  const names: Record<CurveType, string> = {
    [CurveType.LINEAR]: 'Линейная',
    [CurveType.EXPONENTIAL]: 'Экспоненциальная',
    [CurveType.SIGMOID]: 'Сигмоидная',
    [CurveType.CONSTANT_PRODUCT]: 'Constant Product',
    [CurveType.LOGARITHMIC]: 'Логарифмическая'
  }
  return names[curveType] || curveType
}

/**
 * Получить цвет кривой для графика
 */
export function getCurveColor(curveType: CurveType): string {
  const colors: Record<CurveType, string> = {
    [CurveType.LINEAR]: '#3b82f6', // blue-500
    [CurveType.EXPONENTIAL]: '#ef4444', // red-500
    [CurveType.SIGMOID]: '#8b5cf6', // violet-500
    [CurveType.CONSTANT_PRODUCT]: '#10b981', // green-500
    [CurveType.LOGARITHMIC]: '#f59e0b' // amber-500
  }
  return colors[curveType] || '#6b7280'
}

/**
 * Рекомендуемые параметры для каждого типа кривой
 */
export const CURVE_PRESETS = {
  conservative: {
    [CurveType.LINEAR]: {
      initialPrice: 0.000001,
      slope: 0.000001
    },
    [CurveType.EXPONENTIAL]: {
      initialPrice: 0.000001,
      growthFactor: 1.000005
    },
    [CurveType.SIGMOID]: {
      initialPrice: 0.000001,
      midpoint: 250_000,
      steepness: 0.00001
    },
    [CurveType.CONSTANT_PRODUCT]: {
      k: 500_000_000
    },
    [CurveType.LOGARITHMIC]: {
      initialPrice: 0.000001,
      base: 2,
      scaleFactor: 0.0005
    }
  },
  balanced: {
    [CurveType.LINEAR]: {
      initialPrice: 0.000005,
      slope: 0.000005
    },
    [CurveType.EXPONENTIAL]: {
      initialPrice: 0.000005,
      growthFactor: 1.00001
    },
    [CurveType.SIGMOID]: {
      initialPrice: 0.000005,
      midpoint: 250_000,
      steepness: 0.00002
    },
    [CurveType.CONSTANT_PRODUCT]: {
      k: 1_000_000_000
    },
    [CurveType.LOGARITHMIC]: {
      initialPrice: 0.000005,
      base: 2,
      scaleFactor: 0.001
    }
  },
  aggressive: {
    [CurveType.LINEAR]: {
      initialPrice: 0.00001,
      slope: 0.00001
    },
    [CurveType.EXPONENTIAL]: {
      initialPrice: 0.00001,
      growthFactor: 1.00002
    },
    [CurveType.SIGMOID]: {
      initialPrice: 0.00001,
      midpoint: 250_000,
      steepness: 0.00005
    },
    [CurveType.CONSTANT_PRODUCT]: {
      k: 2_000_000_000
    },
    [CurveType.LOGARITHMIC]: {
      initialPrice: 0.00001,
      base: 2,
      scaleFactor: 0.002
    }
  }
}
