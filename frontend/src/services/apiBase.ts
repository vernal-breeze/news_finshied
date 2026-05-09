/**
 * 统一解析 VITE_API_BASE_URL。
 *
 * axios 的 `baseURL` + `url` 会拼接；`api.ts` 中路径已带 `/api/...` 前缀，
 * 故此处不得再返回 `/api`，否则会出现 `/api/api/clues` 导致 404。
 *
 * 支持：
 * - 未设置：空字符串，请求为 `/api/...`（Vite dev 将 `/api` 代理到后端）
 * - `http://127.0.0.1:8000` → 同上，完整 URL 为 `http://127.0.0.1:8000/api/...`
 * - `http://127.0.0.1:8000/api` → 去掉末尾 `/api`，避免与路径前缀重复
 */
export function getApiBaseUrl(): string {
  const raw = (import.meta.env.VITE_API_BASE_URL || '').trim()
  if (!raw) return ''
  let u = raw.replace(/\/$/, '')
  if (u.endsWith('/api')) u = u.slice(0, -4)
  return u
}

/**
 * 认证接口路径为 `/api/auth/...`，此处返回不含 `/api` 的 origin，与完整路径拼接后即为正确地址。
 */
export function getAuthRequestOrigin(): string {
  const raw = (import.meta.env.VITE_API_BASE_URL || '').trim()
  if (!raw) return ''
  const u = raw.replace(/\/$/, '')
  if (u.endsWith('/api')) return u.slice(0, -4)
  return u
}
