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

// 高亮搜索关键词
const HighlightText = ({ text, keywords }: { text: string; keywords: string[] }) => {
  if (!keywords.length || !text) return <span>{text}</span>

  const parts = text.split(new RegExp(`(${keywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi'))

  return (
    <span>
      {parts.map((part, i) =>
        keywords.some(kw => part.toLowerCase() === kw.toLowerCase()) ? (
          <mark key={i} style={{ backgroundColor: '#ffe58f', padding: '0 2px', borderRadius: 2 }}>{part}</mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </span>
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
  const [searchFields, setSearchFields] = useState<string[]>([])
  const [searchMode, setSearchMode] = useState<'fuzzy' | 'exact' | 'smart'>('fuzzy')
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
  const [sources, setSources] = useState<{ rss: any[]; api: any[]; search: any[] }>({ rss: [], api: [], search: [] })

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
      if (searchFields.length > 0) params.search_fields = searchFields.join(',')
      if (searchMode && searchMode !== 'fuzzy') params.search_mode = searchMode
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
  }, [statusFilter, categoryFilter, searchText, dateRange, currentPage, pageSize, searchFields, searchMode])

  useEffect(() => {
    fetchClues()
  }, [fetchClues])

  // 加载可用信源列表
  useEffect(() => {
    clueAPI.getSources().then((res: any) => {
      const data = res?.data || res
      setSources({
        rss: data?.rss || [],
        api: data?.api || [],
        search: data?.search || [],
      })
    }).catch(() => {})
  }, [])

  const resetFilters = () => {
    setSearchText('')
    setStatusFilter(undefined)
    setCategoryFilter(undefined)
    setDateRange([null, null])
    setSearchFields([])
    setSearchMode('fuzzy')
    toast.info('筛选条件已重置')
  }

  const hasActiveFilters = searchText || statusFilter || categoryFilter || dateRange[0] || searchFields.length > 0 || searchMode !== 'fuzzy'

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
      await fetchClues()
    } catch (error) {
      toast.error('创建稿件失败')
    }
  }

  const refreshAfterCollection = async () => {
    if (currentPage !== 1) {
      setCurrentPage(1)
      return
    }
    await fetchClues()
  }

  const handleCollect = async (values: any) => {
    setCollecting(true)
    try {
      const maxN = Number(values.maxResults)
      const result: any = await clueAPI.collectMultichannel(
        String(values.keywords || '').trim(),
        Array.isArray(values.channels) ? values.channels : [],
        values.timeRange,
        Number.isFinite(maxN) && maxN > 0 ? maxN : 15
      )

      // 解析响应数据
      const data = result?.data || result
      const created = data?.created || 0
      const fetched = data?.fetched || 0
      const message = result?.message || ''
      const errors = data?.errors || []
      if (created > 0) {
        await refreshAfterCollection()
        toast.success(message || `✅ 成功采集 ${created} 条线索`)
        setCollectModalVisible(false)
        collectForm.resetFields()

        // 如果有部分失败，显示警告
        if (errors.length > 0) {
          setTimeout(() => {
            toast.warning(`⚠️ 部分渠道失败: ${errors.slice(0, 2).join('; ')}`, 5000)
          }, 1000)
        }
      } else if (fetched > 0) {
        toast.warning('⚠️ 采集到内容但入库失败，请查看后端日志')
        await refreshAfterCollection()
      } else {
        if (result?.code === 202 || errors.length > 0) {
          toast.error(message || '❌ 未采集到有效线索', 6000)

          // 显示详细的错误信息
          if (errors.length > 0) {
            console.error('📋 采集错误详情:', errors)
            setTimeout(() => {
              toast.info('💡 建议：尝试 Bing搜索、腾讯新闻、知乎日报等可用渠道', 8000)
            }, 1500)
          }
        } else {
          toast.warning(message || '未获取到线索，请更换关键词或渠道')
        }
        await refreshAfterCollection()  // 刷新列表以显示现有数据
      }
    } catch (error: unknown) {
      console.error('❌ 采集请求失败:', error)
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
      converted: { color: 'blue', text: '已转稿' },
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
      render: (_: any, record: NewsClue) => {
        const searchKeywords = searchText ? searchText.split(',').map(k => k.trim()).filter(k => k) : []
        return (
          <div>
            <Space>
              <BulbOutlined style={{ color: '#faad14', flexShrink: 0 }} />
              <Tooltip title={record.title}>
                {record.source_url ? (
                  <a href={normalizeExternalUrl(record.source_url)} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}>
                    <Text strong style={{ maxWidth: 260, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#1890ff', textDecoration: 'none' }}>
                      {searchKeywords.length > 0 ? <HighlightText text={record.title} keywords={searchKeywords} /> : record.title}
                    </Text>
                  </a>
                ) : (
                  <Text strong style={{ maxWidth: 260, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {searchKeywords.length > 0 ? <HighlightText text={record.title} keywords={searchKeywords} /> : record.title}
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
        )
      },
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
          { key: 'converted', label: '已转稿' },
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
            placeholder="搜索标题、内容、关键词、来源或分类"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onSearch={handleSearch}
            allowClear
            style={{ width: 260 }}
            size="small"
          />
          <Select
            mode="multiple"
            size="small"
            placeholder="搜索范围"
            allowClear
            style={{ width: 200 }}
            value={searchFields}
            onChange={(values) => setSearchFields(values as string[])}
            maxTagCount={2}
          >
            <Option value="title">标题</Option>
            <Option value="content">内容</Option>
            <Option value="keywords">关键词</Option>
            <Option value="source">来源</Option>
            <Option value="category">分类</Option>
          </Select>
          <Segmented
            size="small"
            value={searchMode}
            onChange={(value) => setSearchMode(value as 'fuzzy' | 'exact' | 'smart')}
            options={[
              { label: '模糊搜索', value: 'fuzzy' },
              { label: '精确匹配', value: 'exact' },
              { label: '智能排序', value: 'smart' },
            ]}
          />
          <Select size="small" placeholder="状态" allowClear style={{ width: 100 }} value={statusFilter} onChange={setStatusFilter}>
            <Option value="pending">待处理</Option>
            <Option value="processed">已处理</Option>
            <Option value="converted">已转稿</Option>
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
              {searchFields.length > 0 && <Tag closable onClose={() => setSearchFields([])}>范围: {searchFields.join(',')}</Tag>}
              {searchMode !== 'fuzzy' && <Tag closable onClose={() => setSearchMode('fuzzy')}>{searchMode === 'exact' ? '精确匹配' : '智能排序'}</Tag>}
              {statusFilter && <Tag closable onClose={() => setStatusFilter(undefined)}>{statusFilter === 'pending' ? '待处理' : statusFilter === 'processed' ? '已处理' : statusFilter === 'converted' ? '已转稿' : '已归档'}</Tag>}
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
                  <Option value="converted">已转稿</Option>
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
        <Form form={collectForm} layout="vertical" onFinish={handleCollect} initialValues={{ channels: ['all'], maxResults: 15 }}>
          <Alert
            message="多渠道新闻采集"
            description={
              <div>
                <p>输入关键词后，系统将从选定渠道自动采集相关新闻线索并保存到数据库。</p>
                <div style={{ marginTop: 8, padding: '8px 12px', background: '#fffbe6', borderRadius: 6, fontSize: 12 }}>
                  <Text strong style={{ color: '#d48806' }}>💡 推荐配置：</Text>
                  <ul style={{ margin: '4px 0 0 0', paddingLeft: 20, color: '#666' }}>
                    <li><strong>搜索发现：</strong>Bing搜索（关键词检索，推荐）</li>
                    <li><strong>新闻门户：</strong>腾讯新闻、新浪新闻</li>
                    <li><strong>API 热榜：</strong>知乎日报、B站热门（适合不限定关键词时使用）</li>
                    <li><strong>说明：</strong>已隐藏无法稳定采集的渠道，并取消去重入库</li>
                  </ul>
                </div>
              </div>
            }
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
              placeholder="选择渠道"
              allowClear
              optionFilterProp="children"
            >
              <Select.OptGroup label="RSS 订阅源（推荐）">
                {sources.rss.map((s: any) => (
                  <Option key={s.key} value={s.key}>{s.name}（{s.category}）</Option>
                ))}
              </Select.OptGroup>
              <Select.OptGroup label="API 源">
                {sources.api.map((s: any) => (
                  <Option key={s.key} value={s.key}>{s.name}（{s.category}）</Option>
                ))}
              </Select.OptGroup>
              <Select.OptGroup label="搜索引擎发现">
                {sources.search.map((s: any) => (
                  <Option key={s.key} value={s.key}>{s.name}（{s.category}）</Option>
                ))}
              </Select.OptGroup>
            </Select>
          </Form.Item>
          <Form.Item name="maxResults" label="采集总条数上限" extra="关键词越精准、上限越大，结果越丰富">
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
            <Segmented value={searchSource} onChange={(val) => setSearchSource(val as string)} options={[
              { label: '全部', value: 'news' },
              ...sources.rss.map((s: any) => ({ label: s.name, value: s.key })),
              ...sources.api.map((s: any) => ({ label: s.name, value: s.key })),
            ]} />
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
