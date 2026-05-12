import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { getApiBaseUrl } from './apiBase'

/**
 * 解析分页响应（axios 拦截器已返回 body）。
 * - 标准：`{ data: T[], total, page, ... }`
 * - 线索列表嵌套：`{ data: { data: T[], total, ... } }`（见后端 create_clues_paginated_response）
 */
export function unwrapPaginated<T>(raw: unknown): { items: T[]; total: number } {
  if (raw == null || typeof raw !== 'object') return { items: [], total: 0 }
  const r = raw as Record<string, unknown>
  const inner = r.data
  if (inner && typeof inner === 'object' && !Array.isArray(inner)) {
    const nest = inner as Record<string, unknown>
    if (Array.isArray(nest.data)) {
      const items = nest.data as T[]
      return { items, total: Number(nest.total) || items.length }
    }
  }
  if (Array.isArray(inner)) {
    const items = inner as T[]
    return { items, total: Number(r.total) ?? items.length }
  }
  return { items: [], total: 0 }
}

/**
 * 解析「线索搜索资料」POST 返回的 results。
 * 响应结构：{ code: 200, message: "...", data: { keyword: "...", total: N, results: [...] } }
 * axios 拦截器返回 response.data，即 { code, message, data } 中的 data
 */
export function unwrapSearchInfoResults(raw: unknown): Array<{
  title: string
  url: string
  snippet: string
  source: string
}> {
  if (raw == null || typeof raw !== 'object') return []
  const r = raw as Record<string, unknown>

  // 直接从顶层找 results（某些响应格式）
  if (Array.isArray((r as { results?: unknown }).results)) {
    return (r as { results: unknown[] }).results as any[]
  }

  // DataResponse 包装：{ data: { keyword, total, results } }
  const data = r.data
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    const d = data as Record<string, unknown>
    // SearchInfoResponse 直接在 data.results
    if (Array.isArray(d.results)) return d.results as any[]
    // 可能的二次嵌套
    const inner = (d as { data?: unknown }).data
    if (inner && typeof inner === 'object' && Array.isArray((inner as Record<string, unknown>).results)) {
      return (inner as { results: unknown[] }).results as any[]
    }
  }
  return []
}

// API 基础配置（与 authClient 的 origin 解析一致，见 apiBase.ts）
const API_BASE_URL = getApiBaseUrl()
const REQUEST_TIMEOUT = 30000

// 创建 axios 实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: REQUEST_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // data 为空（null/undefined）时删除 Content-Type，避免 uvicorn 因 "application/json + 空 body" 报 400
    if (config.data == null && config.method && config.method.toLowerCase() !== 'get') {
      const h = config.headers
      if (h && typeof h.delete === 'function') {
        h.delete('Content-Type')
      } else if (h && typeof h === 'object') {
        delete (h as Record<string, unknown>)['Content-Type']
        delete (h as Record<string, unknown>)['content-type']
      }
    }
    // FormData 不能使用默认的 application/json，否则后端无法解析 multipart，会 422
    if (config.data instanceof FormData) {
      const h = config.headers
      if (h && typeof h.delete === 'function') {
        h.delete('Content-Type')
      } else if (h && typeof h === 'object') {
        delete (h as Record<string, unknown>)['Content-Type']
        delete (h as Record<string, unknown>)['content-type']
      }
    }
    const path = `${config.baseURL || ''}${config.url || ''}`
    const isAuthLogin = path.includes('/auth/login') || path.includes('/auth/token')
    const token = localStorage.getItem('token')
    if (token && !isAuthLogin) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // 添加时间戳防止缓存
    if (config.method === 'get') {
      config.params = { ...config.params, _t: Date.now() }
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error: AxiosError) => {
    // 错误处理
    if (error.response) {
      // 服务器返回错误状态码
      const status = error.response.status
      const data = error.response.data as any
      
      switch (status) {
        case 400:
          console.error('请求参数错误:', data?.message || 'Invalid request')
          break
        case 401:
          console.error('未授权，请重新登录')
          if (localStorage.getItem('token')) {
            localStorage.removeItem('token')
            localStorage.removeItem('user')
            localStorage.removeItem('username')
            window.dispatchEvent(new Event('auth-changed'))
          }
          {
            const path = window.location.pathname
            const onEditor =
              path.startsWith('/editor') ||
              ['/clues', '/articles', '/topics', '/analytics', '/ai-article'].some((p) =>
                path.startsWith(p)
              )
            const onReview = path.startsWith('/review') && !path.includes('/review/login')
            if (onEditor && path !== '/login') {
              window.location.replace('/login')
            } else if (onReview) {
              window.location.replace('/review/login')
            } else if (path.startsWith('/reader/messages')) {
              window.location.replace(
                `/login?next=${encodeURIComponent(path + window.location.search)}`
              )
            }
          }
          break
        case 403:
          console.error('没有权限访问该资源')
          break
        case 404:
          console.error('请求的资源不存在')
          break
        case 429:
          console.error('请求过于频繁，请稍后再试')
          break
        case 500:
          console.error('服务器内部错误')
          break
        default:
          console.error(`API Error [${status}]:`, data?.message || 'Unknown error')
      }
    } else if (error.request) {
      // 请求已发出但没有收到响应
      console.error('网络错误，请检查网络连接')
    } else {
      // 请求配置出错
      console.error('请求配置错误:', error.message)
    }
    return Promise.reject(error)
  }
)

