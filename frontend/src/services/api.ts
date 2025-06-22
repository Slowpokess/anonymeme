/**
 * 🌐 API Service для взаимодействия с backend
 * Production-ready HTTP клиент с автоматической обработкой ошибок
 */

import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios'
import toast from 'react-hot-toast'
import { 
  ApiResponse, 
  PaginatedResponse, 
  Token, 
  Trade, 
  User, 
  Portfolio,
  TradeEstimate,
  Analytics,
  CreateTokenForm,
  TradeForm,
  ApiError
} from '@/types'

class ApiService {
  private client: AxiosInstance
  private baseURL: string

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Добавляем JWT токен если есть
        const token = localStorage.getItem('auth_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }

        // Логирование в development
        if (process.env.NODE_ENV === 'development') {
          console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`)
        }

        return config
      },
      (error) => {
        console.error('❌ Request Error:', error)
        return Promise.reject(error)
      }
    )

    // Response interceptor
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        // Логирование в development
        if (process.env.NODE_ENV === 'development') {
          console.log(`✅ API Response: ${response.status} ${response.config.url}`)
        }

        return response
      },
      (error: AxiosError) => {
        this.handleApiError(error)
        return Promise.reject(error)
      }
    )
  }

  private handleApiError(error: AxiosError) {
    const apiError = error.response?.data as ApiError

    // Обработка различных типов ошибок
    if (error.response?.status === 401) {
      // Unauthorized - очищаем токен и перенаправляем на авторизацию
      localStorage.removeItem('auth_token')
      toast.error('Сессия истекла. Переподключите кошелек')
      // TODO: redirect to auth
    } else if (error.response?.status === 429) {
      // Rate limiting
      toast.error('Слишком много запросов. Попробуйте позже')
    } else if (error.response?.status >= 500) {
      // Server errors
      toast.error('Ошибка сервера. Попробуйте позже')
    } else if (apiError?.message) {
      // API error with message
      toast.error(apiError.message)
    } else if (error.code === 'NETWORK_ERROR') {
      // Network error
      toast.error('Ошибка сети. Проверьте подключение')
    } else {
      // Generic error
      toast.error('Произошла ошибка. Попробуйте еще раз')
    }

    console.error('❌ API Error:', {
      status: error.response?.status,
      message: apiError?.message || error.message,
      url: error.config?.url,
      method: error.config?.method,
    })
  }

  // === AUTH ===

  async authenticateWallet(walletAddress: string, signature: string): Promise<ApiResponse<{ token: string; user: User }>> {
    const response = await this.client.post('/api/v1/auth/wallet', {
      wallet_address: walletAddress,
      signature,
    })
    return response.data
  }

  async refreshToken(): Promise<ApiResponse<{ token: string }>> {
    const response = await this.client.post('/api/v1/auth/refresh')
    return response.data
  }

  // === TOKENS ===

  async getTokens(params?: {
    page?: number
    limit?: number
    search?: string
    status?: string
    sort_by?: string
    order?: 'asc' | 'desc'
  }): Promise<PaginatedResponse<Token>> {
    const response = await this.client.get('/api/v1/tokens', { params })
    return response.data
  }

  async getToken(tokenId: string): Promise<ApiResponse<Token>> {
    const response = await this.client.get(`/api/v1/tokens/${tokenId}`)
    return response.data
  }

  async createToken(data: CreateTokenForm): Promise<ApiResponse<Token>> {
    const formData = new FormData()
    
    Object.entries(data).forEach(([key, value]) => {
      if (value !== undefined) {
        if (value instanceof File) {
          formData.append(key, value)
        } else {
          formData.append(key, String(value))
        }
      }
    })

    const response = await this.client.post('/api/v1/tokens', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  async getTrendingTokens(): Promise<ApiResponse<Token[]>> {
    const response = await this.client.get('/api/v1/tokens/trending')
    return response.data
  }

  async getTokenPrice(tokenId: string): Promise<ApiResponse<{
    current_price: string
    market_cap: string
    volume_24h: string
    price_change_24h: number
  }>> {
    const response = await this.client.get(`/api/v1/tokens/${tokenId}/price`)
    return response.data
  }

  async getTokenChart(tokenId: string, timeframe: '1h' | '24h' | '7d' | '30d'): Promise<ApiResponse<Array<{
    timestamp: number
    price: number
    volume: number
  }>>> {
    const response = await this.client.get(`/api/v1/tokens/${tokenId}/chart`, {
      params: { timeframe }
    })
    return response.data
  }

  // === TRADING ===

  async estimateTrade(tokenId: string, amount: string, tradeType: 'buy' | 'sell'): Promise<ApiResponse<TradeEstimate>> {
    const response = await this.client.post('/api/v1/trading/estimate', {
      token_id: tokenId,
      amount,
      trade_type: tradeType,
    })
    return response.data
  }

  async executeTrade(data: TradeForm): Promise<ApiResponse<Trade>> {
    const response = await this.client.post('/api/v1/trading/trade', data)
    return response.data
  }

  async getTrades(params?: {
    page?: number
    limit?: number
    user_id?: string
    token_id?: string
    trade_type?: string
  }): Promise<PaginatedResponse<Trade>> {
    const response = await this.client.get('/api/v1/trading/trades', { params })
    return response.data
  }

  async getUserTrades(userId: string, params?: {
    page?: number
    limit?: number
    token_id?: string
  }): Promise<PaginatedResponse<Trade>> {
    const response = await this.client.get(`/api/v1/trading/users/${userId}/trades`, { params })
    return response.data
  }

  // === PORTFOLIO ===

  async getUserPortfolio(userId?: string): Promise<ApiResponse<Portfolio>> {
    const endpoint = userId 
      ? `/api/v1/trading/users/${userId}/portfolio`
      : '/api/v1/trading/portfolio'
    const response = await this.client.get(endpoint)
    return response.data
  }

  async getTradingStats(period: '1h' | '24h' | '7d' | '30d' = '24h'): Promise<ApiResponse<{
    period: string
    total_trades: number
    total_volume_sol: number
    total_fees_paid: number
    buy_trades: number
    sell_trades: number
    average_slippage: number
    largest_trade_sol: number
    trades_per_day: number
  }>> {
    const response = await this.client.get('/api/v1/trading/stats', {
      params: { period }
    })
    return response.data
  }

  // === USERS ===

  async getUser(userId: string): Promise<ApiResponse<User>> {
    const response = await this.client.get(`/api/v1/users/${userId}`)
    return response.data
  }

  async getUserByWallet(walletAddress: string): Promise<ApiResponse<User>> {
    const response = await this.client.get(`/api/v1/users/wallet/${walletAddress}`)
    return response.data
  }

  async updateUserProfile(userId: string, data: Partial<User>): Promise<ApiResponse<User>> {
    const response = await this.client.put(`/api/v1/users/${userId}`, data)
    return response.data
  }

  async getUserStats(userId: string): Promise<ApiResponse<{
    total_trades: number
    total_volume: string
    tokens_created: number
    portfolio_value: string
    pnl_24h: string
  }>> {
    const response = await this.client.get(`/api/v1/users/${userId}/stats`)
    return response.data
  }

  // === ANALYTICS ===

  async getAnalytics(): Promise<ApiResponse<Analytics>> {
    const response = await this.client.get('/api/v1/analytics/overview')
    return response.data
  }

  async getMarketOverview(): Promise<ApiResponse<{
    total_tokens: number
    total_volume_24h: string
    total_trades_24h: number
    active_users_24h: number
    top_gainers: Token[]
    top_losers: Token[]
  }>> {
    const response = await this.client.get('/api/v1/analytics/market')
    return response.data
  }

  async getLeaderboard(type: 'volume' | 'pnl' | 'trades', timeframe: '24h' | '7d' | '30d' | 'all'): Promise<ApiResponse<Array<{
    user: User
    value: string
    rank: number
  }>>> {
    const response = await this.client.get('/api/v1/analytics/leaderboard', {
      params: { type, timeframe }
    })
    return response.data
  }

  // === HEALTH CHECK ===

  async healthCheck(): Promise<ApiResponse<{
    status: string
    timestamp: string
    version: string
  }>> {
    const response = await this.client.get('/health')
    return response.data
  }

  // === UTILITY METHODS ===

  setAuthToken(token: string) {
    localStorage.setItem('auth_token', token)
    this.client.defaults.headers.Authorization = `Bearer ${token}`
  }

  clearAuthToken() {
    localStorage.removeItem('auth_token')
    delete this.client.defaults.headers.Authorization
  }

  getAuthToken(): string | null {
    return localStorage.getItem('auth_token')
  }

  isAuthenticated(): boolean {
    return !!this.getAuthToken()
  }

  // === FILE UPLOAD ===

  async uploadFile(file: File, type: 'avatar' | 'token_image'): Promise<ApiResponse<{ url: string }>> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('type', type)

    const response = await this.client.post('/api/v1/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 60000, // 1 минута для загрузки файлов
    })
    return response.data
  }
}

// Singleton instance
export const apiService = new ApiService()
export default apiService