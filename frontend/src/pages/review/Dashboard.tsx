import React, { useState, useEffect, useRef } from 'react'
import { Card, Row, Col, Statistic, Typography, Table, Tag, Progress, Space, Button, Avatar, Badge, Drawer, Descriptions, Modal } from 'antd'
import { 
  RobotOutlined, CheckCircleOutlined,
  CloseCircleOutlined, ThunderboltOutlined, ExclamationCircleOutlined,
  ArrowRightOutlined, BellOutlined, EyeOutlined, GlobalOutlined,
  HeartOutlined, HeartFilled
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { articleAPI, reviewAPI, contentAPI, feedbackAPI, unwrapPaginated } from '../../services/api'
import { toast } from '../../components/common/Toast'
import MarkdownRenderer from '../../components/MarkdownRenderer'
import './Dashboard.css'

const { Title, Text, Paragraph } = Typography

interface AIQueueItem {
  id: number
  title: string
  abstract: string
  author: string
  category: string
  aiScore: number
  aiSuggestion: '通过' | '需人工复核' | '不通过'
  /** 大模型或规则引擎给出的理由 */
  aiReason?: string
  aiIssues?: string[]
  submittedAt: string
  status: 'draft' | 'pending_review' | 'approved' | 'rejected'
  content?: string
  tags?: string[]
}

const ReviewDashboard: React.FC = () => {
  const [aiQueue, setAiQueue] = useState<AIQueueItem[]>([])
  const [loading, setLoading] = useState(true)
  const mountedRef = useRef(true)
  const [likedArticles, setLikedArticles] = useState<Set<number>>(new Set())
  const [previewVisible, setPreviewVisible] = useState(false)
  const [selectedArticle, setSelectedArticle] = useState<AIQueueItem | null>(null)
  const [publishModalOpen, setPublishModalOpen] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [publishingArticle, setPublishingArticle] = useState<AIQueueItem | null>(null)
  const [stats, setStats] = useState({
    totalToday: 0,
    aiPassed: 0,
    needHumanReview: 0,
    aiRejected: 0
  })

  const getSuggestionColor = (suggestion: string) => {
    switch (suggestion) {
      case '通过': return 'green'
      case '需人工复核': return 'orange'
      case '不通过': return 'red'
      default: return 'default'
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return '#52c41a'
    if (score >= 60) return '#faad14'
    return '#ff4d4f'
  }

  const fallbackHeuristic = (a: any): Pick<AIQueueItem, 'aiScore' | 'aiSuggestion' | 'aiReason'> => {
    const contentLen = (a.content || '').length
    const aiScore = contentLen > 500 ? 85 : contentLen > 200 ? 70 : 55
    const aiSuggestion = (aiScore >= 80 ? '通过' : aiScore >= 60 ? '需人工复核' : '不通过') as AIQueueItem['aiSuggestion']
    return {
      aiScore,
      aiSuggestion,
      aiReason: '（离线）按长度估算，请检查网络或 API 配置',
    }
  }

  // 从API获取待审稿件，并对每篇调用大模型预审
  const fetchAIQueue = async () => {
    setLoading(true)
    try {
      const response = await articleAPI.list({ status: 'pending_review', page_size: 50 })
      const { items: articles } = unwrapPaginated(response)

      // 1) 先用本地规则秒出初始列表
      const baseWithFallback = articles.map((a: any) => {
        const base = {
          id: a.id,
          title: a.title,
          abstract: a.abstract || (a.content || '').slice(0, 100),
          author: a.author || '未知',
          category: a.category || '未分类',
          submittedAt: a.created_at,
          status: a.status,
          content: a.content,
          tags: a.tags,
        }
        const fb = fallbackHeuristic(a)
        return { ...base, ...fb }
      })
      setAiQueue(baseWithFallback)
      setStats({
        totalToday: baseWithFallback.length,
        aiPassed: baseWithFallback.filter(x => x.aiSuggestion === '通过').length,
        needHumanReview: baseWithFallback.filter(x => x.aiSuggestion === '需人工复核').length,
        aiRejected: baseWithFallback.filter(x => x.aiSuggestion === '不通过').length,
      })
      setLoading(false)

      // 2) 后台逐批调用 AI 审核，拿到结果后替换对应条目
      const BATCH_SIZE = 3
      for (let i = 0; i < articles.length; i += BATCH_SIZE) {
        if (!mountedRef.current) break  // 组件已卸载，停止请求
        const batch = articles.slice(i, i + BATCH_SIZE)
        const batchResults = await Promise.all(
          batch.map(async (a: any, bi: number) => {
            try {
              const r = (await contentAPI.aiReview({ article_id: a.id })) as any
              const payload = r?.data ?? r
              const score = typeof payload?.score === 'number' ? payload.score : 70
              const sug = payload?.suggestion as string | undefined
              const suggestion: AIQueueItem['aiSuggestion'] =
                sug === '通过' || sug === '需人工复核' || sug === '不通过'
                  ? sug
                  : score >= 80 ? '通过' : score >= 60 ? '需人工复核' : '不通过'
              return {
                idx: i + bi,
                aiScore: score,
                aiSuggestion: suggestion,
                aiReason: payload?.reason || payload?.comment || '',
                aiIssues: Array.isArray(payload?.issues) ? payload.issues : [],
              }
            } catch {
              // AI 调用失败，保持已有 fallback 评分
              return null
            }
          })
        )
        // 更新 state：逐条替换
        if (!mountedRef.current) break
        setAiQueue(prev => {
          const next = [...prev]
          batchResults.forEach(result => {
            if (result !== null) {
              next[result.idx] = {
                ...next[result.idx],
                aiScore: result.aiScore,
                aiSuggestion: result.aiSuggestion,
                aiReason: result.aiReason,
                aiIssues: result.aiIssues,
              }
            }
          })
          return next
        })
        // 更新统计
        setAiQueue(prev => {
          setStats({
            totalToday: prev.length,
            aiPassed: prev.filter(x => x.aiSuggestion === '通过').length,
            needHumanReview: prev.filter(x => x.aiSuggestion === '需人工复核').length,
            aiRejected: prev.filter(x => x.aiSuggestion === '不通过').length,
          })
          return prev
        })
      }
    } catch (error) {
      console.error('获取AI审核队列失败:', error)
      // 使用模拟数据作为后备
      setAiQueue(getMockData())
      setLoading(false)
    }
  }

  const handleLike = async (articleId: number) => {
    setLikedArticles(prev => new Set(prev).add(articleId))
    try { await feedbackAPI.recordLike(articleId) }
    catch { toast.error('点赞失败') }
  }

  // 模拟数据
  const getMockData = (): AIQueueItem[] => [
    {
      id: 1,
      title: '我国新能源汽车销量突破1000万辆大关',
      abstract: '据中国汽车工业协会最新数据显示...',
      author: 'user',
      category: '科技',
      aiScore: 92,
      aiSuggestion: '通过',
      submittedAt: dayjs().subtract(10, 'minute').toISOString(),
      status: 'draft',
    },
    {
      id: 2,
      title: '北京发布高考改革新政策',
      abstract: '北京市教育委员会今日发布...',
      author: 'user',
      category: '教育',
      aiScore: 78,
      aiSuggestion: '需人工复核',
      submittedAt: dayjs().subtract(30, 'minute').toISOString(),
      status: 'draft',
    },
    {
      id: 3,
      title: '华为发布新一代鸿蒙操作系统',
      abstract: '华为今日在开发者大会上正式发布...',
      author: 'user',
      category: '科技',
      aiScore: 45,
      aiSuggestion: '需人工复核',
      submittedAt: dayjs().subtract(1, 'hour').toISOString(),
      status: 'draft',
    },
    {
      id: 4,
      title: '某地出现重大安全事故',
      abstract: '据网友爆料，某地发生...',
      author: 'user',
      category: '社会',
      aiScore: 20,
      aiSuggestion: '不通过',
      submittedAt: dayjs().subtract(2, 'hour').toISOString(),
      status: 'draft',
    },
  ]

  // 组件加载时获取数据
  useEffect(() => {
    mountedRef.current = true
    fetchAIQueue()
    return () => { mountedRef.current = false }
  }, [])

  const openPublishModal = (article: AIQueueItem) => {
    setPublishingArticle(article)
    setPublishModalOpen(true)
  }

  const handleConfirmPublish = async () => {
    if (!publishingArticle) return
    setPublishing(true)
    try {
      await reviewAPI.create({
        article_id: publishingArticle.id,
        reviewer: 'AI审核',
        level: 'first',
        result: 'approved',
        comment: 'AI自动审核通过',
      })

      toast.success('审核通过并已发布！')
      setPublishModalOpen(false)
      setPublishingArticle(null)
      if (selectedArticle?.id === publishingArticle.id) {
        setPreviewVisible(false)
        setSelectedArticle(null)
      }
      await fetchAIQueue()
    } catch (error: any) {
      console.error('发布失败:', error)
      const errMsg = error?.response?.data?.message?.message || error?.message || '发布失败'
      toast.error(errMsg)
    } finally {
      setPublishing(false)
    }
  }

  const handleSendToHumanReview = async (id: number) => {
    try {
      // 先获取文章当前状态
      const response = await articleAPI.get(id) as any
      const currentStatus = response?.data?.status
      
      if (currentStatus === 'pending_review') {
        toast.warning('该稿件已在审核队列中，请勿重复提交')
        return
      }
      if (currentStatus === 'approved' || currentStatus === 'published') {
        toast.warning('该稿件已通过审核，无需再次提交')
        return
      }
      
      await articleAPI.submitForReview(id)
      toast.success('已提交人工审核')
      setAiQueue(prev => prev.filter(item => item.id !== id))
    } catch (error: any) {
      console.error('提交人工审核失败:', error)
      const errMsg = error?.response?.data?.message?.message || error?.message || '提交失败'
      toast.error(errMsg)
    }
  }

  const handlePreview = async (article: AIQueueItem) => {
    setSelectedArticle(article)
    setPreviewVisible(true)
  }

  const columns: ColumnsType<AIQueueItem> = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (text, record) => (
        <div>
          <Text strong>{text}</Text>
          <div>
            <Tag>{record.category}</Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>{record.author}</Text>
          </div>
        </div>
      ),
    },
    {
      title: 'AI评分',
      dataIndex: 'aiScore',
      key: 'aiScore',
      width: 120,
      render: (score) => (
        <div style={{ textAlign: 'center' }}>
          <Progress
            percent={score}
            size="small"
            strokeColor={getScoreColor(score)}
            format={(p) => <span style={{ color: getScoreColor(score), fontWeight: 'bold' }}>{p}</span>}
          />
        </div>
      ),
    },
    {
      title: 'AI建议',
      dataIndex: 'aiSuggestion',
      key: 'aiSuggestion',
      width: 120,
      render: (suggestion) => (
        <Tag color={getSuggestionColor(suggestion)} icon={
          suggestion === '通过' ? <CheckCircleOutlined /> : 
          suggestion === '需人工复核' ? <ExclamationCircleOutlined /> : 
          <CloseCircleOutlined />
        }>
          {suggestion}
        </Tag>
      ),
    },
    {
      title: '提交时间',
      dataIndex: 'submittedAt',
      key: 'submittedAt',
      width: 120,
      render: (time) => (
        <Text type="secondary">{dayjs(time).fromNow()}</Text>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
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
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record)}
          >
            预览
          </Button>
          {record.aiSuggestion === '需人工复核' && (
            <Button 
              type="primary" 
              size="small"
              icon={<ArrowRightOutlined />}
              onClick={() => handleSendToHumanReview(record.id)}
            >
              发送人工审核
            </Button>
          )}
          {record.aiSuggestion === '通过' && (
            <Button type="primary" size="small" onClick={() => openPublishModal(record)}>
              确认发布
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div className="review-dashboard">
      <div className="review-dashboard-header">
        <Space align="center" size="middle">
          <Avatar size={48} style={{ backgroundColor: '#1890ff' }} icon={<RobotOutlined />} />
          <div>
            <Title level={2} style={{ margin: 0 }}>AI智能审核</Title>
            <Text type="secondary">AI预审所有投稿，辅助人工审核决策</Text>
          </div>
        </Space>
      </div>

      <Row gutter={[20, 20]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card className="stat-card stat-card-blue" hoverable>
            <Statistic
              title="今日投稿"
              value={stats.totalToday}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="stat-card stat-card-green" hoverable>
            <Statistic
              title="AI建议通过"
              value={stats.aiPassed}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="stat-card stat-card-orange" hoverable>
            <Statistic
              title="需人工复核"
              value={stats.needHumanReview}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="stat-card stat-card-red" hoverable>
            <Statistic
              title="AI建议不通过"
              value={stats.aiRejected}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <Space>
            <BellOutlined style={{ color: '#1890ff' }} />
            <span>待处理队列</span>
            <Badge count={aiQueue.length} style={{ backgroundColor: '#1890ff' }} />
          </Space>
        }
        extra={<Text type="secondary">{loading ? '大模型预审中…' : '预审完成'}</Text>}
      >
        <Table
          columns={columns}
          dataSource={aiQueue}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Row gutter={[20, 20]} style={{ marginTop: 20 }}>
        <Col xs={24} lg={16}>
          <Card title="AI审核说明">
            <Paragraph>
              <Title level={5}>AI智能审核流程</Title>
              <ol style={{ paddingLeft: 20 }}>
                <li><Text>用户提交稿件后，AI自动进行预审</Text></li>
                <li><Text>后端调用大模型，根据要素、客观性、合规与可读性等给出评分(0-100)与建议</Text></li>
                <li><Text>评分≥80分：AI建议"通过"，可直接发布</Text></li>
                <li><Text>评分60-79分：AI建议"需人工复核"，由人工审核最终决定</Text></li>
                <li><Text>评分&lt;60分：AI建议"不通过"，可由人工复核后决定</Text></li>
              </ol>
            </Paragraph>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="快捷操作">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button type="primary" block icon={<ArrowRightOutlined />} href="/review/queue">
                进入人工审核
              </Button>
              <Button block icon={<CheckCircleOutlined />}>
                查看已发布
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 文章预览抽屉 */}
      <Drawer
        title={selectedArticle?.title || '文章预览'}
        placement="right"
        width={700}
        open={previewVisible}
        onClose={() => setPreviewVisible(false)}
        extra={
          <Button 
            type="link" 
            icon={<GlobalOutlined />} 
            onClick={() => selectedArticle && window.open(`/reader/article/${selectedArticle.id}`, '_blank')}
          >
            访问网页
          </Button>
        }
      >
        {selectedArticle && (
          <div>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="作者">{selectedArticle.author || '-'}</Descriptions.Item>
              <Descriptions.Item label="分类">
                <Tag color="blue">{selectedArticle.category || '-'}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="AI评分">
                <Progress 
                  percent={selectedArticle.aiScore} 
                  size="small"
                  strokeColor={getScoreColor(selectedArticle.aiScore)}
                />
              </Descriptions.Item>
              <Descriptions.Item label="AI建议">
                <Tag color={getSuggestionColor(selectedArticle.aiSuggestion)}>
                  {selectedArticle.aiSuggestion}
                </Tag>
              </Descriptions.Item>
              {selectedArticle.aiReason && (
                <Descriptions.Item label="AI理由" span={2}>
                  {selectedArticle.aiReason}
                </Descriptions.Item>
              )}
              {selectedArticle.tags && selectedArticle.tags.length > 0 && (
                <Descriptions.Item label="标签" span={2}>
                  {selectedArticle.tags.map((tag, i) => (
                    <Tag key={i}>{tag}</Tag>
                  ))}
                </Descriptions.Item>
              )}
            </Descriptions>

            <Typography style={{ marginTop: 16 }}>
              <Title level={5}>摘要</Title>
              <Paragraph type="secondary">{selectedArticle.abstract || '暂无摘要'}</Paragraph>
            </Typography>

            <Typography>
              <Title level={5}>内容预览</Title>
              <div style={{ 
                whiteSpace: 'pre-wrap', 
                lineHeight: 1.8,
                maxHeight: 400,
                overflow: 'auto',
                padding: 12,
                background: '#f5f5f5',
                borderRadius: 4
              }}>
                <MarkdownRenderer
                  content={selectedArticle.content || selectedArticle.abstract}
                  style={{ maxHeight: 400, overflow: 'auto', padding: 12, background: '#f5f5f5', borderRadius: 4 }}
                />
              </div>
            </Typography>
          </div>
        )}
      </Drawer>

      <Modal
        title="确认发布"
        open={publishModalOpen}
        onOk={handleConfirmPublish}
        onCancel={() => {
          if (publishing) return
          setPublishModalOpen(false)
          setPublishingArticle(null)
        }}
        confirmLoading={publishing}
        okText="确认发布"
        cancelText="取消"
      >
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Text>确认将该稿件作为 AI 审核通过结果直接发布吗？</Text>
          {publishingArticle && (
            <Card size="small" style={{ background: '#fafafa' }}>
              <Space direction="vertical" size={4}>
                <Text strong>{publishingArticle.title}</Text>
                <Space>
                  <Tag color="blue">{publishingArticle.category}</Tag>
                  <Text type="secondary">{publishingArticle.author}</Text>
                </Space>
                <Text type="secondary">AI 评分：{publishingArticle.aiScore}</Text>
              </Space>
            </Card>
          )}
        </Space>
      </Modal>
    </div>
  )
}

export default ReviewDashboard
