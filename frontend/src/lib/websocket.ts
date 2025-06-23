/**
 * 🔌 WebSocket клиент для real-time обновлений
 * Production-ready WebSocket интеграция с автоподключением и восстановлением
 */

export type EventType = 
  | 'price_update'
  | 'new_trade'
  | 'token_created'
  | 'token_graduated'
  | 'user_connected'
  | 'user_disconnected'
  | 'portfolio_update'
  | 'market_stats'
  | 'error'
  | 'heartbeat'

export interface WebSocketMessage {
  type: EventType | string
  data: Record<string, any>
  timestamp: string
  room?: string
  user_id?: string
}

export interface WebSocketConfig {
  url: string
  reconnectInterval?: number
  maxReconnectAttempts?: number
  heartbeatInterval?: number
  debug?: boolean
}

export type EventHandler = (data: any) => void

class WebSocketClient {
  private ws: WebSocket | null = null
  private config: Required<WebSocketConfig>
  private eventHandlers: Map<string, EventHandler[]> = new Map()
  private reconnectAttempts = 0
  private isConnecting = false
  private heartbeatTimer: NodeJS.Timeout | null = null
  private reconnectTimer: NodeJS.Timeout | null = null
  private isDestroyed = false

  constructor(config: WebSocketConfig) {
    this.config = {
      reconnectInterval: 5000,
      maxReconnectAttempts: 10,
      heartbeatInterval: 30000,
      debug: false,
      ...config
    }

    this.log('WebSocket клиент инициализирован')
  }

  /**
   * Подключение к WebSocket серверу
   */
  async connect(token?: string, room?: string, userId?: string): Promise<void> {
    if (this.isConnecting || this.isDestroyed) {
      return
    }

    this.isConnecting = true

    try {
      // Формирование URL с параметрами
      const url = new URL(this.config.url)
      if (token) url.searchParams.set('token', token)
      if (room) url.searchParams.set('room', room)
      if (userId) url.searchParams.set('user_id', userId)

      this.log(`Подключение к WebSocket: ${url.toString()}`)

      this.ws = new WebSocket(url.toString())

      this.ws.onopen = () => {
        this.log('✅ WebSocket подключен')
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.startHeartbeat()
        this.emit('connected', {})
      }

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          this.handleMessage(message)
        } catch (error) {
          this.log(`❌ Ошибка парсинга сообщения: ${error}`)
        }
      }

      this.ws.onclose = (event) => {
        this.log(`🔌 WebSocket отключен: ${event.code} ${event.reason}`)
        this.isConnecting = false
        this.stopHeartbeat()
        this.emit('disconnected', { code: event.code, reason: event.reason })

        if (!this.isDestroyed && event.code !== 1000) {
          this.scheduleReconnect()
        }
      }

