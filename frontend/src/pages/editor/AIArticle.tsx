import { useState, useEffect, useMemo } from 'react'
import {
  Card,
  Button,
  Input,
  Select,
  Form,
  Row,
  Col,
  Typography,
  Space,
  Divider,
  List,
  Empty,
  Badge,
  Modal,
  Alert,
  Steps,
  Spin,
  Tabs,
  Result,
  Tag,
  Tooltip,
  Progress,
  Segmented,
} from 'antd'
import {
  RobotOutlined,
  ThunderboltOutlined,
  EditOutlined,
  SaveOutlined,
  FileTextOutlined,
  BulbOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
  CopyOutlined,
  EyeOutlined,
  HistoryOutlined,
  StarOutlined,
  LikeOutlined,
  AlertOutlined,
  QuestionCircleOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import { contentAPI, articleAPI, clueAPI, topicAPI, unwrapPaginated } from '../../services/api'
import type { NewsClue, ContentGenerationResult } from '../../types'
import { toast } from '../../components/common/Toast'

const { Text, Paragraph } = Typography
const { Option } = Select
const { Step } = Steps
const { Search } = Input

/** 分页接口：稿件列表在 data 上即为数组 */
function unwrapArticleList(res: unknown): any[] {
  const r = res as { data?: unknown }
  if (Array.isArray(res)) return res as any[]
  if (Array.isArray(r?.data)) return r.data as any[]
  const inner = r?.data as { data?: unknown } | undefined
  if (inner && Array.isArray(inner.data)) return inner.data as any[]
  return []
}

/** 线索列表：嵌套在 data.data */
function unwrapClueList(res: unknown): NewsClue[] {
  const r = res as { data?: unknown }
  if (Array.isArray(res)) return res as NewsClue[]
  const d = r?.data as { data?: unknown } | NewsClue[] | undefined
  if (Array.isArray(d)) return d as NewsClue[]
  if (d && typeof d === 'object' && Array.isArray((d as { data?: unknown }).data)) {
    return (d as { data: NewsClue[] }).data
  }
  return []
}

function normalizeKeywords(raw: unknown): string[] {
  if (Array.isArray(raw)) {
    return raw.map((k) => String(k).trim()).filter(Boolean)
  }
  if (typeof raw === 'string') {
    return raw.split(/[,，]/).map((k) => k.trim()).filter(Boolean)
  }
  return []
}

const AI_ARTICLE_DRAFT_KEY = 'ai_article_generation_draft_v1'

/** 从多条线索生成「主题」占位文案（不替代用户已输入的主题） */
function buildClueTopicHint(clues: NewsClue[]): string {
  if (!clues.length) return ''
  const parts = clues.map((c) => (c.title || '').trim()).filter(Boolean).slice(0, 4)
  const joined = parts.join(' · ')
  return joined.length > 100 ? `${joined.slice(0, 97)}...` : joined
}

function formatAxiosErrorMessage(error: unknown): string {
  const e = error as { response?: { data?: unknown }; message?: string }
  const data = e?.response?.data as Record<string, unknown> | string | undefined
  if (typeof data === 'string') return data
  if (data && typeof data === 'object') {
    const msg = data.message
    if (typeof msg === 'string') return msg
    const detail = data.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail[0] && typeof detail[0] === 'object' && 'msg' in detail[0]) {
      return String((detail[0] as { msg: string }).msg)
    }
  }
  return e?.message || '请求失败，请检查网络或后端是否已启动'
}

