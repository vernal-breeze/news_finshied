import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Input,
  Popconfirm,
  Progress,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd'
import type { TableProps } from 'antd'
import {
  BarChartOutlined,
  CheckCircleOutlined,
  DashboardOutlined,
  DeleteOutlined,
  FileTextOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
  SettingOutlined,
  TeamOutlined,
  UserSwitchOutlined,
} from '@ant-design/icons'
import { adminAPI, settingsAPI, unwrapPaginated } from '../../services/api'
import { toast } from '../../components/common/Toast'

const { Text, Paragraph } = Typography
const { Option } = Select

interface AdminUser {
  id: number
  username: string
  nickname: string
  full_name: string
  email: string
  role: string
  role_label: string
  is_active: boolean
  created_at: string
  updated_at: string
  article_count: number
  published_count: number
  pending_review_count: number
  draft_count: number
  review_count: number
  clue_count: number
}

interface AdminOverview {
  users: {
    total: number
    active: number
    inactive: number
    reviewers: number
    reporters: number
    editors: number
    by_role: Array<{ role: string; label: string; count: number }>
  }
  content: {
    articles: number
    clues: number
    reviews: number
    published: number
    draft: number
    pending_review: number
    recent_articles_7days: number
    recent_clues_7days: number
  }
  traffic: {
    views: number
    likes: number
  }
  recent_users: AdminUser[]
}

interface SystemSettings {
  site_name: string
  description: string
  allow_registration: boolean
  require_ai_check: boolean
  email_notification?: boolean
  review_timeout_hours: number
  min_word_count: number
}

const roleColor: Record<string, string> = {
  admin: 'red',
  chief_editor: 'purple',
  editor: 'blue',
  reviewer: 'orange',
  reporter: 'green',
  user: 'cyan',
}

