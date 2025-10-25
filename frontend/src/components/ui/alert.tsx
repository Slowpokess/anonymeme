/**
 * ⚠️ Alert компоненты
 * Уведомления и сообщения для пользователей
 */

import React from 'react'
import { clsx } from 'clsx'

interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info'
}

export function Alert({
  variant = 'default',
  className,
  children,
  ...props
}: AlertProps) {
  return (
    <div
      className={clsx(
        'relative w-full rounded-lg border p-4',
        {
          'bg-white border-gray-200 text-gray-900 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100': variant === 'default',
          'bg-green-50 border-green-200 text-green-900 dark:bg-green-900/20 dark:border-green-800 dark:text-green-100': variant === 'success',
          'bg-yellow-50 border-yellow-200 text-yellow-900 dark:bg-yellow-900/20 dark:border-yellow-800 dark:text-yellow-100': variant === 'warning',
          'bg-red-50 border-red-200 text-red-900 dark:bg-red-900/20 dark:border-red-800 dark:text-red-100': variant === 'error',
          'bg-blue-50 border-blue-200 text-blue-900 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-100': variant === 'info',
        },
        className
      )}
      role="alert"
      {...props}
    >
      {children}
    </div>
  )
}

export function AlertTitle({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h5
      className={clsx('mb-1 font-medium leading-none tracking-tight', className)}
      {...props}
    >
      {children}
    </h5>
  )
}

export function AlertDescription({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <div
      className={clsx('text-sm opacity-90', className)}
      {...props}
    >
      {children}
    </div>
  )
}
