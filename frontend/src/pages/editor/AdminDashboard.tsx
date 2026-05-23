import { useEffect, useState, type ReactNode } from 'react'
import {
  Badge,
  Button,
  Card,
  Descriptions,
  Divider,
  Drawer,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd'
import type { TableProps } from 'antd'
import {
  AuditOutlined,
  DeleteOutlined,
  EyeOutlined,
  KeyOutlined,
  ReloadOutlined,
  SearchOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { adminAPI, articleAPI, unwrapPaginated } from '../../services/api'
import { toast } from '../../components/common/Toast'

const { Text, Paragraph } = Typography
const { Option } = Select

export type AdminUserTabKey = 'all' | 'admin' | 'reviewer' | 'editor'

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

interface AdminArticle {
  id: number
  title: string
  status: string
  category: string
  created_at: string
  updated_at: string
}

const roleColor: Record<string, string> = {
  admin: 'red',
  chief_editor: 'purple',
  editor: 'blue',
  reviewer: 'orange',
  reporter: 'green',
  user: 'cyan',
}

const userTabs: Array<{
  key: AdminUserTabKey
  label: string
  roles?: string[]
  icon: ReactNode
}> = [
  { key: 'all', label: '全部内部人员', roles: ['admin', 'reviewer', 'reporter', 'editor', 'chief_editor'], icon: <TeamOutlined /> },
  { key: 'admin', label: '管理员', roles: ['admin'], icon: <UserOutlined /> },
  { key: 'reviewer', label: '审核员', roles: ['reviewer'], icon: <AuditOutlined /> },
  { key: 'editor', label: '编辑人员', roles: ['reporter', 'editor', 'chief_editor'], icon: <UserOutlined /> },
]

const formatDate = (value?: string) => {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

interface AdminDashboardProps {
  tabKey?: AdminUserTabKey
}

const AdminDashboard = ({ tabKey = 'all' }: AdminDashboardProps) => {
  const [passwordForm] = Form.useForm()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [tableLoading, setTableLoading] = useState(false)
  const [articlesLoading, setArticlesLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [activeState, setActiveState] = useState<string>('all')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [detailOpen, setDetailOpen] = useState(false)
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null)
  const [selectedArticles, setSelectedArticles] = useState<AdminArticle[]>([])
  const [passwordModalOpen, setPasswordModalOpen] = useState(false)
  const [resettingPassword, setResettingPassword] = useState(false)
  const [deletingUserId, setDeletingUserId] = useState<number | null>(null)

  const activeTab = userTabs.find((item) => item.key === tabKey) || userTabs[0]
  const canManageSelectedUser = selectedUser
    ? ['reporter', 'editor', 'chief_editor'].includes(selectedUser.role)
    : false

  const loadUsers = async () => {
    setTableLoading(true)
    try {
      const roleParams = activeTab.roles || []
      const params: Record<string, unknown> = {
        page,
        page_size: pageSize,
      }
      if (search.trim()) params.search = search.trim()
      if (roleParams.length === 1) params.role = roleParams[0]
      if (roleParams.length > 1) params.roles = roleParams.join(',')
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
      await loadUsers()
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [page, pageSize, tabKey, activeState])

  useEffect(() => {
    setPage(1)
    setSearch('')
    setSelectedUser(null)
    setSelectedArticles([])
    setDetailOpen(false)
  }, [tabKey])

  const handleSearch = () => {
    if (page !== 1) {
      setPage(1)
      return
    }
    loadUsers()
  }

  const openDetail = (record: AdminUser) => {
    setSelectedUser(record)
    setDetailOpen(true)
    loadUserArticles(record.id)
  }

  const closeDetail = () => {
    setDetailOpen(false)
  }

  const loadUserArticles = async (userId: number) => {
    setArticlesLoading(true)
    try {
      const res = await articleAPI.list({ author_id: userId, page_size: 20 })
      const { items } = unwrapPaginated<AdminArticle>(res)
      setSelectedArticles(items)
    } catch (error) {
      setSelectedArticles([])
      toast.error('获取人员稿件失败')
    } finally {
      setArticlesLoading(false)
    }
  }

  const handleResetPassword = async (values: { new_password: string }) => {
    if (!selectedUser) return
    setResettingPassword(true)
    try {
      await adminAPI.resetUserPassword(selectedUser.id, values.new_password)
      toast.success('密码已重置')
      setPasswordModalOpen(false)
      passwordForm.resetFields()
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.response?.data?.message
      toast.error(detail || '重置密码失败')
    } finally {
      setResettingPassword(false)
    }
  }

  const handleDeleteUser = async (user: AdminUser) => {
    setDeletingUserId(user.id)
    try {
      await adminAPI.deleteUser(user.id)
      toast.success(`已删除账号：${user.username}`)
      setDetailOpen(false)
      setSelectedUser(null)
      setSelectedArticles([])
      if (users.length === 1 && page > 1) {
        setPage(page - 1)
      } else {
        await loadUsers()
      }
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.response?.data?.message
      toast.error(detail || '删除人员账号失败')
    } finally {
      setDeletingUserId(null)
    }
  }

  const getArticleStatusTag = (status: string) => {
    const map: Record<string, { color: string; text: string }> = {
      draft: { color: 'default', text: '草稿' },
      pending_review: { color: 'orange', text: '待审核' },
      reviewing: { color: 'blue', text: '审核中' },
      approved: { color: 'green', text: '已通过' },
      rejected: { color: 'red', text: '已拒绝' },
      published: { color: 'green', text: '已发布' },
      archived: { color: 'default', text: '已归档' },
    }
    const item = map[status] || { color: 'default', text: status || '-' }
    return <Tag color={item.color}>{item.text}</Tag>
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
      title: '加入时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 130,
      render: (value: string) => <Text type="secondary">{formatDate(value)}</Text>,
    },
    {
      title: '操作',
      key: 'action',
      width: 96,
      fixed: 'right',
      render: (_value, record) => (
        <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => openDetail(record)}>
          查看
        </Button>
      ),
    },
  ]

  const articleColumns: TableProps<AdminArticle>['columns'] = [
    {
      title: '稿件',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (value: string) => <Text strong>{value || '未命名稿件'}</Text>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 92,
      render: getArticleStatusTag,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 112,
      render: (value: string) => <Text type="secondary">{formatDate(value)}</Text>,
    },
  ]

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-in-out' }}>
      <Card
        title={
          <Space>
            <TeamOutlined style={{ color: 'var(--app-primary)' }} />
            <span style={{ fontWeight: 600 }}>{activeTab.label}</span>
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
            <Button icon={<ReloadOutlined />} onClick={refreshAll} loading={loading}>
              刷新
            </Button>
          </Space>
        }
        style={{ borderRadius: 12 }}
      >
        <Paragraph type="secondary" style={{ marginTop: 0 }}>
          当前页面仅用于查看{activeTab.key === 'all' ? '系统中的管理员、审核员和编辑人员账号' : `${activeTab.label}账号`}，投稿用户不在管理员端展示。
        </Paragraph>
        <Table
          rowKey="id"
          size="small"
          loading={tableLoading}
          columns={columns}
          dataSource={users}
          scroll={{ x: 760 }}
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
      <Drawer
        title={
          <Space>
            <EyeOutlined />
            <span>用户详情</span>
          </Space>
        }
        width={720}
        open={detailOpen}
        onClose={closeDetail}
        destroyOnClose
      >
        {selectedUser && (
          <>
            <Space align="center" style={{ marginBottom: 20 }}>
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: 10,
                  background: 'var(--app-primary-muted)',
                  color: 'var(--app-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 18,
                  fontWeight: 700,
                }}
              >
                {(selectedUser.full_name || selectedUser.nickname || selectedUser.username)
                  .slice(0, 1)
                  .toUpperCase()}
              </div>
              <div>
                <Text strong style={{ display: 'block' }}>
                  {selectedUser.full_name || selectedUser.nickname || selectedUser.username}
                </Text>
                <Space size={6}>
                  <Tag color={roleColor[selectedUser.role] || 'default'}>
                    {selectedUser.role_label || selectedUser.role}
                  </Tag>
                  <Badge
                    status={selectedUser.is_active ? 'success' : 'default'}
                    text={selectedUser.is_active ? '启用' : '停用'}
                  />
                </Space>
              </div>
            </Space>

            {canManageSelectedUser && (
              <Space style={{ marginBottom: 16 }}>
                <Button
                  icon={<KeyOutlined />}
                  onClick={() => {
                    passwordForm.resetFields()
                    setPasswordModalOpen(true)
                  }}
                >
                  重置密码
                </Button>
                <Popconfirm
                  title="确认删除编辑人员账号？"
                  description="删除账号后无法登录，历史稿件会保留但不再绑定到该账号。"
                  okText="确认删除"
                  cancelText="取消"
                  okButtonProps={{ danger: true, loading: deletingUserId === selectedUser.id }}
                  onConfirm={() => handleDeleteUser(selectedUser)}
                >
                  <Button danger icon={<DeleteOutlined />} loading={deletingUserId === selectedUser.id}>
                    删除账号
                  </Button>
                </Popconfirm>
              </Space>
            )}

            <Descriptions column={1} size="small" bordered labelStyle={{ width: 92 }}>
              <Descriptions.Item label="账号">@{selectedUser.username}</Descriptions.Item>
              <Descriptions.Item label="邮箱">
                {selectedUser.email || <Text type="secondary">未填写</Text>}
              </Descriptions.Item>
              <Descriptions.Item label="昵称">
                {selectedUser.nickname || <Text type="secondary">未填写</Text>}
              </Descriptions.Item>
              <Descriptions.Item label="加入时间">
                {formatDate(selectedUser.created_at)}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {formatDate(selectedUser.updated_at)}
              </Descriptions.Item>
            </Descriptions>

            <Divider orientation="left" plain>
              业务数据
            </Divider>
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="稿件">{selectedUser.article_count}</Descriptions.Item>
              <Descriptions.Item label="已发布">{selectedUser.published_count}</Descriptions.Item>
              <Descriptions.Item label="待审核">{selectedUser.pending_review_count}</Descriptions.Item>
              <Descriptions.Item label="草稿">{selectedUser.draft_count}</Descriptions.Item>
              <Descriptions.Item label="线索">{selectedUser.clue_count}</Descriptions.Item>
              <Descriptions.Item label="审核">{selectedUser.review_count}</Descriptions.Item>
            </Descriptions>

            <Divider orientation="left" plain>
              投稿稿件
            </Divider>
            <Table
              rowKey="id"
              size="small"
              loading={articlesLoading}
              columns={articleColumns}
              dataSource={selectedArticles}
              pagination={false}
              scroll={{ x: 540 }}
              locale={{ emptyText: '暂无投稿稿件' }}
            />
          </>
        )}
      </Drawer>

      <Modal
        title="重置编辑人员密码"
        open={passwordModalOpen}
        onOk={() => passwordForm.submit()}
        onCancel={() => setPasswordModalOpen(false)}
        confirmLoading={resettingPassword}
        okText="确认重置"
        cancelText="取消"
      >
        <Form form={passwordForm} layout="vertical" onFinish={handleResetPassword}>
          <Form.Item
            name="new_password"
            label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码至少 6 位' },
            ]}
          >
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default AdminDashboard
