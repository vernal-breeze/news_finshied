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
  Drawer,
  Descriptions,
  Progress,
  Divider,
  Badge,
  Empty,
  Spin,
  Alert,
  Segmented,
  Dropdown,
} from 'antd'
import type { TableProps, MenuProps } from 'antd'
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  SearchOutlined,
  ReloadOutlined,
  RobotOutlined,
  LinkOutlined,
  FileTextOutlined,
  BulbOutlined,
  GlobalOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloudDownloadOutlined,
  ClearOutlined,
  BarChartOutlined,
} from '@ant-design/icons'
import { clueAPI, articleAPI, unwrapPaginated, unwrapSearchInfoResults } from '../../services/api'
import { normalizeExternalUrl } from '../../utils/url'
import type { NewsClue } from '../../types'
import { toast } from '../../components/common/Toast'

const { Title, Text, Paragraph } = Typography
const { Option } = Select
const { TextArea } = Input

// 相对时间
const relativeTime = (dateStr: string): string => {
  if (!dateStr) return '-'
  const diff = Date.now() - new Date(dateStr).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return '刚刚'
  if (m < 60) return `${m}分钟前`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}小时前`
  const d = Math.floor(h / 24)
  if (d < 7) return `${d}天前`
  return new Date(dateStr).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

// 紧凑评分条
const CompactScore = ({ score }: { score: number }) => {
  const color = score >= 80 ? '#52c41a' : score >= 60 ? '#faad14' : '#ff4d4f'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 80 }}>
      <div style={{ flex: 1, height: 4, background: '#f0f0f0', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{ width: `${score}%`, height: '100%', background: color, borderRadius: 2 }} />
      </div>
      <Text style={{ fontSize: 11, color: '#888', minWidth: 24 }}>{score}</Text>
    </div>
  )
}

const Clues = () => {
  const [clues, setClues] = useState<NewsClue[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingClue, setEditingClue] = useState<NewsClue | null>(null)
  const [detailVisible, setDetailVisible] = useState(false)
  const [selectedClue, setSelectedClue] = useState<NewsClue | null>(null)
  const [form] = Form.useForm()
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined)
  const [dateRange, setDateRange] = useState<[string | null, string | null]>([null, null])
  const [analyzing, setAnalyzing] = useState<number | null>(null)
  const [collectModalVisible, setCollectModalVisible] = useState(false)
  const [collectForm] = Form.useForm()
  const [collecting, setCollecting] = useState(false)
  const [analysisModalVisible, setAnalysisModalVisible] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<any>(null)
  const [searchModalVisible, setSearchModalVisible] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [searchSource, setSearchSource] = useState('news')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [searchInfoAttempted, setSearchInfoAttempted] = useState(false)
  const [searchMaxResults, setSearchMaxResults] = useState(15)
  const [exactMatch, setExactMatch] = useState(false)
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [batchDeleteLoading, setBatchDeleteLoading] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(15)

  const fetchClues = useCallback(async () => {
    setLoading(true)
    try {
      const params: any = {
        page: currentPage,
        page_size: pageSize
      }
      if (statusFilter) params.status = statusFilter
      if (categoryFilter) params.category = categoryFilter
      if (searchText) params.search = searchText
      if (dateRange[0] && dateRange[1]) {
        params.start_date = dateRange[0]
        params.end_date = dateRange[1]
      }
      const data = await clueAPI.list(params)
      const { items: list, total: totalCount } = unwrapPaginated<NewsClue>(data)
      setClues(list)
      setTotal(totalCount)
    } catch (error) {
      toast.error('获取线索列表失败')
    } finally {
      setLoading(false)
      setInitialLoading(false)
    }
  }, [statusFilter, categoryFilter, searchText, dateRange, currentPage, pageSize])

  useEffect(() => {
    fetchClues()
  }, [fetchClues])

  const resetFilters = () => {
    setSearchText('')
    setStatusFilter(undefined)
    setCategoryFilter(undefined)
    setDateRange([null, null])
    toast.info('筛选条件已重置')
  }

  const hasActiveFilters = searchText || statusFilter || categoryFilter || dateRange[0]

  const handleSearch = () => fetchClues()

  const handleCreate = () => {
    setEditingClue(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (record: NewsClue) => {
    setEditingClue(record)
    form.setFieldsValue({ ...record, keywords: record.keywords?.join(', ') })
    setModalVisible(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await clueAPI.delete(id)
      toast.success('删除成功')
      fetchClues()
    } catch (error) {
      toast.error('删除失败')
    }
  }

  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) { toast.warning('请先选择要删除的线索'); return }
    setBatchDeleteLoading(true)
    try {
      const ids = selectedRowKeys.map(k => Number(k))
      await clueAPI.batchDelete(ids)
      toast.success(`成功删除 ${ids.length} 条线索`)
      setSelectedRowKeys([])
      fetchClues()
    } catch (error) {
      toast.error('批量删除失败')
    } finally {
      setBatchDeleteLoading(false)
    }
  }

  const handleSubmit = async (values: any) => {
    try {
      const data = {
        ...values,
        keywords: values.keywords
          ? values.keywords.split(',').map((k: string) => k.trim()).filter((k: string) => k)
          : [],
      }
      if (editingClue) {
        await clueAPI.update(editingClue.id, data)
        toast.success('更新成功')
      } else {
        await clueAPI.create(data)
        toast.success('创建成功')
      }
      setModalVisible(false)
      fetchClues()
    } catch (error) {
      toast.error(editingClue ? '更新失败' : '创建失败')
    }
  }

  const handleAnalyze = async (clue: NewsClue) => {
    setAnalyzing(clue.id)
    try {
      const result = await clueAPI.analyze(clue.id)
      setAnalysisResult((result as any).data)
      setAnalysisModalVisible(true)
      toast.success('AI分析完成')
    } catch (error) {
      toast.error('AI分析失败')
    } finally {
      setAnalyzing(null)
    }
  }

  const openSearchModal = (clue: NewsClue) => {
    setSelectedClue(clue)
    setSearchKeyword(clue.title)
    setSearchSource('all')
    setSearchResults([])
    setSearchInfoAttempted(false)
    setSearchModalVisible(true)
  }

  const handleSearchInfo = async (keyword: string) => {
    if (!selectedClue) return
    setSearchLoading(true)
    try {
      const result = await clueAPI.searchInfo(selectedClue.id, {
        keyword, engine: 'duckduckgo', source: searchSource, max_results: searchMaxResults, exact_match: exactMatch,
      })
      setSearchResults(unwrapSearchInfoResults(result))
    } catch (error) {
      toast.error('搜索资料失败，请稍后重试')
      setSearchResults([])
    } finally {
      setSearchInfoAttempted(true)
      setSearchLoading(false)
    }
  }

  const handleCreateArticle = async (clue: NewsClue) => {
    try {
      await articleAPI.create({
        title: clue.title,
        content: clue.content || '',
        abstract: clue.content?.slice(0, 200) || '',
        category: clue.category || '新闻',
        tags: clue.keywords || [],
        status: 'draft',
        author: '编辑',
        clue_id: clue.id,
      })
      toast.success('稿件创建成功！可前往稿件管理页面查看')
    } catch (error) {
      toast.error('创建稿件失败')
    }
  }

  const handleCollect = async (values: any) => {
    setCollecting(true)
    try {
      const maxN = Number(values.maxResults)
      await clueAPI.collectMultichannel(
        String(values.keywords || '').trim(),
        Array.isArray(values.channels) ? values.channels : [],
        values.timeRange,
        Number.isFinite(maxN) && maxN > 0 ? maxN : 15
      )
      await fetchClues()
      toast.success('采集完成，列表已刷新')
      setCollectModalVisible(false)
      collectForm.resetFields()
    } catch (error: unknown) {
      const ax = error as { response?: { data?: { detail?: string; message?: string } } }
      const d = ax.response?.data
      const msg =
        (typeof d?.detail === 'string' && d.detail) ||
        (typeof d?.message === 'string' && d.message) ||
        '采集失败，请检查网络或稍后重试'
      toast.error(msg)
    } finally {
      setCollecting(false)
    }
  }

  const getStatusTag = (status: string) => {
    const config: Record<string, { color: string; text: string }> = {
      pending: { color: 'orange', text: '待处理' },
      processed: { color: 'green', text: '已处理' },
      archived: { color: 'default', text: '已归档' },
    }
    const item = config[status] || config.pending
    return <Tag color={item.color} style={{ margin: 0 }}>{item.text}</Tag>
  }

  const getCategoryTag = (category?: string) => {
    if (!category) return null
    const colorMap: Record<string, string> = {
      '时政': 'red', '经济': 'gold', '社会': 'green', '科技': 'cyan',
      '文化': 'purple', '体育': 'orange', '娱乐': 'magenta', '国际': 'blue',
    }
    return <Tag color={colorMap[category] || 'default'} style={{ margin: 0 }}>{category}</Tag>
  }

  const stats = {
    total: total,
    pending: clues.filter(c => c.status === 'pending').length,
    processed: clues.filter(c => c.status === 'processed').length,
    highValue: clues.filter(c => (c.news_value_score || 0) >= 80).length,
  }

  const columns: TableProps<NewsClue>['columns'] = [
    {
      title: '标题 / 来源',
      key: 'title',
      render: (_: any, record: NewsClue) => (
        <div>
          <Space>
            <BulbOutlined style={{ color: '#faad14', flexShrink: 0 }} />
            <Tooltip title={record.title}>
              {record.source_url ? (
                <a href={normalizeExternalUrl(record.source_url)} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}>
                  <Text strong style={{ maxWidth: 260, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#1890ff', textDecoration: 'none' }}>
                    {record.title}
                  </Text>
                </a>
              ) : (
                <Text strong style={{ maxWidth: 260, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {record.title}
                </Text>
              )}
            </Tooltip>
            {record.source_url && (
              <a href={normalizeExternalUrl(record.source_url)} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()} title="打开来源">
                <LinkOutlined style={{ color: '#1890ff', fontSize: 12 }} />
              </a>
            )}
          </Space>
          <div style={{ marginTop: 2 }}>
            <Tag icon={<GlobalOutlined />} color="blue" style={{ margin: 0, fontSize: 11 }}>
              {record.source && record.source.length > 10 ? record.source.slice(0, 10) + '..' : (record.source || '未知')}
            </Tag>
          </div>
        </div>
      ),
      width: 300,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 80,
      render: (cat: string) => getCategoryTag(cat) || <Text type="secondary">-</Text>,
    },
    {
      title: '新闻价值',
      dataIndex: 'news_value_score',
      key: 'news_value_score',
      width: 110,
      render: (score: number) => score ? <CompactScore score={score} /> : <Text type="secondary">-</Text>,
    },
    {
      title: '传播潜力',
      dataIndex: 'propagation_potential',
      key: 'propagation_potential',
      width: 110,
      render: (score: number) => score ? <CompactScore score={score} /> : <Text type="secondary">-</Text>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: string, record: NewsClue) => {
        const items: MenuProps['items'] = [
          { key: 'pending', label: '待处理' },
          { key: 'processed', label: '已处理' },
          { key: 'archived', label: '已归档' },
        ]
        return (
          <Dropdown menu={{ items, onClick: ({ key }) => {
            clueAPI.update(record.id, { status: key }).then(() => fetchClues()).catch(() => toast.error('状态更新失败'))
          }}} trigger={['click']}>
            <div style={{ cursor: 'pointer' }}>{getStatusTag(status)}</div>
          </Dropdown>
        )
      },
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 90,
      render: (date: string) => (
        <Text type="secondary" style={{ fontSize: 12 }}>{relativeTime(date)}</Text>
      ),
      sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      defaultSortOrder: 'descend',
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_: any, record: NewsClue) => (
        <Space size={2}>
          <Tooltip title="详情">
            <Button type="text" icon={<EyeOutlined />} size="small" onClick={() => { setSelectedClue(record); setDetailVisible(true) }} />
          </Tooltip>
          <Tooltip title="编辑">
            <Button type="text" icon={<EditOutlined />} size="small" onClick={() => handleEdit(record)} />
          </Tooltip>
          <Tooltip title="生成稿件">
            <Button type="text" icon={<FileTextOutlined />} size="small" onClick={() => handleCreateArticle(record)} />
          </Tooltip>
          <Tooltip title="AI分析">
            <Button type="text" icon={<RobotOutlined />} size="small" onClick={() => handleAnalyze(record)} loading={analyzing === record.id} />
          </Tooltip>
          <Popconfirm title="确认删除" description="删除后无法恢复" onConfirm={() => handleDelete(record.id)} okText="确认" cancelText="取消" okButtonProps={{ danger: true }}>
            <Button type="text" danger icon={<DeleteOutlined />} size="small" />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-in-out', padding: 0, minHeight: '100%' }}>
      {/* 统计卡片 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
        {[
          { label: '总线索', value: stats.total, icon: <BulbOutlined />, color: '#faad14', bg: 'linear-gradient(135deg, #fff7e6, #fff)' },
          { label: '待处理', value: stats.pending, icon: <ExclamationCircleOutlined />, color: '#fa8c16', bg: 'linear-gradient(135deg, #fff7e6, #fff)' },
          { label: '已处理', value: stats.processed, icon: <CheckCircleOutlined />, color: '#52c41a', bg: 'linear-gradient(135deg, #f6ffed, #fff)' },
          { label: '高价值', value: stats.highValue, icon: <BarChartOutlined />, color: '#722ed1', bg: 'linear-gradient(135deg, #f9f0ff, #fff)' },
        ].map((s, i) => (
          <Col xs={12} sm={6} key={i}>
            <Card
              size="small"
              style={{ borderRadius: 10, border: 'none', boxShadow: '0 1px 4px rgba(0,0,0,0.06)', background: s.bg }}
              styles={{ body: { padding: '12px 16px' } }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>{s.label}</Text>
                  <div style={{ fontSize: 24, fontWeight: 700, color: s.color, lineHeight: 1.2, marginTop: 2 }}>{stats.total === 0 && !loading ? '-' : s.value}</div>
                </div>
                <div style={{ fontSize: 22, color: s.color, opacity: 0.8 }}>{s.icon}</div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 主表格卡片 */}
      <Card
        title={
          <Space>
            <BulbOutlined style={{ color: '#faad14', fontSize: 16 }} />
            <span style={{ fontWeight: 600 }}>新闻线索</span>
            {stats.pending > 0 && <Badge count={stats.pending} style={{ marginLeft: 4 }} overflowCount={99} />}
          </Space>
        }
        extra={
          <Space>
            {selectedRowKeys.length > 0 && (
              <Popconfirm title={`确认删除选中的 ${selectedRowKeys.length} 条线索？`} onConfirm={handleBatchDelete} okText="确认删除" cancelText="取消" okButtonProps={{ danger: true, loading: batchDeleteLoading }}>
                <Button danger size="small" icon={<DeleteOutlined />}>批量删除 ({selectedRowKeys.length})</Button>
              </Popconfirm>
            )}
            <Button size="small" icon={<CloudDownloadOutlined />} onClick={() => setCollectModalVisible(true)}>采集</Button>
            <Button type="primary" size="small" icon={<PlusOutlined />} onClick={handleCreate}>新建</Button>
            <Button size="small" icon={<ReloadOutlined />} onClick={fetchClues} loading={loading}>刷新</Button>
          </Space>
        }
        style={{ borderRadius: 12, border: 'none', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
        styles={{ body: { padding: '0 16px 16px' } }}
      >
        {/* 搜索筛选栏 */}
        <div style={{ padding: '12px 0', display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', borderBottom: '1px solid #f0f0f0', marginBottom: 12 }}>
          <Input.Search
            placeholder="搜索标题、内容或关键词"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onSearch={handleSearch}
            allowClear
            style={{ width: 220 }}
            size="small"
          />
          <Select size="small" placeholder="状态" allowClear style={{ width: 100 }} value={statusFilter} onChange={setStatusFilter}>
            <Option value="pending">待处理</Option>
            <Option value="processed">已处理</Option>
            <Option value="archived">已归档</Option>
          </Select>
          <Select size="small" placeholder="分类" allowClear style={{ width: 90 }} value={categoryFilter} onChange={setCategoryFilter}>
            {['时政','经济','社会','科技','文化','体育','娱乐','国际'].map(c => <Option key={c} value={c}>{c}</Option>)}
          </Select>
          {hasActiveFilters && (
            <Button size="small" type="text" danger icon={<ClearOutlined />} onClick={resetFilters}>重置</Button>
          )}
        </div>

        {/* 筛选提示 */}
        {hasActiveFilters && (
          <Alert
            message={<Space size={4} wrap>
              <Text type="secondary">筛选：</Text>
              {searchText && <Tag closable onClose={() => setSearchText('')}>{searchText}</Tag>}
              {statusFilter && <Tag closable onClose={() => setStatusFilter(undefined)}>{statusFilter === 'pending' ? '待处理' : statusFilter === 'processed' ? '已处理' : '已归档'}</Tag>}
              {categoryFilter && <Tag closable onClose={() => setCategoryFilter(undefined)}>{categoryFilter}</Tag>}
            </Space>}
            type="info" style={{ marginBottom: 12, borderRadius: 8 }} showIcon={false}
          />
        )}

        {/* 表格 */}
        {initialLoading ? (
          <div style={{ textAlign: 'center', padding: '60px 0' }}><Spin size="large" /><Text type="secondary" style={{ display: 'block', marginTop: 16 }}>加载中...</Text></div>
        ) : clues.length === 0 ? (
          <Empty description={hasActiveFilters ? '没有符合筛选条件的线索' : '暂无线索'} image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ padding: '40px 0' }}>
            {hasActiveFilters ? <Button type="primary" size="small" onClick={resetFilters}>重置筛选</Button>
              : <Button type="primary" size="small" icon={<PlusOutlined />} onClick={handleCreate}>新建线索</Button>}
          </Empty>
        ) : (
          <Table
            columns={columns}
            dataSource={clues}
            rowKey="id"
            loading={loading}
            size="small"
            rowSelection={{ selectedRowKeys, onChange: (keys) => setSelectedRowKeys(keys) }}
            pagination={{
              current: currentPage,
              pageSize: pageSize,
              total: total,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条`,
              onChange: (page, size) => {
                setCurrentPage(page);
                setPageSize(size);
              },
              onShowSizeChange: (_page, size) => {
                setPageSize(size);
                setCurrentPage(1);
              }
            }}
            scroll={{ x: 900 }}
            rowClassName={(record) => record.status === 'pending' ? 'clue-row-pending' : ''}
          />
        )}
      </Card>

      {/* 新建/编辑弹窗 */}
      <Modal
        title={<Space><EditOutlined />{editingClue ? '编辑线索' : '新建线索'}</Space>}
        open={modalVisible} onOk={() => form.submit()} onCancel={() => setModalVisible(false)}
        width={640} okText={editingClue ? '保存' : '创建'} cancelText="取消"
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="title" label="标题" rules={[{ required: true, message: '请输入标题' }]}>
            <Input placeholder="请输入线索标题" />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="source" label="来源"><Input placeholder="如：微博、腾讯新闻" /></Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="source_url" label="来源链接"><Input placeholder="https://..." /></Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="category" label="分类">
                <Select placeholder="选择分类" allowClear>
                  {['时政','经济','社会','科技','文化','体育','娱乐','国际'].map(c => <Option key={c} value={c}>{c}</Option>)}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="status" label="状态" initialValue="pending">
                <Select placeholder="选择状态">
                  <Option value="pending">待处理</Option>
                  <Option value="processed">已处理</Option>
                  <Option value="archived">已归档</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="keywords" label="关键词"><Input placeholder="多个关键词用逗号分隔" /></Form.Item>
          <Form.Item name="content" label="内容"><TextArea rows={3} placeholder="请输入线索内容" /></Form.Item>
        </Form>
      </Modal>

      {/* 详情抽屉 */}
      <Drawer
        title={<Space><EyeOutlined />线索详情</Space>}
        placement="right" width={560} onClose={() => setDetailVisible(false)} open={detailVisible}
        extra={
          <Space>
            <Button size="small" icon={<SearchOutlined />} onClick={() => selectedClue && openSearchModal(selectedClue)}>搜索资料</Button>
            <Button type="primary" size="small" icon={<FileTextOutlined />} onClick={() => selectedClue && handleCreateArticle(selectedClue)}>生成稿件</Button>
          </Space>
        }
      >
        {selectedClue && (
          <>
            <Title level={5}>{selectedClue.title}</Title>
            <Space style={{ marginBottom: 12 }}>
              {getCategoryTag(selectedClue.category)}
              {getStatusTag(selectedClue.status)}
              {selectedClue.source && <Tag icon={<GlobalOutlined />}>{selectedClue.source}</Tag>}
            </Space>
            {selectedClue.source_url && (
              <div style={{ marginBottom: 12 }}>
                <a href={normalizeExternalUrl(selectedClue.source_url)} target="_blank" rel="noopener noreferrer">
                  <LinkOutlined /> 查看原文
                </a>
              </div>
            )}
            <Descriptions column={1} size="small" style={{ marginBottom: 12 }}>
              <Descriptions.Item label="关键词">
                <Space wrap>{selectedClue.keywords?.map((k, i) => <Tag key={i}>{k}</Tag>) || '-'}</Space>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">{new Date(selectedClue.created_at).toLocaleString('zh-CN')}</Descriptions.Item>
              {selectedClue.processed_at && <Descriptions.Item label="处理时间">{new Date(selectedClue.processed_at).toLocaleString('zh-CN')}</Descriptions.Item>}
            </Descriptions>
            {selectedClue.content && (
              <>
                <Divider style={{ margin: '12px 0' }} />
                <Title level={5}>内容</Title>
                <Paragraph style={{ background: '#fafafa', padding: 12, borderRadius: 8, fontSize: 13 }}>{selectedClue.content}</Paragraph>
              </>
            )}
            {(selectedClue.news_value_score || selectedClue.propagation_potential) && (
              <>
                <Divider style={{ margin: '12px 0' }} />
                <Title level={5}>AI 评分</Title>
                <Space direction="vertical" style={{ width: '100%' }}>
                  {selectedClue.news_value_score && (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <Text>新闻价值</Text><Text strong>{selectedClue.news_value_score}/100</Text>
                      </div>
                      <Progress percent={selectedClue.news_value_score} strokeColor={selectedClue.news_value_score >= 80 ? '#52c41a' : selectedClue.news_value_score >= 60 ? '#faad14' : '#ff4d4f'} />
                    </div>
                  )}
                  {selectedClue.propagation_potential && (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <Text>传播潜力</Text><Text strong>{selectedClue.propagation_potential}/100</Text>
                      </div>
                      <Progress percent={selectedClue.propagation_potential} strokeColor={selectedClue.propagation_potential >= 80 ? '#52c41a' : selectedClue.propagation_potential >= 60 ? '#faad14' : '#ff4d4f'} />
                    </div>
                  )}
                </Space>
              </>
            )}
            <Divider style={{ margin: '12px 0' }} />
            <Button icon={<RobotOutlined />} onClick={() => handleAnalyze(selectedClue)} loading={analyzing === selectedClue.id} style={{ marginRight: 8 }}>AI 分析</Button>
          </>
        )}
      </Drawer>

      {/* 采集弹窗 */}
      <Modal
        title={<Space><CloudDownloadOutlined style={{ color: '#1890ff' }} />采集新闻线索</Space>}
        open={collectModalVisible} onOk={() => collectForm.submit()} onCancel={() => { setCollectModalVisible(false); collectForm.resetFields() }}
        confirmLoading={collecting} width={560} okText="开始采集" cancelText="取消"
      >
        <Form form={collectForm} layout="vertical" onFinish={handleCollect} initialValues={{ channels: ['news_sites'], maxResults: 15 }}>
          <Alert
            message="定向采集"
            description="请先选择具体新闻媒体或「全网」，再设采集条数上限；不选「全网」时结果主要来自所选门户/RSS，避免来源过于随机。"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Form.Item name="keywords" label="关键词" rules={[{ required: true, message: '请输入关键词' }]}>
            <Input placeholder="如：人工智能、科技创新（多个用逗号分隔）" />
          </Form.Item>
          <Form.Item name="channels" label="媒体与渠道" rules={[{ required: true, message: '请至少选择一项' }]}>
            <Select
              mode="multiple"
              placeholder="选择新闻媒体、全网搜索或社交平台"
              allowClear
              optionFilterProp="children"
              listHeight={320}
            >
              <Select.OptGroup label="新闻门户（推荐指定媒体）">
                <Option value="news_sites">全网资讯（Bing 混合，来源不固定）</Option>
                <Option value="tencent">腾讯新闻</Option>
                <Option value="netease">网易新闻</Option>
                <Option value="sina">新浪新闻</Option>
                <Option value="ifeng">凤凰网</Option>
                <Option value="thepaper">澎湃新闻</Option>
                <Option value="sohu">搜狐新闻</Option>
                <Option value="toutiao">今日头条</Option>
              </Select.OptGroup>
              <Select.OptGroup label="社交与政务">
                <Option value="weibo">微博（定向）</Option>
                <Option value="social_media">知乎 / 微信 / 小红书等（Bing 社媒）</Option>
                <Option value="government">政府网站（gov.cn）</Option>
              </Select.OptGroup>
            </Select>
          </Form.Item>
          <Form.Item name="maxResults" label="采集总条数上限" extra="多关键词、多来源时会去重，实际条数可能略少于上限">
            <Select>
              <Option value={5}>5 条</Option>
              <Option value={10}>10 条</Option>
              <Option value={15}>15 条</Option>
              <Option value={20}>20 条</Option>
              <Option value={30}>30 条</Option>
              <Option value={50}>50 条</Option>
              <Option value={80}>80 条</Option>
              <Option value={100}>100 条</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 搜索资料弹窗 */}
      <Modal
        title={<Space><SearchOutlined style={{ color: '#1890ff' }} />搜索相关资料{searchResults.length > 0 && <Tag color="orange">{searchResults.length}条</Tag>}</Space>}
        open={searchModalVisible} onCancel={() => setSearchModalVisible(false)}
        footer={searchResults.length > 0 ? <Button type="text" danger size="small" icon={<DeleteOutlined />} onClick={() => setSearchResults([])}>清空全部</Button> : null}
        width={720}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Input.Search placeholder="输入关键词搜索相关资料" value={searchKeyword} onChange={(e) => setSearchKeyword(e.target.value)} onSearch={handleSearchInfo} loading={searchLoading} enterButton={<Button type="primary" icon={<SearchOutlined />}>搜索</Button>} size="large" />
          <Space wrap>
            <Segmented value={searchSource} onChange={(val) => setSearchSource(val as string)} options={[{ label: '新闻', value: 'news' }, { label: '社交', value: 'social' }]} />
            <Select value={searchMaxResults} onChange={setSearchMaxResults} style={{ width: 100 }} options={[
              { label: '15条', value: 15 },
              { label: '30条', value: 30 },
              { label: '50条', value: 50 },
            ]} />
            <Button
              type={exactMatch ? 'primary' : 'default'}
              icon={<SearchOutlined />}
              onClick={() => setExactMatch(!exactMatch)}
              size='middle'
            >
              精确匹配
            </Button>
          </Space>
          {searchResults.length === 0 && !searchLoading && (
            <Empty
              description={searchInfoAttempted ? '未检索到结果，可换关键词或切换新闻/社交后再试' : '输入关键词后点击搜索'}
              style={{ padding: '40px 0' }}
            />
          )}
          <div style={{ maxHeight: 380, overflowY: 'auto' }}>
            {searchResults.map((item: any, idx: number) => (
              <Card
                key={idx}
                size="small"
                style={{ marginBottom: 6, cursor: item.url && item.url !== '#' ? 'pointer' : 'default' }}
                hoverable
                onClick={() => {
                  if (item.url && item.url !== '#') {
                    window.open(normalizeExternalUrl(item.url), '_blank', 'noopener,noreferrer')
                  }
                }}
                title={<Text style={{ fontSize: 13 }}>{item.title}</Text>}
                extra={<Space>{item.source && <Tag color="blue" style={{ fontSize: 11 }}>{item.source}</Tag>}<Button type="text" danger size="small" icon={<DeleteOutlined />} onClick={(e) => { e.stopPropagation(); setSearchResults(searchResults.filter((_: any, i: number) => i !== idx)) }} />{item.url && item.url !== '#' && <a onClick={(e) => e.stopPropagation()} href={normalizeExternalUrl(item.url)} target="_blank" rel="noopener noreferrer"><LinkOutlined /> 打开</a>}</Space>}>
                <Text type="secondary" style={{ fontSize: 12 }}>{item.snippet || '暂无摘要'}</Text>
              </Card>
            ))}
          </div>
        </Space>
      </Modal>

      {/* AI分析结果弹窗 */}
      <Modal
        title={<Space><RobotOutlined style={{ color: '#722ed1' }} />AI 分析结果</Space>}
        open={analysisModalVisible} onCancel={() => setAnalysisModalVisible(false)}
        footer={<Button onClick={() => setAnalysisModalVisible(false)}>关闭</Button>}
        width={600}
      >
        {analysisResult && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="推荐分类"><Tag color="blue">{analysisResult.category}</Tag><Text type="secondary" style={{ marginLeft: 8 }}>置信度: {analysisResult.category_confidence}%</Text></Descriptions.Item>
            <Descriptions.Item label="新闻价值"><Progress percent={analysisResult.news_value_score} status="active" /></Descriptions.Item>
            <Descriptions.Item label="传播潜力"><Progress percent={analysisResult.propagation_potential} status="active" /></Descriptions.Item>
            <Descriptions.Item label="情感倾向"><Tag color={analysisResult.sentiment === 'positive' ? 'green' : analysisResult.sentiment === 'negative' ? 'red' : 'default'}>{analysisResult.sentiment === 'positive' ? '正面' : analysisResult.sentiment === 'negative' ? '负面' : '中立'}</Tag></Descriptions.Item>
            <Descriptions.Item label="AI 建议"><Text>{analysisResult.recommendation}</Text></Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      <style>{`
        .clue-row-pending { background: #fffbe6 !important; }
        .clue-row-pending:hover { background: #fff1b8 !important; }
        .ant-table { font-size: 13px; }
        .ant-table-thead > tr > th { background: #fafafa !important; font-size: 12px !important; text-transform: uppercase; letter-spacing: 0.5px; }
        .ant-card-head { border-bottom: none !important; min-height: 48px !important; padding: 0 16px !important; }
        .ant-card-head-title { padding: 12px 0 !important; }
        .ant-card-body { padding: 0 !important; }
      `}</style>
    </div>
  )
}

export default Clues
