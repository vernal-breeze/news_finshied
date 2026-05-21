import React, { useState, useEffect } from 'react'
import { Form, Input, Button, Card, Typography, Checkbox } from 'antd'
import { toast } from '../../components/common/Toast'
import { UserOutlined, LockOutlined, EditOutlined } from '@ant-design/icons'
import { useNavigate, Link, useSearchParams } from 'react-router-dom'
import { loginAndFetchUser, parseApiError, workspacePathForRole } from '../../services/authClient'
import './Login.css'

const { Title, Text, Paragraph } = Typography

interface LoginForm {
  username: string
  password: string
  remember: boolean
}

function isSafeInternalNext(path: string): boolean {
  if (!path.startsWith('/') || path.startsWith('//')) return false
  return path.startsWith('/reader') || path.startsWith('/editor')
}

const EditorLogin: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) return
    const nextRaw = searchParams.get('next')
    if (nextRaw && isSafeInternalNext(nextRaw)) {
      navigate(nextRaw, { replace: true })
      return
    }
    let role: string | undefined
    try {
      const u = JSON.parse(localStorage.getItem('user') || 'null') as { role?: string } | null
      role = typeof u?.role === 'string' ? u.role : undefined
    } catch {
      role = undefined
    }
    navigate(workspacePathForRole(role), { replace: true })
  }, [navigate, searchParams])

  const onFinish = async (values: LoginForm) => {
    setLoading(true)
    try {
      const { access_token, user } = await loginAndFetchUser(values.username, values.password)

      localStorage.setItem('token', access_token)
      localStorage.setItem('username', values.username)
      localStorage.setItem('user', JSON.stringify(user))
      window.dispatchEvent(new Event('auth-changed'))

      toast.success('登录成功')

      const nextRaw = searchParams.get('next')
      if (nextRaw && isSafeInternalNext(nextRaw)) {
        navigate(nextRaw, { replace: true })
      } else {
        navigate(workspacePathForRole(user.role as string | undefined))
      }
    } catch (error: unknown) {
      toast.error(parseApiError(error))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="editor-login-container">
      <div className="editor-login-background">
        <div className="editor-login-gradient" />
      </div>

      <Card className="editor-login-card" variant="borderless">
        <div className="editor-login-header">
          <div className="editor-login-logo">
            <EditOutlined className="editor-login-icon" />
          </div>
          <Title level={3} style={{ marginBottom: 8, textAlign: 'center' }}>
            新闻内容采编系统
          </Title>
          <Text type="secondary" style={{ fontSize: 16 }}>
            投稿端
          </Text>
        </div>

        <Form
          name="editor_login"
          onFinish={onFinish}
          autoComplete="off"
          size="large"
          initialValues={{ remember: true }}
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input
              prefix={<UserOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="用户名"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="密码"
            />
          </Form.Item>

          <Form.Item name="remember" valuePropName="checked">
            <Checkbox>记住我</Checkbox>
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{ height: 48, fontSize: 16 }}
            >
              登录
            </Button>
          </Form.Item>
        </Form>

        <div className="editor-login-footer">
          <Paragraph type="secondary" style={{ textAlign: 'center', marginBottom: 0 }}>
            <Text type="secondary">还没有账号？</Text>{' '}
            <Link to="/register">注册投稿账号</Link>
          </Paragraph>
          <Paragraph type="secondary" style={{ textAlign: 'center', marginTop: 8 }}>
            <Text type="secondary">
              审核端 <a href="/review/login">登录</a>
            </Text>
          </Paragraph>
        </div>
      </Card>
    </div>
  )
}

export default EditorLogin