export default api

export const clueAPI = {
  list: (params?: any) => api.get('/api/clues', { params }),
  get: (id: number) => api.get(`/api/clues/${id}`),
  create: (data: any) => api.post('/api/clues', data),
  update: (id: number, data: any) => api.put(`/api/clues/${id}`, data),
  delete: (id: number) => api.delete(`/api/clues/${id}`),
  batchDelete: (ids: number[]) => api.post('/api/clues/batch-delete', ids),
  analyze: (id: number) => api.post(`/api/clues/${id}/analyze`),
  collect: (params: { url: string; timeRange?: string; maxResults?: number }) =>
    api.get('/api/clues/collect', { params, timeout: 60000 }),
  collectMultichannel: (keywords: string, channels: string[], _timeRange?: string, maxResults?: number) =>
    api.get('/api/clues/collect/multichannel', { params: { keywords, channels: channels.join(','), max_results: maxResults }, timeout: 60000 }),
  searchInfo: (id: number, data: { keyword: string; engine?: string; source?: string; max_results?: number; exact_match?: boolean }) =>
    api.post(`/api/clues/${id}/search-info`, data, { timeout: 60000 }),
  getSources: () => api.get('/api/clues/sources'),
  verifySource: (body: { url: string; type?: string; key?: string }) =>
    api.post('/api/clues/sources/verify', body, { timeout: 15000 }),
}

export const articleAPI = {
  list: (params?: any) => api.get('/api/articles', { params }),
  get: (id: number) => api.get(`/api/articles/${id}`),
  create: (data: any) => api.post('/api/articles', data),
  update: (id: number, data: any) => api.put(`/api/articles/${id}`, data),
  delete: (id: number) => api.delete(`/api/articles/${id}`),
  publish: (id: number) => api.post(`/api/articles/${id}/publish`),
  submitForReview: (id: number) => api.post(`/api/articles/${id}/submit-review`),
  reviews: (id: number) => api.get(`/api/articles/${id}/reviews`),
}

export const contentAPI = {
  /** AI 写稿，生成较慢，单独延长超时 */
  generate: (data: any) =>
    api.post('/api/content/generate', data, { timeout: 120000 }),
  generateTitle: (data: any) => api.post('/api/content/generate-title', data),
  summarize: (data: any) => api.post('/api/content/summarize', data),
  extractKeywords: (data: any) => api.post('/api/content/extract-keywords', data),
  evaluateQuality: (data: any) => api.post('/api/content/evaluate-quality', data),
  /** 内容改进：润色/扩展/精简/重写 */
  improve: (data: {
    original_content: string
    improve_type?: 'polish' | 'expand' | 'condense' | 'rewrite'
    focus_area?: 'clarity' | 'depth' | 'engagement' | 'accuracy'
    target_length?: number
  }) => api.post('/api/content/improve', data, { timeout: 60000 }),
  /** 审核端：大模型预审稿件（可只传 article_id） */
  aiReview: (data: {
    article_id?: number
    title?: string
    abstract?: string
    content?: string
  }) => api.post('/api/content/ai-review', data, { timeout: 90000 }),
}

export const reviewAPI = {
  list: (params?: any) => api.get('/api/reviews', { params }),
  getPending: () => api.get('/api/reviews/pending'),
  create: (data: any) => api.post('/api/reviews', data),
  getByArticle: (articleId: number) => api.get(`/api/articles/${articleId}/reviews`),
}

