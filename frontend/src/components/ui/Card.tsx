/**
 * 🃏 Card компонент
 * Универсальная карточка с поддержкой различных вариантов стилизации
 */

import React from 'react'
import { clsx } from 'clsx'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'outlined' | 'ghost'
  padding?: 'none' | 'sm' | 'md' | 'lg'
  children: React.ReactNode
}

export function Card({ 
  variant = 'default', 
  padding = 'md', 
  className, 
  children, 
  ...props 
}: CardProps) {
  return (
    <div
      className={clsx(
        'rounded-lg',
        {
          // Варианты стилизации
          'bg-white border border-gray-200 shadow-sm': variant === 'default',
          'bg-white border border-gray-200 shadow-lg': variant === 'elevated',
          'bg-transparent border border-gray-200': variant === 'outlined',
          'bg-gray-50 border-0': variant === 'ghost',
          
          // Размеры отступов
          'p-0': padding === 'none',
          'p-3': padding === 'sm',
          'p-4': padding === 'md',
          'p-6': padding === 'lg',
        },
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export default Card