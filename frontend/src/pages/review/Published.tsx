import React, { useState, useEffect } from 'react'
import { Table, Card, Tag, Button, Space, Typography, Input, Select, Popconfirm } from 'antd'
import { SearchOutlined, EyeOutlined, DeleteOutlined, ReloadOutlined, GlobalOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import api, { articleAPI } from '../../services/api'
import { toast } from '../../components/common/Toast'
import './Published.css'

const { Title, Text } = Typography

interface PublishedArticle {
  id: number
  title: string
  author: string
  category: string
  tags: string[]
  published_at: string
  view_count?: number
  status: string
}

const Published: React.FC = () => {
  const [articles, setArticles] = useState<PublishedArticle[]>([])
  const [loading, setLoading] = useState(true)
  const [searchText, setSearchText] = useState('')
  const [category, setCategory] = useState<string | undefined>()
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    fetchPublishedArticles()
  }, [refreshKey])

  const fetchPublishedArticles = async () => {
    setLoading(true)
    try {
      const res = (await api.get('/api/public/articles', {
        params: {
          page: 1,
          page_size: 100,
        },
      })) as { code?: number; data?: PublishedArticle[] }
      if (res.code === 200 || Array.isArray(res.data)) {
        setArticles(Array.isArray(res.data) ? res.data : [])
      }
    } catch (error) {
      console.error('获取已发布稿件失败:', error)
      toast.error('获取已发布稿件失败')
    } finally {
      setLoading(false)
    }
  }

  const handleViewArticle = (id: number) => {
    // 打开文章详情页（读者端）
    window.open(`/reader/article/${id}`, '_blank')
  }

  const handleOffline = async (id: number) => {
    try {
      await articleAPI.delete(id)
      toast.success('已下线')
      setRefreshKey(k => k + 1)
    } catch (error) {
      toast.error('下线失败')
    }
  }

  const filteredArticles = articles.filter(article => {
    const matchSearch = !searchText || article.title.toLowerCase().includes(searchText.toLowerCase())
    const matchCategory = !category || article.category === category
    return matchSearch && matchCategory
  })

  const columns: ColumnsType<PublishedArticle> = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (text, record) => (
        <div>
          <Text strong>{text}</Text>
          <div>
            <Tag color="blue">{record.category}</Tag>
            {record.tags?.slice(0, 2).map((tag, i) => (
              <Tag key={i} style={{ marginRight: 4 }}>{tag}</Tag>
            ))}
          </div>
        </div>
      ),
    },
    {
      title: '作者',
      dataIndex: 'author',
      key: 'author',
      width: 100,
    },
    {
      title: '发布时间',
      dataIndex: 'published_at',
      key: 'published_at',
      width: 150,
      render: (time) => time ? dayjs(time).format('YYYY-MM-DD HH:mm') : '-',
      sorter: (a, b) => dayjs(a.published_at || 0).unix() - dayjs(b.published_at || 0).unix(),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record) => (
        <Space>
          <Button 
            type="link" 
            icon={<EyeOutlined />} 
            onClick={() => handleViewArticle(record.id)}
          >
            查看
          </Button>
          <Button 
            type="link" 
            icon={<GlobalOutlined />}
            onClick={() => handleViewArticle(record.id)}
          >
            访问网页
          </Button>
          <Popconfirm
            title="确定要下线这篇文章吗？"
            onConfirm={() => handleOffline(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              下线
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className="published-container">
      <div className="published-header">
        <Title level={2}>发布管理</Title>
        <Text type="secondary">查看和管理已发布的稿件，点击"访问网页"可在浏览器中查看</Text>
      </div>

      <Card>
        <div className="published-filters" style={{ marginBottom: 16 }}>
          <Space wrap>
            <Input
              placeholder="搜索标题"
              prefix={<SearchOutlined />}
              style={{ width: 200 }}
              allowClear
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
            />
            <Select 
              placeholder="选择分类" 
              style={{ width: 120 }} 
              allowClear
              value={category}
              onChange={setCategory}
            >
              <Select.Option value="科技">科技</Select.Option>
              <Select.Option value="财经">财经</Select.Option>
              <Select.Option value="教育">教育</Select.Option>
              <Select.Option value="体育">体育</Select.Option>
              <Select.Option value="社会">社会</Select.Option>
              <Select.Option value="娱乐">娱乐</Select.Option>
            </Select>
            <Button 
              icon={<ReloadOutlined />}
              onClick={() => setRefreshKey(k => k + 1)}
            >
              刷新
            </Button>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={filteredArticles}
          rowKey="id"
          loading={loading}
          pagination={{ 
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 篇`
          }}
        />
      </Card>
    </div>
  )
}

export default Published