export const feedbackAPI = {
  getStats: (days?: number) => api.get('/api/feedback/stats', { params: { days } }),
  getTrends: (days?: number) => api.get('/api/feedback/trends', { params: { days } }),
  getByArticle: (articleId: number) => api.get(`/api/feedback/${articleId}`),
  recordView: (articleId: number) => api.post(`/api/feedback/${articleId}/view`),
  recordLike: (articleId: number) => api.post(`/api/feedback/${articleId}/like`),
  recordShare: (articleId: number) => api.post(`/api/feedback/${articleId}/share`),
  recordComment: (articleId: number) => api.post(`/api/feedback/${articleId}/comment`),
}

export const collectionAPI = {
  listTasks: (params?: any) => api.get('/api/collection/tasks', { params }),
  createTask: (data: any) => api.post('/api/collection/tasks', data),
  listMaterials: (params?: any) => api.get('/api/collection/materials', { params }),
}

export const statsAPI = {
  getDashboard: () => api.get('/api/stats/dashboard'),
}

/** 选题策划（与《选题策划功能接入方案》一致：列表、AI 分析、指派、稿件进度、反馈反哺） */
export const topicAPI = {
  list: (params?: Record<string, unknown>) => api.get('/api/topics', { params }),
  get: (id: number) => api.get(`/api/topics/${id}`),
  create: (data: Record<string, unknown>) => api.post('/api/topics', data),
  update: (id: number, data: Record<string, unknown>) => api.put(`/api/topics/${id}`, data),
  delete: (id: number) => api.delete(`/api/topics/${id}`),
  aiAnalyze: (id: number) =>
    api.post(`/api/topics/${id}/ai-analyze`, {}, { timeout: 120000 }),
  assign: (id: number, body: { editor: string; assigned_user_id?: number | null }) =>
    api.post(`/api/topics/${id}/assign`, body),
  syncFeedback: (id: number) => api.post(`/api/topics/${id}/sync-feedback`),
  articles: (id: number) => api.get(`/api/topics/${id}/articles`),
  getAvailableArticles: (topicId: number, params?: { page?: number; page_size?: number; search?: string }) =>
    api.get(`/api/topics/${topicId}/available-articles`, { params }),
  linkArticle: (topicId: number, articleId: number) =>
    api.post(`/api/topics/${topicId}/articles`, { article_id: articleId }),
  unlinkArticle: (topicId: number, articleId: number) =>
    api.delete(`/api/topics/${topicId}/articles/${articleId}`),
}

// 系统 API
export const userAPI = {
  getProfile: () => api.get('/api/users/me'),
  updateProfile: (data: { nickname?: string; email?: string; full_name?: string }) =>
    api.put('/api/users/me', data),
  updatePassword: (data: { old_password: string; new_password: string }) =>
    api.put('/api/users/me/password', data),
  uploadAvatar: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/api/users/me/avatar', fd)
  },
}

export const settingsAPI = {
  get: () => api.get('/api/settings'),
  update: (data: Record<string, unknown>) => api.put('/api/settings', data),
}

export const uploadAPI = {
  /** 需登录；响应体为 { code, message, data: { url } } */
  image: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/api/upload/image', fd)
  },
}

export const publicReaderAPI = {
  listComments: (articleId: number) =>
    api.get(`/api/public/articles/${articleId}/comments`),
  postComment: (
    articleId: number,
    body: { content: string; author_name?: string; parent_id?: number | null }
  ) => api.post(`/api/public/articles/${articleId}/comments`, body),
}

export const systemAPI = {
  // 健康检查
  health: () => api.get('/health'),
  
  // 系统状态
  status: () => api.get('/status'),
  
  // AI 速率限制状态
  rateLimitStatus: () => api.get('/api/ai/rate-limit-status'),
  
  // AI 缓存统计
  cacheStats: () => api.get('/api/ai/cache-stats'),
}

// 辅助函数：格式化日期
export const formatDate = (dateStr: string): string => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// 辅助函数：相对时间
export const formatRelativeTime = (dateStr: string): string => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  if (hours < 24) return `${hours} 小时前`
  if (days < 7) return `${days} 天前`
  return formatDate(dateStr)
}

// 辅助函数：数字格式化
export const formatNumber = (num: number): string => {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toLocaleString()
}

// 辅助函数：百分比格式化
export const formatPercent = (num: number): string => {
  return (num * 100).toFixed(1) + '%'
}