const formatDate = (value?: string) => {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const AdminDashboard = () => {
  const [overview, setOverview] = useState<AdminOverview | null>(null)
  const [settings, setSettings] = useState<SystemSettings | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [tableLoading, setTableLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [role, setRole] = useState<string | undefined>()
  const [activeState, setActiveState] = useState<string>('all')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [deletingUserId, setDeletingUserId] = useState<number | null>(null)

  const activeRate = useMemo(() => {
    if (!overview?.users.total) return 0
    return Math.round((overview.users.active / overview.users.total) * 100)
  }, [overview])

  const loadOverview = async () => {
    try {
      const [overviewRes, settingsRes] = await Promise.all([
        adminAPI.overview(),
        settingsAPI.get(),
      ])
      setOverview((overviewRes as { data?: AdminOverview }).data || null)
      setSettings((settingsRes as { data?: SystemSettings }).data || null)
    } catch (error) {
      toast.error('获取管理员概览失败，请确认当前账号为管理员')
    }
  }

  const loadUsers = async () => {
    setTableLoading(true)
    try {
      const params: Record<string, unknown> = {
        page,
        page_size: pageSize,
      }
      if (search.trim()) params.search = search.trim()
      if (role) params.role = role
      if (activeState !== 'all') params.is_active = activeState === 'active'
      const res = await adminAPI.users(params)
      const { items, total: totalCount } = unwrapPaginated<AdminUser>(res)
      setUsers(items)
      setTotal(totalCount)
    } catch (error) {
      toast.error('获取人员列表失败')
      setUsers([])
      setTotal(0)
    } finally {
      setTableLoading(false)
    }
  }

  const refreshAll = async () => {
    setLoading(true)
    try {
      await Promise.all([loadOverview(), loadUsers()])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadOverview()
  }, [])

  useEffect(() => {
    loadUsers()
  }, [page, pageSize, role, activeState])

  const handleSearch = () => {
    if (page !== 1) {
      setPage(1)
      return
    }
    loadUsers()
  }

  const handleDeleteUser = async (user: AdminUser) => {
    setDeletingUserId(user.id)
    try {
      await adminAPI.deleteUser(user.id)
      toast.success(`已删除账号：${user.username}`)
      if (users.length === 1 && page > 1) {
        setPage(page - 1)
      } else {
        await loadUsers()
      }
      await loadOverview()
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.response?.data?.message
      toast.error(detail || '删除人员账号失败')
    } finally {
      setDeletingUserId(null)
    }
  }

  const columns: TableProps<AdminUser>['columns'] = [
    {
      title: '人员',
      key: 'user',
      width: 230,
      render: (_value, record) => (
        <Space>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: 'var(--app-primary-muted)',
              color: 'var(--app-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
            }}
          >
            {(record.full_name || record.nickname || record.username).slice(0, 1).toUpperCase()}
          </div>
          <div style={{ minWidth: 0 }}>
            <Text strong style={{ display: 'block' }}>
              {record.full_name || record.nickname || record.username}
            </Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              @{record.username}
            </Text>
          </div>
        </Space>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 110,
      render: (value: string, record) => (
        <Tag color={roleColor[value] || 'default'}>{record.role_label || value}</Tag>
      ),
    },
    {
      title: '联系方式',
      dataIndex: 'email',
      key: 'email',
      ellipsis: true,
      render: (value: string) => value || <Text type="secondary">未填写</Text>,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 90,
      render: (value: boolean) => (
        <Badge status={value ? 'success' : 'default'} text={value ? '启用' : '停用'} />
      ),
    },
    {
      title: '产出数据',
      key: 'metrics',
      width: 280,
      render: (_value, record) => (
        <Space wrap size={[6, 4]}>
          <Tag>稿件 {record.article_count}</Tag>
          <Tag color="green">发布 {record.published_count}</Tag>
          <Tag color="orange">待审 {record.pending_review_count}</Tag>
          <Tag color="blue">线索 {record.clue_count}</Tag>
          <Tag color="purple">审核 {record.review_count}</Tag>
        </Space>
      ),
    },
    {
      title: '加入时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 130,
      render: (value: string) => <Text type="secondary">{formatDate(value)}</Text>,
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 100,
      render: (_value, record) => (
        <Popconfirm
          title="确认删除人员账号？"
          description={`删除后将无法登录，历史稿件和线索会保留。账号：${record.username}`}
          okText="确认删除"
          cancelText="取消"
          okButtonProps={{ danger: true, loading: deletingUserId === record.id }}
          onConfirm={() => handleDeleteUser(record)}
        >
          <Button
            type="text"
            danger
            size="small"
            icon={<DeleteOutlined />}
            loading={deletingUserId === record.id}
          >
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ]

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-in-out' }}>
      <Card
        title={
          <Space>
            <DashboardOutlined style={{ color: 'var(--app-primary)' }} />
            <span style={{ fontWeight: 600 }}>管理员控制台</span>
          </Space>
        }
        extra={
          <Button icon={<ReloadOutlined />} onClick={refreshAll} loading={loading}>
            刷新
          </Button>
        }
        style={{ borderRadius: 12, marginBottom: 16 }}
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16, borderRadius: 8 }}
          message="管理员端用于查看系统配置、数据监控、统计报表，以及管理审核员、记者和编辑人员。"
        />

        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <Card size="small" style={{ borderRadius: 10 }}>
              <Statistic
                title="系统人员"
                value={overview?.users.total || 0}
                prefix={<TeamOutlined />}
                suffix={<Text type="secondary" style={{ fontSize: 12 }}>人</Text>}
              />
              <Progress percent={activeRate} size="small" strokeColor="#52c41a" style={{ marginTop: 8 }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card size="small" style={{ borderRadius: 10 }}>
              <Statistic
                title="稿件总量"
                value={overview?.content.articles || 0}
                prefix={<FileTextOutlined />}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                已发布 {overview?.content.published || 0} · 待审 {overview?.content.pending_review || 0}
              </Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card size="small" style={{ borderRadius: 10 }}>
              <Statistic
                title="新闻线索"
                value={overview?.content.clues || 0}
                prefix={<BarChartOutlined />}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                近 7 天新增 {overview?.content.recent_clues_7days || 0}
              </Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card size="small" style={{ borderRadius: 10 }}>
              <Statistic
                title="阅读反馈"
                value={overview?.traffic.views || 0}
                prefix={<CheckCircleOutlined />}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                点赞 {overview?.traffic.likes || 0}
              </Text>
            </Card>
          </Col>
        </Row>
      </Card>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <SettingOutlined />
                <span>系统配置概览</span>
              </Space>
            }
            style={{ borderRadius: 12, height: '100%' }}
          >
            {settings ? (
              <Descriptions column={1} size="small" bordered labelStyle={{ width: 150 }}>
                <Descriptions.Item label="系统名称">{settings.site_name}</Descriptions.Item>
                <Descriptions.Item label="系统说明">{settings.description}</Descriptions.Item>
                <Descriptions.Item label="注册开关">
                  <Tag color={settings.allow_registration ? 'green' : 'red'}>
                    {settings.allow_registration ? '开放注册' : '关闭注册'}
                  </Tag>
                  <Tag color={settings.require_ai_check ? 'purple' : 'default'}>
                    {settings.require_ai_check ? '启用 AI 检查' : '未启用 AI 检查'}
                  </Tag>
                  <Tag color={settings.email_notification ? 'blue' : 'default'}>
                    {settings.email_notification ? '通知开启' : '通知关闭'}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="审核超时">{settings.review_timeout_hours} 小时</Descriptions.Item>
                <Descriptions.Item label="最低字数">{settings.min_word_count} 字</Descriptions.Item>
              </Descriptions>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无配置数据" />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <UserSwitchOutlined />
                <span>角色分布</span>
              </Space>
            }
            style={{ borderRadius: 12, height: '100%' }}
          >
            <Row gutter={[12, 12]}>
              {(overview?.users.by_role || []).map((item) => (
                <Col xs={12} sm={8} key={item.role}>
                  <Card size="small" style={{ borderRadius: 8, textAlign: 'center' }}>
                    <Tag color={roleColor[item.role] || 'default'} style={{ marginBottom: 8 }}>
                      {item.label}
                    </Tag>
                    <Statistic value={item.count} valueStyle={{ fontSize: 22 }} />
                  </Card>
                </Col>
              ))}
            </Row>
            {!overview?.users.by_role?.length && (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无人员数据" />
            )}
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <Space>
            <SafetyCertificateOutlined style={{ color: '#722ed1' }} />
            <span>人员查看</span>
            <Badge count={total} overflowCount={999} style={{ backgroundColor: 'var(--app-primary)' }} />
          </Space>
        }
        extra={
          <Space wrap>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="搜索姓名、账号、邮箱"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onPressEnter={handleSearch}
              style={{ width: 220 }}
            />
            <Select
              allowClear
              placeholder="角色"
              value={role}
              onChange={(value) => {
                setRole(value)
                setPage(1)
              }}
              style={{ width: 120 }}
            >
              <Option value="reviewer">审核员</Option>
              <Option value="reporter">记者</Option>
              <Option value="editor">编辑</Option>
              <Option value="chief_editor">主编</Option>
              <Option value="admin">管理员</Option>
              <Option value="user">投稿用户</Option>
            </Select>
            <Select
              value={activeState}
              onChange={(value) => {
                setActiveState(value)
                setPage(1)
              }}
              style={{ width: 110 }}
            >
              <Option value="all">全部状态</Option>
              <Option value="active">启用</Option>
              <Option value="inactive">停用</Option>
            </Select>
            <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
              查询
            </Button>
          </Space>
        }
        style={{ borderRadius: 12 }}
      >
        <Paragraph type="secondary" style={{ marginTop: 0 }}>
          这里用于查看和删除审核员、记者、编辑等账号。删除账号不会清除历史稿件、线索和审核记录。
        </Paragraph>
        <Table
          rowKey="id"
          size="small"
          loading={tableLoading}
          columns={columns}
          dataSource={users}
          scroll={{ x: 980 }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (n) => `共 ${n} 人`,
            onChange: (nextPage, nextSize) => {
              setPage(nextPage)
              setPageSize(nextSize)
            },
          }}
        />
      </Card>
    </div>
  )
}

export default AdminDashboard
