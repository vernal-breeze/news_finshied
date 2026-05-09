import React, { useState } from 'react'
import { Layout, Menu, theme, Typography, Badge, Tooltip, Dropdown } from 'antd'

interface Notification {
  id: number
  title: string
  content: string
  time: string
  read: boolean
}
import { toast } from '../common/Toast'
import { useNavigate, useLocation } from 'react-router-dom'
import type { MenuProps } from 'antd'
import {
  HomeOutlined,
  FileTextOutlined,
  BulbOutlined,

  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  CheckCircleOutlined,
  BarChartOutlined,
  RobotOutlined,
  BellOutlined,
  SettingOutlined,
  LogoutOutlined,
  QuestionCircleOutlined,
  GlobalOutlined,
  FlagOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'

const { Header, Sider, Content } = Layout
const { Title, Text } = Typography

interface MainLayoutProps {
  children: React.ReactNode
}

type MenuItem = Required<MenuProps>['items'][number]

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const {
    token: { colorBgContainer, colorText },
  } = theme.useToken()

  // Notification state
  const [notifications, setNotifications] = useState<Notification[]>([])
  const unreadCount = notifications.filter(n => !n.read).length

  // Get user role from localStorage
  const userStr = localStorage.getItem('user')
  const userRole = userStr ? JSON.parse(userStr).role : 'user'

  // Active article/pending review counts for badges
  const pendingCount = 0 // This would come from API in real app

  // 投稿用户(user)不显示审核管理，审核员(reviewer)不显示选题策划
  const menuItems: MenuItem[] = [
    {
      key: '/editor',
      icon: <HomeOutlined />,
      label: '首页',
    },
    {
      key: '/editor/clues',
      icon: <BulbOutlined />,
      label: (
        <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          新闻线索
          {pendingCount > 0 && (
            <Badge count={pendingCount} size="small" style={{ marginLeft: 8 }} />
          )}
        </span>
      ),
    },
    userRole !== 'reviewer'
      ? {
          key: '/editor/topics',
          icon: <FlagOutlined />,
          label: '选题策划',
        }
      : null,
    {
      key: '/editor/ai-article',
      icon: <RobotOutlined />,
      label: 'AI稿件生成',
    },
    {
      key: '/editor/articles',
      icon: <FileTextOutlined />,
      label: '稿件管理',
    },
    {
      key: '/editor/analytics',
      icon: <BarChartOutlined />,
      label: '反馈分析',
    },
    // 只有审核员才能看到审核管理
    userRole === 'reviewer' ? {
      key: '/review',
      icon: <CheckCircleOutlined />,
      label: '审核管理',
    } : null,
    {
      key: 'reader-portal',
      icon: <GlobalOutlined />,
      label: '读者端',
    },
  ].filter(Boolean) as MenuItem[]

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人中心',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
    },
    {
      type: 'divider',
    },
    {
      key: 'help',
      icon: <QuestionCircleOutlined />,
      label: '帮助文档',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ]

  const notificationItems: MenuProps['items'] = [
    ...notifications.map(n => ({
      key: `notif-${n.id}`,
      label: (
        <div style={{ padding: '8px 0', opacity: n.read ? 0.6 : 1, maxWidth: 260 }}>
          <div style={{ fontWeight: n.read ? 400 : 600, marginBottom: 4 }}>{n.title}</div>
          <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>{n.content}</div>
          <div style={{ fontSize: 11, color: '#999' }}>{dayjs(n.time).fromNow()}</div>
        </div>
      ),
    })),
    { type: 'divider' as const },
    {
      key: 'mark-all-read',
      label: <div style={{ textAlign: 'center', color: 'var(--app-primary)' }}>全部标为已读</div>,
    },
  ]

  const handleNotificationClick = ({ key }: { key: string }) => {
    if (key === 'mark-all-read') {
      setNotifications(prev => prev.map(n => ({ ...n, read: true })))
    } else if (key.startsWith('notif-')) {
      const id = parseInt(key.replace('notif-', ''))
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
    }
  }

  const handleUserMenu: MenuProps['onClick'] = ({ key }) => {
    if (key === 'logout') {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      localStorage.removeItem('username')
      window.dispatchEvent(new Event('auth-changed'))
      toast.success('已退出登录')
      navigate('/login')
      return
    }
    if (key === 'profile') {
      toast.info('个人中心功能开发中')
      return
    }
    if (key === 'settings') {
      toast.info('系统设置功能开发中')
      return
    }
    if (key === 'help') {
      toast.info('帮助文档整理中，请联系管理员')
    }
  }

  // Get user info
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  const userName = user.full_name || user.username || '用户'
  const userRoleText = user.role === 'user' ? '投稿用户' : user.role === 'reviewer' ? '审核员' : '编辑'

  // Get page title based on current path
  const getPageTitle = () => {
    const pathMap: Record<string, string> = {
      '/editor': '首页',
      '/editor/clues': '新闻线索管理',
      '/editor/topics': '选题策划',
      '/editor/ai-article': 'AI稿件生成',
      '/editor/articles': '稿件管理',
      '/review': '审核管理',
      '/editor/analytics': '反馈分析',
    }
    return pathMap[location.pathname] || '新闻内容采编系统'
  }

  return (
    <Layout style={{ minHeight: '100vh', background: 'var(--app-bg)' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={220}
        style={{
          background: 'var(--app-sider-bg)',
          transition: 'all 0.3s cubic-bezier(0.645, 0.045, 0.355, 1)',
          overflow: 'hidden',
          boxShadow: 'none',
          borderRight: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        {/* Logo Area */}
        <div
          style={{
            height: 64,
            margin: 0,
            background: 'transparent',
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? 0 : '0 20px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          }}
        >
          <Tooltip title={collapsed ? '新闻采编系统' : ''} placement="right">
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              cursor: 'pointer',
              transition: 'all 0.3s',
            }}>
              <div style={{
                width: 36,
                height: 36,
                borderRadius: 8,
                background: 'var(--app-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}>
                <FileTextOutlined style={{ fontSize: 18, color: 'white' }} />
              </div>
              {!collapsed && (
                <div style={{ overflow: 'hidden' }}>
                  <span style={{
                    color: 'white',
                    fontWeight: 600,
                    fontSize: 15,
                    letterSpacing: '0.02em',
                    whiteSpace: 'nowrap',
                  }}>
                    新闻采编
                  </span>
                  <Text style={{ 
                    display: 'block', 
                    fontSize: 11, 
                    color: 'rgba(255,255,255,0.42)',
                    marginTop: 2,
                  }}>
                    News Editing
                  </Text>
                </div>
              )}
            </div>
          </Tooltip>
        </div>

        {/* Navigation Menu */}
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => {
            if (key === 'reader-portal') {
              window.open('/reader', '_blank', 'noopener,noreferrer')
              return
            }
            navigate(key)
          }}
          style={{
            marginTop: 8,
            height: 'calc(100vh - 64px - 48px)',
            borderRight: 0,
            background: 'transparent',
            overflowY: 'auto',
            overflowX: 'hidden',
          }}
        />

        {/* Collapsed indicator at bottom */}
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            height: 48,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            cursor: 'pointer',
          }}
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? (
            <Tooltip title="展开菜单" placement="right">
              <MenuUnfoldOutlined style={{ fontSize: 16, color: 'rgba(255,255,255,0.65)' }} />
            </Tooltip>
          ) : (
            <Text style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>
              点击收起
            </Text>
          )}
        </div>
      </Sider>

      <Layout>
        {/* Header */}
        <Header
          style={{
            padding: '0 28px',
            background: colorBgContainer,
            borderBottom: '1px solid var(--app-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            zIndex: 10,
            boxShadow: 'none',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {/* Collapse Button */}
            <Tooltip title={collapsed ? '展开菜单' : '收起菜单'}>
              <div
                onClick={() => setCollapsed(!collapsed)}
                style={{
                  fontSize: 18,
                  color: colorText,
                  cursor: 'pointer',
                  padding: 8,
                  borderRadius: 6,
                  transition: 'all 0.3s',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
                className="hover-bg-gray"
              >
                {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              </div>
            </Tooltip>

            {/* Breadcrumb / Page Title */}
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 8,
              paddingLeft: 16,
              borderLeft: '1px solid var(--app-border)',
            }}>
              <Title level={4} style={{
                margin: 0,
                color: colorText,
                fontSize: 16,
                fontWeight: 600,
                letterSpacing: '-0.01em',
              }}>
                {getPageTitle()}
              </Title>
            </div>
          </div>

          {/* Right Side - Notifications & User */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {/* Notifications */}
            <Dropdown 
              menu={{ items: notificationItems, onClick: handleNotificationClick }}
              placement="bottomRight"
              trigger={['click']}
            >
              <Tooltip title="通知中心">
                <div
                  style={{
                    padding: 8,
                    borderRadius: 8,
                    cursor: 'pointer',
                    transition: 'all 0.3s',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                  className="hover-bg-gray"
                >
                  <Badge count={unreadCount} size="small" offset={[-2, 2]}>
                    <BellOutlined style={{ fontSize: 18, color: colorText }} />
                  </Badge>
                </div>
              </Tooltip>
            </Dropdown>

            {/* User Dropdown */}
            <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenu }} placement="bottomRight" trigger={['click']}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                padding: '4px 12px 4px 4px',
                background: '#faf7f7',
                borderRadius: 10,
                border: '1px solid var(--app-border)',
                gap: 10,
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              className="hover-bg-gray"
              >
                <div style={{
                  width: 32,
                  height: 32,
                  borderRadius: '50%',
                  background: 'var(--app-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <UserOutlined style={{ fontSize: 15, color: 'white' }} />
                </div>
                <div>
                  <Text style={{
                    display: 'block',
                    fontSize: 13,
                    fontWeight: 600,
                    lineHeight: 1.2,
                    color: colorText,
                  }}>
                    {userName}
                  </Text>
                  <Text style={{
                    display: 'block',
                    fontSize: 11,
                    color: 'var(--app-text-muted)',
                    lineHeight: 1.2,
                  }}>
                    {userRoleText}
                  </Text>
                </div>
              </div>
            </Dropdown>
          </div>
        </Header>

        {/* Main Content */}
        <Content
          style={{
            margin: '20px 24px 24px',
            padding: 0,
            minHeight: 280,
            background: 'transparent',
          }}
        >
          {children}
        </Content>

        {/* Footer */}
        <div
          style={{
            padding: '14px 24px',
            textAlign: 'center',
            borderTop: '1px solid var(--app-border)',
            background: colorBgContainer,
          }}
        >
          <Text type="secondary" style={{ fontSize: 12, color: 'var(--app-text-muted)' }}>
            新闻内容采编系统 © {new Date().getFullYear()} · 基于 AI 智能驱动
          </Text>
        </div>
      </Layout>

      {/* Global Styles for Hover Effects */}
      <style>{`
        .hover-bg-gray:hover {
          background: rgba(198, 40, 40, 0.06);
        }
        .ant-menu-dark .ant-menu-item-selected::after {
          display: none;
        }
      `}</style>
    </Layout>
  )
}

export default MainLayout
