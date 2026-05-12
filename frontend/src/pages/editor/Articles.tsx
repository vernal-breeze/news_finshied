import { useState, useEffect, useCallback } from 'react'
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
  Tooltip,
  Popconfirm,
  Typography,
  Badge,
  Drawer,
  Descriptions,
  Divider,
  Tabs,
  Timeline,
  Empty,
  Spin,
  Alert,
  Statistic,
  List,
  Avatar,
  Segmented,
  Upload,
} from 'antd'
import type { UploadProps } from 'antd'
import type { TableProps } from 'antd'
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  SearchOutlined,
  ReloadOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  SendOutlined,
  AuditOutlined,
  TagOutlined,
  ClearOutlined,
  CopyOutlined,
  PictureOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import { useSearchParams } from 'react-router-dom'
import { articleAPI, topicAPI, unwrapPaginated, uploadAPI } from '../../services/api'
import type { Article, TopicPlanning } from '../../types'
import { toast } from '../../components/common/Toast'
import type { AxiosError } from 'axios'

const { Title, Text, Paragraph } = Typography

function toastUploadError(err: unknown) {
  const ax = err as AxiosError<{ message?: string; detail?: unknown }>
  const status = ax.response?.status
  if (status === 401) {
    toast.error('未登录或登录已过期，请重新登录后再上传')
    return
  }
  if (status === 422) {
    toast.error('上传请求格式异常，请重试（若仍失败请刷新页面）')
    return
  }
  if (status === 413) {
    toast.error('图片过大，请使用 5MB 以内的 jpg/png/gif/webp')
    return
  }
  toast.error('上传失败，请检查网络与图片格式（5MB 以内）')
}
const { Option } = Select
const { TextArea } = Input


