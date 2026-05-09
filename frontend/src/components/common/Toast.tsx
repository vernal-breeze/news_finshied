import React, { createContext, useContext, useCallback } from 'react'
import { App, notification } from 'antd'
import type { MessageInstance } from 'antd/es/message/interface'

type NotificationType = 'success' | 'error' | 'info' | 'warning'

interface ToastConfig {
  type: NotificationType
  title: string
  description?: string
  duration?: number
}

interface ToastContextType {
  showToast: (config: ToastConfig) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

/** 与 ConfigProvider 主题联动的 message 实例（避免静态 message.xxx 警告） */
const messageApiRef = { current: null as MessageInstance | null }

export const useToast = () => {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return context
}

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { message: messageApi } = App.useApp()
  const [api, contextHolder] = notification.useNotification()

  messageApiRef.current = messageApi

  const showToast = useCallback((config: ToastConfig) => {
    const { type, title, description, duration = 4.5 } = config

    api[type]({
      message: title,
      description,
      duration,
      placement: 'topRight',
      style: {
        borderRadius: 8,
      },
    })
  }, [api])

  return (
    <ToastContext.Provider value={{ showToast }}>
      {contextHolder}
      {children}
    </ToastContext.Provider>
  )
}

// Hook for simple message.toast usage (backward compatible)
export const toast = {
  success: (content: string, duration = 3) => messageApiRef.current?.success(content, duration),
  error: (content: string, duration = 3) => messageApiRef.current?.error(content, duration),
  info: (content: string, duration = 3) => messageApiRef.current?.info(content, duration),
  warning: (content: string, duration = 3) => messageApiRef.current?.warning(content, duration),
  loading: (content: string, duration = 0) => messageApiRef.current?.loading(content, duration),
}

export default ToastProvider
