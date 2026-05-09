export interface NewsClue {
  id: number
  title: string
  source?: string
  source_url?: string
  content?: string
  category?: string
  keywords?: string[]
  news_value_score?: number
  propagation_potential?: number
  status: 'pending' | 'processed' | 'archived'
  created_at: string
  processed_at?: string
}

export interface Article {
  id: number
  title: string
  content: string
  abstract?: string
  author?: string
  category?: string
  tags?: string[]
  images?: string[]
  /** 主题封面（读者端头图），优先于配图首张 */
  cover_image?: string
  status: 'draft' | 'pending_review' | 'reviewing' | 'approved' | 'rejected' | 'published'
  version: number
  parent_version_id?: number
  clue_id?: number
  topic_id?: number
  view_count?: number
  like_count?: number
  created_at: string
  updated_at: string
  published_at?: string
}

export interface Review {
  id: number
  article_id: number
  reviewer: string
  level: 'first' | 'second' | 'third'
  comment?: string
  result: 'approved' | 'rejected' | 'need_revision'
  reviewed_at: string
}

export interface TopicPlanning {
  id: number
  title: string
  description?: string
  category?: string
  editor?: string
  planned_date?: string
  status: 'draft' | 'planning' | 'in_progress' | 'completed' | 'cancelled'
  ref_clue_ids?: number[]
  ai_score?: number
  ai_suggestion?: string
  assigned_user_id?: number | null
  performance_score?: number | null
  creator_id?: number | null
  created_at: string
  updated_at: string
}

export interface FeedbackStats {
  total_views: number
  total_likes: number
  total_comments: number
  total_shares: number
  avg_engagement_rate: number
  top_articles: Array<{
    id: number
    title: string
    views: number
    trending_score: number
  }>
}

export interface PublicationFeedback {
  id: number
  article_id: number
  view_count: number
  like_count: number
  comment_count: number
  share_count: number
  engagement_rate: number
  trending_score: number
  feedback_summary?: string
  created_at: string
  updated_at: string
}

export interface AIAnalysisResult {
  category: string
  category_confidence: number
  news_value_score: number
  propagation_potential: number
  keywords: string[]
  sentiment: string
  sentiment_confidence: number
  timeliness: string
  recommendation: string
}

export interface ContentGenerationResult {
  suggested_titles: string[]
  draft_content: string
  recommended_angles: string[]
  structure_suggestion: string
}

export interface CollectionTask {
  id: number
  name: string
  description?: string
  source?: string
  keywords?: string[]
  status: 'pending' | 'running' | 'completed' | 'failed'
  schedule?: Record<string, any>
  created_at: string
  updated_at: string
  last_run_at?: string
}

export interface DashboardStats {
  clues: {
    total: number
    pending: number
    processed: number
  }
  articles: {
    total: number
    by_status: Record<string, number>
    recent_7_days: number
  }
  recent_activity: {
    new_clues_7days: number
    new_articles_7days: number
  }
  categories: Array<{
    category: string
    count: number
  }>
}

export interface Message {
  id: number
  content: string
  type: 'interaction' | 'system' | 'notification'
  is_read: boolean
  created_at: string
  sender?: string
  related_id?: number
  related_type?: 'article' | 'comment' | 'message'
  read_at?: string | null
}

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
  request_id?: string
}

export interface PaginatedResponse<T> {
  code: number
  message: string
  data: T[]
  total: number
  page: number
  page_size: number
  has_next: boolean
  has_prev: boolean
}
