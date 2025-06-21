/**
 * 🔌 WebSocket Service для real-time обновлений
 * Production-ready WebSocket клиент с автоматическим переподключением
 */

import { io, Socket } from 'socket.io-client'
import { WSPriceUpdate, WSTradeUpdate, WSTokenUpdate } from '@/types'

export type WSEventHandler<T = any> = (data: T) => void

class WebSocketService {
  private socket: Socket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private isConnecting = false
  private eventHandlers: Map<string, Set<WSEventHandler>> = new Map()

  constructor() {
    this.connect()
  }

  private connect() {
    if (this.isConnecting || this.socket?.connected) {
      return
    }

    this.isConnecting = true

    try {
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8001'
      
      this.socket = io(wsUrl, {
        transports: ['websocket', 'polling'],
        timeout: 10000,
        reconnection: true,
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: this.reconnectDelay,
        auth: {
          token: localStorage.getItem('auth_token'),
        },
      })

      this.setupEventListeners()
      
      console.log('🔌 Connecting to WebSocket...', wsUrl)
    } catch (error) {
      console.error('❌ WebSocket connection error:', error)
      this.isConnecting = false
    }
  }

  private setupEventListeners() {
    if (!this.socket) return

    // Connection events
    this.socket.on('connect', () => {
      console.log('✅ WebSocket connected')
      this.isConnecting = false
      this.reconnectAttempts = 0
    })

    this.socket.on('disconnect', (reason) => {
      console.log('🔌 WebSocket disconnected:', reason)
      this.isConnecting = false
      
      if (reason === 'io server disconnect') {
        // Server disconnected, try to reconnect
        this.scheduleReconnect()
      }
    })

    this.socket.on('connect_error', (error) => {
      console.error('❌ WebSocket connection error:', error)
      this.isConnecting = false
      this.scheduleReconnect()
    })

    this.socket.on('reconnect', (attempt) => {
      console.log(`🔄 WebSocket reconnected after ${attempt} attempts`)
      this.reconnectAttempts = 0
    })

    this.socket.on('reconnect_error', (error) => {
      console.error('❌ WebSocket reconnection error:', error)
    })

    this.socket.on('reconnect_failed', () => {
      console.error('❌ WebSocket reconnection failed')
    })

    // Custom events
    this.socket.on('price_update', (data: WSPriceUpdate) => {
      this.emit('price_update', data)
    })

    this.socket.on('trade_update', (data: WSTradeUpdate) => {
      this.emit('trade_update', data)
    })

    this.socket.on('token_update', (data: WSTokenUpdate) => {
      this.emit('token_update', data)
    })

    this.socket.on('market_data', (data: any) => {
      this.emit('market_data', data)
    })

    this.socket.on('user_notification', (data: any) => {
      this.emit('user_notification', data)
    })
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('❌ Max reconnection attempts reached')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1) // Exponential backoff
    
    console.log(`⏳ Scheduling reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`)
    
