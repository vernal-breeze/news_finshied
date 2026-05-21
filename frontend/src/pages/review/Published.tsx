import React, { useState, useEffect } from 'react'
import { Table, Card, Tag, Button, Space, Typography, Input, Select, Modal } from 'antd'
import { SearchOutlined, EyeOutlined, DeleteOutlined, ReloadOutlined, GlobalOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import api, { articleAPI } from '../../services/api'
import { toast } from '../../components/common/Toast'
import './Published.css'

const { Title, Text } = Typography
const { TextArea } = Input

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

  // 下线弹窗
  const [unpublishModalOpen, setUnpublishModalOpen] = useState(false)
  const [unpublishArticleId, setUnpublishArticleId] = useState<number | null>(null)
  const [unpublishReason, setUnpublishReason] = useState('')
  const [unpublishing, setUnpublishing] = useState(false)

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
    window.open(`/reader/article/${id}`, '_blank')
  }

  const handleUnpublish = async () => {
    if (!unpublishArticleId) return
    if (!unpublishReason.trim()) {
      toast.error('请填写下线理由')
      return
    }
    setUnpublishing(true)
    try {
      await articleAPI.unpublish(unpublishArticleId, unpublishReason.trim())
      toast.success('已下线')
      setUnpublishModalOpen(false)
      setUnpublishArticleId(null)
      setUnpublishReason('')
      setRefreshKey(k => k + 1)
    } catch (error) {
      toast.error('下线失败')
    } finally {
      setUnpublishing(false)
    }
  }

  const openUnpublishModal = (id: number) => {
    setUnpublishArticleId(id)
    setUnpublishReason('')
    setUnpublishModalOpen(true)
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
          <Button 
            type="link" 
            danger 
            icon={<DeleteOutlined />}
            onClick={() => openUnpublishModal(record.id)}
          >
            下线
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div className="published-container">
      <div className="published-header">
        <Title level={2}>发布管理</Title>
        <Text type="secondary">查看和管理已发布的稿件，下线时需要填写理由</Text>
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

      <Modal
        title="下线确认"
        open={unpublishModalOpen}
        onOk={handleUnpublish}
        onCancel={() => { setUnpublishModalOpen(false); setUnpublishReason('') }}
        confirmLoading={unpublishing}
        okText="确认下线"
        cancelText="取消"
        okButtonProps={{ danger: true }}
      >
        <div style={{ marginBottom: 8 }}>
          <Text type="secondary">请填写下线理由，作者将收到通知后进行修改并重新提交：</Text>
        </div>
        <TextArea
          placeholder="例如：标题与内容不符、数据有误、配图不当..."
          rows={3}
          value={unpublishReason}
          onChange={e => setUnpublishReason(e.target.value)}
        />
      </Modal>
    </div>
  )
}

export default Published
