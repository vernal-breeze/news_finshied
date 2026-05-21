import React, { useState, useEffect } from 'react'
import {
  Row,
  Col,
  Card,
  Typography,
  Carousel,
  Space,
  Tag,
  Spin,
  Empty,
  Avatar,
  List,
} from 'antd'
import type { CustomArrowProps } from '@ant-design/react-slick'
import {
  ClockCircleOutlined,
  EyeOutlined,
  FireOutlined,
  LeftOutlined,
  RightOutlined,
  RightCircleOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { fetchPublicArticleList } from '../../services/readerApi'
import ReaderHeader from '../../components/reader/ReaderHeader'
import './Home.css'

const { Title, Text, Paragraph } = Typography

interface FeaturedArticle {
  id: number
  title: string
  abstract: string
  cover_image: string
  category: string
  published_at: string
  view_count: number
  author: string
}

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

/** 与后端稿件分类字段一致（中文） */
/** 避免把 currentSlide / slideCount 等传给 DOM，消除 React 警告 */
const CarouselPrevArrow: React.FC<CustomArrowProps> = (props) => {
  const { className, style, onClick } = props
  return (
    <button
      type="button"
      className={className}
      style={style}
      onClick={onClick}
      aria-label="上一张"
    >
      <LeftOutlined />
    </button>
  )
}

const CarouselNextArrow: React.FC<CustomArrowProps> = (props) => {
  const { className, style, onClick } = props
  return (
    <button
      type="button"
      className={className}
      style={style}
      onClick={onClick}
      aria-label="下一张"
    >
      <RightOutlined />
    </button>
  )
}

const categories = [
  { key: 'all', name: '全部' },
  { key: '科技', name: '科技' },
  { key: '财经', name: '财经' },
  { key: '民生', name: '民生' },
  { key: '文化', name: '文化' },
  { key: '教育', name: '教育' },
  { key: '交通', name: '交通' },
  { key: '环保', name: '环保' },
  { key: '农业', name: '农业' },
]

const ReaderHome: React.FC = () => {
  const [loading, setLoading] = useState(true)
  const [featuredArticles, setFeaturedArticles] = useState<FeaturedArticle[]>([])
  const [articles, setArticles] = useState<Article[]>([])
  const [selectedCategory, setSelectedCategory] = useState('all')
  const navigate = useNavigate()

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const cat = selectedCategory === 'all' ? undefined : selectedCategory
        const list = await fetchPublicArticleList({
          category: cat,
          page_size: 50,
        })
        // 轮播展示最新 3 条；列表区展示全部。若用 slice(3) 作为列表，当仅 1～3 篇已发布时下方会空白。
        setFeaturedArticles(list.slice(0, 3) as FeaturedArticle[])
        setArticles(list)
      } catch {
        setFeaturedArticles(getMockFeatured())
        setArticles(getMockArticles())
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [selectedCategory])

  const getMockFeatured = (): FeaturedArticle[] => [
    {
      id: 1,
      title: '我国新能源汽车销量突破1000万辆，引领全球绿色转型',
      abstract:
        '最新数据显示，2024年我国新能源汽车销量持续攀升，全年突破1000万辆大关，渗透率超过40%，在全球市场中占据领先地位。这一里程碑式的成就标志着我国新能源汽车产业已进入全新发展阶段...',
      cover_image: 'https://picsum.photos/800/400?random=1',
      category: '财经',
      published_at: dayjs().subtract(2, 'hour').toISOString(),
      view_count: 12580,
      author: '记者小明',
    },
    {
      id: 2,
      title: '北京发布高考改革新政策，2025年起实施',
      abstract:
        '北京市教育局今日正式发布高考改革实施方案，涉及考试科目设置、录取规则等多个方面的重大调整。新政策将于2025年起正式实施，届时将影响全市数十万考生的命运...',
      cover_image: 'https://picsum.photos/800/400?random=2',
      category: '社会',
      published_at: dayjs().subtract(5, 'hour').toISOString(),
      view_count: 8960,
      author: '编辑小王',
    },
    {
      id: 3,
      title: '华为发布鸿蒙Next：纯血鸿蒙时代来临',
      abstract:
        '华为今日在深圳举办新品发布会，正式推出鸿蒙Next操作系统。该系统采用全新架构，不再兼容安卓应用，被余承东称为"真正的国产操作系统"...',
      cover_image: 'https://picsum.photos/800/400?random=3',
      category: '科技',
      published_at: dayjs().subtract(8, 'hour').toISOString(),
      view_count: 15670,
      author: '记者小红',
    },
  ]

  const getMockArticles = (): Article[] => [
    {
      id: 4,
      title: '央行宣布降准0.5个百分点，释放万亿流动性',
      abstract:
        '中国人民银行宣布，从2月5日起下调金融机构存款准备金率0.5个百分点，预计释放长期资金约1万亿元。',
      cover_image: 'https://picsum.photos/400/200?random=4',
      category: '财经',
      published_at: dayjs().subtract(1, 'day').toISOString(),
      view_count: 5680,
      author: '记者张三',
    },
    {
      id: 5,
      title: '杭州亚运会中国代表团金牌数创新高',
      abstract:
        '杭州亚运会圆满落幕，中国代表团以201枚金牌的成绩创历史新高，展现了强大的竞技体育实力。',
      cover_image: 'https://picsum.photos/400/200?random=5',
      category: '体育',
      published_at: dayjs().subtract(2, 'day').toISOString(),
      view_count: 12340,
      author: '记者李四',
    },
    {
      id: 6,
      title: '人工智能技术在医疗领域取得新突破',
      abstract:
        '多家科研机构宣布，人工智能辅助诊断系统在多项测试中达到专家水平，为基层医疗带来革命性变化。',
      cover_image: 'https://picsum.photos/400/200?random=6',
      category: '科技',
      published_at: dayjs().subtract(3, 'day').toISOString(),
      view_count: 7890,
      author: '记者王五',
    },
    {
      id: 7,
      title: '春节档电影票房创新高，国产片表现亮眼',
      abstract:
        '2026年春节档电影票房突破100亿元，创下历史新高。多部国产影片表现亮眼，成为票房主力。',
      cover_image: 'https://picsum.photos/400/200?random=7',
      category: '娱乐',
      published_at: dayjs().subtract(4, 'day').toISOString(),
      view_count: 15670,
      author: '记者赵六',
    },
    {
      id: 8,
      title: '知名歌手举办线上演唱会，吸引千万观众',
      abstract:
        '某知名歌手举办线上演唱会，通过多个平台同步直播，吸引了超过1000万观众观看。',
      cover_image: 'https://picsum.photos/400/200?random=8',
      category: '娱乐',
      published_at: dayjs().subtract(5, 'day').toISOString(),
      view_count: 9876,
      author: '记者孙七',
    },
  ]

  const formatViews = (views: number) => {
    if (views >= 10000) {
      return (views / 10000).toFixed(1) + '万'
    }
    return views.toLocaleString()
  }

  if (loading) {
    return (
      <div className="reader-loading">
        <Spin size="large" />
        <Text>加载中...</Text>
      </div>
    )
  }

  return (
    <div className="reader-home">
      <ReaderHeader />

      <nav className="reader-nav">
        <div className="reader-nav-content">
          <Space size="middle" wrap>
            {categories.map((cat) => (
              <Tag
                key={cat.key}
                className={selectedCategory === cat.key ? 'active' : ''}
                onClick={() => setSelectedCategory(cat.key)}
              >
                {cat.name}
              </Tag>
            ))}
          </Space>
        </div>
      </nav>

      <main className="reader-main">
        {featuredArticles.length > 0 && (
          <section className="reader-featured">
            <Carousel
              autoplay
              autoplaySpeed={5000}
              dots
              arrows
              prevArrow={<CarouselPrevArrow />}
              nextArrow={<CarouselNextArrow />}
            >
              {featuredArticles.map((article) => (
                <div key={article.id} className="featured-slide">
                  <div
                    className="featured-image"
                    style={{ backgroundImage: `url(${article.cover_image})` }}
                    onClick={() => navigate(`/reader/article/${article.id}`)}
                    role="presentation"
                  >
                    <div className="featured-overlay">
                      <Tag color="blue">{article.category}</Tag>
                      <Title level={3} className="featured-title">
                        {article.title}
                      </Title>
                      <Paragraph className="featured-abstract" ellipsis={{ rows: 2 }}>
                        {article.abstract}
                      </Paragraph>
                      <Space className="featured-meta">
                        <Text>
                          <Avatar size="small">{article.author[0]}</Avatar> {article.author}
                        </Text>
                        <Text>
                          <ClockCircleOutlined /> {dayjs(article.published_at).fromNow()}
                        </Text>
                        <Text>
                          <EyeOutlined /> {formatViews(article.view_count)}
                        </Text>
                      </Space>
                    </div>
                  </div>
                </div>
              ))}
            </Carousel>
          </section>
        )}

        <section className="reader-articles">
          <Row gutter={[24, 24]}>
            {articles.length > 0 ? (
              articles.map((article) => (
                <Col xs={24} sm={12} lg={8} key={article.id}>
                  <Card
                    className="article-card"
                    hoverable
                    cover={
                      <div
                        className="article-cover"
                        style={{ backgroundImage: `url(${article.cover_image})` }}
                        onClick={() => navigate(`/reader/article/${article.id}`)}
                        role="presentation"
                      />
                    }
                    onClick={() => navigate(`/reader/article/${article.id}`)}
                  >
                    <Tag color="blue" className="article-category">
                      {article.category}
                    </Tag>
                    <Title level={5} className="article-title" ellipsis={{ rows: 2 }}>
                      {article.title}
                    </Title>
                    <Paragraph className="article-abstract" ellipsis={{ rows: 2 }}>
                      {article.abstract}
                    </Paragraph>
                    <div className="article-meta">
                      <Space>
                        <Text type="secondary">
                          <Avatar size="small">{article.author[0]}</Avatar> {article.author}
                        </Text>
                      </Space>
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
              ))
            ) : (
              <Col span={24}>
                <Empty description="暂无文章" />
              </Col>
            )}
          </Row>
        </section>

        <section className="reader-hot">
          <Card
            title={
              <Space>
                <FireOutlined style={{ color: '#f5222d' }} />
                <span>热点新闻</span>
              </Space>
            }
          >
            <List
              dataSource={articles.slice(0, 5)}
              renderItem={(item, index) => (
                <List.Item
                  className="hot-item"
                  onClick={() => navigate(`/reader/article/${item.id}`)}
                >
                  <List.Item.Meta
                    avatar={
                      <span
                        className={`hot-rank rank-${index < 3 ? 'top' : 'normal'}`}
                      >
                        {index + 1}
                      </span>
                    }
                    title={<Text ellipsis>{item.title}</Text>}
                    description={`${item.category} · ${dayjs(item.published_at).fromNow()}`}
                  />
                  <RightCircleOutlined style={{ color: '#bfbfbf' }} />
                </List.Item>
              )}
            />
          </Card>
        </section>
      </main>

      <footer className="reader-footer">
        <Text type="secondary">
          © {new Date().getFullYear()} 新闻内容采编系统 · 基于大模型技术
        </Text>
      </footer>
    </div>
  )
}

export default ReaderHome