const Articles = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingArticle, setEditingArticle] = useState<Article | null>(null)
  const [detailVisible, setDetailVisible] = useState(false)
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null)
  const [form] = Form.useForm()
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined)
  const [reviews, setReviews] = useState<any[]>([])
  const [viewMode, setViewMode] = useState<'table' | 'list'>('table')
  const [articleImages, setArticleImages] = useState<string[]>([])
  const [coverImage, setCoverImage] = useState<string>('')
  const [topicOptions, setTopicOptions] = useState<TopicPlanning[]>([])
  const [topicLoading, setTopicLoading] = useState(false)

  const fetchArticles = useCallback(async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (statusFilter) params.status = statusFilter
      if (categoryFilter) params.category = categoryFilter
      if (searchText) params.search = searchText
      const data = await articleAPI.list(params)
      setArticles(Array.isArray(data) ? data : (data as any).data || [])
    } catch (error) {
      toast.error('获取稿件列表失败')
    } finally {
      setLoading(false)
      setInitialLoading(false)
    }
  }, [statusFilter, categoryFilter, searchText])

  useEffect(() => {
    fetchArticles()
    fetchTopicOptions() // 组件加载时获取选题列表
  }, [fetchArticles])

  useEffect(() => {
    const status = searchParams.get('status')
    if (status) {
      setStatusFilter(status)
    }
    if (searchParams.get('new') === '1') {
      setEditingArticle(null)
      form.resetFields()
      setModalVisible(true)
      fetchTopicOptions()
      const next = new URLSearchParams(searchParams)
      next.delete('new')
      setSearchParams(next, { replace: true })
    }
  }, [searchParams, setSearchParams, form])

  // Reset filters
  const resetFilters = () => {
    setSearchText('')
    setStatusFilter(undefined)
    setCategoryFilter(undefined)
    toast.info('筛选条件已重置')
  }

  const hasActiveFilters = searchText || statusFilter || categoryFilter

  const handleSearch = () => {
    fetchArticles()
  }

  const handleCreate = () => {
    setEditingArticle(null)
    form.resetFields()
    setArticleImages([])
    setCoverImage('')
    fetchTopicOptions()
    setModalVisible(true)
  }

  const handleEdit = (record: Article) => {
    setEditingArticle(record)
    form.setFieldsValue({
      ...record,
      tags: record.tags?.join(', '),
      topic_id: record.topic_id,
    })
    setArticleImages(Array.isArray(record.images) ? record.images : [])
    setCoverImage(record.cover_image || '')
    fetchTopicOptions()
    setModalVisible(true)
  }

  const fetchTopicOptions = useCallback(async () => {
    setTopicLoading(true)
    try {
      const raw = await topicAPI.list({
        page: 1,
        page_size: 100,
        order_by: '-updated_at',
      })
      const { items } = unwrapPaginated<TopicPlanning>(raw)
      setTopicOptions(items)
    } catch {
      setTopicOptions([])
      toast.error('加载选题列表失败')
    } finally {
      setTopicLoading(false)
    }
  }, [])

  const handleDelete = async (id: number) => {
    try {
      await articleAPI.delete(id)
      toast.success('删除成功')
      fetchArticles()
    } catch (error) {
      toast.error('删除失败')
    }
  }

  const handleSubmit = async (values: any) => {
    try {
      const { topic_id, ...restValues } = values
      const data = {
        ...restValues,
        tags: restValues.tags
          ? restValues.tags.split(',').map((t: string) => t.trim()).filter((t: string) => t)
          : [],
        images: articleImages,
        cover_image: coverImage.trim() ? coverImage.trim() : null,
      }

      if (editingArticle) {
        await articleAPI.update(editingArticle.id, {
          ...data,
          topic_id: topic_id ?? undefined,
        })
        toast.success('更新成功')
      } else {
        await articleAPI.create({
          ...data,
          topic_id: topic_id ?? undefined,
        })
        toast.success('创建成功')
      }
      setModalVisible(false)
      fetchArticles()
    } catch (error) {
      toast.error(editingArticle ? '更新失败' : '创建失败')
    }
  }

  const handleSubmitForReview = async (id: number) => {
    try {
      await articleAPI.submitForReview(id)
      toast.success('已提交审核，审核员可在「审核管理 → 人工审核」中处理')
      fetchArticles()
    } catch (error: any) {
      const errMsg = error?.response?.data?.message?.message || error?.message || '提交失败'
      toast.error(errMsg)
    }
  }

  const handlePublish = async (id: number) => {
    try {
      await articleAPI.publish(id)
      toast.success('发布成功！')
      fetchArticles()
    } catch (error: any) {
      const raw =
        error?.response?.data?.message?.message ||
        error?.response?.data?.detail ||
        error?.message ||
        '发布失败'
      const errMsg = typeof raw === 'string' ? raw : '发布失败'
      if (
        errMsg.includes('不允许发布') ||
        errMsg.includes('请先通过审核') ||
        errMsg.includes('approved')
      ) {
        toast.error(
          '须先通过审核：请在稿件上点击「提交审核」，审核员在「审核管理 → 人工审核」通过后，再点击「发布」'
        )
      } else {
        toast.error(errMsg)
      }
    }
  }

  const handleViewDetail = async (record: Article) => {
    setSelectedArticle(record)
    setDetailVisible(true)

    try {
      // 同时加载稿件详情、审核记录和选题信息
      const [articleRes, reviewsRes] = await Promise.all([
        articleAPI.get(record.id).catch(() => record), // 获取完整的稿件信息，包括topic_id
        articleAPI.reviews(record.id).catch(() => ({ data: [] })),
        fetchTopicOptions().catch(() => {}) // 加载选题列表
      ])
      
      // 更新selectedArticle为包含topic_id的完整信息
      setSelectedArticle((articleRes as any).data || articleRes)
      setReviews((reviewsRes as any).data || [])
    } catch (error) {
      console.error('获取详情失败:', error)
    } finally {
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('已复制到剪贴板')
  }

  const uploadProps: UploadProps = {
    accept: 'image/jpeg,image/png,image/gif,image/webp',
    showUploadList: false,
    beforeUpload: async (file) => {
      const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
      if (!allowedTypes.includes(file.type)) {
        toast.error('仅支持 JPG/PNG/GIF/WebP 格式')
        return false
      }
      const maxSize = 5 * 1024 * 1024
      if (file.size > maxSize) {
        toast.error('图片大小不能超过 5MB')
        return false
      }
      try {
        const res = (await uploadAPI.image(file as File)) as { data?: { url?: string } }
        const url = res?.data?.url
        if (url) {
          setArticleImages((prev) => [...prev, url])
          toast.success('图片已上传')
        } else {
          toast.error('上传失败：未返回地址')
        }
      } catch (e) {
        toastUploadError(e)
      }
      return false
    },
  }

  const coverUploadProps: UploadProps = {
    accept: 'image/jpeg,image/png,image/gif,image/webp',
    showUploadList: false,
    beforeUpload: async (file) => {
      try {
        const res = (await uploadAPI.image(file as File)) as { data?: { url?: string } }
        const url = res?.data?.url
        if (url) {
          setCoverImage(url)
          toast.success('封面已设置')
        } else {
          toast.error('上传失败：未返回地址')
        }
      } catch (e) {
        toastUploadError(e)
      }
      return false
    },
  }

  const getStatusTag = (status: string) => {
    const config: Record<string, { color: string; text: string }> = {
      draft: { color: 'default', text: '草稿' },
      pending_review: { color: 'orange', text: '待审核' },
      reviewing: { color: 'processing', text: '审核中' },
      approved: { color: 'success', text: '已通过' },
      rejected: { color: 'error', text: '已驳回' },
      published: { color: 'blue', text: '已发布' },
    }
    const item = config[status] || config.draft
    return <Tag color={item.color}>{item.text}</Tag>
  }

  const getCategoryTag = (category?: string) => {
    if (!category) return null
    const colorMap: Record<string, string> = {
      '时政': 'red',
      '经济': 'gold',
      '社会': 'green',
      '科技': 'cyan',
      '文化': 'purple',
      '体育': 'orange',
      '娱乐': 'magenta',
      '国际': 'blue',
    }
    return <Tag color={colorMap[category] || 'default'}>{category}</Tag>
  }

  const columns: TableProps<Article>['columns'] = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      width: 300,
      render: (text: string, record: Article) => (
        <Space>
          <FileTextOutlined style={{ color: '#1890ff' }} />
          <Tooltip title={text}>
            <Text 
              strong 
              style={{ 
                maxWidth: 220, 
                overflow: 'hidden', 
                textOverflow: 'ellipsis', 
                whiteSpace: 'nowrap',
                display: 'inline-block',
                cursor: 'pointer'
              }}
              onClick={() => handleViewDetail(record)}
            >
              {text}
            </Text>
          </Tooltip>
        </Space>
      ),
    },
    {
      title: '作者',
      dataIndex: 'author',
      key: 'author',
      width: 100,
      render: (author: string) => author || <Text type="secondary">-</Text>,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 100,
      render: (category: string) => getCategoryTag(category) || '-',
    },
    {
      title: '关联选题',
      dataIndex: 'topic_id',
      key: 'topic',
      width: 150,
      render: (topicId: number) => {
        if (!topicId) return '-';
        const topic = topicOptions.find(t => t.id === topicId);
        return topic ? (
          <Tooltip title={topic.title}>
            <Tag color="blue" style={{ maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {topic.title}
            </Tag>
          </Tooltip>
        ) : (
          <Tag color="default">选题不存在</Tag>
        );
      },
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      width: 150,
      ellipsis: true,
      render: (tags: string[]) =>
        tags && tags.length > 0 ? (
          <Space wrap size={[4, 4]}>
            {tags.slice(0, 2).map((tag, index) => (
              <Tag key={index} style={{ marginRight: 0 }}>
                {tag}
              </Tag>
            ))}
            {tags.length > 2 && (
              <Tag style={{ marginRight: 0 }}>+{tags.length - 2}</Tag>
            )}
          </Space>
        ) : (
          '-'
        ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status),
      filters: [
        { text: '草稿', value: 'draft' },
        { text: '待审核', value: 'pending_review' },
        { text: '审核中', value: 'reviewing' },
        { text: '已通过', value: 'approved' },
        { text: '已驳回', value: 'rejected' },
        { text: '已发布', value: 'published' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 160,
      render: (date: string) => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {new Date(date).toLocaleString('zh-CN')}
        </Text>
      ),
      sorter: (a, b) => new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime(),
      defaultSortOrder: 'descend',
    },
    {
      title: '操作',
      key: 'action',
      width: 260,
      fixed: 'right' as const,
      render: (_: any, record: Article) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button type="text" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)} />
          </Tooltip>
          <Tooltip title="编辑">
            <Button type="text" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          {(record.status === 'draft' || record.status === 'rejected') && (
            <Tooltip title="提交审核">
              <Button
                type="text"
                icon={<AuditOutlined style={{ color: '#1890ff' }} />}
                onClick={() => handleSubmitForReview(record.id)}
              />
            </Tooltip>
          )}
          {record.status === 'approved' && (
            <Tooltip title="发布（需已通过审核）">
              <Button
                type="text"
                icon={<SendOutlined style={{ color: '#52c41a' }} />}
                onClick={() => handlePublish(record.id)}
              />
            </Tooltip>
          )}
          {record.status === 'published' && (
            <Tooltip title="复制链接">
              <Button
                type="text"
                icon={<CopyOutlined />}
                onClick={() => copyToClipboard(`${record.title}`)}
              />
            </Tooltip>
          )}
          <Popconfirm
            title="确认删除"
            description="删除后无法恢复，是否继续？"
            onConfirm={() => handleDelete(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // Stats
  const stats = {
    total: articles.length,
    draft: articles.filter(a => a.status === 'draft').length,
    pending: articles.filter(a => ['pending_review', 'reviewing'].includes(a.status)).length,
    published: articles.filter(a => a.status === 'published').length,
  }

  // Quick status filter options
  const statusOptions = [
    { label: '全部', value: undefined },
    { label: '草稿', value: 'draft', count: stats.draft },
    { label: '待审核', value: 'pending_review', count: stats.pending },
    { label: '已发布', value: 'published', count: stats.published },
  ]

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-in-out' }}>
      {/* Stats Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: 8 }}>
            <Statistic
              title="总稿件数"
              value={stats.total}
              prefix={<FileTextOutlined style={{ color: '#1890ff' }} />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: 8 }}>
            <Statistic
              title="草稿"
              value={stats.draft}
              prefix={<EditOutlined style={{ color: '#8c8c8c' }} />}
              valueStyle={{ color: '#8c8c8c' }}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: 8 }}>
            <Statistic
              title="待审核"
              value={stats.pending}
              prefix={<ClockCircleOutlined style={{ color: '#faad14' }} />}
              valueStyle={{ color: '#faad14' }}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: 8 }}>
            <Statistic
              title="已发布"
              value={stats.published}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
              loading={loading}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Card */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <FileTextOutlined style={{ fontSize: 18, color: 'white' }} />
            </div>
            <span style={{ fontWeight: 600, fontSize: 16 }}>稿件管理</span>
          </div>
        }
        extra={
          <Space>
            <Segmented
              options={[
                { label: '表格', value: 'table' },
                { label: '列表', value: 'list' },
              ]}
              value={viewMode}
              onChange={(value) => setViewMode(value as 'table' | 'list')}
              size="small"
            />
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建稿件
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchArticles} loading={loading}>
              刷新
            </Button>
          </Space>
        }
        style={{ borderRadius: 12 }}
      >
        <Alert
          type="info"
          showIcon
          closable
          message="发布须先过审：草稿请点击「提交审核」（或详情内按钮），审核员登录后在「审核管理 → 人工审核」处理；状态为「已通过」后再点「发布」。"
          style={{ marginBottom: 16, borderRadius: 8 }}
        />
        {/* Quick Status Filter */}
        <div style={{ marginBottom: 16 }}>
          <Space wrap size="middle">
            {statusOptions.map(opt => (
              <Button
                key={opt.value || 'all'}
                type={statusFilter === opt.value ? 'primary' : 'default'}
                onClick={() => setStatusFilter(opt.value)}
                style={{ borderRadius: 8 }}
              >
                {opt.label}
                {opt.count !== undefined && (
                  <Badge count={opt.count} style={{ marginLeft: 8 }} size="small" />
                )}
              </Button>
            ))}
          </Space>
        </div>

        {/* Search and Filters */}
        <Row gutter={[12, 12]} align="middle" style={{ marginBottom: 16 }}>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Input.Search
              placeholder="搜索标题或内容"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onSearch={handleSearch}
              allowClear
              prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
            />
          </Col>
          <Col xs={24} sm={12} md={16} lg={18}>
            <Space wrap>
              <Select
                placeholder="状态筛选"
                allowClear
                style={{ minWidth: 120 }}
                value={statusFilter}
                onChange={setStatusFilter}
              >
                <Option value="draft">草稿</Option>
                <Option value="pending_review">待审核</Option>
                <Option value="reviewing">审核中</Option>
                <Option value="approved">已通过</Option>
                <Option value="rejected">已驳回</Option>
                <Option value="published">已发布</Option>
              </Select>
              <Select
                placeholder="分类筛选"
                allowClear
                style={{ minWidth: 120 }}
                value={categoryFilter}
                onChange={setCategoryFilter}
              >
                <Option value="时政">时政</Option>
                <Option value="经济">经济</Option>
                <Option value="社会">社会</Option>
                <Option value="科技">科技</Option>
                <Option value="文化">文化</Option>
                <Option value="体育">体育</Option>
                <Option value="娱乐">娱乐</Option>
                <Option value="国际">国际</Option>
              </Select>
              {hasActiveFilters && (
                <Button 
                  icon={<ClearOutlined />} 
                  onClick={resetFilters}
                  type="text"
                  danger
                >
                  重置
                </Button>
              )}
            </Space>
          </Col>
        </Row>

        {/* Active Filters Summary */}
        {hasActiveFilters && (
          <Alert
            message={
              <Space>
                <Text>当前筛选：</Text>
                {searchText && <Tag closable onClose={() => setSearchText('')}>搜索: {searchText}</Tag>}
                {statusFilter && <Tag closable onClose={() => setStatusFilter(undefined)}>状态: {[statusFilter === 'draft' ? '草稿' : statusFilter === 'pending_review' ? '待审核' : statusFilter === 'reviewing' ? '审核中' : statusFilter === 'approved' ? '已通过' : statusFilter === 'rejected' ? '已驳回' : '已发布']}</Tag>}
                {categoryFilter && <Tag closable onClose={() => setCategoryFilter(undefined)}>分类: {categoryFilter}</Tag>}
              </Space>
            }
            type="info"
            style={{ marginBottom: 16, borderRadius: 8 }}
            showIcon
          />
        )}

        {/* Content */}
        {initialLoading ? (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <Spin size="large" />
            <Text type="secondary" style={{ display: 'block', marginTop: 16 }}>
              加载中...
            </Text>
          </div>
        ) : articles.length === 0 ? (
          <Empty 
            description={
              hasActiveFilters ? '没有符合筛选条件的稿件' : '暂无稿件，点击上方按钮新建'
            }
            style={{ padding: '60px 0' }}
          >
            {hasActiveFilters ? (
              <Button type="primary" onClick={resetFilters}>
                重置筛选
              </Button>
            ) : (
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                新建稿件
              </Button>
            )}
          </Empty>
        ) : viewMode === 'table' ? (
          <Table
            columns={columns}
            dataSource={articles}
            rowKey="id"
            loading={loading}
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
              showQuickJumper: true,
            }}
            scroll={{ x: 1200 }}
          />
        ) : (
          <List
            dataSource={articles}
            loading={loading}
            renderItem={(article) => (
              <List.Item
                key={article.id}
                actions={[
                  <Button type="text" icon={<EyeOutlined />} onClick={() => handleViewDetail(article)} />,
                  <Button type="text" icon={<EditOutlined />} onClick={() => handleEdit(article)} />,
                  (article.status === 'draft' || article.status === 'rejected') && (
                    <Tooltip title="提交审核后，审核员可在审核端看到">
                      <Button
                        type="text"
                        icon={<AuditOutlined style={{ color: '#1890ff' }} />}
                        onClick={() => handleSubmitForReview(article.id)}
                      />
                    </Tooltip>
                  ),
                  article.status === 'approved' && (
                    <Tooltip title="发布上线（需已通过审核）">
                      <Button
                        type="text"
                        icon={<SendOutlined style={{ color: '#52c41a' }} />}
                        onClick={() => handlePublish(article.id)}
                      />
                    </Tooltip>
                  ),
                  <Popconfirm
                    title="确认删除"
                    onConfirm={() => handleDelete(article.id)}
                  >
                    <Button type="text" danger icon={<DeleteOutlined />} />
                  </Popconfirm>,
                ].filter(Boolean)}
                style={{
                  padding: '16px 24px',
                  background: '#fafafa',
                  borderRadius: 8,
                  marginBottom: 8,
                }}
              >
                <List.Item.Meta
                  avatar={
                    <Avatar
                      style={{
                        background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)',
                      }}
                      icon={<FileTextOutlined />}
                    />
                  }
                  title={
                    <Space>
                      <Text strong>{article.title}</Text>
                      {getStatusTag(article.status)}
                      <Badge count={`v${article.version}`} style={{ backgroundColor: '#52c41a' }} />
                    </Space>
                  }
                  description={
                    <Space direction="vertical" size={4}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {article.author || '未知作者'} · {getCategoryTag(article.category)} · {new Date(article.updated_at).toLocaleString('zh-CN')}
                      </Text>
                      {article.abstract && (
                        <Text 
                          type="secondary" 
                          style={{ fontSize: 12 }}
                          ellipsis
                        >
                          {article.abstract}
                        </Text>
                      )}
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={
          <Space>
            <EditOutlined />
            {editingArticle ? '编辑稿件' : '新建稿件'}
          </Space>
        }
        open={modalVisible}
        onOk={() => form.submit()}
        onCancel={() => setModalVisible(false)}
        width={800}
        okText={editingArticle ? '保存' : '创建'}
        cancelText="取消"
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="title"
            label="标题"
            rules={[{ required: true, message: '请输入标题' }]}
          >
            <Input placeholder="请输入稿件标题" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="author" label="作者">
                <Input placeholder="请输入作者" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="category" label="分类">
                <Select placeholder="选择分类" allowClear>
                  <Option value="时政">时政</Option>
                  <Option value="经济">经济</Option>
                  <Option value="社会">社会</Option>
                  <Option value="科技">科技</Option>
                  <Option value="文化">文化</Option>
                  <Option value="体育">体育</Option>
                  <Option value="娱乐">娱乐</Option>
                  <Option value="国际">国际</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="abstract" label="摘要">
            <TextArea rows={2} placeholder="请输入摘要" />
          </Form.Item>
          <Form.Item name="topic_id" label="关联选题策划（可选）">
            <Select
              allowClear
              loading={topicLoading}
              placeholder="不选择则不关联选题"
              options={topicOptions.map((topic) => ({
                value: topic.id,
                label: topic.title,
              }))}
            />
          </Form.Item>
          <Form.Item label="主题封面（读者端）">
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Space wrap>
                <Upload {...coverUploadProps}>
                  <Button icon={<PictureOutlined />} type="dashed">
                    上传封面图
                  </Button>
                </Upload>
                {coverImage && (
                  <Button type="link" danger onClick={() => setCoverImage('')}>
                    清除封面
                  </Button>
                )}
              </Space>
              {coverImage ? (
                <div
                  style={{
                    position: 'relative',
                    border: '1px solid #f0f0f0',
                    borderRadius: 8,
                    overflow: 'hidden',
                    maxWidth: 360,
                  }}
                >
                  <img
                    src={coverImage}
                    alt="封面预览"
                    style={{ width: '100%', height: 160, objectFit: 'cover', display: 'block' }}
                  />
                </div>
              ) : (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  未设置时使用「配图」中的第一张作为列表与详情头图；可单独上传以固定展示。
                </Text>
              )}
            </Space>
          </Form.Item>
          <Form.Item
            label="正文配图"
            tooltip="上传后点「插入正文」可在稿件中显示图片；读者端会按 Markdown 图片格式渲染"
          >
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Upload {...uploadProps}>
                <Button icon={<PictureOutlined />} type="dashed">
                  上传配图（需登录）
                </Button>
              </Upload>
              <Space wrap size={[8, 8]}>
                {articleImages.map((u) => (
                  <div
                    key={u}
                    style={{
                      position: 'relative',
                      border: '1px solid #f0f0f0',
                      borderRadius: 8,
                      padding: 4,
                      width: 100,
                    }}
                  >
                    <img
                      src={u}
                      alt=""
                      style={{ width: 88, height: 88, objectFit: 'cover', borderRadius: 6, display: 'block' }}
                    />
                    <Button
                      type="link"
                      size="small"
                      block
                      style={{ padding: '0 0 4px', fontSize: 12, height: 'auto' }}
                      onClick={() => {
                        const cur = (form.getFieldValue('content') as string) || ''
                        form.setFieldsValue({
                          content: `${cur}${cur.trim() ? '\n\n' : ''}![](${u})\n\n`,
                        })
                        toast.success('已插入到正文（读者端显示为图片）')
                      }}
                    >
                      插入正文
                    </Button>
                    <Button
                      type="text"
                      danger
                      size="small"
                      icon={<CloseCircleOutlined />}
                      onClick={() => setArticleImages((p) => p.filter((x) => x !== u))}
                      style={{ position: 'absolute', top: 0, right: 0 }}
                    />
                  </div>
                ))}
              </Space>
            </Space>
          </Form.Item>
          <Form.Item
            name="content"
            label="内容"
            rules={[{ required: true, message: '请输入内容' }]}
          >
            <TextArea rows={8} placeholder="请输入稿件内容" />
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Input placeholder="多个标签用逗号分隔" />
          </Form.Item>
          <Form.Item name="status" label="状态" initialValue="draft">
            <Select placeholder="选择状态">
              <Option value="draft">草稿</Option>
              <Option value="pending_review">待审核</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Drawer */}
      <Drawer
        title={
          <Space>
            <EyeOutlined />
            稿件详情
          </Space>
        }
        placement="right"
        width={700}
        onClose={() => setDetailVisible(false)}
        open={detailVisible}
        extra={
          selectedArticle &&
          (selectedArticle.status === 'draft' ||
            selectedArticle.status === 'rejected' ||
            selectedArticle.status === 'approved') && (
            <Space>
              {(selectedArticle.status === 'draft' || selectedArticle.status === 'rejected') && (
                <>
                  <Button
                    type="primary"
                    icon={<EditOutlined />}
                    onClick={() => {
                      setDetailVisible(false)
                      handleEdit(selectedArticle)
                    }}
                  >
                    编辑
                  </Button>
                  <Button
                    type="primary"
                    icon={<AuditOutlined />}
                    onClick={() => handleSubmitForReview(selectedArticle.id)}
                  >
                    提交审核
                  </Button>
                </>
              )}
              {selectedArticle.status === 'approved' && (
                <Button type="primary" icon={<SendOutlined />} onClick={() => handlePublish(selectedArticle.id)}>
                  发布上线
                </Button>
              )}
            </Space>
          )
        }
      >
        {selectedArticle && (
          <Tabs 
            defaultActiveKey="1" 
            size="large"
            items={[
              {
                key: '1',
                label: '基本信息',
                children: (
                  <>
                    <Descriptions column={1} bordered size="small">
                      <Descriptions.Item label="标题">
                        <Text strong>{selectedArticle.title}</Text>
                      </Descriptions.Item>
                      <Descriptions.Item label="作者">{selectedArticle.author || '-'}</Descriptions.Item>
                      <Descriptions.Item label="分类">{getCategoryTag(selectedArticle.category) || '-'}</Descriptions.Item>
                      <Descriptions.Item label="关联选题">
                        {selectedArticle.topic_id ? (
                          <>
                            {topicOptions.find(t => t.id === selectedArticle.topic_id) ? (
                              <Tag color="blue">
                                {topicOptions.find(t => t.id === selectedArticle.topic_id)?.title}
                              </Tag>
                            ) : (
                              <Tag color="default">选题不存在</Tag>
                            )}
                          </>
                        ) : (
                          '-' 
                        )}
                      </Descriptions.Item>
                      <Descriptions.Item label="主题封面">
                        {selectedArticle.cover_image ? (
                          <img
                            src={selectedArticle.cover_image}
                            alt=""
                            style={{ maxWidth: 240, maxHeight: 120, objectFit: 'cover', borderRadius: 8 }}
                          />
                        ) : (
                          <Text type="secondary">未单独设置（读者端优先使用配图首张）</Text>
                        )}
                      </Descriptions.Item>
                      <Descriptions.Item label="状态">{getStatusTag(selectedArticle.status)}</Descriptions.Item>
                      <Descriptions.Item label="版本">v{selectedArticle.version}</Descriptions.Item>
                      <Descriptions.Item label="创建时间">
                        {new Date(selectedArticle.created_at).toLocaleString('zh-CN')}
                      </Descriptions.Item>
                      <Descriptions.Item label="更新时间">
                        {new Date(selectedArticle.updated_at).toLocaleString('zh-CN')}
                      </Descriptions.Item>
                      {selectedArticle.published_at && (
                        <Descriptions.Item label="发布时间">
                          {new Date(selectedArticle.published_at).toLocaleString('zh-CN')}
                        </Descriptions.Item>
                      )}
                    </Descriptions>

                    <Divider />

                    <Title level={5}>摘要</Title>
                    <Paragraph 
                      style={{ 
                        background: '#fafafa', 
                        padding: 16, 
                        borderRadius: 8,
                        whiteSpace: 'pre-wrap'
                      }}
                    >
                      {selectedArticle.abstract || '无摘要'}
                    </Paragraph>

                    <Divider />

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <Title level={5} style={{ margin: 0 }}>内容</Title>
                      <Button 
                        type="text" 
                        icon={<CopyOutlined />} 
                        size="small"
                        onClick={() => copyToClipboard(selectedArticle.content)}
                      >
                        复制
                      </Button>
                    </div>
                    <Paragraph style={{ 
                      background: '#fafafa', 
                      padding: 16, 
                      borderRadius: 8,
                      whiteSpace: 'pre-wrap',
                      maxHeight: 300,
                      overflow: 'auto'
                    }}>
                      {selectedArticle.content}
                    </Paragraph>

                    {selectedArticle.tags && selectedArticle.tags.length > 0 && (
                      <>
                        <Divider />
                        <Title level={5}>标签</Title>
                        <Space wrap>
                          {selectedArticle.tags.map((tag, index) => (
                            <Tag key={index} color="blue" icon={<TagOutlined />}>
                              {tag}
                            </Tag>
                          ))}
                        </Space>
                      </>
                    )}
                  </>
                )
              },
              {
                key: '2',
                label: '审核记录',
                children: (
                  <>
                    {reviews.length > 0 ? (
                      <Timeline>
                        {reviews.map((review) => (
                          <Timeline.Item
                            key={review.id}
                            color={
                              review.result === 'approved'
                                ? 'green'
                                : review.result === 'rejected'
                                ? 'red'
                                : 'blue'
                            }
                          >
                            <div>
                              <Space>
                                <Text strong>{review.reviewer}</Text>
                                <Tag
                                  color={
                                    review.result === 'approved'
                                      ? 'success'
                                      : review.result === 'rejected'
                                      ? 'error'
                                      : 'processing'
                                  }
                                >
                                  {review.result === 'approved'
                                    ? '通过'
                                    : review.result === 'rejected'
                                    ? '驳回'
                                    : '需修改'}
                                </Tag>
                              </Space>
                              <br />
                              <Text type="secondary">
                                {new Date(review.created_at).toLocaleString('zh-CN')}
                              </Text>
                              {review.comment && (
                                <>
                                  <br />
                                  <Text style={{ 
                                    display: 'block', 
                                    marginTop: 8,
                                    padding: 8,
                                    background: '#fafafa',
                                    borderRadius: 4
                                  }}>
                                    审核意见：{review.comment}
                                  </Text>
                                </>
                              )}
                            </div>
                          </Timeline.Item>
                        ))}
                      </Timeline>
                    ) : (
                      <Empty description="暂无审核记录" />
                    )}
                  </>
                )
              }
            ]}
          />
        )}
      </Drawer>
    </div>
  )
}

export default Articles
