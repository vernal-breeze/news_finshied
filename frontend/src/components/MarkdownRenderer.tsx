import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './MarkdownRenderer.css'

interface MarkdownRendererProps {
  content: string
  /** 可选替代文本，content 为空时展示 */
  placeholder?: string
  style?: React.CSSProperties
}

/**
 * 通用 Markdown 渲染组件。
 * - 自动移除第一行的 # 标题（避免重复，因为卡片/页面通常已有 title）
 * - 支持 GFM 表格、删除线等
 */
const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  placeholder = '暂无内容',
  style,
}) => {
  if (!content?.trim()) {
    return <div style={{ color: '#999', ...style }}>{placeholder}</div>
  }

  // 如果整个内容只有一行 # 标题，视为空
  const trimmed = content.trim()
  if (trimmed.match(/^#{1,3}\s+.+$/) && !trimmed.includes('\n')) {
    return <div style={{ color: '#999', ...style }}>{placeholder}</div>
  }

  return (
    <div className="markdown-body" style={style}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  )
}

export default MarkdownRenderer
