import React from 'react'
import { Card, Form, Input, Button, Switch, Space, Typography, Divider } from 'antd'
import { toast } from '../../components/common/Toast'
import { SaveOutlined } from '@ant-design/icons'
import './Settings.css'

const { Title, Text } = Typography

const Settings: React.FC = () => {
  const [form] = Form.useForm()

  const handleSave = () => {
    toast.success('设置已保存')
  }

  return (
    <div className="settings-container">
      <div className="settings-header">
        <Title level={2}>系统设置</Title>
        <Text type="secondary">配置审核系统参数</Text>
      </div>

      <Card title="基本设置" style={{ marginBottom: 24 }}>
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            autoPublish: false,
            requireAICheck: true,
            emailNotification: true,
          }}
        >
          <Form.Item label="自动发布">
            <Space>
              <Switch />
              <Text type="secondary">审核通过后自动发布（需主编权限）</Text>
            </Space>
          </Form.Item>

          <Form.Item label="AI 辅助审核">
            <Space>
              <Switch />
              <Text type="secondary">自动进行 AI 语法和事实检查</Text>
            </Space>
          </Form.Item>

          <Form.Item label="邮件通知">
            <Space>
              <Switch />
              <Text type="secondary">新稿件提交时发送邮件通知</Text>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Card title="通知设置" style={{ marginBottom: 24 }}>
        <Form layout="vertical">
          <Form.Item label="审核超时提醒">
            <Space>
              <Input type="number" defaultValue={24} style={{ width: 100 }} suffix="小时" />
              <Text type="secondary">超过此时间未处理的稿件发送提醒</Text>
            </Space>
          </Form.Item>

          <Form.Item label="邮件地址">
            <Input placeholder="审核通知邮件地址" style={{ width: 300 }} />
          </Form.Item>
        </Form>
      </Card>

      <Card title="审核流程设置">
        <Form layout="vertical">
          <Form.Item label="默认审核级别">
            <Input type="number" defaultValue={2} style={{ width: 100 }} suffix="级" />
            <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
              设置稿件需要经过的审核级别数量（1-3级）
            </Text>
          </Form.Item>

          <Form.Item label="最低字数要求">
            <Input type="number" defaultValue={500} style={{ width: 100 }} suffix="字" />
            <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
              稿件最低字数要求，低于此字数无法提交审核
            </Text>
          </Form.Item>

          <Divider />

          <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
            保存设置
          </Button>
        </Form>
      </Card>
    </div>
  )
}

export default Settings
