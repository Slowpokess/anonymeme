/**
 * 🔘 Универсальная кнопка с различными вариантами стилизации
 * Production-ready компонент с полной поддержкой accessibility
 */

import React from 'react'
import { clsx } from 'clsx'
import { Loader2 } from 'lucide-react'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success'
  size?: 'sm' | 'md' | 'lg' | 'xl'
  loading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  fullWidth?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({
    className,
    variant = 'primary',
    size = 'md',
    loading = false,
    leftIcon,
    rightIcon,
    fullWidth = false,
    disabled,
    children,
    ...props
  }, ref) => {
    const baseClasses = clsx(
      // Base styles
      'inline-flex items-center justify-center font-medium transition-all duration-200',
      'focus:outline-none focus:ring-2 focus:ring-offset-2',
      'disabled:opacity-50 disabled:cursor-not-allowed',
      'relative overflow-hidden',
      
      // Size variants
      {
        'px-3 py-1.5 text-sm rounded-md': size === 'sm',
        'px-4 py-2 text-sm rounded-md': size === 'md',
        'px-6 py-3 text-base rounded-lg': size === 'lg',
        'px-8 py-4 text-lg rounded-lg': size === 'xl',
      },
      
      // Color variants
      {
        // Primary
        'bg-primary-600 hover:bg-primary-700 text-white border border-transparent': 
          variant === 'primary',
        'focus:ring-primary-500': variant === 'primary',
        
        // Secondary
        'bg-gray-600 hover:bg-gray-700 text-white border border-transparent': 
          variant === 'secondary',
        'focus:ring-gray-500': variant === 'secondary',
        
        // Outline
        'bg-transparent hover:bg-primary-50 text-primary-700 border border-primary-300': 
          variant === 'outline',
        'focus:ring-primary-500': variant === 'outline',
        
        // Ghost
        'bg-transparent hover:bg-gray-100 text-gray-700 border border-transparent': 
          variant === 'ghost',
        'focus:ring-gray-500': variant === 'ghost',
        
        // Danger
        'bg-error-600 hover:bg-error-700 text-white border border-transparent': 
          variant === 'danger',
        'focus:ring-error-500': variant === 'danger',
        
        // Success
        'bg-success-600 hover:bg-success-700 text-white border border-transparent': 
          variant === 'success',
        'focus:ring-success-500': variant === 'success',
      },
      
      // Full width
      {
        'w-full': fullWidth,
      },
      
      className
    )

    const isDisabled = disabled || loading

    return (
      <button
        className={baseClasses}
        disabled={isDisabled}
        ref={ref}
        {...props}
      >
        {/* Loading spinner */}
        {loading && (
          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
        )}
        
        {/* Left icon */}
        {leftIcon && !loading && (
          <span className="mr-2">
            {leftIcon}
          </span>
        )}
        
        {/* Button content */}
        {children}
        
        {/* Right icon */}
        {rightIcon && (
          <span className="ml-2">
            {rightIcon}
          </span>
        )}
        
        {/* Ripple effect on click */}
        <span className="absolute inset-0 overflow-hidden rounded-inherit">
          <span className="absolute inset-0 bg-white opacity-0 hover:opacity-10 active:opacity-20 transition-opacity duration-200" />
        </span>
      </button>
    )
  }
)

Button.displayName = 'Button'

export { Button }