    setTimeout(() => {
      this.connect()
    }, delay)
  }

  private emit(event: string, data: any) {
    const handlers = this.eventHandlers.get(event)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data)
        } catch (error) {
          console.error(`❌ Error in WebSocket event handler for ${event}:`, error)
        }
      })
    }
  }

  // === PUBLIC METHODS ===

  /**
   * Подписка на события WebSocket
   */
  on<T = any>(event: string, handler: WSEventHandler<T>): () => void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set())
    }
    
    this.eventHandlers.get(event)!.add(handler)
    
    // Возвращаем функцию для отписки
    return () => {
      this.off(event, handler)
    }
  }

  /**
   * Отписка от событий WebSocket
   */
  off(event: string, handler: WSEventHandler) {
    const handlers = this.eventHandlers.get(event)
    if (handlers) {
      handlers.delete(handler)
      if (handlers.size === 0) {
        this.eventHandlers.delete(event)
      }
    }
  }

  /**
   * Подписка на обновления цен токена
   */
  subscribeToTokenPrice(tokenId: string) {
    if (this.socket?.connected) {
      this.socket.emit('subscribe_token_price', { token_id: tokenId })
    }
  }

  /**
   * Отписка от обновлений цен токена
   */
  unsubscribeFromTokenPrice(tokenId: string) {
    if (this.socket?.connected) {
      this.socket.emit('unsubscribe_token_price', { token_id: tokenId })
    }
  }

  /**
   * Подписка на торговые обновления
   */
  subscribeToTrades(tokenId?: string) {
    if (this.socket?.connected) {
      this.socket.emit('subscribe_trades', { token_id: tokenId })
    }
  }

  /**
   * Отписка от торговых обновлений
   */
  unsubscribeFromTrades(tokenId?: string) {
    if (this.socket?.connected) {
      this.socket.emit('unsubscribe_trades', { token_id: tokenId })
    }
  }

  /**
   * Подписка на уведомления пользователя
   */
  subscribeToUserNotifications(userId: string) {
    if (this.socket?.connected) {
      this.socket.emit('subscribe_user_notifications', { user_id: userId })
    }
  }

  /**
   * Отписка от уведомлений пользователя
   */
  unsubscribeFromUserNotifications(userId: string) {
    if (this.socket?.connected) {
      this.socket.emit('unsubscribe_user_notifications', { user_id: userId })
    }
  }

  /**
   * Отправка сообщения через WebSocket
   */
  emit(event: string, data: any) {
    if (this.socket?.connected) {
      this.socket.emit(event, data)
    } else {
      console.warn('⚠️ WebSocket not connected, message not sent:', event, data)
    }
  }

  /**
   * Проверка статуса подключения
   */
  isConnected(): boolean {
    return this.socket?.connected || false
  }

  /**
   * Принудительное переподключение
   */
  reconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.connect()
    }
  }

  /**
   * Обновление токена авторизации
   */
  updateAuthToken(token: string) {
    if (this.socket) {
      this.socket.auth = { token }
      if (this.socket.connected) {
        this.socket.emit('auth_update', { token })
      }
    }
  }

  /**
   * Закрытие соединения
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
    this.eventHandlers.clear()
    this.isConnecting = false
    this.reconnectAttempts = 0
  }

  /**
   * Получение статистики соединения
   */
  getConnectionStats() {
    return {
      connected: this.isConnected(),
      reconnectAttempts: this.reconnectAttempts,
      eventHandlers: Array.from(this.eventHandlers.keys()),
      socketId: this.socket?.id,
    }
  }
}

// Singleton instance
export const wsService = new WebSocketService()
export default wsService

// === REACT HOOKS ===

import { useEffect, useRef } from 'react'

/**
 * React Hook для подписки на WebSocket события
 */
export function useWebSocket<T = any>(
  event: string, 
  handler: WSEventHandler<T>,
  dependencies: any[] = []
) {
  const handlerRef = useRef(handler)
  handlerRef.current = handler

  useEffect(() => {
    const unsubscribe = wsService.on(event, handlerRef.current)
    return unsubscribe
  }, [event, ...dependencies])
}

/**
 * React Hook для подписки на обновления цен токена
 */
export function useTokenPrice(tokenId: string, handler: WSEventHandler<WSPriceUpdate>) {
  useEffect(() => {
    if (!tokenId) return

    wsService.subscribeToTokenPrice(tokenId)
    const unsubscribe = wsService.on('price_update', (data: WSPriceUpdate) => {
      if (data.token_id === tokenId) {
        handler(data)
      }
    })

    return () => {
      wsService.unsubscribeFromTokenPrice(tokenId)
      unsubscribe()
    }
  }, [tokenId, handler])
}

/**
 * React Hook для подписки на торговые обновления
 */
export function useTrades(tokenId: string | undefined, handler: WSEventHandler<WSTradeUpdate>) {
  useEffect(() => {
    wsService.subscribeToTrades(tokenId)
    const unsubscribe = wsService.on('trade_update', (data: WSTradeUpdate) => {
      if (!tokenId || data.token.id === tokenId) {
        handler(data)
      }
    })

    return () => {
      wsService.unsubscribeFromTrades(tokenId)
      unsubscribe()
    }
  }, [tokenId, handler])
}