const AIArticle = () => {
  const [form] = Form.useForm()
  const [generating, setGenerating] = useState(false)
  const [generatedContent, setGeneratedContent] = useState<ContentGenerationResult | null>(null)
  const [clues, setClues] = useState<NewsClue[]>([])
  const [selectedClues, setSelectedClues] = useState<NewsClue[]>([])
  const [generatedArticles, setGeneratedArticles] = useState<any[]>([])
  const [currentStep, setCurrentStep] = useState(0)
  const [previewVisible, setPreviewVisible] = useState(false)
  const [previewContent, setPreviewContent] = useState('')
  const [previewArticleTitle, setPreviewArticleTitle] = useState('')
  const [cluesLoading, setCluesLoading] = useState(false)
  const [saveLoading, setSaveLoading] = useState(false)
  const [generationProgress, setGenerationProgress] = useState(0)
  const [clueSearch, setClueSearch] = useState('')
  const [articleSearch, setArticleSearch] = useState('')
  const [improving, setImproving] = useState(false)
  const [improveModalVisible, setImproveModalVisible] = useState(false)
  const [improvedContent, setImprovedContent] = useState<{ content: string; notes: string[] } | null>(null)
  const [improveType, setImproveType] = useState<'polish' | 'expand' | 'condense' | 'rewrite'>('polish')
  const [improveFocus, setImproveFocus] = useState<'clarity' | 'depth' | 'engagement' | 'accuracy' | ''>('')
  const [topics, setTopics] = useState<any[]>([])
  const [topicsLoading, setTopicsLoading] = useState(false)
  const [customTitle, setCustomTitle] = useState('')
  /** 当前选中的备选标题下标，用于保存与预览 */
  const [selectedTitleIndex, setSelectedTitleIndex] = useState(0)
  /** 线索生成时的主题提示（不直接写入 topic 输入框，避免覆盖用户输入） */
  const [clueTopicHint, setClueTopicHint] = useState('')
  /** 内嵌预览：点击候选标题时展开预览区 */
  const [inlinePreviewVisible, setInlinePreviewVisible] = useState(false)

  const filteredClues = useMemo(() => {
    const q = clueSearch.trim().toLowerCase()
    if (!q) return clues
    return clues.filter((c) => {
      const title = (c.title || '').toLowerCase()
      const cat = (c.category || '').toLowerCase()
      const body = (c.content || '').toLowerCase()
      const kws = (c.keywords || []).join(' ').toLowerCase()
      return title.includes(q) || cat.includes(q) || body.includes(q) || kws.includes(q)
    })
  }, [clues, clueSearch])

  const filteredGeneratedArticles = useMemo(() => {
    const q = articleSearch.trim().toLowerCase()
    if (!q) return generatedArticles
    return generatedArticles.filter((a: { title?: string; author?: string; content?: string; category?: string }) => {
      const title = (a.title || '').toLowerCase()
      const author = (a.author || '').toLowerCase()
      const content = (a.content || '').toLowerCase()
      const category = (a.category || '').toLowerCase()
      return title.includes(q) || author.includes(q) || content.includes(q) || category.includes(q)
    })
  }, [generatedArticles, articleSearch])

  useEffect(() => {
    fetchClues()
    fetchGeneratedArticles()
    fetchTopics()
  }, [])

  /** 从 sessionStorage 恢复未完成的生成结果（刷新/误关页不丢候选标题） */
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(AI_ARTICLE_DRAFT_KEY)
      if (!raw) return
      const parsed = JSON.parse(raw) as {
        generatedContent?: ContentGenerationResult
        currentStep?: number
        selectedTitleIndex?: number
        customTitle?: string
        inlinePreviewVisible?: boolean
      }
      if (parsed.generatedContent?.draft_content || parsed.generatedContent?.suggested_titles?.length) {
        const gc = parsed.generatedContent!
        setGeneratedContent(gc)
        if (typeof parsed.currentStep === 'number') setCurrentStep(parsed.currentStep)
        if (typeof parsed.selectedTitleIndex === 'number') {
          const n = gc.suggested_titles?.length ?? 0
          const max = Math.max(0, n - 1)
          setSelectedTitleIndex(Math.min(Math.max(0, parsed.selectedTitleIndex), max))
        }
        if (typeof parsed.customTitle === 'string') setCustomTitle(parsed.customTitle)
        if (typeof parsed.inlinePreviewVisible === 'boolean') setInlinePreviewVisible(parsed.inlinePreviewVisible)
      }
    } catch {
      /* ignore */
    }
  }, [])

  useEffect(() => {
    if (!generatedContent) {
      sessionStorage.removeItem(AI_ARTICLE_DRAFT_KEY)
      return
    }
    try {
      sessionStorage.setItem(
        AI_ARTICLE_DRAFT_KEY,
        JSON.stringify({
          generatedContent,
          currentStep,
          selectedTitleIndex,
          customTitle,
          inlinePreviewVisible,
        })
      )
    } catch {
      /* ignore */
    }
  }, [generatedContent, currentStep, selectedTitleIndex, customTitle, inlinePreviewVisible])

  const fetchClues = async () => {
    setCluesLoading(true)
    try {
      const data = await clueAPI.list({ page_size: 100 })
      setClues(unwrapClueList(data))
    } catch (error) {
      toast.error('获取线索列表失败')
    } finally {
      setCluesLoading(false)
    }
  }

  const fetchGeneratedArticles = async () => {
    try {
      const data = await articleAPI.list({ page_size: 20 })
      const articles = unwrapArticleList(data)
      setGeneratedArticles(articles.filter((a: any) => a.author === 'AI 助手' || a.clue_id).slice(0, 20))
    } catch (error) {
      console.error('获取稿件列表失败:', error)
    }
  }

  const fetchTopics = async () => {
    setTopicsLoading(true)
    try {
      const data = await topicAPI.list({ page_size: 100 })
      const { items } = unwrapPaginated(data)
      setTopics(items.filter((t: any) => t.status !== 'cancelled'))
    } catch (error) {
      console.error('获取选题列表失败:', error)
    } finally {
      setTopicsLoading(false)
    }
  }

  const handleGenerate = async (values: any) => {
    setGenerating(true)
    setGenerationProgress(0)
    
    // Simulate progress for better UX
    const progressInterval = setInterval(() => {
      setGenerationProgress(prev => Math.min(prev + 10, 90))
    }, 500)

    try {
      const keywords = normalizeKeywords(values.keywords)
      const allValues = form.getFieldsValue() as { content?: string }
      const topicTrim = String(values.topic ?? '').trim()
      const topicForApi =
        topicTrim ||
        clueTopicHint ||
        (selectedClues.length > 0 ? buildClueTopicHint(selectedClues) : '')

      const requestData = {
        topic: topicForApi,
        keywords,
        style: values.style || 'formal',
        length: values.length || 'medium',
        title_count: values.titleCount ?? 3,
        tone: values.tone || 'professional',
        audience: values.audience || 'general',
        reference_material: allValues.content?.trim() || undefined,
      }

      const result = (await contentAPI.generate(requestData)) as {
        data?: ContentGenerationResult
        code?: number
        message?: string
      }

      clearInterval(progressInterval)
      setGenerationProgress(100)

      if (result.code != null && result.code !== 200) {
        toast.error(result.message || '生成失败')
        return
      }

      const payload = result?.data
      const hasBody =
        (payload?.draft_content && String(payload.draft_content).trim().length > 0) ||
        (payload?.suggested_titles && payload.suggested_titles.length > 0)
      if (!payload || !hasBody) {
        toast.error('接口返回数据格式异常，请查看控制台')
        console.error('generate response:', result)
        return
      }
      setGeneratedContent(payload)
      setSelectedTitleIndex(0)
      setCustomTitle('')
      setClueTopicHint('')
      setInlinePreviewVisible(false)
      setCurrentStep(1)
      toast.success('AI 生成完成！', 5)
    } catch (error) {
      clearInterval(progressInterval)
      console.error('AI 生成失败:', error)
      toast.error(formatAxiosErrorMessage(error))
    } finally {
      setGenerating(false)
    }
  }

  const handleSaveArticle = async (title: string, content: string) => {
    setSaveLoading(true)
    try {
      const values = form.getFieldsValue()
      const articleData = {
      title: title,
      content: content,
      abstract: content.slice(0, 200) + (content.length > 200 ? '...' : ''),
      category: values.category || '新闻',
      tags: normalizeKeywords(values.keywords),
      status: 'draft',
      author: 'AI 助手',
      topic_id: (values.topic_id != null && values.topic_id !== '' && Number.isInteger(Number(values.topic_id))) ? Number(values.topic_id) : undefined,
    }

      await articleAPI.create(articleData)
      toast.success('稿件保存成功！可前往稿件管理页面查看')
      fetchGeneratedArticles()
      sessionStorage.removeItem(AI_ARTICLE_DRAFT_KEY)
      setCurrentStep(2)
    } catch (error) {
      toast.error('保存失败：' + formatAxiosErrorMessage(error))
    } finally {
      setSaveLoading(false)
    }
  }

  const handleImproveContent = async () => {
    if (!generatedContent?.draft_content) return
    setImproving(true)
    try {
      const result = await contentAPI.improve({
        original_content: generatedContent.draft_content,
        improve_type: improveType,
        focus_area: improveFocus || undefined,
      }) as { data?: { improved_content: string; improvement_notes: string[] } }
      if (result?.data) {
        setImprovedContent({
          content: result.data.improved_content,
          notes: result.data.improvement_notes || [],
        })
        toast.success('内容改进完成！')
      }
    } catch (error) {
      toast.error('改进失败：' + formatAxiosErrorMessage(error))
    } finally {
      setImproving(false)
    }
  }

  const handleSelectClue = (clue: NewsClue) => {
    if (selectedClues.find(c => c.id === clue.id)) {
      setSelectedClues(selectedClues.filter(c => c.id !== clue.id))
    } else {
      setSelectedClues([...selectedClues, clue])
    }
  }

  const handleGenerateFromClues = () => {
    if (selectedClues.length === 0) {
      toast.warning('请至少选择一条线索')
      return
    }

    const combinedContent = selectedClues.map(c => c.content).join('\n\n')
    const keywords = selectedClues.flatMap(c => c.keywords || [])
    const uniqueKeywords = [...new Set(keywords)]

    // 绝不覆盖主题输入框！仅设置关键词和正文引用
    form.setFieldsValue({
      keywords: uniqueKeywords,
      content: combinedContent,
    })

    // 将线索标题摘要作为「建议主题」，以独立提示横幅展示，用户可手动采纳
    const hint = buildClueTopicHint(selectedClues)
    setClueTopicHint(hint)

    setCurrentStep(0)
    toast.success('已加载线索关键词与正文；如需使用线索主题，请点击下方建议横幅采纳')
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('已复制到剪贴板')
  }

  const steps = [
    {
      title: '输入需求',
      icon: <EditOutlined />,
    },
    {
      title: 'AI 生成',
      icon: <RobotOutlined />,
    },
    {
      title: '保存稿件',
      icon: <CheckCircleOutlined />,
    },
  ]

  // Writing style options with descriptions
  const styleOptions = [
    { value: 'formal', label: '正式', desc: '适用于官方报道、新闻发布' },
    { value: 'casual', label: '轻松', desc: '适用于社交媒体、自媒体' },
    { value: 'eye_catching', label: '吸引眼球', desc: '适用于标题党、爆款文章' },
  ]

  // Tone options
  const toneOptions = [
    { value: 'professional', label: '专业严谨' },
    { value: 'friendly', label: '友好亲切' },
    { value: 'objective', label: '客观中立' },
    { value: 'passionate', label: '热情洋溢' },
  ]

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-in-out' }}>
      <Row gutter={[24, 24]}>
        {/* Main Generation Area */}
        <Col xs={24} lg={16}>
          <Card
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    background: 'linear-gradient(135deg, #722ed1 0%, #531dab 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <RobotOutlined style={{ fontSize: 18, color: 'white' }} />
                </div>
                <span style={{ fontWeight: 600, fontSize: 16 }}>AI 智能生成</span>
                <Tag color="purple" style={{ marginLeft: 8 }}>Beta</Tag>
              </div>
            }
            extra={
              <Space>
                <Tooltip title="帮助">
                  <Button type="text" icon={<QuestionCircleOutlined />} />
                </Tooltip>
              </Space>
            }
            style={{ borderRadius: 12 }}
          >
            <Steps current={currentStep} style={{ marginBottom: 32 }} size="small">
              {steps.map((step, index) => (
                <Step key={index} title={step.title} icon={step.icon} />
              ))}
            </Steps>

            {/* Step 0: Input Form */}
            {currentStep === 0 && (
              <Form
                form={form}
                layout="vertical"
                onFinish={handleGenerate}
                initialValues={{
                  length: 'medium',
                  style: 'formal',
                  tone: 'professional',
                  titleCount: 3,
                }}
              >
                {/* 线索主题建议横幅（不直接覆盖输入框） */}
                {clueTopicHint && (
                  <Alert
                    type="info"
                    showIcon
                    icon={<BulbOutlined />}
                    style={{ marginBottom: 16, borderRadius: 8 }}
                    message={
                      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                        <span>
                          <Text strong>线索建议主题：</Text>
                          <Text>{clueTopicHint}</Text>
                        </span>
                        <Space size={4}>
                          <Button
                            type="primary"
                            size="small"
                            onClick={() => {
                              form.setFieldsValue({ topic: clueTopicHint })
                              setClueTopicHint('')
                              toast.success('已采纳线索建议主题')
                            }}
                          >
                            采纳
                          </Button>
                          <Button
                            size="small"
                            onClick={() => setClueTopicHint('')}
                          >
                            忽略
                          </Button>
                        </Space>
                      </Space>
                    }
                  />
                )}

                {/* Topic Input */}
                <Form.Item
                  name="topic"
                  label="主题/标题"
                  rules={[{ required: true, message: '请输入主题' }, { min: 2, message: '主题至少2个字符' }]}
                  tooltip="写作方向或概括性主题；从线索加载时不会自动覆盖此处内容"
                >
                  <Input
                    placeholder="请输入文章主题或标题，例如：人工智能对未来新闻业的影响"
                    prefix={<EditOutlined />}
                    size="large"
                    showCount
                    maxLength={100}
                  />
                </Form.Item>

                {/* Style and Length */}
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item name="style" label="写作风格" tooltip="选择文章的写作风格">
                      <Select placeholder="选择风格" size="large">
                        {styleOptions.map(opt => (
                          <Option key={opt.value} value={opt.value}>
                            <div>
                              <Text>{opt.label}</Text>
                              <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>
                                {opt.desc}
                              </Text>
                            </div>
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="tone" label="文章语调" tooltip="选择文章的语调">
                      <Select placeholder="选择语调" size="large">
                        {toneOptions.map(opt => (
                          <Option key={opt.value} value={opt.value}>
                            {opt.label}
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>

                {/* Keywords */}
                <Form.Item
                  name="keywords"
                  label="关键词"
                  tooltip="输入相关关键词，用逗号分隔，有助于AI更准确地生成内容"
                >
                  <Select
                    mode="tags"
                    placeholder="输入关键词，用逗号分隔，例如：科技创新，数字经济"
                    size="large"
                    tokenSeparators={[',']}
                  />
                </Form.Item>

                {/* 关联选题 */}
                <Form.Item name="topic_id" label="关联选题策划（可选）" tooltip="选择要将此稿件关联到的选题">
                  <Select
                    allowClear
                    placeholder="不选择则不关联选题"
                    loading={topicsLoading}
                    showSearch
                    filterOption={(input, option) =>
                      (option?.children as unknown as string)?.toLowerCase().includes(input.toLowerCase())
                    }
                  >
                    {topics.map((t: any) => (
                      <Option key={t.id} value={t.id}>
                        {t.title}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>

                {/* Category */}
                <Form.Item name="category" label="文章分类" tooltip="选择文章所属分类">
                  <Select placeholder="选择分类" size="large" allowClear>
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

                {/* 线索合并正文（由「从线索生成」写入，随请求作为 reference_material） */}
                <Form.Item name="content" hidden>
                  <Input.TextArea autoSize={{ minRows: 1, maxRows: 4 }} />
                </Form.Item>

                {/* Segmented 为受控组件，与 Form 联动稳定；避免 Card 点击被拦截 */}
                <Form.Item
                  name="length"
                  label="文章长度"
                  rules={[{ required: true, message: '请选择文章长度' }]}
                  tooltip="切换篇幅要求，默认「中等」"
                >
                  <Segmented
                    block
                    size="large"
                    options={[
                      {
                        label: (
                          <div style={{ padding: '4px 0' }}>
                            <div>📝 简短</div>
                            <Text type="secondary" style={{ fontSize: 11 }}>
                              500-800字
                            </Text>
                          </div>
                        ),
                        value: 'short',
                      },
                      {
                        label: (
                          <div style={{ padding: '4px 0' }}>
                            <div>📄 中等</div>
                            <Text type="secondary" style={{ fontSize: 11 }}>
                              1000-1500字
                            </Text>
                          </div>
                        ),
                        value: 'medium',
                      },
                      {
                        label: (
                          <div style={{ padding: '4px 0' }}>
                            <div>📚 详细</div>
                            <Text type="secondary" style={{ fontSize: 11 }}>
                              2000+字
                            </Text>
                          </div>
                        ),
                        value: 'long',
                      },
                    ]}
                  />
                </Form.Item>

                <Form.Item name="titleCount" label="生成标题数量" tooltip="AI 生成的备选标题条数">
                  <Select size="large" options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: `${n} 条` }))} />
                </Form.Item>

                {/* Generate Button */}
                <Form.Item>
                  <Button
                    type="primary"
                    htmlType="submit"
                    size="large"
                    icon={<ThunderboltOutlined />}
                    loading={generating}
                    block
                    style={{
                      height: 52,
                      fontSize: 16,
                      background: generating ? '#52c41a' : 'linear-gradient(135deg, #722ed1 0%, #531dab 100%)',
                      border: 'none',
                    }}
                  >
                    {generating ? (
                      <Space>
                        AI 正在创作中...
                        <Progress
                          percent={generationProgress}
                          size="small"
                          status="active"
                          style={{ width: 100 }}
                        />
                      </Space>
                    ) : (
                      '开始生成'
                    )}
                  </Button>
                </Form.Item>
              </Form>
            )}

            {/* Step 1: Generated Content */}
            {currentStep === 1 && generatedContent && (
              <div>
                <Alert
                  message={
                    <Space>
                      <CheckCircleOutlined style={{ color: '#52c41a' }} />
                      <Text strong>AI 生成完成</Text>
                    </Space>
                  }
                  description="以下是 AI 为您生成的内容，您可以选择保存或重新生成"
                  type="success"
                  showIcon
                  style={{ marginBottom: 24, borderRadius: 8 }}
                  action={
                    <Button size="small" icon={<ReloadOutlined />} onClick={() => {
                      sessionStorage.removeItem(AI_ARTICLE_DRAFT_KEY)
                      setCurrentStep(0)
                      setGeneratedContent(null)
                      setSelectedTitleIndex(0)
                      setCustomTitle('')
                      setInlinePreviewVisible(false)
                    }}>
                      重新生成
                    </Button>
                  }
                />

                <Tabs
                  defaultActiveKey="1"
                  type="card"
                  size="small"
                  items={[
                    {
                      key: '1',
                      label: (
                        <Space size={4}>
                          <StarOutlined style={{ color: '#faad14' }} />
                          <span>建议标题</span>
                          <Tag>{generatedContent.suggested_titles?.length || 0} 个</Tag>
                        </Space>
                      ),
                      children: (
                        <>
                        <List
                          dataSource={generatedContent.suggested_titles || []}
                          locale={{ emptyText: '暂无备选标题' }}
                          renderItem={(title, index) => (
                            <List.Item
                              actions={[
                                <Button
                                  key="preview"
                                  type="link"
                                  size="small"
                                  icon={<EyeOutlined />}
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setPreviewArticleTitle(title)
                                    setPreviewContent(generatedContent.draft_content)
                                    setPreviewVisible(true)
                                  }}
                                >
                                  全屏预览
                                </Button>,
                                <Button
                                  key="copy"
                                  type="text"
                                  icon={<CopyOutlined />}
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    copyToClipboard(title)
                                  }}
                                >
                                  复制
                                </Button>,
                                <Button
                                  key="save"
                                  type="primary"
                                  size="small"
                                  icon={<SaveOutlined />}
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setSelectedTitleIndex(index)
                                    handleSaveArticle(title, generatedContent.draft_content)
                                  }}
                                  loading={saveLoading}
                                >
                                  保存此标题
                                </Button>,
                              ]}
                              style={{
                                cursor: 'pointer',
                                background:
                                  index === selectedTitleIndex
                                    ? '#e6f4ff'
                                    : index === 0
                                      ? '#f0f5ff'
                                      : 'transparent',
                                border:
                                  index === selectedTitleIndex
                                    ? '2px solid #1890ff'
                                    : '1px solid #f0f0f0',
                                borderRadius: 8,
                                marginBottom: 8,
                                padding: 12,
                                transition: 'all 0.25s ease',
                              }}
                              onClick={() => {
                                setSelectedTitleIndex(index)
                                setInlinePreviewVisible(true)
                              }}
                            >
                              <Space>
                                <Badge count={index + 1} style={{ backgroundColor: index === selectedTitleIndex ? '#1890ff' : index === 0 ? '#1890ff' : '#8c8c8c' }} />
                                <Text strong={index === selectedTitleIndex || index === 0}>{title}</Text>
                                {index === 0 && <Tag color="blue">推荐</Tag>}
                                {index === selectedTitleIndex && <Tag color="purple">当前选用</Tag>}
                              </Space>
                            </List.Item>
                          )}
                        />

                        {/* 内嵌预览区：点击标题后展开，提供即时反馈 */}
                        {inlinePreviewVisible && generatedContent.suggested_titles?.length > 0 && (
                          <Card
                            size="small"
                            style={{
                              marginTop: 12,
                              borderRadius: 8,
                              border: '1px solid #d9d9d9',
                              background: '#fafafa',
                              animation: 'fadeIn 0.3s ease-in-out',
                            }}
                            title={
                              <Space>
                                <EyeOutlined style={{ color: '#1890ff' }} />
                                <Text strong style={{ fontSize: 14 }}>
                                  标题预览：{generatedContent.suggested_titles[selectedTitleIndex] || generatedContent.suggested_titles[0]}
                                </Text>
                                <Tag color="purple">第 {selectedTitleIndex + 1} 条</Tag>
                              </Space>
                            }
                            extra={
                              <Button
                                type="text"
                                size="small"
                                onClick={() => setInlinePreviewVisible(false)}
                              >
                                收起
                              </Button>
                            }
                          >
                            <Paragraph
                              ellipsis={{ rows: 6, expandable: true, symbol: '展开全文' }}
                              style={{
                                whiteSpace: 'pre-wrap',
                                lineHeight: 1.8,
                                marginBottom: 0,
                                color: '#333',
                              }}
                            >
                              {generatedContent.draft_content}
                            </Paragraph>
                          </Card>
                        )}
                        </>
                      ),
                    },
                    {
                      key: '2',
                      label: (
                        <Space size={4}>
                          <FileTextOutlined style={{ color: '#52c41a' }} />
                          <span>文章内容</span>
                        </Space>
                      ),
                      children: (
                        <div style={{ position: 'relative', background: '#fafafa', padding: 16, borderRadius: 8 }}>
                          <Space style={{ position: 'absolute', top: 8, right: 8 }}>
                            <Button
                              type="text"
                              icon={<CopyOutlined />}
                              onClick={() => copyToClipboard(generatedContent.draft_content)}
                            >
                              复制全文
                            </Button>
                            <Button
                              type="primary"
                              icon={<EditOutlined />}
                              onClick={() => setImproveModalVisible(true)}
                            >
                              改进内容
                            </Button>
                          </Space>
                          <Paragraph
                            style={{
                              whiteSpace: 'pre-wrap',
                              paddingRight: 80,
                              lineHeight: 1.8,
                              marginBottom: 0,
                            }}
                          >
                            {generatedContent.draft_content}
                          </Paragraph>
                        </div>
                      ),
                    },
                    {
                      key: '3',
                      label: (
                        <Space size={4}>
                          <BulbOutlined style={{ color: '#fa8c16' }} />
                          <span>推荐写作角度</span>
                        </Space>
                      ),
                      children: (
                        <List
                          dataSource={generatedContent.recommended_angles}
                          renderItem={(angle) => (
                            <List.Item style={{ padding: '8px 0' }}>
                              <Space>
                                <LikeOutlined style={{ color: '#52c41a' }} />
                                <Text>{angle}</Text>
                              </Space>
                            </List.Item>
                          )}
                        />
                      ),
                    },
                    {
                      key: '4',
                      label: (
                        <Space size={4}>
                          <AlertOutlined style={{ color: '#722ed1' }} />
                          <span>结构建议</span>
                        </Space>
                      ),
                      children: (
                        <Paragraph style={{ background: '#fafafa', padding: 16, borderRadius: 8 }}>
                          {generatedContent.structure_suggestion}
                        </Paragraph>
                      ),
                    },
                  ]}
                />

                <Divider />

                {/* Quick Save */}
                <Card size="small" style={{ background: '#f0f5ff', borderRadius: 8 }}>
                  <Row gutter={16} align="middle">
                    <Col flex="1">
                      <Space direction="vertical" size="small" style={{ width: '100%' }}>
                        <Input
                          placeholder="自定义稿件标题（留空使用AI推荐标题）"
                          value={customTitle}
                          onChange={(e) => setCustomTitle(e.target.value)}
                          prefix={<EditOutlined />}
                          allowClear
                        />
                        <Space direction="vertical" size={4} style={{ width: '100%' }}>
                          <Space>
                            <FileTextOutlined style={{ fontSize: 16, color: '#1890ff' }} />
                            <Text type="secondary">
                              {customTitle ? '' : (generatedContent.suggested_titles[selectedTitleIndex] || generatedContent.suggested_titles[0] || 'AI 推荐标题')}
                              {' · '}
                              {form.getFieldValue('category') || '未分类'} · AI 助手生成
                            </Text>
                          </Space>
                          {(() => {
                            const selectedTopicId = form.getFieldValue('topic_id')
                            if (!selectedTopicId) return null
                            const selectedTopic = topics.find((t: any) => t.id === selectedTopicId)
                            return selectedTopic ? (
                              <Space size={4}>
                                <Tag color="purple">选题</Tag>
                                <Text type="secondary" style={{ fontSize: 12 }}>{selectedTopic.title}</Text>
                              </Space>
                            ) : null
                          })()}
                        </Space>
                      </Space>
                    </Col>
                    <Col>
                      <Space>
                        <Button
                          icon={<EditOutlined />}
                          onClick={() => {
                            sessionStorage.removeItem(AI_ARTICLE_DRAFT_KEY)
                            setCurrentStep(0)
                            setGeneratedContent(null)
                            setCustomTitle('')
                            setSelectedTitleIndex(0)
                            setInlinePreviewVisible(false)
                          }}
                        >
                          重新生成
                        </Button>
                        <Button
                          type="primary"
                          icon={<SaveOutlined />}
                          onClick={() => {
                            const titleToSave =
                              customTitle?.trim() ||
                              generatedContent.suggested_titles[selectedTitleIndex] ||
                              generatedContent.suggested_titles[0]
                            if (titleToSave) {
                              handleSaveArticle(titleToSave, generatedContent.draft_content)
                            }
                          }}
                          loading={saveLoading}
                        >
                          保存稿件
                        </Button>
                      </Space>
                    </Col>
                  </Row>
                </Card>
              </div>
            )}

            {/* Step 2: Success */}
            {currentStep === 2 && (
              <Result
                status="success"
                icon={<CheckCircleOutlined style={{ color: '#52c41a', fontSize: 64 }} />}
                title="稿件保存成功！"
                subTitle="您可以在稿件管理页面查看、编辑和发布"
                extra={[
                  <Button
                    key="continue"
                    onClick={() => {
                      sessionStorage.removeItem(AI_ARTICLE_DRAFT_KEY)
                      setCurrentStep(0)
                      setGeneratedContent(null)
                      setSelectedTitleIndex(0)
                      setCustomTitle('')
                      setInlinePreviewVisible(false)
                      setClueTopicHint('')
                      form.resetFields()
                    }}
                  >
                    继续生成
                  </Button>,
                  <Button
                    key="view"
                    type="primary"
                    onClick={() => window.location.href = '/articles'}
                  >
                    查看稿件
                  </Button>,
                ]}
                style={{
                  padding: '40px 0',
                }}
              />
            )}
          </Card>
        </Col>

        {/* Sidebar - Clues & History */}
        <Col xs={24} lg={8}>
          {/* From Clues Card */}
          <Card
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: 6,
                    background: 'linear-gradient(135deg, #faad14 0%, #fa8c16 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <BulbOutlined style={{ fontSize: 14, color: 'white' }} />
                </div>
                <span style={{ fontWeight: 600, fontSize: 14 }}>从线索生成</span>
              </div>
            }
            extra={
              <Badge count={selectedClues.length} overflowCount={9}>
                <Text type="secondary">已选</Text>
              </Badge>
            }
            style={{ borderRadius: 12, marginBottom: 16 }}
          >
            <Text type="secondary" style={{ display: 'block', marginBottom: 12, fontSize: 12 }}>
              选择新闻线索，AI 将基于线索内容生成稿件
            </Text>

            {/* 固定在卡片顶部，不随列表滚动 */}
            <div style={{ marginBottom: 12, flexShrink: 0 }}>
              <Space size={6} style={{ marginBottom: 8 }}>
                <SearchOutlined style={{ color: 'var(--app-primary, #c62828)' }} />
                <Text strong style={{ fontSize: 13 }}>
                  搜索线索
                </Text>
              </Space>
              <Search
                allowClear
                placeholder="标题、分类、正文、关键词"
                value={clueSearch}
                onChange={(e) => setClueSearch(e.target.value)}
                onSearch={(v) => setClueSearch(v)}
                enterButton="搜索"
                style={{ width: '100%' }}
              />
            </div>

            {/* 仅列表区域滚动，避免把搜索框滚出视口 */}
            <div
              style={{
                maxHeight: 320,
                overflowY: 'auto',
                paddingRight: 2,
              }}
            >
              {cluesLoading ? (
                <div style={{ textAlign: 'center', padding: '24px 0' }}>
                  <Spin size="small" />
                </div>
              ) : clues.length > 0 ? (
                <List
                  dataSource={filteredClues}
                  locale={{ emptyText: clueSearch.trim() ? '无匹配线索，换个关键词试试' : '暂无数据' }}
                  renderItem={(clue) => {
                    const isSelected = selectedClues.find(c => c.id === clue.id)
                    return (
                      <List.Item
                        style={{
                          cursor: 'pointer',
                          background: isSelected ? '#f0f5ff' : 'transparent',
                          borderRadius: 8,
                          padding: 10,
                          marginBottom: 6,
                          border: isSelected ? '1px solid #1890ff' : '1px solid #f0f0f0',
                          transition: 'all 0.2s',
                        }}
                        onClick={() => handleSelectClue(clue)}
                        onMouseEnter={(e) => {
                          if (!isSelected) e.currentTarget.style.background = '#fafafa'
                        }}
                        onMouseLeave={(e) => {
                          if (!isSelected) e.currentTarget.style.background = 'transparent'
                        }}
                      >
                        <Space>
                          <div style={{
                            width: 20,
                            height: 20,
                            borderRadius: 4,
                            background: isSelected ? '#1890ff' : '#f0f0f0',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: isSelected ? 'white' : '#8c8c8c',
                            fontSize: 12,
                          }}>
                            {isSelected ? <CheckCircleOutlined /> : null}
                          </div>
                          <div>
                            <Text 
                              strong 
                              style={{ 
                                fontSize: 13,
                                display: 'block',
                                maxWidth: 180,
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap'
                              }}
                            >
                              {clue.title}
                            </Text>
                            <Text type="secondary" style={{ fontSize: 11 }}>
                              {clue.category} · {new Date(clue.created_at).toLocaleDateString('zh-CN')}
                            </Text>
                          </div>
                        </Space>
                      </List.Item>
                    )
                  }}
                />
              ) : (
                <Empty description="暂无可用线索" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </div>

            {selectedClues.length > 0 && (
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                onClick={handleGenerateFromClues}
                block
                style={{ marginTop: 12 }}
              >
                基于 {selectedClues.length} 条线索生成
              </Button>
            )}
          </Card>

          {/* Recent Articles */}
          <Card
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: 6,
                    background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <HistoryOutlined style={{ fontSize: 14, color: 'white' }} />
                </div>
                <span style={{ fontWeight: 600, fontSize: 14 }}>最近生成</span>
              </div>
            }
            style={{ borderRadius: 12 }}
          >
            <div style={{ marginBottom: 12, flexShrink: 0 }}>
              <Space size={6} style={{ marginBottom: 8 }}>
                <SearchOutlined style={{ color: 'var(--app-primary, #c62828)' }} />
                <Text strong style={{ fontSize: 13 }}>
                  搜索历史稿件
                </Text>
              </Space>
              <Search
                allowClear
                placeholder="标题、作者、分类、正文关键词"
                value={articleSearch}
                onChange={(e) => setArticleSearch(e.target.value)}
                onSearch={(v) => setArticleSearch(v)}
                enterButton="搜索"
                style={{ width: '100%' }}
              />
            </div>
            <div style={{ maxHeight: 260, overflowY: 'auto', paddingRight: 2 }}>
              {generatedArticles.length > 0 ? (
                <List
                  dataSource={filteredGeneratedArticles}
                  locale={{ emptyText: articleSearch.trim() ? '无匹配稿件' : '暂无数据' }}
                  renderItem={(article) => (
                    <List.Item
                      style={{ padding: '8px 0' }}
                      actions={[
                        <Button
                          key="preview"
                          type="text"
                          icon={<EyeOutlined />}
                          size="small"
                          onClick={() => {
                            setPreviewArticleTitle(article.title || '')
                            setPreviewContent(article.content)
                            setPreviewVisible(true)
                          }}
                        />,
                      ]}
                    >
                      <div style={{ flex: 1, overflow: 'hidden' }}>
                        <Text 
                          strong 
                          style={{ 
                            fontSize: 13,
                            display: 'block',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }}
                        >
                          {article.title}
                        </Text>
                        <Space size={4}>
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            {article.author || 'AI 助手'}
                          </Text>
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            ·
                          </Text>
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            {new Date(article.created_at).toLocaleDateString('zh-CN')}
                          </Text>
                        </Space>
                      </div>
                    </List.Item>
                  )}
                />
              ) : (
                <Empty description="暂无生成记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </div>
          </Card>
        </Col>
      </Row>

      {/* Preview Modal */}
      <Modal
        title={
          <Space>
            <EyeOutlined />
            {previewArticleTitle ? `预览：${previewArticleTitle}` : '预览内容'}
          </Space>
        }
        open={previewVisible}
        onCancel={() => {
          setPreviewVisible(false)
          setPreviewArticleTitle('')
        }}
        width={800}
        footer={[
          <Button
            key="copy"
            icon={<CopyOutlined />}
            onClick={() =>
              copyToClipboard(
                previewArticleTitle
                  ? `【标题】${previewArticleTitle}\n\n${previewContent}`
                  : previewContent
              )
            }
          >
            复制
          </Button>,
          <Button
            key="close"
            type="primary"
            onClick={() => {
              setPreviewVisible(false)
              setPreviewArticleTitle('')
            }}
          >
            关闭
          </Button>,
        ]}
      >
        <Paragraph style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
          {previewContent}
        </Paragraph>
      </Modal>

      {/* Improve Content Modal */}
      <Modal
        title={
          <Space>
            <EditOutlined style={{ color: '#1890ff' }} />
            改进内容
          </Space>
        }
        open={improveModalVisible}
        onCancel={() => setImproveModalVisible(false)}
        width={700}
        footer={null}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Row gutter={16}>
            <Col span={12}>
              <Text strong>改进类型</Text>
              <Select
                value={improveType}
                onChange={setImproveType}
                style={{ width: '100%', marginTop: 4 }}
                options={[
                  { label: '润色 - 优化语言表达', value: 'polish' },
                  { label: '扩展 - 增加深度和细节', value: 'expand' },
                  { label: '精简 - 压缩冗余内容', value: 'condense' },
                  { label: '重写 - 改变结构和风格', value: 'rewrite' },
                ]}
              />
            </Col>
            <Col span={12}>
              <Text strong>重点方向（可选）</Text>
              <Select
                value={improveFocus}
                onChange={setImproveFocus}
                allowClear
                style={{ width: '100%', marginTop: 4 }}
                placeholder="不指定则全面改进"
                options={[
                  { label: '清晰度 - 语言更清晰易懂', value: 'clarity' },
                  { label: '深度 - 增加分析洞察', value: 'depth' },
                  { label: '吸引力 - 更生动可读', value: 'engagement' },
                  { label: '准确性 - 修正错误', value: 'accuracy' },
                ]}
              />
            </Col>
          </Row>
          <Button
            type="primary"
            icon={<RobotOutlined />}
            loading={improving}
            onClick={handleImproveContent}
            block
            size="large"
          >
            开始改进
          </Button>

          {improvedContent && (
            <>
              <Divider>改进结果</Divider>
              <Alert
                message="改进说明"
                description={
                  <ul style={{ margin: '8px 0', paddingLeft: 20 }}>
                    {improvedContent.notes.map((note, i) => (
                      <li key={i}>{note}</li>
                    ))}
                  </ul>
                }
                type="success"
                showIcon
              />
              <Card size="small" style={{ background: '#fafafa' }}>
                <Paragraph style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8, marginBottom: 0 }}>
                  {improvedContent.content}
                </Paragraph>
              </Card>
              <Space>
                <Button
                  icon={<CopyOutlined />}
                  onClick={() => {
                    copyToClipboard(improvedContent.content)
                    toast.success('已复制到剪贴板')
                  }}
                >
                  复制改进内容
                </Button>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={() => {
                    const titleToSave =
                      customTitle?.trim() ||
                      generatedContent?.suggested_titles?.[selectedTitleIndex] ||
                      generatedContent?.suggested_titles?.[0]
                    if (titleToSave) {
                      handleSaveArticle(titleToSave, improvedContent.content)
                      setImproveModalVisible(false)
                    }
                  }}
                >
                  保存为新稿件
                </Button>
              </Space>
            </>
          )}
        </Space>
      </Modal>
    </div>
  )
}

export default AIArticle
