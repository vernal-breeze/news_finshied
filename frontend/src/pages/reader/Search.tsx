import React, { useState } from 'react'
import { 
  Input, Card, Typography, Space, Tag, Empty, 
  Spin, List, Select, Button, Divider
} from 'antd'
import { 
  SearchOutlined, ClockCircleOutlined, 
  EyeOutlined, FilterOutlined, AudioOutlined
} from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import dayjs from 'dayjs'
import { fetchPublicArticleList } from '../../services/readerApi'
import ReaderHeader from '../../components/reader/ReaderHeader'
import './Search.css'

const { Title, Text } = Typography
const { Search } = Input
const { Option } = Select

interface SearchResult {
  id: number
  title: string
  abstract: string
  category: string
  published_at: string
  view_count: number
  author: string
}

const categories = [
  { value: '', label: '全部分类' },
  { value: '科技', label: '科技' },
  { value: '财经', label: '财经' },
  { value: '社会', label: '社会' },
  { value: '文化', label: '文化' },
  { value: '体育', label: '体育' },
  { value: '时政', label: '时政' },
]

const hotKeywords = [
  '新能源汽车', '高考改革', '华为鸿蒙', '央行降准', 
  '亚运会', '人工智能', '数字经济', '碳中和'
]

const ReaderSearch: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const [keyword, setKeyword] = useState(searchParams.get('q') || '')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [category, setCategory] = useState('')
  const [hasSearched, setHasSearched] = useState(false)
  const navigate = useNavigate()

  const handleSearch = async (value: string) => {
    if (!value.trim()) return
    
    setKeyword(value)
    setSearchParams({ q: value })
    setLoading(true)
    setHasSearched(true)

    try {
      const list = await fetchPublicArticleList({
        search: value,
        category: category || undefined,
        page_size: 50,
      })
      setResults(list as SearchResult[])
    } catch (error) {
      // 使用模拟数据
      setResults(getMockResults(value))
    } finally {
      setLoading(false)
    }
  }

  const getMockResults = (kw: string): SearchResult[] => [
    {
      id: 1,
      title: `${kw}销量突破1000万辆，引领全球绿色转型`,
      abstract: `最新数据显示，2024年我国${kw}销量持续攀升，全年突破1000万辆大关，渗透率超过40%。`,
      category: '财经',
      published_at: dayjs().subtract(2, 'hour').toISOString(),
      view_count: 12580,
      author: '记者小明',
    },
    {
      id: 2,
      title: `${kw}相关政策解读：行业迎来新机遇`,
      abstract: `随着${kw}产业的快速发展，国家出台了一系列扶持政策，为行业注入新动力。`,
      category: '财经',
      published_at: dayjs().subtract(5, 'hour').toISOString(),
      view_count: 8960,
      author: '编辑小王',
    },
    {
      id: 3,
      title: `专家解读：${kw}发展趋势分析`,
      abstract: `多位行业专家表示，${kw}将成为未来经济增长的重要引擎，市场潜力巨大。`,
      category: '科技',
      published_at: dayjs().subtract(1, 'day').toISOString(),
      view_count: 5680,
      author: '记者小红',
    },
  ]

  const handleKeywordClick = (kw: string) => {
    setKeyword(kw)
    handleSearch(kw)
  }

  const handleCategoryChange = (value: string) => {
    setCategory(value)
    if (keyword) {
      handleSearch(keyword)
    }
  }

  return (
    <div className="reader-search">
      <ReaderHeader showSearch={false} />

      <main className="reader-search-main">
        {/* 搜索框 */}
        <Card className="search-box-card">
          <Search
            placeholder="输入关键词搜索新闻..."
            enterButton={
              <Button type="primary" icon={<SearchOutlined />}>
                搜索
              </Button>
            }
            size="large"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={handleSearch}
            allowClear
          />
          
          <Divider>热门搜索</Divider>
          <Space wrap size="middle">
            {hotKeywords.map(kw => (
              <Tag 
                key={kw}
                className="hot-keyword"
                onClick={() => handleKeywordClick(kw)}
              >
                <AudioOutlined /> {kw}
              </Tag>
            ))}
          </Space>
        </Card>

        {/* 筛选 */}
        <Card className="search-filter-card">
          <Space>
            <FilterOutlined />
            <Text>筛选：</Text>
            <Select
              placeholder="选择分类"
              style={{ width: 150 }}
              value={category || undefined}
              onChange={handleCategoryChange}
              allowClear
            >
              {categories.map(cat => (
                <Option key={cat.value} value={cat.value}>
                  {cat.label}
                </Option>
              ))}
            </Select>
          </Space>
        </Card>

        {/* 结果 */}
        <div className="search-results">
          {loading ? (
            <div className="reader-loading">
              <Spin size="large" />
              <Text>搜索中...</Text>
            </div>
          ) : hasSearched ? (
            results.length > 0 ? (
              <>
                <Text type="secondary" className="results-count">
                  找到 {results.length} 条相关结果
                </Text>
                <Card>
                  <List
                    dataSource={results}
                    renderItem={item => (
                      <List.Item 
                        className="search-result-item"
                        onClick={() => navigate(`/reader/article/${item.id}`)}
                      >
                        <List.Item.Meta
                          title={
                            <Title level={5} className="result-title">
                              {item.title}
                            </Title>
                          }
                          description={
                            <Space split={<Divider type="vertical" />}>
                              <Text type="secondary">{item.author}</Text>
                              <Text type="secondary">{item.category}</Text>
                              <Text type="secondary">
                                <ClockCircleOutlined /> {dayjs(item.published_at).fromNow()}
                              </Text>
                              <Text type="secondary">
                                <EyeOutlined /> {item.view_count.toLocaleString()}
                              </Text>
                            </Space>
                          }
                        />
                      </List.Item>
                    )}
                  />
                </Card>
              </>
            ) : (
              <Empty 
                description={
                  <Space direction="vertical">
                    <Text>未找到与 "{keyword}" 相关的新闻</Text>
                    <Text type="secondary">请尝试其他关键词或调整筛选条件</Text>
                  </Space>
                }
              />
            )
          ) : (
            <Empty description="输入关键词开始搜索" />
          )}
        </div>
      </main>

      {/* 页脚 */}
      <footer className="reader-footer">
        <Text type="secondary">
          © {new Date().getFullYear()} 新闻内容采编系统 · 基于大模型技术
        </Text>
      </footer>
    </div>
  )
}

export default ReaderSearch
