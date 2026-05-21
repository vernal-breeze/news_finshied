/** 系统设置 - 采编端（只读查看） */
import React, { useEffect, useState } from 'react'
import { Card, Descriptions, Spin, Typography, Tag, Divider, message } from 'antd'
import { SettingOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { settingsAPI } from '../../services/api'

const { Title } = Typography

interface SystemSettings {
  site_name: string
  logo_url: string
  copyright: string
  favicon_url: string
  description: string
  allow_registration: boolean
  require_ai_check: boolean
  review_timeout_hours: number
  min_word_count: number
}

const EditorSettings: React.FC = () => {
  const [loading, setLoading] = useState(true)
  const [settings, setSettings] = useState<SystemSettings | null>(null)

  useEffect(() => {
    settingsAPI.get()
      .then((res: any) => setSettings(res?.data as SystemSettings))
      .catch(() => message.error('获取系统设置失败'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '80px 0' }}><Spin size="large" /></div>
  }

  if (!settings) return null

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <Title level={3} style={{ marginBottom: 24 }}>
        <SettingOutlined style={{ marginRight: 8 }} />
        系统设置
      </Title>

      <Card>
        <div style={{ textAlign: 'center', marginBottom: 16 }}>
          <InfoCircleOutlined style={{ color: '#1890ff', marginRight: 8 }} />
          当前以 {getUserRoleLabel()} 身份查看系统配置，如需修改请联系管理员或主编。
        </div>
        <Divider />

        <Descriptions bordered column={1} size="small" labelStyle={{ width: 180 }}>
          <Descriptions.Item label="系统名称">{settings.site_name}</Descriptions.Item>
          <Descriptions.Item label="系统描述">{settings.description}</Descriptions.Item>
          <Descriptions.Item label="版权信息">{settings.copyright}</Descriptions.Item>
          <Descriptions.Item label="Logo URL">
            {settings.logo_url || <span style={{ color: '#ccc' }}>未设置</span>}
          </Descriptions.Item>
          <Descriptions.Item label="Favicon URL">
            {settings.favicon_url || <span style={{ color: '#ccc' }}>未设置</span>}
          </Descriptions.Item>
          <Descriptions.Item label="功能开关">
            <Tag color={settings.allow_registration ? 'green' : 'red'}>
              {settings.allow_registration ? '开放注册' : '关闭注册'}
            </Tag>
            <Tag color={settings.require_ai_check ? 'green' : 'orange'} style={{ marginLeft: 8 }}>
              {settings.require_ai_check ? '需要AI检查' : '无需AI检查'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="审核超时">
            {settings.review_timeout_hours
              ? `${settings.review_timeout_hours} 小时`
              : '不限时'}
          </Descriptions.Item>
          <Descriptions.Item label="最低字数">
            {settings.min_word_count
              ? `${settings.min_word_count} 字`
              : '不限制'}
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  )
}

function getUserRoleLabel(): string {
  try {
    const userStr = localStorage.getItem('user')
    if (!userStr) return '未登录'
    const role = JSON.parse(userStr).role
    const labels: Record<string, string> = {
      editor: '采编人员', reviewer: '审核员', admin: '管理员', chief_editor: '主编'
    }
    return labels[role] || role
  } catch {
    return '未知'
  }
}

export default EditorSettings
