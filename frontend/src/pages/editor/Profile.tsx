/** 个人中心 - 采编端 */
import React, { useEffect, useState } from 'react'
import {
  Card, Row, Col, Descriptions, Statistic, Avatar, Button, Form, Input,
  Modal, Upload, message, Spin, Tabs, Typography, Divider
} from 'antd'
import {
  UserOutlined, EditOutlined, LockOutlined, MailOutlined,
  FileTextOutlined, CheckCircleOutlined, BulbOutlined,
  ClockCircleOutlined, CameraOutlined, PictureOutlined
} from '@ant-design/icons'
import { userAPI, uploadAPI } from '../../services/api'
import type { UploadFile } from 'antd/es/upload'
import { UploadChangeParam } from 'antd/es/upload'
import dayjs from 'dayjs'

const { Title, Text } = Typography

interface ProfileData {
  id: number
  username: string
  nickname: string
  email: string
  role: string
  avatar: string
  full_name: string
  created_at: string
  updated_at: string
  article_count: number
  published_count: number
  pending_review_count: number
  clue_count: number
  last_login: string
}

const roleLabels: Record<string, string> = {
  editor: '采编人员',
  reviewer: '审核员',
  admin: '系统管理员',
  chief_editor: '主编',
}

const Profile: React.FC = () => {
  const [loading, setLoading] = useState(true)
  const [profile, setProfile] = useState<ProfileData | null>(null)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [pwdModalOpen, setPwdModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()
  const [pwdForm] = Form.useForm()

  const fetchProfile = async () => {
    try {
      setLoading(true)
      const res = await userAPI.getProfile()
      setProfile(res?.data as ProfileData)
    } catch {
      message.error('获取个人信息失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchProfile() }, [])

  const openEditModal = () => {
    form.setFieldsValue({
      nickname: profile?.nickname,
      email: profile?.email,
      full_name: profile?.full_name,
    })
    setEditModalOpen(true)
  }

  const handleSaveProfile = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)
      await userAPI.updateProfile(values)
      message.success('个人信息已更新')
      setEditModalOpen(false)
      fetchProfile()
    } catch (e: any) {
      if (e?.errorFields) return // 表单校验失败
      message.error(e?.detail || '更新失败')
    } finally {
      setSaving(false)
    }
  }

  const handleChangePassword = async () => {
    try {
      const values = await pwdForm.validateFields()
      setSaving(true)
      await userAPI.updatePassword(values)
      message.success('密码已修改，请重新登录')
      setPwdModalOpen(false)
      pwdForm.resetFields()
      setTimeout(() => {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.dispatchEvent(new Event('auth-changed'))
      }, 800)
    } catch (e: any) {
      if (e?.errorFields) return
      message.error(e?.detail || '密码修改失败')
    } finally {
      setSaving(false)
    }
  }

  const handleAvatarUpload = async (info: UploadChangeParam<UploadFile>) => {
    if (info.file.status === 'done') {
      message.success('头像已更新')
      fetchProfile()
    } else if (info.file.status === 'error') {
      message.error('头像上传失败')
    }
  }

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '80px 0' }}><Spin size="large" /></div>
  }

  if (!profile) return null

  return (
    <div style={{ padding: 24, maxWidth: 960, margin: '0 auto' }}>
      <Title level={3} style={{ marginBottom: 24 }}>
        <UserOutlined style={{ marginRight: 8 }} />
        个人中心
      </Title>

      {/* 基本信息卡片 */}
      <Card style={{ marginBottom: 24 }} styles={{ body: { padding: 32 } }}>
        <Row gutter={[32, 24]} align="middle">
          <Col xs={24} sm={6} style={{ textAlign: 'center' }}>
            <div style={{ position: 'relative', display: 'inline-block' }}>
              {profile.avatar ? (
                <Avatar size={100} src={profile.avatar} />
              ) : (
                <Avatar size={100} icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
              )}
              <Upload
                showUploadList={false}
                customRequest={async ({ file, onSuccess, onError }) => {
                  try {
                    const res = await userAPI.uploadAvatar(file as File)
                    onSuccess?.(res)
                  } catch (err) {
                    onError?.(err as any)
                  }
                }}
                onChange={handleAvatarUpload}
                accept="image/*"
              >
                <Button
                  shape="circle"
                  size="small"
                  icon={<CameraOutlined />}
                  style={{
                    position: 'absolute', bottom: 0, right: -4,
                    backgroundColor: '#1890ff', color: '#fff', border: 'none'
                  }}
                />
              </Upload>
            </div>
            <div style={{ marginTop: 12 }}>
              <Text strong style={{ fontSize: 16 }}>{profile.nickname || profile.username}</Text>
            </div>
            <div style={{ marginTop: 4 }}>
              <Text type="secondary">@{profile.username}</Text>
            </div>
            <div style={{ marginTop: 8 }}>
              <span style={{
                display: 'inline-block', padding: '2px 12px', borderRadius: 12,
                backgroundColor: '#e6f7ff', color: '#1890ff', fontSize: 12
              }}>
                {roleLabels[profile.role] || profile.role}
              </span>
            </div>
          </Col>
          <Col xs={24} sm={18}>
            <Descriptions column={{ xs: 1, sm: 2 }} size="small" colon={false}>
              <Descriptions.Item label={<><MailOutlined /> 邮箱</>}>
                {profile.email || '未设置'}
              </Descriptions.Item>
              <Descriptions.Item label={<><UserOutlined /> 姓名</>}>
                {profile.full_name || '未设置'}
              </Descriptions.Item>
              <Descriptions.Item label={<><ClockCircleOutlined /> 注册时间</>}>
                {profile.created_at ? dayjs(profile.created_at).format('YYYY-MM-DD HH:mm') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label={<><ClockCircleOutlined /> 最近活动</>}>
                {profile.last_login ? dayjs(profile.last_login).format('YYYY-MM-DD HH:mm') : '-'}
              </Descriptions.Item>
            </Descriptions>
            <div style={{ marginTop: 16 }}>
              <Button icon={<EditOutlined />} onClick={openEditModal} style={{ marginRight: 8 }}>
                编辑资料
              </Button>
              <Button icon={<LockOutlined />} onClick={() => setPwdModalOpen(true)}>
                修改密码
              </Button>
            </div>
          </Col>
        </Row>
      </Card>

      {/* 统计数据 */}
      <Card style={{ marginBottom: 24 }} styles={{ body: { padding: 24 } }}>
        <Row gutter={24}>
          <Col xs={12} sm={6}>
            <Statistic title="总稿件" value={profile.article_count} prefix={<FileTextOutlined />} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="已发布" value={profile.published_count} prefix={<FileTextOutlined />} valueStyle={{ color: '#52c41a' }} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="待审核" value={profile.pending_review_count} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#faad14' }} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="新闻线索" value={profile.clue_count} prefix={<BulbOutlined />} />
          </Col>
        </Row>
      </Card>

      {/* 编辑资料弹窗 */}
      <Modal
        title="编辑个人资料"
        open={editModalOpen}
        onOk={handleSaveProfile}
        onCancel={() => setEditModalOpen(false)}
        confirmLoading={saving}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="nickname" label="昵称" rules={[{ max: 20, message: '昵称最多20个字符' }]}>
            <Input placeholder="请输入昵称" prefix={<UserOutlined />} />
          </Form.Item>
          <Form.Item name="email" label="邮箱" rules={[{ type: 'email', message: '请输入有效的邮箱地址' }]}>
            <Input placeholder="请输入邮箱" prefix={<MailOutlined />} />
          </Form.Item>
          <Form.Item name="full_name" label="姓名" rules={[{ max: 50, message: '姓名最多50个字符' }]}>
            <Input placeholder="请输入真实姓名" prefix={<UserOutlined />} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 修改密码弹窗 */}
      <Modal
        title="修改密码"
        open={pwdModalOpen}
        onOk={handleChangePassword}
        onCancel={() => { setPwdModalOpen(false); pwdForm.resetFields() }}
        confirmLoading={saving}
        destroyOnHidden
      >
        <Form form={pwdForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="old_password" label="原密码"
            rules={[{ required: true, message: '请输入原密码' }]}>
            <Input.Password placeholder="请输入原密码" prefix={<LockOutlined />} />
          </Form.Item>
          <Form.Item name="new_password" label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码至少6位' },
            ]}>
            <Input.Password placeholder="请输入新密码" prefix={<LockOutlined />} />
          </Form.Item>
          <Form.Item name="confirm_password" label="确认新密码"
            dependencies={['new_password']}
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) {
                    return Promise.resolve()
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'))
                },
              }),
            ]}>
            <Input.Password placeholder="请再次输入新密码" prefix={<LockOutlined />} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Profile
