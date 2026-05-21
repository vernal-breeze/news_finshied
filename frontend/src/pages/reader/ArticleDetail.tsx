import React, { useState, useEffect } from 'react'
import { 
  Card, Typography, Space, Tag, Avatar, Button, 
  Divider, List, Spin, Breadcrumb, Input, Form
} from 'antd'
import { 
  ClockCircleOutlined, EyeOutlined, LikeOutlined,
  ShareAltOutlined, BookOutlined, PrinterOutlined
} from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../../services/api'
import dayjs from 'dayjs'
import { publicReaderAPI, feedbackAPI } from '../../services/api'
import { normalizeReaderArticle } from '../../services/readerApi'
import { useAuthSnapshot } from '../../hooks/useAuthSnapshot'
import ReaderHeader from '../../components/reader/ReaderHeader'
import { toast } from '../../components/common/Toast'
import MarkdownRenderer from '../../components/MarkdownRenderer'
import './ArticleDetail.css'

const { Title, Text, Paragraph } = Typography

interface Article {
  id: number
  title: string
  content: string
  abstract: string
  cover_image: string
  category: string
  tags: string[]
  published_at: string
  view_count: number
  like_count: number
  author: string
  author_id: number
  author_avatar: string
}

interface ReaderComment {
  id: number
  article_id?: number
  parent_id?: number | null
  author_name: string
  content: string
  reply_to_name?: string | null
  created_at: string
}

type CommentNode = ReaderComment & { children: CommentNode[] }

function buildCommentTree(flat: ReaderComment[]): CommentNode[] {
  const map = new Map<number, CommentNode>()
  flat.forEach((c) => map.set(c.id, { ...c, children: [] }))
  const roots: CommentNode[] = []
  flat.forEach((c) => {
    const n = map.get(c.id)!
    const pid = c.parent_id
    if (!pid) {
      roots.push(n)
    } else {
      const p = map.get(pid)
      if (p) p.children.push(n)
      else roots.push(n)
    }
  })
  return roots
}

const ReaderArticleDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const [article, setArticle] = useState<Article | null>(null)
  const [loading, setLoading] = useState(true)
  const [fontSize, setFontSize] = useState<'small' | 'medium' | 'large'>(() => {
    const saved = localStorage.getItem('reader-font-size')
    return (saved === 'small' || saved === 'medium' || saved === 'large') ? saved : 'medium'
  })
  const [liked, setLiked] = useState(false)
  const [comments, setComments] = useState<ReaderComment[]>([])
  const [commentText, setCommentText] = useState('')
  const [guestName, setGuestName] = useState('')
  const [commentLoading, setCommentLoading] = useState(false)
  const [replyTo, setReplyTo] = useState<{ id: number; name: string } | null>(null)
  const navigate = useNavigate()
  const { user: loggedUser, isLoggedIn } = useAuthSnapshot()

  useEffect(() => {
    fetchArticle()
  }, [id])

  const loadComments = async (articleId: number) => {
    try {
      const res = (await publicReaderAPI.listComments(articleId)) as { data?: ReaderComment[] }
      setComments(Array.isArray(res?.data) ? res.data : [])
    } catch {
      setComments([])
    }
  }

  useEffect(() => {
    if (article?.id) {
      loadComments(article.id)
    }
  }, [article?.id])

  // 记住字体大小选择
  useEffect(() => {
    localStorage.setItem('reader-font-size', fontSize)
  }, [fontSize])

  const fetchArticle = async () => {
    setLoading(true)
    try {
      const body = (await api.get(`/api/public/articles/${id}`)) as { data?: Record<string, unknown> }
      const raw = body?.data
      if (raw) {
        const norm = normalizeReaderArticle(raw)
        setArticle({
          ...norm,
          ...(raw as object),
          content: String(raw.content ?? ''),
          cover_image: norm.cover_image,
        } as Article)
      } else {
        setArticle(null)
      }
    } catch (error) {
      // 使用模拟数据
      setArticle({
        id: Number(id) || 1,
        title: '我国新能源汽车销量突破1000万辆，引领全球绿色转型',
        author_id: 0,
        content: `最新数据显示，2024年我国新能源汽车销量持续攀升，全年突破1000万辆大关，渗透率超过40%，在全球市场中占据领先地位。这一里程碑式的成就标志着我国新能源汽车产业已进入全新发展阶段。

一、市场现状

数据显示，2024年我国新能源汽车销量同比增长超过30%，多家车企销量创下历史新高。从品牌分布来看，比亚迪、特斯拉、广汽埃安等品牌表现突出，造车新势力如蔚来、小鹏、理想也保持了稳健增长态势。

二、政策支持

国家出台了一系列政策支持新能源汽车发展，包括购置税减免、充电设施建设补贴、牌照优惠等。特别是2024年以来，新能源汽车购置税减免政策延续，为市场注入强劲动力。

三、技术进步

电池技术取得突破性进展，续航里程普遍提升至500公里以上，充电时间大幅缩短。智能驾驶技术日益成熟，辅助驾驶功能成为标配。

四、市场展望

业内专家预计，2025年新能源汽车渗透率将超过50%，市场前景广阔。同时，随着国际市场竞争加剧，中国新能源汽车出海步伐将加快。`,
        abstract: '最新数据显示，2024年我国新能源汽车销量持续攀升，全年突破1000万辆大关，渗透率超过40%，在全球市场中占据领先地位。',
        cover_image: 'https://picsum.photos/900/400?random=1',
        category: '财经',
        tags: ['新能源', '汽车', '产业', '绿色经济'],
        published_at: dayjs().subtract(2, 'hour').toISOString(),
        view_count: 12580,
        like_count: 456,
        author: '记者小明',
        author_avatar: '',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleShare = async () => {
    if (!article?.id) return

    try {
      if (navigator.share) {
        await navigator.share({
          title: article.title,
          text: article.abstract || article.title,
          url: window.location.href,
        })
      } else {
        await navigator.clipboard.writeText(window.location.href)
        toast.success('链接已复制到剪贴板')
      }

      await feedbackAPI.recordShare(article.id)
    } catch (error) {
      // 用户主动取消系统分享时，不提示失败也不计数
      if (error instanceof DOMException && error.name === 'AbortError') {
        return
      }
      console.error('分享失败:', error)
      toast.error('分享失败，请稍后重试')
    }
  }

  const handleLike = async () => {
    if (liked) {
      toast.info('您已经点过赞了')
      return
    }
    // 检查是否自己在给自己点赞
    const currentUserId = (loggedUser as { id?: number } | null)?.id
    if (currentUserId && article?.author_id && currentUserId === article.author_id) {
      toast.info('自己无法给自己的帖子点赞')
      return
    }
    try {
      await feedbackAPI.recordLike(article?.id || 0)
      setLiked(true)
      // 更新本地点赞数
      setArticle(prev => prev ? { ...prev, like_count: (prev.like_count || 0) + 1 } : null)
      toast.success('点赞成功')
    } catch (error) {
      console.error('点赞失败:', error)
      toast.error('点赞失败，请稍后重试')
    }
  }

  const handlePrint = () => {
    window.print()
  }

  const handleSubmitComment = async () => {
    if (!article?.id || !commentText.trim()) {
      toast.warning('请输入评论内容')
      return
    }
    if (!isLoggedIn && !guestName.trim()) {
      toast.warning('未登录时请填写昵称')
      return
    }
    setCommentLoading(true)
    try {
      await publicReaderAPI.postComment(article.id, {
        content: commentText.trim(),
        author_name: isLoggedIn ? undefined : guestName.trim() || undefined,
        parent_id: replyTo?.id,
      })
      toast.success(replyTo ? '回复已发布' : '评论已发布')
      setCommentText('')
      setReplyTo(null)
      await loadComments(article.id)
    } catch {
      toast.error('发表评论失败')
    } finally {
      setCommentLoading(false)
    }
  }

  const displayName =
    (loggedUser as { nickname?: string; full_name?: string; username?: string } | null)?.nickname?.trim() ||
    (loggedUser as { full_name?: string; username?: string } | null)?.full_name?.trim() ||
    (loggedUser as { username?: string } | null)?.username ||
    '用户'

  const renderCommentNodes = (nodes: CommentNode[], depth: number): React.ReactNode =>
    nodes.map((node) => (
      <div
        key={node.id}
        className={depth > 0 ? 'comment-node comment-node-nested' : 'comment-node'}
        style={{ marginLeft: depth > 0 ? 12 : 0 }}
      >
        <div className="comment-node-inner">
          <div className="comment-node-head">
            <Text strong>{node.author_name}</Text>
            {node.reply_to_name ? (
              <Text type="secondary" className="comment-reply-hint">
                {' '}
                回复 @{node.reply_to_name}
              </Text>
            ) : null}
            <Text type="secondary" className="comment-time">
              {node.created_at ? dayjs(node.created_at).format('MM-DD HH:mm') : ''}
            </Text>
          </div>
          <Paragraph className="comment-node-body" style={{ marginBottom: 8 }}>
            {node.content}
          </Paragraph>
          <Button type="link" size="small" className="comment-reply-btn" onClick={() => setReplyTo({ id: node.id, name: node.author_name })}>
            回复
          </Button>
        </div>
        {node.children?.length ? renderCommentNodes(node.children, depth + 1) : null}
      </div>
    ))

  const fontSizeMap = {
    small: '14px',
    medium: '16px',
    large: '18px',
  }

  if (loading) {
    return (
      <div className="reader-loading">
        <Spin size="large" />
        <Text>加载中...</Text>
      </div>
    )
  }

  if (!article) {
    return (
      <div className="reader-loading">
        <Text>文章不存在</Text>
        <Button onClick={() => navigate('/reader')}>返回首页</Button>
      </div>
    )
  }

  return (
    <div className="reader-article">
      <ReaderHeader
        variant="article"
        extra={
          <Space size={0}>
            <Button type="text" icon={<PrinterOutlined />} onClick={handlePrint} aria-label="打印" />
            <Button type="text" icon={<ShareAltOutlined />} onClick={handleShare} aria-label="分享" />
          </Space>
        }
      />

      <main className="reader-article-main">
        <article className="article-container">
          {/* 面包屑 */}
          <Breadcrumb
            className="article-breadcrumb"
            items={[
              { title: <a onClick={() => navigate('/reader')}>首页</a> },
              { title: article.category },
              { title: article.title.slice(0, 10) + '...' },
            ]}
          />

          {/* 文章头部 */}
          <header className="article-header">
            <Tag color="blue" className="article-category">{article.category}</Tag>
            <Title level={2} className="article-title">
              {article.title}
            </Title>
            
            <div className="article-meta">
              <Space>
                <Avatar style={{ backgroundColor: '#1890ff' }}>
                  {(article.author || '读').slice(0, 1)}
                </Avatar>
                <Text strong>{article.author || '匿名'}</Text>
              </Space>
              <Space split={<Divider type="vertical" />}>
                <Text type="secondary">
                  <ClockCircleOutlined /> {article.published_at ? dayjs(article.published_at).format('YYYY-MM-DD HH:mm') : '未发布'}
                </Text>
                <Text type="secondary">
                  <EyeOutlined /> {(article.view_count || 0).toLocaleString()} 阅读
                </Text>
              </Space>
            </div>

            {/* 标签 */}
            <Space className="article-tags" wrap>
              {(article.tags || []).map(tag => (
                <Tag key={tag}>{tag}</Tag>
              ))}
            </Space>
          </header>

          {/* 封面图 */}
          {article.cover_image && (
            <div 
              className="article-cover"
              style={{ backgroundImage: `url(${article.cover_image})` }}
            />
          )}

          {/* 摘要 */}
          <Card className="article-abstract-card">
            <Paragraph italic type="secondary">
              {article.abstract}
            </Paragraph>
          </Card>

          {/* 正文（支持单独成段的 ![](url) Markdown 图片） */}
          <div className="article-content" style={{ fontSize: fontSizeMap[fontSize] }}>
            <MarkdownRenderer
              content={article.content}
              style={{ lineHeight: 2.0 }}
            />
          </div>

          {/* 字体大小调节 */}
          <Card className="article-tools" size="small">
            <Space>
              <Text type="secondary">字体大小：</Text>
              <Button.Group>
                <Button 
                  size="small" 
                  type={fontSize === 'small' ? 'primary' : 'default'}
                  onClick={() => setFontSize('small')}
                >
                  小
                </Button>
                <Button 
                  size="small" 
                  type={fontSize === 'medium' ? 'primary' : 'default'}
                  onClick={() => setFontSize('medium')}
                >
                  中
                </Button>
                <Button 
                  size="small" 
                  type={fontSize === 'large' ? 'primary' : 'default'}
                  onClick={() => setFontSize('large')}
                >
                  大
                </Button>
              </Button.Group>
            </Space>
          </Card>

          {/* 点赞分享 */}
          <Card className="article-actions" size="small">
            <Space size="large">
              <Button 
                icon={<LikeOutlined />} 
                type={liked ? 'primary' : 'default'}
                onClick={handleLike}
              >
                点赞 {(article.like_count || 0)}
              </Button>
              <Button icon={<ShareAltOutlined />} onClick={handleShare}>
                分享
              </Button>
            </Space>
          </Card>

          {/* 评论 */}
          <Card className="article-comments" title="读者评论" style={{ marginTop: 24 }}>
            <div className="comment-thread">
              {comments.length === 0 ? (
                <Text type="secondary">暂无评论，来抢沙发吧</Text>
              ) : (
                renderCommentNodes(buildCommentTree(comments), 0)
              )}
            </div>
            <Divider />
            {replyTo ? (
              <div className="comment-replying-bar">
                <Text type="secondary">
                  回复 <Text strong>@{replyTo.name}</Text>
                </Text>
                <Button type="link" size="small" onClick={() => setReplyTo(null)}>
                  取消
                </Button>
              </div>
            ) : null}
            <Form layout="vertical">
              {!isLoggedIn && (
                <Form.Item label="昵称（未登录必填）">
                  <Input
                    placeholder="您的昵称"
                    value={guestName}
                    onChange={(e) => setGuestName(e.target.value)}
                    maxLength={50}
                  />
                </Form.Item>
              )}
              <Form.Item label={isLoggedIn ? `以「${displayName}」发表评论` : '发表评论'}>
                <Input.TextArea
                  rows={3}
                  placeholder={replyTo ? `回复 @${replyTo.name}…` : '文明发言，理性讨论'}
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  maxLength={2000}
                  showCount
                />
              </Form.Item>
              <Space>
                <Button type="primary" loading={commentLoading} onClick={handleSubmitComment}>
                  {replyTo ? '发布回复' : '发布评论'}
                </Button>
              </Space>
            </Form>
          </Card>

          {/* 相关推荐 */}
          <Card 
            className="article-related"
            title={
              <Space>
                <BookOutlined />
                <span>相关推荐</span>
              </Space>
            }
          >
            <List
              size="small"
              dataSource={[
                { id: 2, title: '央行宣布降准0.5个百分点，释放万亿流动性', category: '财经' },
                { id: 3, title: '华为发布鸿蒙Next：纯血鸿蒙时代来临', category: '科技' },
                { id: 4, title: '人工智能技术在医疗领域取得新突破', category: '科技' },
              ]}
              renderItem={item => (
                <List.Item 
                  className="related-item"
                  onClick={() => navigate(`/reader/article/${item.id}`)}
                >
                  <Text ellipsis>{item.title}</Text>
                  <Tag>{item.category}</Tag>
                </List.Item>
              )}
            />
          </Card>
        </article>
      </main>

      {/* 页脚 */}
      <footer className="reader-footer">
        <Text type="secondary">
          © {new Date().getFullYear()} 新闻内容采编系统 · 基于大模型技术
        </Text>
      </footer>
    </div>
  )
}

export default ReaderArticleDetail
