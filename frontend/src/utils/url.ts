/** 将来源链接规范为可跳转的 http(s) 地址 */
export function normalizeExternalUrl(raw: string | undefined | null): string {
  if (raw == null || typeof raw !== 'string') return '#'
  const t = raw.trim()
  if (!t) return '#'
  if (/^https?:\/\//i.test(t)) return t
  if (/^\/\//.test(t)) return `https:${t}`
  return `https://${t.replace(/^\/+/, '')}`
}
