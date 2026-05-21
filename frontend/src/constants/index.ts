/** 路由路径常量 */
export const ROUTES = {
  READER_HOME: '/reader',
  READER_ARTICLE: (id: number) => `/reader/article/${id}`,
  READER_SEARCH: '/reader/search',
  READER_CATEGORY: (category: string) => `/reader/category/${category}`,
  READER_MESSAGES: '/reader/messages',
  LOGIN: '/login',
  REGISTER: '/register',
  EDITOR_HOME: '/editor',
  EDITOR_CLUES: '/editor/clues',
  EDITOR_ARTICLES: '/editor/articles',
  EDITOR_TOPICS: '/editor/topics',
  EDITOR_ANALYTICS: '/editor/analytics',
  EDITOR_AI_ARTICLE: '/editor/ai-article',
  REVIEW_LOGIN: '/review/login',
  REVIEW_DASHBOARD: '/review',
  REVIEW_QUEUE: '/review/queue',
  REVIEW_PUBLISHED: '/review/published',
  REVIEW_SETTINGS: '/review/settings',
} as const

/** API 端点常量 */
export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/api/auth/login',
    REGISTER: '/api/auth/register',
    ME: '/api/auth/me',
  },
  CLUES: '/api/clues',
  ARTICLES: '/api/articles',
  TOPICS: '/api/topics',
  REVIEWS: '/api/reviews',
  CONTENT: '/api/content',
  FEEDBACK: '/api/feedback',
  PUBLIC: '/api/public',
  COLLECTION: '/api/collection',
  STATS: '/api/stats',
  HEALTH: '/health',
  UPLOAD: '/api/upload/image',
} as const
