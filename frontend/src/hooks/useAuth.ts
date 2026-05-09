import { useCallback } from 'react'

export interface UserInfo {
  user_id: number
  username: string
  email: string
  full_name: string
  role: string
  is_active: boolean
}

export function useAuth() {
  const getUser = useCallback((): UserInfo | null => {
    try {
      const str = localStorage.getItem('user')
      if (!str) return null
      return JSON.parse(str)
    } catch {
      return null
    }
  }, [])

  const getToken = useCallback((): string | null => {
    return localStorage.getItem('token')
  }, [])

  const isLoggedIn = useCallback((): boolean => {
    return !!localStorage.getItem('token')
  }, [])

  const isReviewer = useCallback((): boolean => {
    const user = getUser()
    return user?.role === 'reviewer'
  }, [getUser])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('username')
    window.dispatchEvent(new CustomEvent('auth-changed'))
  }, [])

  return { getUser, getToken, isLoggedIn, isReviewer, logout }
}
