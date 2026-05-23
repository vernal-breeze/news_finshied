import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Space,
  Select,
  Button,
  Empty,
  Typography,
  Divider,
} from 'antd'
import { toast } from '../../components/common/Toast'
import {
  BarChartOutlined,
  EyeOutlined,
  LikeOutlined,
  CommentOutlined,
  ShareAltOutlined,
  FireOutlined,
  ReloadOutlined,
  TrophyOutlined,
  ExportOutlined,
} from '@ant-design/icons'
import { feedbackAPI, unwrapPaginated } from '../../services/api'
import type { FeedbackStats } from '../../types'

const { Title, Text } = Typography
const { Option } = Select

interface AnalyticsArticle {
  id: number
  article_id: number
  title: string
  category: string
  view_count: number
  like_count: number
  comment_count: number
  share_count: number
  engagement_rate: number
  trending_score: number
  published_at?: string
}

const Analytics = () => {
  const [stats, setStats] = useState<FeedbackStats | null>(null)
  const [articles, setArticles] = useState<AnalyticsArticle[]>([])
  const [loading, setLoading] = useState(false)
  const [timeRange, setTimeRange] = useState<number>(7)
  const navigate = useNavigate()

  useEffect(() => {
    fetchData()
  }, [timeRange])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [statsRes, articlesRes] = await Promise.all([
        feedbackAPI.getStats(timeRange),
        feedbackAPI.listArticles({ days: timeRange, page_size: 100 }),
      ])

      setStats((statsRes as { data?: FeedbackStats }).data ?? null)
      const { items } = unwrapPaginated<AnalyticsArticle>(articlesRes)
      setArticles(items)
    } catch (error) {
      toast.error('获取数据失败')
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      title: '排名',
      key: 'rank',
      width: 80,
      render: (_: any, __: any, index: number) => {
        const colors = ['#f5222d', '#fa8c16', '#faad14', '#1890ff', '#52c41a']
        return (
          <span
            style={{
              display: 'inline-block',
              width: 28,
              height: 28,
              lineHeight: '28px',
              textAlign: 'center',
              borderRadius: '50%',
              background: index < 5 ? colors[index] : '#d9d9d9',
              color: 'white',
              fontWeight: 'bold',
              fontSize: 14,
            }}
          >
            {index + 1}
          </span>
        )
      },
    },
    {
      title: '稿件标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (text: string, record: AnalyticsArticle) => (
        <Space>
          <a onClick={() => navigate(`/reader/article/${record.article_id || record.id}`)}>
            <Text strong>{text}</Text>
          </a>
          <Button
            type="link"
            size="small"
            icon={<ExportOutlined />}
            onClick={() => navigate(`/reader/article/${record.article_id || record.id}`)}
          >
            查看
          </Button>
        </Space>
      ),
    },
    {
      title: '阅读量',
      dataIndex: 'view_count',
      key: 'views',
      width: 120,
      render: (views: number) => (
        <Space>
          <EyeOutlined style={{ color: '#1890ff' }} />
          <span style={{ fontWeight: 600 }}>{views || 0}</span>
        </Space>
      ),
    },
    {
      title: '点赞',
      dataIndex: 'like_count',
      key: 'likes',
      width: 100,
      render: (likes: number) => (
        <Space>
          <LikeOutlined style={{ color: '#eb2f96' }} />
          <span>{likes || 0}</span>
        </Space>
      ),
    },
    {
      title: '评论',
      dataIndex: 'comment_count',
      key: 'comments',
      width: 100,
      render: (comments: number) => (
        <Space>
          <CommentOutlined style={{ color: '#52c41a' }} />
          <span>{comments || 0}</span>
        </Space>
      ),
    },
    {
      title: '分享',
      dataIndex: 'share_count',
      key: 'shares',
      width: 100,
      render: (shares: number) => (
        <Space>
          <ShareAltOutlined style={{ color: '#722ed1' }} />
          <span>{shares || 0}</span>
        </Space>
      ),
    },
    {
      title: '热度',
      dataIndex: 'trending_score',
      key: 'trending',
      width: 100,
      render: (score: number) => {
        const config = [
          { min: 80, color: 'error', text: '爆款' },
          { min: 60, color: 'warning', text: '热门' },
          { min: 40, color: 'processing', text: '良好' },
          { min: 0, color: 'default', text: '一般' },
        ]
        const item = config.find((c) => (score || 0) >= c.min) || config[config.length - 1]
        return (
          <Tag color={item.color} icon={<FireOutlined />}>
            {item.text}
          </Tag>
        )
      },
    },
  ]

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-in-out' }}>
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: 'linear-gradient(135deg, #13c2c2 0%, #08979c 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <BarChartOutlined style={{ fontSize: 18, color: 'white' }} />
            </div>
            <span style={{ fontWeight: 600, fontSize: 16 }}>反馈分析</span>
          </div>
        }
        extra={
          <Space>
            <Select
              value={timeRange}
              onChange={setTimeRange}
              style={{ width: 120 }}
              placeholder="时间范围"
            >
              <Option value={7}>最近7天</Option>
              <Option value={30}>最近30天</Option>
              <Option value={90}>最近90天</Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={fetchData}>
              刷新
            </Button>
          </Space>
        }
        style={{ borderRadius: 12 }}
      >
        {stats && (
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={24} sm={12} lg={6}>
              <Card hoverable style={{ borderRadius: 8, textAlign: 'center' }}>
                <EyeOutlined style={{ fontSize: 32, color: '#1890ff', marginBottom: 8 }} />
                <Statistic
                  title="总阅读量"
                  value={stats.total_views}
                  valueStyle={{ color: '#1890ff', fontWeight: 600 }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card hoverable style={{ borderRadius: 8, textAlign: 'center' }}>
                <LikeOutlined style={{ fontSize: 32, color: '#eb2f96', marginBottom: 8 }} />
                <Statistic
                  title="总点赞数"
                  value={stats.total_likes}
                  valueStyle={{ color: '#eb2f96', fontWeight: 600 }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card hoverable style={{ borderRadius: 8, textAlign: 'center' }}>
                <CommentOutlined style={{ fontSize: 32, color: '#52c41a', marginBottom: 8 }} />
                <Statistic
                  title="总评论数"
                  value={stats.total_comments}
                  valueStyle={{ color: '#52c41a', fontWeight: 600 }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card hoverable style={{ borderRadius: 8, textAlign: 'center' }}>
                <ShareAltOutlined style={{ fontSize: 32, color: '#722ed1', marginBottom: 8 }} />
                <Statistic
                  title="总分享数"
                  value={stats.total_shares}
                  valueStyle={{ color: '#722ed1', fontWeight: 600 }}
                />
              </Card>
            </Col>
          </Row>
        )}

        <Divider />

        <Title level={5} style={{ marginBottom: 16 }}>
          <TrophyOutlined style={{ color: '#faad14', marginRight: 8 }} />
          已发布稿件反馈
        </Title>

        {articles.length > 0 ? (
          <Table
            columns={columns}
            dataSource={articles}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        ) : (
          <Empty description="暂无已发布稿件" />
        )}
      </Card>
    </div>
  )
}

export default Analytics