      this.ws.onerror = (error) => {
        this.log(`❌ WebSocket ошибка: ${error}`)
        this.isConnecting = false
        this.emit('error', { error })
      }

    } catch (error) {
      this.log(`❌ Не удалось подключиться: ${error}`)
      this.isConnecting = false
      this.scheduleReconnect()
    }
  }

  /**
   * Отключение от WebSocket сервера
   */
  disconnect(): void {
    this.isDestroyed = true
    this.stopHeartbeat()
    this.clearReconnectTimer()

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.close(1000, 'Client disconnect')
    }

    this.ws = null
    this.log('WebSocket отключен')
  }

  /**
   * Отправка сообщения
   */
  send(type: string, data: Record<string, any> = {}): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.log(`❌ Не удалось отправить сообщение ${type}: WebSocket не подключен`)
      return false
    }

    const message: WebSocketMessage = {
      type,
      data,
      timestamp: new Date().toISOString()
    }

    try {
      this.ws.send(JSON.stringify(message))
      this.log(`📤 Отправлено: ${type}`)
      return true
    } catch (error) {
      this.log(`❌ Ошибка отправки сообщения: ${error}`)
      return false
    }
  }

  /**
   * Подписка на событие
   */
  on(event: string, handler: EventHandler): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, [])
    }
    this.eventHandlers.get(event)!.push(handler)
  }

  /**
   * Отписка от события
   */
  off(event: string, handler?: EventHandler): void {
    if (!this.eventHandlers.has(event)) return

    if (handler) {
      const handlers = this.eventHandlers.get(event)!
      const index = handlers.indexOf(handler)
      if (index !== -1) {
        handlers.splice(index, 1)
      }
    } else {
      this.eventHandlers.delete(event)
    }
  }

  /**
   * Присоединение к комнате
   */
  joinRoom(room: string): boolean {
    return this.send('join_room', { room })
  }

  /**
   * Выход из комнаты
   */
  leaveRoom(room: string): boolean {
    return this.send('leave_room', { room })
  }

  /**
   * Подписка на события токена
   */
  subscribeToToken(tokenMint: string): boolean {
    return this.send('subscribe', { subscribe_to: `token_${tokenMint}` })
  }

  /**
   * Подписка на события пользователя
   */
  subscribeToUser(userId: string): boolean {
    return this.send('subscribe', { subscribe_to: `user_${userId}` })
  }

  /**
   * Получение статуса подключения
   */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  /**
   * Получение состояния подключения
   */
  get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED
  }

  // === ПРИВАТНЫЕ МЕТОДЫ ===

  private handleMessage(message: WebSocketMessage): void {
    this.log(`📥 Получено: ${message.type}`)

    // Обработка системных сообщений
    if (message.type === 'heartbeat' && message.data.pong) {
      // Heartbeat ответ - ничего не делаем
      return
    }

    // Вызов обработчиков событий
    this.emit(message.type, message.data)
  }

  private emit(event: string, data: any): void {
    const handlers = this.eventHandlers.get(event) || []
    handlers.forEach(handler => {
      try {
        handler(data)
      } catch (error) {
        this.log(`❌ Ошибка в обработчике события ${event}: ${error}`)
      }
    })
  }

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected) {
        this.send('heartbeat', {})
      }
    }, this.config.heartbeatInterval)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  private scheduleReconnect(): void {
    if (this.isDestroyed || this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      this.log(`❌ Превышено максимальное количество попыток переподключения (${this.config.maxReconnectAttempts})`)
      return
    }

    this.clearReconnectTimer()
    this.reconnectAttempts++

    const delay = Math.min(
      this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1),
      30000 // Максимум 30 секунд
    )

    this.log(`🔄 Переподключение через ${delay}ms (попытка ${this.reconnectAttempts}/${this.config.maxReconnectAttempts})`)

    this.reconnectTimer = setTimeout(() => {
      this.connect()
    }, delay)
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  private log(message: string): void {
    if (this.config.debug) {
      console.log(`[WebSocket] ${message}`)
    }
  }
}

// Глобальный экземпляр WebSocket клиента
let wsClient: WebSocketClient | null = null

export function createWebSocketClient(config: WebSocketConfig): WebSocketClient {
  if (wsClient) {
    wsClient.disconnect()
  }
  
  wsClient = new WebSocketClient(config)
  return wsClient
}

export function getWebSocketClient(): WebSocketClient | null {
  return wsClient
}

// React Hook для WebSocket
export interface UseWebSocketReturn {
  client: WebSocketClient | null
  isConnected: boolean
  connect: (token?: string, room?: string, userId?: string) => Promise<void>
  disconnect: () => void
  send: (type: string, data?: Record<string, any>) => boolean
  on: (event: string, handler: EventHandler) => void
  off: (event: string, handler?: EventHandler) => void
}

export function useWebSocket(config?: Partial<WebSocketConfig>): UseWebSocketReturn {
  // В React приложении это должен быть хук
  // Здесь упрощенная версия для демонстрации
  
  const defaultConfig: WebSocketConfig = {
    url: process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8001/api/v1/websocket/ws',
    reconnectInterval: 5000,
    maxReconnectAttempts: 10,
    heartbeatInterval: 30000,
    debug: process.env.NODE_ENV === 'development',
    ...config
  }

  if (!wsClient) {
    wsClient = new WebSocketClient(defaultConfig)
  }

  return {
    client: wsClient,
    isConnected: wsClient.isConnected,
    connect: wsClient.connect.bind(wsClient),
    disconnect: wsClient.disconnect.bind(wsClient),
    send: wsClient.send.bind(wsClient),
    on: wsClient.on.bind(wsClient),
    off: wsClient.off.bind(wsClient)
  }
}

export default WebSocketClient