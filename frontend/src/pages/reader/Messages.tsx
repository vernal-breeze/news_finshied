import React, { useEffect, useState } from 'react'
import { Button, Empty, List, message, Modal, Typography, Input } from 'antd'
import { MessageOutlined, SendOutlined } from '@ant-design/icons'
import ReaderHeader from '../../components/reader/ReaderHeader'
import { fetchMessages, markMessageAsRead, sendMessageReply } from '../../services/readerApi'
import { Message } from '../../types'
import './Messages.css'

const { Text, Title } = Typography
const { TextArea } = Input

const Messages: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [replyModalVisible, setReplyModalVisible] = useState(false)
  const [replyingMessage, setReplyingMessage] = useState<Message | null>(null)
  const [replyContent, setReplyContent] = useState('')
  const [replying, setReplying] = useState(false)

  useEffect(() => {
    loadMessages()
  }, [])

  const loadMessages = async () => {
    try {
      setLoading(true)
      const data = await fetchMessages()
      setMessages(data as Message[])
    } catch (error) {
      console.error('获取消息失败:', error)
      message.error('获取消息失败')
    } finally {
      setLoading(false)
    }
  }

  const handleMessageClick = async (message: Message) => {
    if (!message.is_read) {
      try {
        await markMessageAsRead(message.id)
        setMessages(prev => prev.map(m => 
          m.id === message.id ? { ...m, is_read: true } : m
        ))
      } catch (error) {
        console.error('标记已读失败:', error)
      }
    }
  }

  const handleReply = (message: Message) => {
    setReplyingMessage(message)
    setReplyContent('')
    setReplyModalVisible(true)
  }

  const handleSendReply = async () => {
    if (!replyingMessage || !replyContent.trim()) return

    try {
      setReplying(true)
      await sendMessageReply(replyingMessage.id, replyContent.trim())
      message.success('回复成功')
      setReplyModalVisible(false)
      loadMessages() // 重新加载消息列表
    } catch (error) {
      console.error('发送回复失败:', error)
      message.error('发送回复失败')
    } finally {
      setReplying(false)
    }
  }

  const getMessageTypeIcon = (type: Message['type']) => {
    switch (type) {
      case 'interaction':
        return <MessageOutlined className="message-type-icon interaction" />
      case 'system':
        return <MessageOutlined className="message-type-icon system" />
      case 'notification':
        return <MessageOutlined className="message-type-icon notification" />
      default:
        return <MessageOutlined className="message-type-icon" />
    }
  }

  const getMessageTypeText = (type: Message['type']) => {
    switch (type) {
      case 'interaction':
        return '互动消息'
      case 'system':
        return '系统消息'
      case 'notification':
        return '通知消息'
      default:
        return '消息'
    }
  }

  return (
    <div className="messages-page">
      <ReaderHeader variant="article" />
      <div className="messages-content">
        <div className="messages-header">
          <Title level={4}>消息中心</Title>
          <Text type="secondary">查看和回复您收到的消息</Text>
        </div>
        <div className="messages-list">
          {loading ? (
            <div className="loading-state">加载中...</div>
          ) : messages.length > 0 ? (
            <List
              dataSource={messages}
              key="id"
              renderItem={(message) => (
                <List.Item
                  key={message.id}
                  className={`message-item ${message.is_read ? 'read' : 'unread'}`}
                  onClick={() => handleMessageClick(message)}
                >
                  <List.Item.Meta
                    avatar={getMessageTypeIcon(message.type)}
                    title={
                      <div className="message-title">
                        <Text strong>{getMessageTypeText(message.type)}</Text>
                        {!message.is_read && <span className="unread-badge">未读</span>}
                      </div>
                    }
                    description={
                      <div className="message-description">
                        <Text>{message.content}</Text>
                        <Text type="secondary" className="message-time">
                          {new Date(message.created_at).toLocaleString()}
                        </Text>
                      </div>
                    }
                  />
                  <Button
                    type="link"
                    icon={<SendOutlined />}
                    onClick={(e) => {
                      e.stopPropagation()
                      handleReply(message)
                    }}
                  >
                    回复
                  </Button>
                </List.Item>
              )}
            />
          ) : (
            <Empty
              description="暂无消息"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          )}
        </div>
      </div>

      <Modal
        title="回复消息"
        open={replyModalVisible}
        onCancel={() => setReplyModalVisible(false)}
        onOk={handleSendReply}
        okText="发送"
        cancelText="取消"
        okButtonProps={{ loading: replying }}
      >
        {replyingMessage && (
          <div className="reply-modal-content">
            <div className="original-message">
              <Text strong>原始消息:</Text>
              <Text>{replyingMessage.content}</Text>
              <Text type="secondary" className="message-time">
                {new Date(replyingMessage.created_at).toLocaleString()}
              </Text>
            </div>
            <div className="reply-input">
              <TextArea
                rows={4}
                placeholder="请输入回复内容"
                value={replyContent}
                onChange={(e) => setReplyContent(e.target.value)}
              />
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default Messages