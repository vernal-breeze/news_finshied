import { createElement } from 'react'
import { Tag } from 'antd'

/** 获取分类标签颜色 */
export function getCategoryTag(category: string) {
  const colorMap: Record<string, string> = {
    '时政': 'red',
    '经济': 'orange',
    '社会': 'blue',
    '科技': 'geekblue',
    '文化': 'purple',
    '体育': 'green',
    '娱乐': 'magenta',
    '国际': 'cyan',
  }
  return createElement(Tag, { color: colorMap[category] || 'default' }, category)
}

/** 获取状态标签颜色 */
export function getStatusTag(status: string) {
  const colorMap: Record<string, string> = {
    draft: 'default',
    pending_review: 'processing',
    reviewing: 'processing',
    approved: 'success',
    rejected: 'error',
    published: 'green',
    archived: 'default',
  }
  const labelMap: Record<string, string> = {
    draft: '草稿',
    pending_review: '待审核',
    reviewing: '审核中',
    approved: '已通过',
    rejected: '已拒绝',
    published: '已发布',
    archived: '已归档',
  }
  return createElement(Tag, { color: colorMap[status] || 'default' }, labelMap[status] || status)
}

/** 所有分类列表 */
export const CATEGORIES = ['时政', '经济', '社会', '科技', '文化', '体育', '娱乐', '国际'] as const
