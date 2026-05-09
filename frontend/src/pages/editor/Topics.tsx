import { useCallback, useEffect, useState } from 'react'
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  Row,
  Col,
  Typography,
  Drawer,
  Descriptions,
  Popconfirm,
  DatePicker,
  InputNumber,
  Spin,
  Empty,
  Pagination,
} from 'antd'
import type { TableProps } from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  RobotOutlined,
  LinkOutlined,
  DisconnectOutlined,
  SyncOutlined,
  TeamOutlined,
  FlagOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { topicAPI, unwrapPaginated } from '../../services/api'
import type { TopicPlanning, Article } from '../../types'
import { toast } from '../../components/common/Toast'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'default' },
  planning: { label: '策划中', color: 'processing' },
  in_progress: { label: '进行中', color: 'blue' },
  completed: { label: '已完成', color: 'success' },
  cancelled: { label: '已取消', color: 'error' },
  active: { label: '策划中', color: 'processing' },
  assigned: { label: '进行中', color: 'blue' },
}

function unwrapData<T>(raw: unknown): T | undefined {
  if (raw != null && typeof raw === 'object' && 'data' in (raw as object)) {
    return (raw as { data: T }).data
  }
  return undefined
}

const Topics = () => {
  const [topics, setTopics] = useState<TopicPlanning[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(12)
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [searchText, setSearchText] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<TopicPlanning | null>(null)
  const [form] = Form.useForm()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [activeTopic, setActiveTopic] = useState<TopicPlanning | null>(null)
  const [topicArticles, setTopicArticles] = useState<Article[]>([])
  const [articlesLoading, setArticlesLoading] = useState(false)
  const [analyzingId, setAnalyzingId] = useState<number | null>(null)
  const [syncLoading, setSyncLoading] = useState(false)
  const [assignForm] = Form.useForm()
  const [linkOpen, setLinkOpen] = useState(false)
  const [linkArticleId, setLinkArticleId] = useState<number | null>(null)
  const [availableArticles, setAvailableArticles] = useState<Article[]>([])
  const [availableTotal, setAvailableTotal] = useState(0)
  const [articleSearchText, setArticleSearchText] = useState('')
  const [articlePage, setArticlePage] = useState(1)
  const [availableLoading, setAvailableLoading] = useState(false)

  const fetchList = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = {
        page,
        page_size: pageSize,
        order_by: '-updated_at',
      }
      if (statusFilter) params.status = statusFilter
      if (searchText.trim()) params.search = searchText.trim()
      const raw = await topicAPI.list(params)
      const { items, total: t } = unwrapPaginated<TopicPlanning>(raw)
      setTopics(items)
      setTotal(t)
    } catch {
      toast.error('加载选题列表失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, statusFilter, searchText])

  useEffect(() => {
    fetchList()
  }, [fetchList])

  const openDetail = async (row: TopicPlanning) => {
    setActiveTopic(row)
    setDrawerOpen(true)
    assignForm.setFieldsValue({
      editor: row.editor || '',
      assigned_user_id: row.assigned_user_id ?? undefined,
    })
    setArticlesLoading(true)
    try {
      const raw = await topicAPI.articles(row.id)
      const list = unwrapData<Article[]>(raw) || []
      setTopicArticles(list)
    } catch {
      setTopicArticles([])
    } finally {
      setArticlesLoading(false)
    }
  }

  const refreshDetailTopic = async () => {
    if (!activeTopic) return
    try {
      const raw = await topicAPI.get(activeTopic.id)
      const t = unwrapData<TopicPlanning>(raw)
      if (t) {
        setActiveTopic(t)
        await fetchList()
      }
    } catch {
      /* ignore */
    }
  }

  const handleCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({
      status: 'draft',
    })
    setModalOpen(true)
  }

  const handleEdit = (row: TopicPlanning) => {
    setEditing(row)
    form.setFieldsValue({
      ...row,
      planned_date: row.planned_date ? dayjs(row.planned_date) : undefined,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const v = await form.validateFields()
      const payload: Record<string, unknown> = {
        title: v.title,
        description: v.description || undefined,
        category: v.category || undefined,
        editor: v.editor || undefined,
        status: v.status,
      }
      if (v.planned_date) {
        payload.planned_date = (v.planned_date as dayjs.Dayjs).toISOString()
      }
      if (editing) {
        await topicAPI.update(editing.id, payload)
        toast.success('选题已更新')
      } else {
        await topicAPI.create(payload)
        toast.success('选题已创建')
      }
      setModalOpen(false)
      fetchList()
    } catch (e: unknown) {
      if (e && typeof e === 'object' && 'errorFields' in e) return
      toast.error('保存失败')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await topicAPI.delete(id)
      toast.success('已删除')
      fetchList()
      if (activeTopic?.id === id) {
        setDrawerOpen(false)
        setActiveTopic(null)
      }
    } catch {
      toast.error('删除失败')
    }
  }

  const runAi = async (id: number) => {
    setAnalyzingId(id)
    try {
      const raw = await topicAPI.aiAnalyze(id)
      const result = unwrapData<Record<string, unknown>>(raw)
      toast.success(
        result?.score != null
          ? `AI 评分 ${result.score}，建议已写入选题`
          : '分析完成'
      )
      await fetchList()
      if (activeTopic?.id === id) await refreshDetailTopic()
    } catch {
      toast.error('AI 分析失败')
    } finally {
      setAnalyzingId(null)
    }
  }

  const runSync = async (id: number) => {
    setSyncLoading(true)
    try {
      await topicAPI.syncFeedback(id)
      toast.success('已根据已发布稿件同步反馈分')
      await fetchList()
      if (activeTopic?.id === id) await refreshDetailTopic()
    } catch {
      toast.error('同步失败（请确认选题下已有已发布稿件）')
    } finally {
      setSyncLoading(false)
    }
  }

  const submitAssign = async () => {
    if (!activeTopic) return
    try {
      const v = await assignForm.validateFields()
      await topicAPI.assign(activeTopic.id, {
        editor: v.editor,
        assigned_user_id: v.assigned_user_id ?? undefined,
      })
      toast.success('指派已保存')
      await refreshDetailTopic()
    } catch (e: unknown) {
      if (e && typeof e === 'object' && 'errorFields' in e) return
      toast.error('指派失败')
    }
  }

  const fetchAvailableArticles = useCallback(async (topicId: number, page = 1, search = '') => {
    setAvailableLoading(true)
    try {
      const raw = await topicAPI.getAvailableArticles(topicId, {
        page,
        page_size: 10,
        search: search || undefined,
      })
      const { items, total } = unwrapPaginated<Article>(raw)
      setAvailableArticles(items)
      setAvailableTotal(total)
      setArticlePage(page)
    } catch {
      setAvailableArticles([])
      setAvailableTotal(0)
    } finally {
      setAvailableLoading(false)
    }
  }, [])

  const openLinkModal = async () => {
    if (!activeTopic) return
    setLinkOpen(true)
    setLinkArticleId(null)
    setArticleSearchText('')
    await fetchAvailableArticles(activeTopic.id, 1, '')
  }

  const linkArticle = async () => {
    if (!activeTopic || !linkArticleId) {
      toast.warning('请选择稿件')
      return
    }
    try {
      await topicAPI.linkArticle(activeTopic.id, linkArticleId)
      toast.success('已关联稿件')
      setLinkOpen(false)
      setLinkArticleId(null)
      const raw = await topicAPI.articles(activeTopic.id)
      setTopicArticles(unwrapData<Article[]>(raw) || [])
      await fetchList()
    } catch {
      toast.error('关联失败，请检查稿件 ID 与权限')
    }
  }

  const unlinkArticle = async (articleId: number) => {
    if (!activeTopic) return
    try {
      await topicAPI.unlinkArticle(activeTopic.id, articleId)
      toast.success('已解除关联')
      const raw = await topicAPI.articles(activeTopic.id)
      setTopicArticles(unwrapData<Article[]>(raw) || [])
      await fetchList()
    } catch {
      toast.error('解除失败')
    }
  }

  const columns: TableProps<TopicPlanning>['columns'] = [
    {
      title: '选题',
      dataIndex: 'title',
      ellipsis: true,
      render: (t: string, row) => (
        <a
          onClick={() => openDetail(row)}
          style={{ fontWeight: 600, color: 'var(--app-primary)' }}
        >
          {t}
        </a>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (s: string) => {
        const m = STATUS_MAP[s] || { label: s, color: 'default' }
        return <Tag color={m.color}>{m.label}</Tag>
      },
    },
    {
      title: '责任编辑',
      dataIndex: 'editor',
      width: 110,
      ellipsis: true,
      render: (e: string) => e || '—',
    },
    {
      title: '截稿/计划',
      dataIndex: 'planned_date',
      width: 120,
      render: (d: string) =>
        d ? dayjs(d).format('MM-DD HH:mm') : '—',
    },
    {
      title: 'AI分',
      dataIndex: 'ai_score',
      width: 72,
      render: (v: number) => (v != null ? v.toFixed(1) : '—'),
    },
    {
      title: '反馈分',
      dataIndex: 'performance_score',
      width: 72,
      render: (v: number | null) => (v != null ? v.toFixed(1) : '—'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 220,
      fixed: 'right',
      render: (_, row) => (
        <Space size="small" wrap>
          <Button type="link" size="small" onClick={() => openDetail(row)}>
            详情
          </Button>
          <Button
            type="link"
            size="small"
            icon={<RobotOutlined />}
            onClick={() => runAi(row.id)}
            loading={analyzingId === row.id}
          >
            AI
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(row)}
          >
            编辑
          </Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(row.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ animation: 'fadeIn 0.25s ease-out' }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 20 }}>
        <Col>
          <Title level={4} style={{ margin: 0 }}>
            <FlagOutlined style={{ marginRight: 8 }} />
            选题策划
          </Title>
          <Text type="secondary" style={{ fontSize: 13 }}>
            创建选题、AI 评估、指派记者、关联线索与稿件，并同步发布反馈形成闭环
          </Text>
        </Col>
        <Col>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新建选题
          </Button>
        </Col>
      </Row>

      <Card
        styles={{ body: { padding: '16px 20px' } }}
        style={{ borderRadius: 12, marginBottom: 16 }}
      >
        <Row gutter={[12, 12]} align="middle">
          <Col xs={24} sm={8} md={6}>
            <Input.Search
              placeholder="搜索标题或说明"
              allowClear
              onSearch={() => {
                setPage(1)
                fetchList()
              }}
              onChange={(e) => setSearchText(e.target.value)}
              value={searchText}
            />
          </Col>
          <Col xs={24} sm={8} md={5}>
            <Select
              allowClear
              placeholder="状态"
              style={{ width: '100%' }}
              value={statusFilter}
              onChange={(v) => {
                setStatusFilter(v)
                setPage(1)
              }}
              options={Object.entries(STATUS_MAP).map(([value, { label }]) => ({
                value,
                label,
              }))}
            />
          </Col>
          <Col>
            <Button
              onClick={() => {
                setPage(1)
                fetchList()
              }}
            >
              刷新
            </Button>
          </Col>
        </Row>
      </Card>

      <Card style={{ borderRadius: 12 }}>
        <Table<TopicPlanning>
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={topics}
          scroll={{ x: 900 }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => {
              setPage(p)
              setPageSize(ps || 12)
            },
          }}
        />
      </Card>

      <Modal
        title={editing ? '编辑选题' : '新建选题'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        width={560}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="title"
            label="选题标题"
            rules={[{ required: true, message: '请输入标题' }]}
          >
            <Input maxLength={500} showCount />
          </Form.Item>
          <Form.Item name="description" label="背景说明">
            <TextArea rows={4} maxLength={4000} showCount />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="category" label="分类">
                <Input placeholder="如：科技 / 社会" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="editor" label="责任编辑">
                <Input placeholder="姓名" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="planned_date" label="截稿 / 计划发布">
                <DatePicker showTime style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="status" label="状态">
                <Select
                  options={Object.entries(STATUS_MAP).map(([value, { label }]) => ({
                    value,
                    label,
                  }))}
                />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      <Drawer
        title={activeTopic?.title || '选题详情'}
        width={520}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false)
          setActiveTopic(null)
        }}
        destroyOnClose
        extra={
          <Space>
            <Button
              icon={<RobotOutlined />}
              loading={activeTopic != null && analyzingId === activeTopic.id}
              onClick={() => activeTopic && runAi(activeTopic.id)}
            >
              AI 分析
            </Button>
            <Button
              icon={<SyncOutlined />}
              loading={syncLoading}
              onClick={() => activeTopic && runSync(activeTopic.id)}
            >
              同步反馈
            </Button>
          </Space>
        }
      >
        {!activeTopic ? (
          <Empty />
        ) : (
          <>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="状态">
                <Tag color={STATUS_MAP[activeTopic.status]?.color}>
                  {STATUS_MAP[activeTopic.status]?.label || activeTopic.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="分类">
                {activeTopic.category || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="AI 评分 (0–10)">
                {activeTopic.ai_score != null ? activeTopic.ai_score.toFixed(1) : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="反馈聚合分 (0–10)">
                {activeTopic.performance_score != null
                  ? activeTopic.performance_score.toFixed(1)
                  : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="关联线索 ID">
                {(activeTopic.ref_clue_ids || []).length
                  ? (activeTopic.ref_clue_ids || []).join(', ')
                  : '—'}
              </Descriptions.Item>
            </Descriptions>

            <Title level={5} style={{ marginTop: 24 }}>
              指派
            </Title>
            <Form form={assignForm} layout="vertical" onFinish={submitAssign}>
              <Form.Item
                name="editor"
                label="责任编辑 / 记者"
                rules={[{ required: true, message: '请填写姓名' }]}
              >
                <Input prefix={<TeamOutlined />} placeholder="记者姓名" />
              </Form.Item>
              <Form.Item name="assigned_user_id" label="系统用户 ID（可选）">
                <InputNumber
                  style={{ width: '100%' }}
                  min={1}
                  placeholder="与账号体系绑定时填写"
                />
              </Form.Item>
              <Button type="primary" htmlType="submit">
                保存指派
              </Button>
            </Form>

            {activeTopic.ai_suggestion ? (
              <>
                <Title level={5} style={{ marginTop: 24 }}>
                  AI 建议
                </Title>
                <Paragraph style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>
                  {activeTopic.ai_suggestion}
                </Paragraph>
              </>
            ) : null}

            <Title level={5} style={{ marginTop: 24 }}>
              旗下稿件
            </Title>
            <Space style={{ marginBottom: 12 }}>
              <Button
                type="dashed"
                icon={<LinkOutlined />}
                onClick={openLinkModal}
              >
                关联稿件
              </Button>
            </Space>
            <Spin spinning={articlesLoading}>
              {topicArticles.length === 0 ? (
                <Empty description="暂无关联稿件" />
              ) : (
                <Table<Article>
                  size="small"
                  rowKey="id"
                  dataSource={topicArticles}
                  pagination={false}
                  columns={[
                    { title: '标题', dataIndex: 'title', ellipsis: true },
                    {
                      title: '状态',
                      dataIndex: 'status',
                      width: 100,
                      render: (s: string) => <Tag>{s}</Tag>,
                    },
                    {
                      title: '',
                      key: 'x',
                      width: 72,
                      render: (_, a) => (
                        <Button
                          type="link"
                          size="small"
                          danger
                          icon={<DisconnectOutlined />}
                          onClick={() => unlinkArticle(a.id)}
                        >
                          移除
                        </Button>
                      ),
                    },
                  ]}
                />
              )}
            </Spin>
          </>
        )}
      </Drawer>

      <Modal
        title="关联已有稿件"
        open={linkOpen}
        onCancel={() => setLinkOpen(false)}
        footer={null}
        width={600}
      >
        <Input
          placeholder="搜索稿件标题或作者..."
          allowClear
          value={articleSearchText}
          onChange={(e) => {
            setArticleSearchText(e.target.value)
            fetchAvailableArticles(activeTopic!.id, 1, e.target.value)
          }}
          style={{ marginBottom: 12 }}
        />
        <Spin spinning={availableLoading}>
          <div style={{ maxHeight: 320, overflow: 'auto', border: '1px solid #f0f0f0', borderRadius: 4 }}>
            {availableArticles.length === 0 ? (
              <Empty description="暂无可选稿件" style={{ padding: 24 }} />
            ) : (
              availableArticles.map((a) => (
                <div
                  key={a.id}
                  onClick={() => {
                    setLinkArticleId(a.id)
                  }}
                  style={{
                    padding: '8px 12px',
                    cursor: 'pointer',
                    background: linkArticleId === a.id ? '#e6f7ff' : 'white',
                    borderBottom: '1px solid #f0f0f0',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <Text strong style={{ display: 'block', fontSize: 14 }}>
                      {a.title}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {a.author} · {a.category || '未分类'} · <Tag style={{ margin: 0 }}>{a.status}</Tag>
                    </Text>
                  </div>
                  {linkArticleId === a.id && (
                    <Tag color="blue">已选择</Tag>
                  )}
                </div>
              ))
            )}
          </div>
        </Spin>
        {availableTotal > availableArticles.length && (
          <div style={{ marginTop: 8, textAlign: 'center' }}>
            <Pagination
              size="small"
              current={articlePage}
              pageSize={10}
              total={availableTotal}
              onChange={(page) => fetchAvailableArticles(activeTopic!.id, page, articleSearchText)}
              showSizeChanger={false}
            />
          </div>
        )}
        <div style={{ marginTop: 16, textAlign: 'right' }}>
          <Button onClick={() => setLinkOpen(false)} style={{ marginRight: 8 }}>
            取消
          </Button>
          <Button
            type="primary"
            onClick={linkArticle}
            disabled={!linkArticleId}
          >
            关联
          </Button>
        </div>
      </Modal>
    </div>
  )
}

export default Topics
