import axios, { AxiosError } from 'axios'
import { getAuthRequestOrigin } from './apiBase'

/**
 * 登录/注册等公开认证接口专用客户端：
 * - 不附加 localStorage 中的旧 JWT（避免与 OAuth2 表单冲突）
 * - baseURL 为后端 origin（无 /api），请求路径仍为 `/api/auth/...`
 * - 未设置 env 时走相对路径，由 Vite 代理到后端
 */
export const authClient = axios.create({
  baseURL: getAuthRequestOrigin(),
  timeout: 30000,
})

function parseApiError(err: unknown): string {
  const ax = err as AxiosError<{
    detail?: string | Array<{ msg?: string }>
    message?: string | { message?: string }
    errors?: string[]
  }>
  const d = ax.response?.data
  if (!d) {
    if (ax.code === 'ERR_NETWORK' || ax.message === 'Network Error') {
      return '无法连接服务器，请确认后端已启动（默认 http://127.0.0.1:8008）且与前端代理一致'
    }
    return '请求失败，请稍后重试'
  }
  if (typeof d.detail === 'string') return d.detail
  if (Array.isArray(d.detail)) {
    return d.detail.map((x) => (typeof x === 'object' && x && 'msg' in x ? String((x as { msg?: string }).msg) : '')).filter(Boolean).join('；') || '请求参数错误'
  }
  if (typeof d.message === 'string') return d.message
  if (d.message && typeof d.message === 'object' && 'message' in d.message) {
    const m = (d.message as { message?: string }).message
    if (typeof m === 'string') return m
  }
  if (Array.isArray(d.errors) && d.errors.length) return d.errors.join('；')
  return '请求失败，请稍后重试'
}

export async function loginAndFetchUser(username: string, password: string): Promise<{
  access_token: string
  user: Record<string, unknown>
}> {
  const body = new URLSearchParams()
  body.set('username', username)
  body.set('password', password)
  body.set('grant_type', 'password')

  const loginRes = await authClient.post<{ access_token: string; token_type?: string }>(
    '/api/auth/login',
    body,
    {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }
  )

  const access_token = loginRes.data?.access_token
  if (!access_token) {
    throw new Error('服务器未返回 access_token')
  }

  const meRes = await authClient.get<Record<string, unknown>>('/api/auth/me', {
    headers: { Authorization: `Bearer ${access_token}` },
  })

  const raw = meRes.data as Record<string, unknown> | undefined
  const user = raw && typeof raw === 'object' && 'data' in raw && raw.data && typeof raw.data === 'object'
    ? (raw.data as Record<string, unknown>)
    : (raw ?? {})

  return { access_token, user }
}

export async function registerAccount(data: {
  username: string
  email: string
  password: string
  nickname?: string
}): Promise<Record<string, unknown>> {
  const res = await authClient.post<Record<string, unknown>>('/api/auth/register', data)
  return res.data ?? {}
}

export { parseApiError }

/** 登录后进入的采编/审核首页（读者端下拉菜单复用） */
export function workspacePathForRole(role: string | undefined): string {
  return role === 'reviewer' ? '/review/queue' : '/editor'
}
