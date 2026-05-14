import React, { useEffect, useState } from 'react'
import { Layout, Menu, Avatar, Dropdown, Badge, Space, Typography, Button, Tooltip } from 'antd'
import { toast } from '../common/Toast'
import { 
  RobotOutlined, CheckCircleOutlined, FileTextOutlined,
  SettingOutlined, LogoutOutlined, UserOutlined, BellOutlined, GlobalOutlined
} from '@ant-design/icons'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import dayjs from 'dayjs'
import type { MenuProps } from 'antd'
import { fetchMessages, fetchUnreadMessageCount, markMessageAsRead } from '../../services/readerApi'
import './ReviewLayout.css'

const { Header, Sider, Content } = Layout
const { Text } = Typography

interface Notification {
  id: number
  title: string
  content: string
  time: string
  read: boolean
  related_id?: number
  related_type?: string
}

const ReviewLayout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)

  const user = JSON.parse(localStorage.getItem('user') || '{}')

  const menuItems = [
    {
      key: '/review',
      icon: <RobotOutlined />,
      label: 'AI审核',
    },
    {
      key: '/review/queue',
      icon: <FileTextOutlined />,
      label: '人工审核',
    },
    {
      key: '/review/published',
      icon: <CheckCircleOutlined />,
      label: '已发布',
    },
    {
      key: '/review/settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
  ]

  useEffect(() => {
    let mounted = true

    const loadNotifications = async () => {
      try {
        const [count, items] = await Promise.all([
          fetchUnreadMessageCount(),
          fetchMessages({ page: 1, page_size: 5 }),
        ])
        if (!mounted) return

        setUnreadCount(count)
        setNotifications(
          (items as Array<any>).map((item) => ({
            id: item.id,
            title: item.type === 'notification' ? '审核通知' : item.type === 'interaction' ? '互动消息' : '系统消息',
            content: item.content,
            time: item.created_at,
            read: Boolean(item.is_read),
            related_id: item.related_id,
            related_type: item.related_type,
          }))
        )
      } catch {
        if (!mounted) return
        setUnreadCount(0)
        setNotifications([])
      }
    }

    loadNotifications()
    window.addEventListener('auth-changed', loadNotifications)
    window.addEventListener('focus', loadNotifications)

    return () => {
      mounted = false
      window.removeEventListener('auth-changed', loadNotifications)
      window.removeEventListener('focus', loadNotifications)
    }
  }, [])

  const notificationItems: MenuProps['items'] = [
    ...notifications.map(n => ({
      key: `notification-${n.id}`,
      label: (
        <div style={{ 
          padding: '8px 0', 
          opacity: n.read ? 0.6 : 1,
          maxWidth: 280,
        }}>
          <div style={{ fontWeight: n.read ? 400 : 600, marginBottom: 4 }}>
            {n.title}
          </div>
          <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
            {n.content}
          </div>
          <div style={{ fontSize: 11, color: '#999' }}>
            {dayjs(n.time).fromNow()}
          </div>
        </div>
      ),
    })),
    ...(
      notifications.length
        ? [{ type: 'divider' as const }]
        : [{
            key: 'empty',
            disabled: true,
            label: <div style={{ padding: '8px 0', color: '#999', textAlign: 'center' }}>暂无通知</div>,
          }]
    ),
    { type: 'divider' as const },
    {
      key: 'mark-all-read',
      label: <div style={{ textAlign: 'center', color: 'var(--app-primary)' }}>全部标为已读</div>,
    },
    {
      key: 'open-review-queue',
      label: <div style={{ textAlign: 'center', color: 'var(--app-primary)' }}>查看审核队列</div>,
    },
  ]

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人信息',
    },
    { type: 'divider' as const },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
    },
  ]

  const handleNotificationClick = async ({ key }: { key: string }) => {
    if (key === 'mark-all-read') {
      const unread = notifications.filter((n) => !n.read)
      await Promise.all(unread.map((item) => markMessageAsRead(item.id).catch(() => undefined)))
      setUnreadCount(0)
      setNotifications(prev => prev.map(n => ({ ...n, read: true })))
      toast.success('已全部标为已读')
    } else if (key === 'open-review-queue') {
      navigate('/review/queue')
    } else if (key.startsWith('notification-')) {
      const id = parseInt(key.replace('notification-', ''))
      await markMessageAsRead(id).catch(() => undefined)
      const target = notifications.find((n) => n.id === id)
      if (target && !target.read) {
        setUnreadCount((prev) => Math.max(prev - 1, 0))
      }
      setNotifications(prev => prev.map(n =>
        n.id === id ? { ...n, read: true } : n
      ))
      if (target?.related_type === 'article' && target.related_id) {
        navigate('/review/queue')
      }
    }
  }

  const handleMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.dispatchEvent(new Event('auth-changed'))
      navigate('/review/login')
    } else if (key === 'profile') {
      navigate('/review/profile')
    } else {
      navigate(key)
    }
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        className="review-sider"
        width={240}
        theme="light"
        style={{
          borderRight: '1px solid var(--app-border)',
          background: '#faf8f8',
        }}
      >
        <div className="review-logo">
          <CheckCircleOutlined className="review-logo-icon" />
          <span>审核端</span>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0 }}
        />
      </Sider>
      
      <Layout>
        <Header className="review-header">
          <div className="review-header-left">
            <span className="review-page-title">
              {menuItems.find(item => item.key === location.pathname)?.label || '新闻审核系统'}
            </span>
          </div>
          <div className="review-header-right">
            <Space size="middle" align="center">
              <Button
                type="text"
                icon={<GlobalOutlined />}
                onClick={() => window.open('/reader', '_blank', 'noopener,noreferrer')}
              >
                读者端
              </Button>
              <Dropdown
                menu={{
                  items: notificationItems,
                  onClick: handleNotificationClick,
                }}
                placement="bottomRight"
                trigger={['click']}
              >
                <Tooltip title="通知">
                  <span className="review-header-icon">
                    <Badge count={unreadCount} size="small" offset={[-2, 2]}>
                      <BellOutlined style={{ fontSize: 18 }} />
                    </Badge>
                  </span>
                </Tooltip>
              </Dropdown>
              <Dropdown
                menu={{
                  items: userMenuItems,
                  onClick: handleMenuClick,
                }}
                placement="bottomRight"
                trigger={['click']}
              >
                <div className="review-header-user" role="presentation">
                  <Avatar
                    size={32}
                    style={{ background: 'var(--app-primary)' }}
                    icon={<UserOutlined />}
                  />
                  <Text ellipsis strong style={{ fontSize: 13 }}>
                    {user.full_name || user.username || '审核员'}
                  </Text>
                </div>
              </Dropdown>
            </Space>
          </div>
        </Header>
        
        <Content className="review-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default ReviewLayout
