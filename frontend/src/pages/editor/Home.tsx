import { Card, Row, Col, Statistic, Button, Typography, Table, Tag, Space, Spin } from 'antd'
import {
  FileTextOutlined,
  BulbOutlined,
  CheckCircleOutlined,
  RocketOutlined,
  ArrowRightOutlined,
  PlusOutlined,
  ThunderboltOutlined,
  TeamOutlined,

  EyeOutlined,
  FireOutlined,
  FlagOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { statsAPI, feedbackAPI } from '../../services/api'
import type { FeedbackStats } from '../../types'
import { toast } from '../../components/common/Toast'

const { Title, Text } = Typography

const Home = () => {
  const navigate = useNavigate()
  const [stats, setStats] = useState({
    clues: 0,
    articles: 0,
    published: 0,
    pending: 0,
  })
  const [topicBrief, setTopicBrief] = useState({ total: 0, active: 0 })
  const [topArticles, setTopArticles] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [dashRes, feedbackRes] = await Promise.all([
          statsAPI.getDashboard(),
          feedbackAPI.getStats(7),
        ])

        const dash = (
          dashRes as {
            data?: {
              clues?: { total?: number }
              articles?: { total?: number; by_status?: Record<string, number> }
              topics?: { total?: number; active?: number }
            }
          }
        ).data
        const feedbackData = (feedbackRes as { data?: FeedbackStats }).data as FeedbackStats | undefined

        const byStatus = dash?.articles?.by_status || {}
        const published = Number(byStatus.published ?? 0)
        const pending =
          Number(byStatus.pending_review ?? 0) + Number(byStatus.reviewing ?? 0)

        setStats({
          clues: dash?.clues?.total ?? 0,
          articles: dash?.articles?.total ?? 0,
          published,
          pending,
        })
        setTopicBrief({
          total: dash?.topics?.total ?? 0,
          active: dash?.topics?.active ?? 0,
        })

        setTopArticles(feedbackData?.top_articles || [])
      } catch (error) {
        console.error('获取统计数据失败:', error)
        toast.error('获取统计数据失败')
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [])

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: 600,
        flexDirection: 'column',
        gap: 16
      }}>
        <Spin size="large" />
        <Text style={{ fontSize: 16, color: '#666' }}>加载中...</Text>
      </div>
    )
  }

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-in-out' }}>
      <div style={{ marginBottom: 32 }}>
        <Title level={2} style={{ fontWeight: 600, color: 'var(--app-text)', letterSpacing: '-0.02em' }}>欢迎使用新闻内容采编系统</Title>
        <Text type="secondary" style={{ fontSize: 15 }}>
          高效管理新闻线索、稿件和选题，提升采编效率
          {topicBrief.total > 0 && (
            <span style={{ marginLeft: 8 }}>
              · 选题 {topicBrief.total} 个（进行中 {topicBrief.active}）
            </span>
          )}
        </Text>
      </div>

      <Row gutter={[20, 24]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card
            hoverable
            style={{
              borderRadius: 12,
              border: '1px solid #e8eaed',
              transition: 'all 0.3s cubic-bezier(0.645, 0.045, 0.355, 1)',
              transform: 'translateY(0)',
              boxShadow: '0 1px 2px rgba(60, 64, 67, 0.06), 0 4px 16px rgba(60, 64, 67, 0.06)',
              background: '#ffffff',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = '0 8px 28px rgba(60, 64, 67, 0.1)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = '0 1px 2px rgba(60, 64, 67, 0.06), 0 4px 16px rgba(60, 64, 67, 0.06)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
              <div>
                <Text type="secondary" style={{ fontSize: 14, display: 'block', marginBottom: 8 }}>新闻线索</Text>
                <Statistic
                  value={stats.clues}
                  valueStyle={{ color: '#faad14', fontWeight: 700, fontSize: 32 }}
                />
              </div>
              <div style={{
                width: 48,
                height: 48,
                borderRadius: 10,
                background: '#fff7ed',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <BulbOutlined style={{ fontSize: 24, color: '#c2410c' }} />
              </div>
            </div>
            <Button
              type="link"
              onClick={() => navigate('/editor/clues')}
              style={{
                padding: 0,
                marginTop: 8,
                color: 'var(--app-primary)',
                fontWeight: 500,
                transition: 'all 0.3s',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              查看详情 <ArrowRightOutlined style={{ fontSize: 12 }} />
            </Button>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card
            hoverable
            style={{
              borderRadius: 12,
              border: '1px solid #e8eaed',
              transition: 'all 0.3s cubic-bezier(0.645, 0.045, 0.355, 1)',
              transform: 'translateY(0)',
              boxShadow: '0 1px 2px rgba(60, 64, 67, 0.06), 0 4px 16px rgba(60, 64, 67, 0.06)',
              background: '#ffffff',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = '0 8px 28px rgba(60, 64, 67, 0.1)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = '0 1px 2px rgba(60, 64, 67, 0.06), 0 4px 16px rgba(60, 64, 67, 0.06)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
              <div>
                <Text type="secondary" style={{ fontSize: 14, display: 'block', marginBottom: 8 }}>稿件总数</Text>
                <Statistic
                  value={stats.articles}
                  valueStyle={{ color: 'var(--app-primary)', fontWeight: 700, fontSize: 32 }}
                />
              </div>
              <div style={{
                width: 48,
                height: 48,
                borderRadius: 10,
                background: '#fef2f2',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <FileTextOutlined style={{ fontSize: 24, color: 'var(--app-primary)' }} />
              </div>
            </div>
            <Button
              type="link"
              onClick={() => navigate('/editor/articles')}
              style={{
                padding: 0,
                marginTop: 8,
                color: 'var(--app-primary)',
                fontWeight: 500,
                transition: 'all 0.3s',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              查看详情 <ArrowRightOutlined style={{ fontSize: 12 }} />
            </Button>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card
            hoverable
            style={{
              borderRadius: 12,
              border: '1px solid #e8eaed',
              transition: 'all 0.3s cubic-bezier(0.645, 0.045, 0.355, 1)',
              transform: 'translateY(0)',
              boxShadow: '0 1px 2px rgba(60, 64, 67, 0.06), 0 4px 16px rgba(60, 64, 67, 0.06)',
              background: '#ffffff',
              cursor: 'pointer',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = '0 8px 28px rgba(60, 64, 67, 0.1)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = '0 1px 2px rgba(60, 64, 67, 0.06), 0 4px 16px rgba(60, 64, 67, 0.06)'
            }}
            onClick={() => navigate('/editor/articles?status=published')}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
              <div>
                <Text type="secondary" style={{ fontSize: 14, display: 'block', marginBottom: 8 }}>已发布</Text>
                <Statistic
                  value={stats.published}
                  valueStyle={{ color: '#52c41a', fontWeight: 700, fontSize: 32 }}
                />
              </div>
              <div style={{
                width: 48,
                height: 48,
                borderRadius: 10,
                background: '#ecfdf5',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <RocketOutlined style={{ fontSize: 24, color: '#059669' }} />
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card
            hoverable
            style={{
              borderRadius: 12,
              border: '1px solid #e8eaed',
              transition: 'all 0.3s cubic-bezier(0.645, 0.045, 0.355, 1)',
              transform: 'translateY(0)',
              boxShadow: '0 1px 2px rgba(60, 64, 67, 0.06), 0 4px 16px rgba(60, 64, 67, 0.06)',
              background: '#ffffff',
              cursor: 'pointer',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = '0 8px 28px rgba(60, 64, 67, 0.1)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = '0 1px 2px rgba(60, 64, 67, 0.06), 0 4px 16px rgba(60, 64, 67, 0.06)'
            }}
            onClick={() => navigate('/editor/articles?status=pending_review')}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
              <div>
                <Text type="secondary" style={{ fontSize: 14, display: 'block', marginBottom: 8 }}>待审核</Text>
                <Statistic
                  value={stats.pending}
                  valueStyle={{ color: '#faad14', fontWeight: 700, fontSize: 32 }}
                />
              </div>
              <div style={{
                width: 48,
                height: 48,
                borderRadius: 10,
                background: '#fffbeb',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <CheckCircleOutlined style={{ fontSize: 24, color: '#d97706' }} />
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[20, 24]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{
                  width: 32,
                  height: 32,
                  borderRadius: 8,
                  background: '#ecfdf5',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <ThunderboltOutlined style={{ fontSize: 18, color: '#059669' }} />
                </div>
                <span style={{ fontWeight: 600, fontSize: 15 }}>快速操作</span>
              </div>
            }
            hoverable
            style={{
              borderRadius: 12,
              border: '1px solid #e8eaed',
              transition: 'all 0.3s cubic-bezier(0.645, 0.045, 0.355, 1)',
              boxShadow: '0 1px 2px rgba(60, 64, 67, 0.06), 0 4px 16px rgba(60, 64, 67, 0.06)',
              background: '#ffffff',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <Button
                type="primary"
                size="large"
                icon={<PlusOutlined />}
                onClick={() => navigate('/editor/articles?new=1')}
                style={{
                  height: 48,
                  fontSize: 15,
                  fontWeight: 500,
                  borderRadius: 8,
                }}
              >
                创建新稿件
              </Button>
              <Button
                size="large"
                icon={<BulbOutlined />}
                onClick={() => navigate('/editor/clues')}
                style={{
                  height: 48,
                  fontSize: 15,
                  fontWeight: 500,
                  borderRadius: 8,
                }}
              >
                查看新闻线索
              </Button>
              <Button
                size="large"
                icon={<FlagOutlined />}
                onClick={() => navigate('/editor/topics')}
                style={{
                  height: 48,
                  fontSize: 15,
                  fontWeight: 500,
                  borderRadius: 8,
                }}
              >
                选题策划
              </Button>
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{
                  width: 32,
                  height: 32,
                  borderRadius: 8,
                  background: '#f0fdfa',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <TeamOutlined style={{ fontSize: 18, color: '#0d9488' }} />
                </div>
                <span style={{ fontWeight: 600, fontSize: 15 }}>系统信息</span>
              </div>
            }
            hoverable
            style={{
              borderRadius: 12,
              border: '1px solid #e8eaed',
              transition: 'all 0.3s cubic-bezier(0.645, 0.045, 0.355, 1)',
              boxShadow: '0 1px 2px rgba(60, 64, 67, 0.06), 0 4px 16px rgba(60, 64, 67, 0.06)',
              background: '#ffffff',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                padding: 12,
                background: '#faf7f7',
                borderRadius: 8,
                gap: 12,
                border: '1px solid #e8eaed',
              }}>
                <div style={{
                  width: 40,
                  height: 40,
                  borderRadius: 10,
                  background: '#fef2f2',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <FileTextOutlined style={{ fontSize: 20, color: 'var(--app-primary)' }} />
                </div>
                <div>
                  <Text type="secondary" style={{ fontSize: 13, display: 'block' }}>总稿件数</Text>
                  <Text strong style={{ fontSize: 18 }}>{stats.articles} 篇</Text>
                </div>
              </div>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                padding: 12,
                background: '#faf7f7',
                borderRadius: 8,
                gap: 12,
                border: '1px solid #e8eaed',
              }}>
                <div style={{
                  width: 40,
                  height: 40,
                  borderRadius: 10,
                  background: '#ecfdf5',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <CheckCircleOutlined style={{ fontSize: 20, color: '#059669' }} />
                </div>
                <div>
                  <Text type="secondary" style={{ fontSize: 13, display: 'block' }}>发布率</Text>
                  <Text strong style={{ fontSize: 18 }}>
                    {stats.articles > 0 ? Math.round((stats.published / stats.articles) * 100) : 0}%
                  </Text>
                </div>
              </div>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                padding: 12,
                background: '#faf7f7',
                borderRadius: 8,
                gap: 12,
                border: '1px solid #e8eaed',
              }}>
                <div style={{
                  width: 40,
                  height: 40,
                  borderRadius: 10,
                  background: '#fff7ed',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <BulbOutlined style={{ fontSize: 20, color: '#c2410c' }} />
                </div>
                <div>
                  <Text type="secondary" style={{ fontSize: 13, display: 'block' }}>待处理线索</Text>
                  <Text strong style={{ fontSize: 18 }}>{stats.clues} 条</Text>
                </div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {topArticles.length > 0 && (
        <Row style={{ marginTop: 24 }}>
          <Col xs={24}>
            <Card
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    background: '#fef2f2',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                    <FireOutlined style={{ fontSize: 18, color: 'var(--app-primary)' }} />
                  </div>
                  <span style={{ fontWeight: 600, fontSize: 15 }}>热门稿件 TOP5</span>
                </div>
              }
              hoverable
              style={{
                borderRadius: 12,
                border: '1px solid #e8eaed',
                boxShadow: '0 1px 2px rgba(60, 64, 67, 0.06), 0 4px 16px rgba(60, 64, 67, 0.06)',
              }}
            >
              <Table
                dataSource={topArticles}
                rowKey="id"
                pagination={false}
                columns={[
                  {
                    title: '排名',
                    dataIndex: 'id',
                    key: 'rank',
                    width: 80,
                    render: (_: any, __: any, index: number) => {
                      const colors = ['#7f1d1d', '#b71c1c', '#c62828', '#e57373', '#ffcdd2']
                      return (
                        <span style={{
                          display: 'inline-block',
                          width: 24,
                          height: 24,
                          lineHeight: '24px',
                          textAlign: 'center',
                          borderRadius: 6,
                          background: colors[index],
                          color: 'white',
                          fontWeight: 600,
                          fontSize: 12,
                        }}>
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
                  },
                  {
                    title: '阅读量',
                    dataIndex: 'views',
                    key: 'views',
                    width: 120,
                    render: (views: number) => (
                      <Space>
                        <EyeOutlined style={{ color: 'var(--app-primary)' }} />
                        <span style={{ fontWeight: 600 }}>{views}</span>
                      </Space>
                    ),
                  },
                  {
                    title: '传播热度',
                    dataIndex: 'trending_score',
                    key: 'trending_score',
                    width: 150,
                    render: (score: number) => {
                      const config = [
                        { min: 80, color: '#f5222d', text: '爆款' },
                        { min: 60, color: '#fa8c16', text: '热门' },
                        { min: 40, color: '#c62828', text: '良好' },
                        { min: 0, color: '#52c41a', text: '一般' },
                      ]
                      const item = config.find(c => score >= c.min) || config[config.length - 1]
                      return (
                        <Tag color={item.color}>
                          {item.text} ({score})
                        </Tag>
                      )
                    },
                  },
                ]}
              />
            </Card>
          </Col>
        </Row>
      )}
    </div>
  )
}

export default Home
