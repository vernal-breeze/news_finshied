import React, { useEffect, useState } from 'react'
import { Badge, Button, Dropdown, Typography } from 'antd'
import type { MenuProps } from 'antd'
import {
  DashboardOutlined,
  LeftOutlined,
  LoginOutlined,
  LogoutOutlined,
  MessageOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthSnapshot } from '../../hooks/useAuthSnapshot'
import { workspacePathForRole } from '../../services/authClient'
import { fetchUnreadMessageCount } from '../../services/readerApi'
import './ReaderHeader.css'

const { Text } = Typography

/** 无用户名时的头像占位：简洁「文档/阅读」意象，优于单字「读」 */
const ReaderAvatarPlaceholderIcon: React.FC = () => (
  <svg
    className="reader-user-avatar-icon"
    width={15}
    height={15}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden
  >
    <path
      d="M7 3h10a2 2 0 012 2v16l-7-3.5L5 21V5a2 2 0 012-2z"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinejoin="round"
    />
    <path d="M9 8h6M9 12h4" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" />
  </svg>
)

export interface ReaderHeaderProps {
  /** 文章页：左侧显示返回 */
  variant?: 'default' | 'article'
  /** 搜索页等可关闭 */
  showSearch?: boolean
  /** 文章页右侧工具（打印、分享等） */
  extra?: React.ReactNode
}

const ReaderHeader: React.FC<ReaderHeaderProps> = ({
  variant = 'default',
  showSearch = true,
  extra,
}) => {
  const navigate = useNavigate()
  const { isLoggedIn, user, role } = useAuthSnapshot()
  const [scrolled, setScrolled] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)

  const rawName = (user?.full_name || user?.username || '').trim()
  const displayName = rawName || '用户'
  const avatarLetter = rawName.slice(0, 1)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    const loadUnreadCount = async () => {
      if (isLoggedIn) {
        try {
          const count = await fetchUnreadMessageCount()
          setUnreadCount(count)
        } catch (error) {
          console.error('获取未读消息失败:', error)
        }
      } else {
        setUnreadCount(0)
      }
    }

    loadUnreadCount()

    // 监听认证状态变化
    const handleAuthChange = () => {
      loadUnreadCount()
    }

    window.addEventListener('auth-changed', handleAuthChange)
    return () => window.removeEventListener('auth-changed', handleAuthChange)
  }, [isLoggedIn])
  const workspace = workspacePathForRole(role)
  const workspaceLabel = role === 'reviewer' ? '审核工作台' : '采编工作台'

  const onLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('username')
    window.dispatchEvent(new Event('auth-changed'))
    navigate('/reader', { replace: true })
  }

  const menuItems: MenuProps['items'] = [
    {
      key: 'workspace',
      icon: <DashboardOutlined />,
      label: workspaceLabel,
      onClick: () => navigate(workspace),
    },
    { type: 'divider' },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
      onClick: onLogout,
    },
  ]

  return (
    <header
      className={`reader-header reader-header-fixed reader-header--${variant}${scrolled ? ' reader-header--scrolled' : ''}`}
    >
      <div className="reader-header-content">
        <div className="reader-header-left">
          {variant === 'article' && (
            <Button
              type="text"
              icon={<LeftOutlined />}
              onClick={() => navigate('/reader')}
              className="reader-header-back"
            >
              返回
            </Button>
          )}
          <button
            type="button"
            className="reader-brand"
            onClick={() => navigate('/reader')}
          >
            <span className="reader-brand-mark" aria-hidden />
            <div className="reader-brand-text">
              <Text className="reader-logo">新闻资讯</Text>
              {variant === 'default' && (
                <Text type="secondary" className="reader-tagline">
                  智能采编 · 权威速递
                </Text>
              )}
            </div>
          </button>
        </div>

        <div className="reader-header-actions">
          {extra}
          {showSearch && (
            <Button
              type="text"
              icon={<SearchOutlined />}
              onClick={() => navigate('/reader/search')}
              className="reader-header-icon-btn"
            >
              搜索
            </Button>
          )}
          {isLoggedIn && (
            <Badge count={unreadCount} showZero={false}>
              <Button
                type="text"
                icon={<MessageOutlined />}
                onClick={() => navigate('/reader/messages')}
                className="reader-header-icon-btn"
              >
                消息
              </Button>
            </Badge>
          )}
          {isLoggedIn ? (
            <Dropdown menu={{ items: menuItems }} placement="bottomRight" trigger={['click']}>
              <button type="button" className="reader-user-chip" aria-haspopup="menu">
                <span className="reader-user-avatar">
                  {avatarLetter ? avatarLetter : <ReaderAvatarPlaceholderIcon />}
                </span>
                <span className="reader-user-name">{displayName}</span>
              </button>
            </Dropdown>
          ) : (
            <Button
              type="text"
              icon={<LoginOutlined />}
              onClick={() => navigate('/login')}
              className="reader-header-icon-btn"
            >
              登录
            </Button>
          )}
        </div>
      </div>
    </header>
  )
}

export default ReaderHeader
