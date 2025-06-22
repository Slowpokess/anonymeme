/**
 * 📝 Универсальный компонент ввода с валидацией
 * Production-ready input с полной поддержкой форм
 */

import React from 'react'
import { clsx } from 'clsx'
import { AlertCircle, Eye, EyeOff } from 'lucide-react'

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label?: string
  error?: string
  helperText?: string
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  variant?: 'default' | 'filled' | 'underlined'
  size?: 'sm' | 'md' | 'lg'
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({
    className,
    type = 'text',
    label,
    error,
    helperText,
    leftIcon,
    rightIcon,
    variant = 'default',
    size = 'md',
    disabled,
    required,
    id,
    ...props
  }, ref) => {
    const [showPassword, setShowPassword] = React.useState(false)
    const [isFocused, setIsFocused] = React.useState(false)
    
    const inputId = id || React.useId()
    const isPassword = type === 'password'
    const inputType = isPassword && showPassword ? 'text' : type
    const hasError = !!error

    const containerClasses = clsx(
      'relative',
      {
        'opacity-50 cursor-not-allowed': disabled,
      }
    )

    const inputClasses = clsx(
      // Base styles
      'w-full transition-all duration-200 outline-none',
      'placeholder:text-gray-400',
      
      // Size variants
      {
        'text-sm': size === 'sm',
        'text-base': size === 'md',
        'text-lg': size === 'lg',
      },
      
      // Padding with icons
      {
        // Small size
        'py-2 px-3': size === 'sm' && !leftIcon && !rightIcon,
        'py-2 pl-9 pr-3': size === 'sm' && leftIcon && !rightIcon,
        'py-2 pl-3 pr-9': size === 'sm' && !leftIcon && rightIcon,
        'py-2 pl-9 pr-9': size === 'sm' && leftIcon && rightIcon,
        
        // Medium size
        'py-2.5 px-4': size === 'md' && !leftIcon && !rightIcon,
        'py-2.5 pl-10 pr-4': size === 'md' && leftIcon && !rightIcon,
        'py-2.5 pl-4 pr-10': size === 'md' && !leftIcon && rightIcon,
        'py-2.5 pl-10 pr-10': size === 'md' && leftIcon && rightIcon,
        
        // Large size
        'py-3 px-5': size === 'lg' && !leftIcon && !rightIcon,
        'py-3 pl-12 pr-5': size === 'lg' && leftIcon && !rightIcon,
        'py-3 pl-5 pr-12': size === 'lg' && !leftIcon && rightIcon,
        'py-3 pl-12 pr-12': size === 'lg' && leftIcon && rightIcon,
      },
      
      // Variant styles
      {
        // Default
        'border rounded-md bg-white': variant === 'default',
        'border-gray-300 hover:border-gray-400': variant === 'default' && !hasError && !isFocused,
        'border-primary-500 ring-1 ring-primary-500': variant === 'default' && !hasError && isFocused,
        'border-error-500 ring-1 ring-error-500': variant === 'default' && hasError,
        
        // Filled
        'border-0 rounded-md bg-gray-100': variant === 'filled',
        'bg-gray-200': variant === 'filled' && isFocused,
        'bg-error-50': variant === 'filled' && hasError,
        
        // Underlined
        'border-0 border-b-2 rounded-none bg-transparent': variant === 'underlined',
        'border-gray-300': variant === 'underlined' && !hasError && !isFocused,
        'border-primary-500': variant === 'underlined' && !hasError && isFocused,
        'border-error-500': variant === 'underlined' && hasError,
      },
      
      // Password field with show/hide button
      {
        'pr-10': isPassword && size === 'sm',
        'pr-12': isPassword && size === 'md',
        'pr-14': isPassword && size === 'lg',
      },
      
      className
    )

    const iconBaseClasses = 'absolute top-1/2 transform -translate-y-1/2 text-gray-400'
    
    const leftIconClasses = clsx(
      iconBaseClasses,
      {
        'left-2 w-4 h-4': size === 'sm',
        'left-3 w-5 h-5': size === 'md',
        'left-4 w-6 h-6': size === 'lg',
      }
    )
    
    const rightIconClasses = clsx(
      iconBaseClasses,
      {
        'right-2 w-4 h-4': size === 'sm',
        'right-3 w-5 h-5': size === 'md',
        'right-4 w-6 h-6': size === 'lg',
      }
    )

    return (
      <div className="space-y-1">
        {/* Label */}
        {label && (
          <label 
            htmlFor={inputId}
            className={clsx(
              'block text-sm font-medium',
              hasError ? 'text-error-700' : 'text-gray-700'
            )}
          >
            {label}
            {required && <span className="text-error-500 ml-1">*</span>}
          </label>
        )}
        
        {/* Input container */}
        <div className={containerClasses}>
          {/* Left icon */}
          {leftIcon && (
            <div className={leftIconClasses}>
              {leftIcon}
            </div>
          )}
          
          {/* Input field */}
          <input
            ref={ref}
            id={inputId}
            type={inputType}
            className={inputClasses}
            disabled={disabled}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            {...props}
          />
          
          {/* Right icon or password toggle */}
          {(rightIcon || isPassword) && (
            <div className={rightIconClasses}>
              {isPassword ? (
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="hover:text-gray-600 transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff /> : <Eye />}
                </button>
              ) : (
                rightIcon
              )}
            </div>
          )}
        </div>
        
        {/* Helper text or error */}
        {(error || helperText) && (
          <div className="flex items-start space-x-1">
            {error && (
              <AlertCircle className="w-4 h-4 text-error-500 mt-0.5 flex-shrink-0" />
            )}
            <p className={clsx(
              'text-sm',
              error ? 'text-error-600' : 'text-gray-500'
            )}>
              {error || helperText}
            </p>
          </div>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'

export { Input }