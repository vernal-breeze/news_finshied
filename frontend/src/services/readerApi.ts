import api from './api'

/** 解析读者消息列表：后端可为 JSON 数组，或项目统一的 { data: [] } */
function unwrapReaderMessageList(raw: unknown): unknown[] {
  if (raw == null) return []
  if (Array.isArray(raw)) return raw
  if (typeof raw === 'object' && 'data' in (raw as object)) {
    const d = (raw as { data?: unknown }).data
    if (Array.isArray(d)) return d
  }
  return []
}

/** 将后端已发布稿件转为读者端列表展示结构 */
export function normalizeReaderArticle(a: Record<string, unknown>) {
  const images = a.images as string[] | undefined
  const firstImg = Array.isArray(images) && images.length ? images[0] : null
  const explicitCover = (a.cover_image as string | undefined)?.trim()
  const id = a.id as number
  return {
    id,
    title: (a.title as string) || '',
    abstract: (a.abstract as string) || '',
    cover_image:
      explicitCover ||
      firstImg ||
      `https://picsum.photos/seed/${id}/800/400`,
    category: (a.category as string) || '资讯',
    published_at:
      (a.published_at as string) ||
      (a.updated_at as string) ||
      new Date().toISOString(),
    view_count: typeof (a as { view_count?: number }).view_count === 'number'
      ? (a as { view_count: number }).view_count
      : 0,
    author: (a.author as string) || '本报记者',
  }
}

export async function fetchPublicArticleList(options?: {
  category?: string
  search?: string
  page?: number
  page_size?: number
}) {
  const body = (await api.get('/api/public/articles', {
    params: {
      page: options?.page ?? 1,
      page_size: options?.page_size ?? 50,
      category: options?.category || undefined,
      search: options?.search || undefined,
    },
  })) as { data?: unknown[] }
  const list = Array.isArray(body?.data) ? body.data : []
  return list.map((item) =>
    normalizeReaderArticle(item as Record<string, unknown>)
  )
}

export async function fetchMessages(options?: {
  page?: number
  page_size?: number
  is_read?: boolean
}) {
  const body = await api.get('/api/reader/messages', {
    params: {
      page: options?.page ?? 1,
      page_size: options?.page_size ?? 20,
      is_read: options?.is_read,
    },
  })
  return unwrapReaderMessageList(body)
}

export async function fetchUnreadMessageCount() {
  const body = (await api.get('/api/reader/messages/unread-count')) as {
    data?: unknown
  }
  const n = body?.data
  if (typeof n === 'number' && !Number.isNaN(n)) return n
  if (n && typeof n === 'object') {
    const count = (n as { count?: unknown }).count
    if (typeof count === 'number' && !Number.isNaN(count)) return count
  }
  return 0
}

export async function markMessageAsRead(messageId: number) {
  await api.put(`/api/reader/messages/${messageId}/read`)
}

export async function sendMessageReply(messageId: number, content: string) {
  await api.post(`/api/reader/messages/${messageId}/reply`, {
    content,
  })
}
