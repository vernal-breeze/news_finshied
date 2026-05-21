import React from 'react'
import ReactDOM from 'react-dom/client'
import { App as AntdApp, ConfigProvider, theme } from 'antd'
import type { ThemeConfig } from 'antd'
import zhCN from 'antd/es/locale/zh_CN'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'
import App from './App'
import './index.css'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

const appTheme: ThemeConfig = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: '#c62828',
    borderRadius: 12,
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif",
    colorBgLayout: '#faf8f8',
    colorText: '#202124',
    colorTextHeading: '#202124',
    colorTextSecondary: '#5f6368',
    colorBorder: '#ebe4e3',
    colorBorderSecondary: '#faf8f8',
    lineHeight: 1.6,
  },
  components: {
    Layout: {
      headerBg: '#ffffff',
      bodyBg: '#faf8f8',
      footerBg: '#ffffff',
      siderBg: '#1a1315',
    },
    Card: {
      borderRadiusLG: 16,
      paddingLG: 22,
    },
    Table: {
      headerBg: '#faf8f8',
    },
    Menu: {
      itemBorderRadius: 10,
      darkItemSelectedBg: 'rgba(255,255,255,0.08)',
    },
  },
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN} theme={appTheme}>
      <AntdApp>
        <App />
      </AntdApp>
    </ConfigProvider>
  </React.StrictMode>,
)
