/**
 * 📊 Progress компонент
 * Индикатор прогресса для визуализации выполнения задач
 */

import React from 'react'
import { clsx } from 'clsx'

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number // 0-100
  max?: number
  variant?: 'default' | 'success' | 'warning' | 'error'
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

export function Progress({
  value = 0,
  max = 100,
  variant = 'default',
  size = 'md',
  showLabel = false,
  className,
  ...props
}: ProgressProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)

  return (
    <div className={clsx('w-full', className)} {...props}>
      <div
        className={clsx(
          'w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden',
          {
            'h-1': size === 'sm',
            'h-2': size === 'md',
            'h-3': size === 'lg',
          }
        )}
      >
        <div
          className={clsx(
            'h-full transition-all duration-300 ease-in-out rounded-full',
            {
              'bg-blue-600 dark:bg-blue-500': variant === 'default',
              'bg-green-600 dark:bg-green-500': variant === 'success',
              'bg-yellow-600 dark:bg-yellow-500': variant === 'warning',
              'bg-red-600 dark:bg-red-500': variant === 'error',
            }
          )}
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={max}
        />
      </div>
      {showLabel && (
        <div className="mt-1 text-xs text-gray-600 dark:text-gray-400 text-right">
          {percentage.toFixed(0)}%
        </div>
      )}
    </div>
  )
}
