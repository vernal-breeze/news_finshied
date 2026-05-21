/** 系统设置 - 审核端（管理员/主编可编辑） */
import React, { useEffect, useState } from 'react'
import {
  Card, Form, Input, Button, Switch, Typography,
  Spin, Tag, message, InputNumber
} from 'antd'
import {
  SaveOutlined, SettingOutlined, LockOutlined,
  SafetyOutlined
} from '@ant-design/icons'
import { settingsAPI } from '../../services/api'
import './Settings.css'

const { Title, Text } = Typography

interface SystemSettings {
  site_name: string
  logo_url: string
  copyright: string
  favicon_url: string
  description: string
  allow_registration: boolean
  require_ai_check: boolean
  email_notification: boolean
  review_timeout_hours: number
  min_word_count: number
}

function getUserRole(): string {
  try {
    const userStr = localStorage.getItem('user')
    return userStr ? JSON.parse(userStr).role || '' : ''
  } catch { return '' }
}

const canEdit = () => {
  const role = getUserRole()
  return role === 'admin' || role === 'chief_editor'
}

const Settings: React.FC = () => {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()
  const editable = canEdit()

  useEffect(() => {
    settingsAPI.get()
      .then((res: any) => {
        const s = res?.data as SystemSettings
        form.setFieldsValue(s)
      })
      .catch(() => message.error('获取系统设置失败'))
      .finally(() => setLoading(false))
  }, [form])

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)
      await settingsAPI.update(values)
      message.success('系统设置已保存')
    } catch (e: any) {
      if (e?.errorFields) return
      if (e?.response?.status === 403) {
        message.error('仅管理员和主编可修改系统设置')
      } else {
        message.error('保存失败')
      }
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '80px 0' }}><Spin size="large" /></div>
  }

  return (
    <div className="settings-container">
      <div className="settings-header">
        <Title level={3}>
          <SettingOutlined style={{ marginRight: 8 }} />
          系统设置
        </Title>
        {editable ? (
          <Tag color="green"><SafetyOutlined /> 管理员模式 - 可编辑</Tag>
        ) : (
          <Tag color="orange"><LockOutlined /> 只读模式</Tag>
        )}
      </div>

      <Form form={form} layout="vertical" disabled={!editable}>
        {/* 基础设置 */}
        <Card title="基础设置" style={{ marginBottom: 24 }}>
          <Form.Item name="site_name" label="系统名称"
            rules={[{ required: true, message: '请输入系统名称' }]}>
            <Input placeholder="新闻内容采编系统" />
          </Form.Item>

          <Form.Item name="description" label="系统描述">
            <Input.TextArea rows={2} placeholder="专业的新闻内容采编与审核平台" />
          </Form.Item>

          <Form.Item name="copyright" label="版权信息">
            <Input placeholder="© 2025 News Editor System" />
          </Form.Item>

          <Form.Item name="logo_url" label="Logo URL">
            <Input placeholder="https://example.com/logo.png" />
          </Form.Item>

          <Form.Item name="favicon_url" label="Favicon URL">
            <Input placeholder="https://example.com/favicon.ico" />
          </Form.Item>
        </Card>

        {/* 功能开关 */}
        <Card title="功能设置" style={{ marginBottom: 24 }}>
          <Form.Item name="allow_registration" label="开放注册" valuePropName="checked">
            <Switch /> <Text type="secondary" style={{ marginLeft: 8 }}>允许用户自行注册账号</Text>
          </Form.Item>

          <Form.Item name="require_ai_check" label="AI 辅助审核" valuePropName="checked">
            <Switch /> <Text type="secondary" style={{ marginLeft: 8 }}>提交审核前自动进行 AI 检查</Text>
          </Form.Item>

          <Form.Item name="email_notification" label="邮件通知" valuePropName="checked">
            <Switch /> <Text type="secondary" style={{ marginLeft: 8 }}>有新稿件或审核结果时发送通知</Text>
          </Form.Item>
        </Card>

        {/* 流程参数 */}
        <Card title="审核参数" style={{ marginBottom: 24 }}>
          <Form.Item name="review_timeout_hours" label="审核超时时间">
            <InputNumber min={1} max={720} addonAfter="小时" style={{ width: 200 }} />
            <Text type="secondary" style={{ display: 'block', marginTop: 4 }}>
              超过此时间未审核的稿件会标记提醒
            </Text>
          </Form.Item>

          <Form.Item name="min_word_count" label="最低字数限制">
            <InputNumber min={0} max={100000} addonAfter="字" style={{ width: 200 }} />
            <Text type="secondary" style={{ display: 'block', marginTop: 4 }}>
              稿件最低字数要求，低于此字数无法提交审核
            </Text>
          </Form.Item>
        </Card>

        {editable && (
          <Button
            type="primary"
            size="large"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={saving}
            style={{ minWidth: 140 }}
          >
            保存设置
          </Button>
        )}
      </Form>

      {!editable && (
        <div style={{
          marginTop: 16, padding: 12, backgroundColor: '#fffbe6',
          border: '1px solid #ffe58f', borderRadius: 6
        }}>
          <LockOutlined style={{ color: '#faad14', marginRight: 6 }} />
          <Text type="warning">当前以审核员身份查看，如需修改设置请联系管理员或主编。</Text>
        </div>
      )}
    </div>
  )
}

export default Settings
