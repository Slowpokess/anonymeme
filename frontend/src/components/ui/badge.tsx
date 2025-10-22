/**
 * 🏷️ Badge компонент
 * Небольшие метки для статусов, категорий и индикаторов
 */

import React from 'react'
import { clsx } from 'clsx'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'secondary'
  size?: 'sm' | 'md' | 'lg'
}

export function Badge({
  variant = 'default',
  size = 'md',
  className,
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center font-medium rounded-full',
        {
          // Варианты цветов
          'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200': variant === 'default',
          'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200': variant === 'success',
          'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200': variant === 'warning',
          'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200': variant === 'error',
          'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200': variant === 'info',
          'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200': variant === 'secondary',

          // Размеры
          'px-2 py-0.5 text-xs': size === 'sm',
          'px-2.5 py-0.5 text-sm': size === 'md',
          'px-3 py-1 text-base': size === 'lg',
        },
        className
      )}
      {...props}
    >
      {children}
    </span>
  )
}
