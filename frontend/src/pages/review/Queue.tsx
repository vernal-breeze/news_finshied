import React, { useState, useEffect } from 'react'
import { 
  Table, Card, Tag, Button, Space, Typography, Input, Select, 
  Badge, Row, Col, Drawer, Descriptions, Statistic,
  Timeline, Empty, Popconfirm
} from 'antd'
import { 
  SearchOutlined, ReloadOutlined, CheckCircleOutlined,
  CloseCircleOutlined, RollbackOutlined, EyeOutlined, GlobalOutlined,
  HeartOutlined, HeartFilled
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { reviewAPI, articleAPI, feedbackAPI } from '../../services/api'
import { toast } from '../../components/common/Toast'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import './Queue.css'
import MarkdownRenderer from '../../components/MarkdownRenderer'

dayjs.extend(relativeTime)

const { Title, Text } = Typography
const { Option } = Select

interface Article {
  id: number
  title: string
  author: string
  category: string
  status: string
  review_level: number
  word_count: number
  created_at: string
  submitted_at: string
  version: number
  content?: string
  abstract?: string
  tags?: string[]
}

interface ReviewRecord {
  id: number
  reviewer: string
  level: string
  result: string
  comment: string
  created_at: string
}

const ReviewQueue: React.FC = () => {
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null)
  const [reviewDrawerVisible, setReviewDrawerVisible] = useState(false)
  const [reviewRecords, setReviewRecords] = useState<ReviewRecord[]>([])
  const [filters, setFilters] = useState({
    keyword: '',
    category: '',
    status: '',
  })
  const [likedArticles, setLikedArticles] = useState<Set<number>>(new Set())

  const handleLike = async (articleId: number) => {
    setLikedArticles(prev => new Set(prev).add(articleId))
    try { await feedbackAPI.recordLike(articleId) }
    catch { toast.error('点赞失败') }
  }

  useEffect(() => {
    fetchQueue()
  }, [])

  const fetchQueue = async () => {
    setLoading(true)
    try {
      const response = await reviewAPI.getPending()
      // 响应结构: { code, message, data: [...] }
      setArticles((response as any).data || [])
    } catch (error) {
      console.error('获取待审队列失败:', error)
      // 使用模拟数据
      setArticles(getMockArticles())
    } finally {
      setLoading(false)
    }
  }

  // 模拟数据
  const getMockArticles = (): Article[] => [
    {
      id: 1,
      title: '我国新能源汽车销量突破1000万辆',
      author: '记者小明',
      category: '财经',
      status: 'pending_review',
      review_level: 1,
      word_count: 1500,
      created_at: dayjs().subtract(2, 'hour').toISOString(),
      submitted_at: dayjs().subtract(1, 'hour').toISOString(),
      version: 1,
    },
    {
      id: 2,
      title: '北京发布高考改革新政策',
      author: '编辑小王',
      category: '教育',
      status: 'reviewing',
      review_level: 2,
      word_count: 2000,
      created_at: dayjs().subtract(5, 'hour').toISOString(),
      submitted_at: dayjs().subtract(4, 'hour').toISOString(),
      version: 2,
    },
    {
      id: 3,
      title: '华为发布新一代鸿蒙操作系统',
      author: '记者小红',
      category: '科技',
      status: 'pending_review',
      review_level: 1,
      word_count: 1800,
      created_at: dayjs().subtract(30, 'minute').toISOString(),
      submitted_at: dayjs().subtract(20, 'minute').toISOString(),
      version: 1,
    },
  ]

  const getStatusTag = (status: string, level: number) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      pending_review: { color: 'orange', text: '待审核' },
      reviewing: { color: 'blue', text: '审核中' },
      approved: { color: 'green', text: '已通过' },
      rejected: { color: 'red', text: '已拒绝' },
    }
    const config = statusMap[status] || { color: 'default', text: status }
    return <Tag color={config.color}>{config.text} - {level}级</Tag>
  }

  const columns: ColumnsType<Article> = [
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      render: (_, record) => (
        <Badge 
          status={record.status === 'pending_review' ? 'warning' : 'processing'}
          text={record.status === 'pending_review' ? '紧急' : '普通'}
        />
      ),
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (text, record) => (
        <a onClick={() => handleViewArticle(record)}>{text || `稿件 #${record.id}`}</a>
      ),
    },
    {
      title: '作者',
      dataIndex: 'author',
      key: 'author',
      width: 100,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 100,
      render: (category) => <Tag color="blue">{category}</Tag>,
    },
    {
      title: '字数',
      dataIndex: 'word_count',
      key: 'word_count',
      width: 100,
      render: (count) => `${Number(count) || 0}字`,
    },
    {
      title: '状态',
      key: 'status',
      width: 120,
      render: (_, record) => getStatusTag(record.status, record.review_level),
    },
    {
      title: '提交时间',
      dataIndex: 'submitted_at',
      key: 'submitted_at',
      width: 150,
      render: (time) => dayjs(time).fromNow(),
      sorter: (a, b) => dayjs(a.submitted_at).unix() - dayjs(b.submitted_at).unix(),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button 
            type="text"
            size="small"
            icon={likedArticles.has(record.id) ? <HeartFilled style={{ color: '#ff4d4f' }} /> : <HeartOutlined />}
            onClick={() => handleLike(record.id)}
          />
          <Button 
            type="link" 
            icon={<EyeOutlined />}
            onClick={() => handleViewArticle(record)}
          >
            查看
          </Button>
          {record.status !== 'approved' && record.status !== 'rejected' && (
            <Button 
              type="link" 
              icon={<CheckCircleOutlined />}
              onClick={() => handleQuickReview(record, 'approve')}
            >
              通过
            </Button>
          )}
        </Space>
      ),
    },
  ]

  const handleViewArticle = async (article: Article) => {
    setSelectedArticle(article)
    setReviewDrawerVisible(true)
    
    // 获取完整文章内容和审核记录
    try {
      // 获取文章详情
      const articleResponse = await articleAPI.get(article.id)
      if ((articleResponse as any).code === 200 && (articleResponse as any).data) {
        const fullArticle = (articleResponse as any).data
        setSelectedArticle(prev => prev ? { ...prev, ...fullArticle } : prev)
      }
      
      // 获取审核记录
      const reviewsResponse = await reviewAPI.getByArticle(article.id)
      setReviewRecords((reviewsResponse as any).data || [])
    } catch (error) {
      console.error('获取审核记录失败:', error)
      setReviewRecords([])
    }
  }

  const handleQuickReview = async (article: Article, action: 'approve' | 'reject' | 'return') => {
    try {
      const username = localStorage.getItem('username') || 'reviewer'
      
      // 映射 action 到 result
      const resultMap: Record<string, 'approved' | 'rejected' | 'need_revision'> = {
        approve: 'approved',
        reject: 'rejected',
        return: 'need_revision',
      }
      
      await reviewAPI.create({
        article_id: article.id,
        reviewer: username,
        level: 'first',
        result: resultMap[action],
        comment: action === 'approve' ? '审核通过' : action === 'reject' ? '审核拒绝' : '需修改后退回',
      })
      toast.success(`稿件 "${article.title}" 已${action === 'approve' ? '通过' : action === 'reject' ? '拒绝' : '退回'}`)
      fetchQueue()
    } catch (error) {
      toast.error('操作失败')
    }
  }

  const filteredArticles = articles.filter(article => {
    const title = String(article.title || '')
    if (filters.keyword && !title.toLowerCase().includes(filters.keyword.toLowerCase())) {
      return false
    }
    if (filters.category && article.category !== filters.category) {
      return false
    }
    return true
  })

  return (
    <div className="review-queue-container">
      <div className="review-queue-header">
        <Title level={2}>待审队列</Title>
        <Text type="secondary">共 {filteredArticles.length} 篇稿件等待审核</Text>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic 
              title="待审核" 
              value={filteredArticles.filter(a => a.status === 'pending_review').length}
              valueStyle={{ color: '#faad14' }}
              prefix={<Badge status="warning" />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="审核中" 
              value={filteredArticles.filter(a => a.status === 'reviewing').length}
              valueStyle={{ color: '#1890ff' }}
              prefix={<Badge status="processing" />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="已通过" 
              value={filteredArticles.filter(a => a.status === 'approved').length}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="已拒绝" 
              value={filteredArticles.filter(a => a.status === 'rejected').length}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <div className="review-queue-filters">
          <Space wrap>
            <Input
              placeholder="搜索标题"
              prefix={<SearchOutlined />}
              style={{ width: 200 }}
              value={filters.keyword}
              onChange={(e) => setFilters({ ...filters, keyword: e.target.value })}
              allowClear
            />
            <Select
              placeholder="选择分类"
              style={{ width: 120 }}
              value={filters.category || undefined}
              onChange={(value) => setFilters({ ...filters, category: value || '' })}
              allowClear
            >
              <Option value="财经">财经</Option>
              <Option value="教育">教育</Option>
              <Option value="科技">科技</Option>
              <Option value="体育">体育</Option>
              <Option value="社会">社会</Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={fetchQueue}>
              刷新
            </Button>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={filteredArticles}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 篇`,
          }}
        />
      </Card>

      <Drawer
        title={selectedArticle?.title || '稿件审阅'}
        placement="right"
        width={800}
        open={reviewDrawerVisible}
        onClose={() => setReviewDrawerVisible(false)}
        extra={
          <Button 
            type="link" 
            icon={<GlobalOutlined />} 
            onClick={() => window.open(`/reader/article/${selectedArticle?.id}`, '_blank')}
          >
            访问网页
          </Button>
        }
      >
        {selectedArticle && (
          <div className="article-review-content">
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="作者">{selectedArticle.author || '-'}</Descriptions.Item>
              <Descriptions.Item label="分类">
                <Tag color="blue">{selectedArticle.category || '-'}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="字数">{selectedArticle.word_count || selectedArticle.content?.length || 0}字</Descriptions.Item>
              <Descriptions.Item label="版本">v{selectedArticle.version || 1}</Descriptions.Item>
              <Descriptions.Item label="提交时间">
                {selectedArticle.submitted_at ? dayjs(selectedArticle.submitted_at).format('YYYY-MM-DD HH:mm') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                {getStatusTag(selectedArticle.status, selectedArticle.review_level || 1)}
              </Descriptions.Item>
              {selectedArticle.tags && selectedArticle.tags.length > 0 && (
                <Descriptions.Item label="标签" span={2}>
                  {selectedArticle.tags.map((tag, i) => (
                    <Tag key={i} style={{ marginRight: 4 }}>{tag}</Tag>
                  ))}
                </Descriptions.Item>
              )}
            </Descriptions>

            {/* 文章内容预览 */}
            <Title level={5} style={{ marginTop: 24 }}>内容预览</Title>
            <Card size="small" style={{ maxHeight: 400, overflow: 'auto' }}>
              {selectedArticle.abstract && (
                <div style={{ marginBottom: 16 }}>
                  <Text strong>摘要：</Text>
                  <Typography.Paragraph type="secondary">{selectedArticle.abstract}</Typography.Paragraph>
                </div>
              )}
              <div style={{ 
                whiteSpace: 'pre-wrap', 
                lineHeight: 1.8,
                maxHeight: 300,
                overflow: 'auto',
                padding: '8px 12px',
                background: '#f5f5f5',
                borderRadius: 4
              }}>
                <MarkdownRenderer
                  content={selectedArticle.content || ''}
                  style={{ padding: '8px 12px', background: '#f5f5f5', borderRadius: 4, maxHeight: 400, overflow: 'auto' }}
                />
              </div>
            </Card>

            <Title level={5} style={{ marginTop: 24 }}>审核历史</Title>
            {reviewRecords.length > 0 ? (
              <Timeline
                items={reviewRecords.map(record => ({
                  color: record.result === 'approved' ? 'green' : record.result === 'rejected' ? 'red' : 'blue',
                  children: (
                    <div>
                      <Text strong>{record.reviewer}</Text>
                      <Text type="secondary"> - {record.level}级审核</Text>
                      <br />
                      <Text>{record.comment || '无'}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {dayjs(record.created_at).format('YYYY-MM-DD HH:mm')}
                      </Text>
                    </div>
                  ),
                }))}
              />
            ) : (
              <Empty description="暂无审核记录" />
            )}

            <div className="review-actions" style={{ marginTop: 24 }}>
              <Space>
                <Button 
                  type="primary" 
                  icon={<CheckCircleOutlined />}
                  onClick={() => {
                    handleQuickReview(selectedArticle, 'approve')
                    setReviewDrawerVisible(false)
                  }}
                >
                  通过
                </Button>
                <Button 
                  icon={<RollbackOutlined />}
                  onClick={() => {
                    handleQuickReview(selectedArticle, 'return')
                    setReviewDrawerVisible(false)
                  }}
                >
                  退回修改
                </Button>
                <Popconfirm
                  title="确定拒绝此稿件？"
                  onConfirm={() => {
                    handleQuickReview(selectedArticle, 'reject')
                    setReviewDrawerVisible(false)
                  }}
                >
                  <Button danger icon={<CloseCircleOutlined />}>
                    拒绝
                  </Button>
                </Popconfirm>
              </Space>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  )
}

export default ReviewQueue
