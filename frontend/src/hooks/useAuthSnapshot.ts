import { useSyncExternalStore } from 'react'

function subscribe(callback: () => void) {
  window.addEventListener('storage', callback)
  window.addEventListener('focus', callback)
  /** 同标签页内登录写入 localStorage 不会触发 storage，由登录页主动派发 */
  window.addEventListener('auth-changed', callback)
  return () => {
    window.removeEventListener('storage', callback)
    window.removeEventListener('focus', callback)
    window.removeEventListener('auth-changed', callback)
  }
}

/** 任意登录信息变化时快照字符串会变，触发重新订阅 */
function getAuthSnapshot(): string {
  return `${localStorage.getItem('token') ?? ''}\0${localStorage.getItem('user') ?? ''}`
}

function getServerSnapshot(): string {
  return '\0'
}

/** 从 localStorage 读取登录态；focus / 其它标签页 storage 变化时刷新 */
export function useAuthSnapshot() {
  useSyncExternalStore(subscribe, getAuthSnapshot, getServerSnapshot)

  const token = localStorage.getItem('token')
  let user: { username?: string; full_name?: string; role?: string } | null = null
  try {
    user = JSON.parse(localStorage.getItem('user') || 'null')
  } catch {
    user = null
  }
  const role = typeof user?.role === 'string' ? user.role : undefined
  return {
    token,
    user,
    role,
    isLoggedIn: Boolean(token),
  }
}
