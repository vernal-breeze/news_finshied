import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { Layout } from 'antd'
import { ToastProvider } from './components/common/Toast'
import { ErrorBoundary } from './components/common/ErrorBoundary'
import MainLayout from './components/layouts/MainLayout'
import ReviewLayout from './components/layouts/ReviewLayout'
import { EditorHome as Home, Clues, Articles, Analytics, AIArticle, Topics } from './pages/editor'
import { EditorLogin, Register } from './pages/auth'
import { ReviewLogin, ReviewDashboard, ReviewQueue, Published, Settings } from './pages/review'
import { ReaderHome, ReaderArticleDetail, ReaderSearch, ReaderCategory, ReaderMessages } from './pages/reader'
import './App.css'

/** 获取当前用户角色 */
function getUserRole(): string {
  try {
    const userStr = localStorage.getItem('user')
    if (userStr) return JSON.parse(userStr).role || ''
  } catch { /* ignore */ }
  return ''
}

// 路由守卫组件
const EditorRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const token = localStorage.getItem('token')
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

const ReviewRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const token = localStorage.getItem('token')
  if (!token) {
    return <Navigate to="/review/login" replace />
  }
  const role = getUserRole()
  if (role !== 'reviewer') {
    return <Navigate to="/review/login" replace />
  }
  return <>{children}</>
}

/** 读者端需登录的页面（如消息中心）：未登录跳转投稿端登录并带回跳地址 */
const ReaderAuthRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation()
  const token = localStorage.getItem('token')
  if (!token) {
    const next = encodeURIComponent(`${location.pathname}${location.search || ''}`)
    return <Navigate to={`/login?next=${next}`} replace />
  }
  return <>{children}</>
}

function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <BrowserRouter
          future={{
            v7_startTransition: true,
            v7_relativeSplatPath: true,
          }}
        >
          <Routes>
          {/* 客户端（读者端 - 公开访问） */}
          <Route path="/reader" element={<ReaderHome />} />
          <Route path="/reader/article/:id" element={<ReaderArticleDetail />} />
          <Route path="/reader/search" element={<ReaderSearch />} />
          <Route path="/reader/category/:category" element={<ReaderCategory />} />
          <Route
            path="/reader/messages"
            element={
              <ReaderAuthRoute>
                <ReaderMessages />
              </ReaderAuthRoute>
            }
          />
          
          {/* 客户端默认首页 */}
          <Route path="/" element={<Navigate to="/reader" replace />} />

          {/* 登录页 */}
          <Route path="/login" element={<EditorLogin />} />
          <Route path="/register" element={<Register />} />
          
          {/* 采编端（需登录） */}
          <Route
            path="/editor"
            element={
              <EditorRoute>
                <Layout style={{ minHeight: '100vh' }}>
                  <MainLayout>
                    <Home />
                  </MainLayout>
                </Layout>
              </EditorRoute>
            }
          />
          <Route
            path="/editor/clues"
            element={
              <EditorRoute>
                <Layout style={{ minHeight: '100vh' }}>
                  <MainLayout>
                    <Clues />
                  </MainLayout>
                </Layout>
              </EditorRoute>
            }
          />
          <Route
            path="/editor/topics"
            element={
              <EditorRoute>
                <Layout style={{ minHeight: '100vh' }}>
                  <MainLayout>
                    <Topics />
                  </MainLayout>
                </Layout>
              </EditorRoute>
            }
          />
          <Route
            path="/editor/articles"
            element={
              <EditorRoute>
                <Layout style={{ minHeight: '100vh' }}>
                  <MainLayout>
                    <Articles />
                  </MainLayout>
                </Layout>
              </EditorRoute>
            }
          />
          <Route
            path="/editor/analytics"
            element={
              <EditorRoute>
                <Layout style={{ minHeight: '100vh' }}>
                  <MainLayout>
                    <Analytics />
                  </MainLayout>
                </Layout>
              </EditorRoute>
            }
          />
          <Route
            path="/editor/ai-article"
            element={
              <EditorRoute>
                <Layout style={{ minHeight: '100vh' }}>
                  <MainLayout>
                    <AIArticle />
                  </MainLayout>
                </Layout>
              </EditorRoute>
            }
          />

          {/* 兼容旧路径 */}
          <Route
            path="/clues"
            element={<Navigate to="/editor/clues" replace />}
          />
          <Route
            path="/articles"
            element={<Navigate to="/editor/articles" replace />}
          />
          <Route
            path="/analytics"
            element={<Navigate to="/editor/analytics" replace />}
          />
          <Route
            path="/ai-article"
            element={<Navigate to="/editor/ai-article" replace />}
          />
          <Route path="/topics" element={<Navigate to="/editor/topics" replace />} />

          {/* 审核端（需登录） */}
          <Route path="/review/login" element={<ReviewLogin />} />
          <Route
            path="/review"
            element={
              <ReviewRoute>
                <ReviewLayout />
              </ReviewRoute>
            }
          >
            <Route index element={<ReviewDashboard />} />
            <Route path="queue" element={<ReviewQueue />} />
            <Route path="published" element={<Published />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ToastProvider>
    </ErrorBoundary>
  )
}

export default App