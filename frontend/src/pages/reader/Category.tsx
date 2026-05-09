import React, { useState, useEffect } from 'react'
import { Row, Col, Card, Typography, Space, Tag, Empty, Spin, Breadcrumb } from 'antd'
import { ClockCircleOutlined, EyeOutlined } from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import dayjs from 'dayjs'
import { fetchPublicArticleList } from '../../services/readerApi'
import ReaderHeader from '../../components/reader/ReaderHeader'
import './Category.css'

const { Title, Text, Paragraph } = Typography

interface Article {
  id: number
  title: string
  abstract: string
  cover_image: string
  category: string
  published_at: string
  view_count: number
  author: string
}

const categories = [
  { key: 'all', name: '全部', icon: '📰', color: '#666' },
  { key: '科技', name: '科技', icon: '💻', color: '#1890ff' },
  { key: '财经', name: '财经', icon: '💰', color: '#52c41a' },
  { key: '社会', name: '社会', icon: '🏠', color: '#722ed1' },
  { key: '文化', name: '文化', icon: '📚', color: '#faad14' },
  { key: '体育', name: '体育', icon: '⚽', color: '#f5222d' },
  { key: '时政', name: '时政', icon: '📌', color: '#eb2f96' },
]

const ReaderCategory: React.FC = () => {
  const { category: categoryParam } = useParams<{ category: string }>()
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const currentCategory = categoryParam || 'all'
  const categoryInfo = categories.find((c) => c.key === currentCategory)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      const cat = currentCategory === 'all' ? undefined : currentCategory
      try {
        const list = await fetchPublicArticleList({
          category: cat,
          page_size: 50,
        })
        setArticles(list)
      } catch {
        setArticles(getMockArticles(currentCategory))
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [currentCategory])

  const getMockArticles = (cat: string): Article[] => {
    const base: Article[] = [
      {
        id: 1,
        title: '华为发布鸿蒙Next：纯血鸿蒙时代来临',
        abstract: '华为正式发布鸿蒙Next版本，不再兼容安卓应用，标志着国产操作系统进入新阶段。',
        cover_image: 'https://picsum.photos/400/200?random=10',
        category: '科技',
        published_at: dayjs().subtract(2, 'hour').toISOString(),
        view_count: 15670,
        author: '记者小红',
      },
      {
        id: 2,
        title: '我国新能源汽车销量突破1000万辆',
        abstract: '2024年全年销量突破1000万辆大关，渗透率超过40%。',
        cover_image: 'https://picsum.photos/400/200?random=12',
        category: '财经',
        published_at: dayjs().subtract(1, 'day').toISOString(),
        view_count: 12580,
        author: '记者张三',
      },
    ]
    if (cat === 'all') return base
    return base.filter((a) => a.category === cat)
  }

  const formatViews = (views: number) => {
    if (views >= 10000) return (views / 10000).toFixed(1) + '万'
    return views.toLocaleString()
  }

  return (
    <div className="reader-category">
      <ReaderHeader />

      {/* 分类导航 */}
      <nav className="category-nav">
        <div className="category-nav-content">
          <Space size="middle" wrap>
            {categories.map(cat => (
              <Tag
                key={cat.key}
                className={currentCategory === cat.key ? 'active' : ''}
                style={{ 
                  fontSize: 16, 
                  padding: '8px 16px',
                  cursor: 'pointer',
                  borderRadius: 20,
                }}
                onClick={() =>
                  navigate(
                    cat.key === 'all'
                      ? '/reader'
                      : `/reader/category/${encodeURIComponent(cat.key)}`
                  )
                }
              >
                {cat.icon} {cat.name}
              </Tag>
            ))}
          </Space>
        </div>
      </nav>

      {/* 主体内容 */}
      <main className="reader-main">
        <Breadcrumb
          className="category-breadcrumb"
          items={[
            { title: <a onClick={() => navigate('/reader')}>首页</a> },
            { title: categoryInfo?.name || '全部分类' },
          ]}
        />

        <div className="category-header" style={{ marginBottom: 24 }}>
          <Space>
            <span style={{ fontSize: 32 }}>{categoryInfo?.icon || '📰'}</span>
            <Title level={2} style={{ margin: 0 }}>
              {categoryInfo?.name || '全部分类'}
            </Title>
          </Space>
        </div>

        {loading ? (
          <div className="reader-loading">
            <Spin size="large" />
            <Text>加载中...</Text>
          </div>
        ) : articles.length > 0 ? (
          <Row gutter={[24, 24]}>
            {articles.map(article => (
              <Col xs={24} sm={12} lg={8} key={article.id}>
                <Card
                  className="article-card"
                  hoverable
                  cover={
                    <div
                      className="article-cover"
                      style={{ backgroundImage: `url(${article.cover_image})` }}
                      onClick={() => navigate(`/reader/article/${article.id}`)}
                    />
                  }
                  onClick={() => navigate(`/reader/article/${article.id}`)}
                >
                  <Tag color={categoryInfo?.color}>{article.category}</Tag>
                  <Title level={5} className="article-title" ellipsis={{ rows: 2 }}>
                    {article.title}
                  </Title>
                  <Paragraph className="article-abstract" ellipsis={{ rows: 2 }}>
                    {article.abstract}
                  </Paragraph>
                  <div className="article-meta">
                    <Text type="secondary">{article.author}</Text>
                    <Space>
                      <Text type="secondary">
                        <ClockCircleOutlined /> {dayjs(article.published_at).fromNow()}
                      </Text>
                      <Text type="secondary">
                        <EyeOutlined /> {formatViews(article.view_count)}
                      </Text>
                    </Space>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        ) : (
          <Empty description="该分类暂无文章" />
        )}
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

export default ReaderCategory
