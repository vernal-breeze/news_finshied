import React, { useState } from 'react'
import { Form, Input, Button, Card, Typography } from 'antd'
import { toast } from '../../components/common/Toast'
import { UserOutlined, LockOutlined, MailOutlined, IdcardOutlined } from '@ant-design/icons'
import { Link, useNavigate } from 'react-router-dom'
import { registerAccount, parseApiError } from '../../services/authClient'
import './Login.css'

const { Title, Text, Paragraph } = Typography

interface RegForm {
  username: string
  email: string
  password: string
  nickname?: string
}

const Register: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const onFinish = async (values: RegForm) => {
    setLoading(true)
    try {
      await registerAccount({
        username: values.username.trim(),
        email: values.email.trim(),
        password: values.password,
        nickname: values.nickname?.trim() || undefined,
      })
      toast.success('注册成功，请登录')
      navigate('/login', { replace: true })
    } catch (error: unknown) {
      toast.error(parseApiError(error))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="editor-login-container">
      <Card className="editor-login-card" variant="borderless">
        <div className="editor-login-header">
          <Title level={3} style={{ marginBottom: 8, textAlign: 'center' }}>
            注册投稿账号
          </Title>
          <Text type="secondary" style={{ fontSize: 15 }}>
            登录 ID 用于登录；昵称为对外展示，可填中文
          </Text>
        </div>

        <Form name="register" onFinish={onFinish} autoComplete="off" size="large" layout="vertical">
          <Form.Item
            label="登录 ID（英文/数字/下划线）"
            name="username"
            rules={[{ required: true, message: '请设置登录 ID' }]}
          >
            <Input prefix={<IdcardOutlined style={{ color: '#a8a29e' }} />} placeholder="例如 my_reporter_01" />
          </Form.Item>

          <Form.Item
            label="对外昵称（可选）"
            name="nickname"
          >
            <Input prefix={<UserOutlined style={{ color: '#a8a29e' }} />} placeholder="读者端评论等展示名" maxLength={50} />
          </Form.Item>

          <Form.Item
            label="邮箱"
            name="email"
            rules={[{ required: true, type: 'email', message: '请输入有效邮箱' }]}
          >
            <Input prefix={<MailOutlined style={{ color: '#a8a29e' }} />} placeholder="邮箱" />
          </Form.Item>

          <Form.Item
            label="密码"
            name="password"
            rules={[{ required: true, min: 6, message: '至少 6 位' }]}
          >
            <Input.Password prefix={<LockOutlined style={{ color: '#a8a29e' }} />} placeholder="密码" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block style={{ height: 46, fontSize: 15 }}>
              注册
            </Button>
          </Form.Item>
        </Form>

        <Paragraph type="secondary" style={{ textAlign: 'center', marginBottom: 0 }}>
          已有账号？<Link to="/login">去登录</Link>
        </Paragraph>
      </Card>
    </div>
  )
}

export default Register
