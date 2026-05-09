# 新闻采编系统 — 优化分析与 AI 提示词指南

> 基于对项目全量代码的深度审计
> 涵盖后端架构、前端组件、工程化配置、安全、性能五大维度
> 2026 年 5 月

---

## 一、优化点总览

本文档基于对新闻采编系统全量代码的深度审计，从后端架构、前端组件、工程化配置、安全、性能五大维度进行分析，共发现 60+ 个优化点。以下为各优先级的概览：

| 优先级 | 数量 | 关键问题 |
|--------|------|----------|
| **P0 紧急** | 16 | 安全漏洞、零测试、缺少工具链、代码致命缺陷 |
| **P1 高优先** | 32 | 架构不合理、代码重复、API 不一致、配置缺失 |
| **P2 中优先** | 18 | 性能优化、类型标注、异步化、文档完善 |

---

## 二、P0 紧急问题（必须立即修复）

### 2.1 安全漏洞

| 问题 | 文件 | 详情 | 修复方案 |
|------|------|------|----------|
| 反馈端点无认证 | routers/feedback.py | record_view/like/share/comment 四个端点无任何认证，任人可无限刷计数 | 添加 Depends(get_current_user) 或 Rate Limiting |
| subprocess 命令注入风险 | services/clue_service.py | 使用 subprocess.run(['curl',...]) 抓取网页，存在命令注入风险 | 替换为 httpx/aiohttp 异步 HTTP 客户端 |
| .env 文件含敏感信息 | backend/.env | SECRET_KEY 和 API Key 硬编码且可能被 git 追踪 | 确保 .env 在 .gitignore 中，仅保留 .env.example |
| Docker 以 root 运行 | backend/Dockerfile | 容器内进程以 root 身份运行 | 添加 USER appuser 指令 |
| 数据库密码硬编码 | docker-compose.yml | POSTGRES_PASSWORD 直接写在 compose 文件中 | 使用环境变量 ${POSTGRES_PASSWORD} |
| TrustedHost 允许所有主机 | main.py | allowed_hosts=["*"] 生产环境不安全 | 从环境变量读取允许的域名列表 |

### 2.2 代码质量致命缺陷

| 问题 | 位置 | 详情 | 修复方案 |
|------|------|------|----------|
| 异常处理风格不统一 | 全局 | auth.py/messages.py 用 HTTPException，其他用自定义异常，响应格式不一致 | 统一使用 core/exceptions.py 中的异常类 |
| 零测试覆盖 | 全局 | 项目完全没有测试文件 | 优先为 Service 层和关键 API 添加 pytest |
| 缺少 ESLint/Prettier | 前端 | 无代码质量检查和格式化工具 | 添加 ESLint + Prettier 配置 |
| 缺少 Alembic 数据库迁移 | 后端 | 使用自定义 schema_migrations，不支持回退和 PostgreSQL | 引入 Alembic 数据库迁移工具 |
| 超大组件未拆分 | 前端 | AIArticle.tsx 1476行、Articles.tsx 1321行，可维护性极差 | 拆分为子组件 + 自定义 Hook |
| 全局认证状态缺失 | 前端 | 多个组件直接读 localStorage，无响应式更新 | 创建 AuthContext + useAuth Hook |

---

## 三、P1 高优先问题（应尽快修复）

### 3.1 后端架构与代码

| 问题 | 文件 | 详情 | 修复方案 |
|------|------|------|----------|
| Service 层依赖注入 | 所有路由文件 | 模块顶层实例化 Service，无法在测试中 mock | 使用 FastAPI Depends 实现服务工厂 |
| 数据库初始化时机 | main.py 第43行 | create_all 在模块导入时执行，而非 lifespan 中 | 移入 lifespan 启动阶段 |
| 连接池未配置 | database.py | config.py 定义了连接池参数但未使用 | 在 create_engine 中使用连接池配置 |
| AI 缓存未使用 | ai_service.py | cache_service.py 已实现但未集成到 AI 调用 | 在 AI API 调用前后加入缓存逻辑 |
| 速率限制器未使用 | rate_limiter.py | 完整的令牌桶限流器但未集成 | 在 AIAPICaller 中集成速率限制 |
| 分页参数不一致 | 多个路由文件 | page_size 默认值在 15/20/10 之间不统一 | 统一使用 config.DEFAULT_PAGE_SIZE |
| auth.py 直接操作数据库 | routers/auth.py | 绕过 Service 层直接使用 db.query(User) | 创建 UserService 封装用户 CRUD |
| 搜索方法大量重复 | clue_service.py | _search_bing/_baidu/_sogou 各定义了两次 | 删除重复方法，提取通用解析逻辑 |
| 日志配置未使用 | main.py | setup_logging() 未传入 config 中的日志参数 | 传入 LOG_LEVEL/LOG_FILE 等配置 |

### 3.2 前端组件与状态

| 问题 | 文件 | 详情 | 修复方案 |
|------|------|------|----------|
| 路由未懒加载 | App.tsx | 所有页面静态 import，首屏加载全部代码 | 使用 React.lazy() + Suspense 代码分割 |
| API 层大量 any 类型 | services/api.ts | 几乎所有 API 方法参数和返回值都是 any | 利用 types/index.ts 已有接口定义类型 |
| 401 处理方式不当 | services/api.ts | 使用 window.location.replace 强制刷新，丢失前端状态 | 通过事件机制通知路由守卫 |
| 组件内重复代码 | 多个组件 | getCategoryTag/getStatusTag/relativeTime 在3+ 处重复 | 统一使用 utils/ 中的实现 |
| 生产环境回退 mock 数据 | 多个页面 | API 失败时静默展示假数据 | 生产环境应显示错误提示 |
| N+1 请求问题 | Analytics.tsx | 对每篇文章逐一请求反馈数据，最多50个 | 后端提供批量接口 |
| 缺少请求取消机制 | 所有 useEffect | 组件卸载时未取消进行中的请求 | 使用 AbortController |

### 3.3 工程化配置

| 问题 | 位置 | 详情 | 修复方案 |
|------|------|------|----------|
| CI 缺少后端测试 | ci.yml | 仅做 import 检查，没有运行 pytest | 添加 backend-test job |
| CI 缺少安全扫描 | ci.yml | 没有 pip3-audit 或 npm audit | 添加依赖漏洞扫描步骤 |
| nginx.conf 缺少安全头 | frontend/nginx.conf | 没有 server_tokens off、CSP、HSTS | 添加安全响应头配置 |
| 缺少部署文档 | docs/ | 没有生产环境部署指南 | 添加 docs/deployment.md |
| python-jose 已停维护 | requirements.txt | 存在已知安全漏洞 | 迁移到 PyJWT |
| 缺少 HTTP 层 Rate Limiting | 全局 | 登录、API 等端点无频率限制 | 添加 slowapi/fastapi-limiter |
| 缺少 HTTPS/TLS 配置 | 全局 | 生产环境未配置 SSL | 在 Nginx 层配置 TLS |

---

## 四、P2 中优先问题（建议改进）

### 4.1 性能与类型

| 问题 | 位置 | 详情 | 修复方案 |
|------|------|------|----------|
| Service 层返回值全标 Any | 所有 Service | 丧失类型检查意义 | 替换为具体 ORM 模型类型 |
| 同步路由处理函数 | 大部分路由 | 使用 def 而非 async def | 逐步改为 async def + 异步会话 |
| AI 重试使用 time.sleep 阻塞 | ai_service.py | 最坏情况阻塞约7秒 | 使用 asyncio.sleep 异步重试 |
| Task Queue 未使用 | task_queue.py | 完整实现但未集成 | 耗时 AI 操作提交到任务队列 |
| 列表未虚拟化 | 前端多个列表 | 100+ 条数据可能导致性能问题 | 使用 @tanstack/react-virtual |
| 密码修改后 Token 未失效 | routers/auth.py | 旧 JWT 在过期前仍有效 | 添加 token_version 字段 |
| 缺少 CSP 和 HSTS 头 | middleware/ | 安全头不完整 | 添加 Content-Security-Policy |
| 缺少 Prometheus 指标 | 全局 | 没有暴露 /metrics 端点 | 添加 prometheus-fastapi-instrumentator |

---

## 五、AI 优化提示词

以下提示词可直接复制给 AI 编码助手（如 SOLO、Cursor、Copilot），用于指导各类优化任务的执行。每个提示词包含完整的上下文、具体任务和预期输出。

### 5.1 提示词一：后端异常处理统一

**适用场景：统一全局异常处理风格，消除 HTTPException 与自定义异常的混用**

```
你是一个 FastAPI 后端开发专家。请帮我统一项目的异常处理风格。

## 项目背景
这是一个新闻采编系统，使用 FastAPI + SQLAlchemy + SQLite/PostgreSQL。
项目路径：backend/app/

## 当前问题
1. routers/auth.py 和 routers/messages.py 大量直接使用 HTTPException
2. routers/articles.py 等使用自定义异常（raise_not_found, raise_bad_request）
3. 异常响应格式不一致：自定义异常返回 {code, message, error_code, request_id}，HTTPException 返回 {detail: "..."}
4. routers/feedback.py 中 4 个端点（record_view/like/share/comment）缺少认证

## 已有基础设施
- backend/app/core/exceptions.py 中已定义 BaseAPIException、NotFoundException、BadRequestException、UnauthorizedException、ForbiddenException
- backend/app/core/auth.py 中已有 get_current_user 依赖和 require_roles() 函数
- backend/app/middleware/ 中已有 request_id 中间件

## 具体任务
1. 将 routers/auth.py 中所有 HTTPException 替换为对应的自定义异常类
2. 将 routers/messages.py 中所有 HTTPException 替换为对应的自定义异常类
3. 为 routers/feedback.py 的 4 个端点添加 Depends(get_current_user) 认证
4. 确保所有异常响应格式统一为 {code, message, error_code, request_id}
5. 不要修改已有的自定义异常类定义

## 约束
- 保持现有 API 路径和参数不变
- 保持向后兼容（响应中保留 message 字段）
- 不要修改 core/exceptions.py 和 core/auth.py
```

### 5.2 提示词二：前端大组件拆分

**适用场景：拆分 AIArticle.tsx (1476行) 和 Articles.tsx (1321行)**

```
你是一个 React + TypeScript 前端开发专家。请帮我拆分超大组件。

## 项目背景
这是一个新闻采编系统的前端，使用 React 18 + TypeScript + Ant Design 5 + Vite 5。
项目路径：frontend/src/

## 当前问题
1. pages/editor/AIArticle.tsx 有 1476 行，约 25 个 useState，包含：
   - 3 步骤表单（选择线索→生成内容→编辑发布）
   - 线索选择侧边栏
   - 搜索结果展示
   - 预览弹窗、改进弹窗
   - sessionStorage 持久化逻辑

2. pages/editor/Articles.tsx 有 1321 行，约 15 个 useState，包含：
   - 文章列表（含筛选、搜索、分页）
   - 创建/编辑弹窗
   - 详情抽屉（含版本历史+审核记录）
   - 图片上传逻辑

## 已有基础设施
- hooks/useAuth.ts — 认证 Hook
- utils/tags.ts — getCategoryTag, getStatusTag
- utils/format.ts — formatRelativeTime, formatNumber
- services/api.ts — API 调用层
- types/index.ts — TypeScript 类型定义

## 具体任务
### AIArticle.tsx 拆分为：
- components/editor/GenerationForm.tsx — 生成表单
- components/editor/GeneratedResultTabs.tsx — 结果标签页
- components/editor/ClueSelector.tsx — 线索选择器
- components/editor/ImproveContentModal.tsx — 改进弹窗
- hooks/useAIArticleGeneration.ts — 状态逻辑聚合

### Articles.tsx 拆分为：
- components/editor/ArticleTable.tsx — 文章列表
- components/editor/ArticleFormModal.tsx — 创建/编辑弹窗
- components/editor/ArticleDetailDrawer.tsx — 详情抽屉
- components/editor/ArticleFilters.tsx — 筛选器
- hooks/useArticles.ts — 列表状态管理

## 约束
- 使用已有的 utils/ 和 hooks/，不要重复创建
- 使用 Ant Design 组件，保持 UI 一致性
- TypeScript 严格模式，不允许 any
- 每个文件不超过 300 行
- 保持现有功能完全不变
```

### 5.3 提示词三：全局认证状态管理

**适用场景：创建 AuthContext，统一认证状态管理**

```
你是一个 React + TypeScript 前端架构专家。请帮我实现全局认证状态管理。

## 项目背景
新闻采编系统前端，React 18 + TypeScript + Ant Design 5。
项目路径：frontend/src/

## 当前问题
1. 多个组件直接读取 localStorage.getItem('user') / localStorage.getItem('token')
   - App.tsx 第14-19行（路由守卫）
   - MainLayout.tsx 第56-57行、第194行
   - ReviewLayout.tsx 第31行
   - Queue.tsx 第237行
2. MainLayout.tsx 中 JSON.parse(localStorage.getItem('user')) 无 try-catch 保护
3. 已有 hooks/useAuth.ts 和 hooks/useAuthSnapshot.ts 两个功能重叠的 Hook，但几乎没被使用
4. 路由守卫仅检查 token 是否存在，不检查是否过期

## 已有基础设施
- hooks/useAuth.ts — getUser, getToken, isLoggedIn, isReviewer, logout
- hooks/useAuthSnapshot.ts — 基于 useSyncExternalStore 的响应式版本
- services/api.ts — 已有 auth-changed 自定义事件机制

## 具体任务
1. 创建 contexts/AuthContext.tsx：
   - 提供 user, token, isLoggedIn, isReviewer, login(), logout()
   - 使用 useSyncExternalStore 监听 localStorage 变化
   - 解析 JWT payload 检查 exp 字段判断 token 是否过期
   - 在 token 过期时自动触发 logout

2. 删除 hooks/useAuthSnapshot.ts，重构 hooks/useAuth.ts 为：
   - 从 AuthContext 消费认证状态
   - 保留 logout() 等便捷方法

3. 修改 App.tsx 路由守卫：
   - 使用 AuthContext 替代直接读取 localStorage
   - 检查 token 有效性（未过期）

4. 修改 MainLayout.tsx 和 ReviewLayout.tsx：
   - 使用 useAuth() Hook 替代直接读取 localStorage
   - 添加 try-catch 保护

## 约束
- 保持现有 API 调用逻辑不变
- 保持现有路由结构不变
- TypeScript 严格模式
```

### 5.4 提示词四：测试框架搭建

**适用场景：为后端和前端添加基础测试**

```
你是一个全栈测试工程师。请帮我为项目搭建测试框架并编写基础测试。

## 项目背景
新闻采编系统：
- 后端：FastAPI + SQLAlchemy + SQLite/PostgreSQL，路径 backend/
- 前端：React 18 + TypeScript + Ant Design 5 + Vite 5，路径 frontend/
- 当前测试覆盖率为 0%

## 后端任务
1. 创建 backend/tests/ 目录结构：
   - tests/conftest.py — 共享 fixtures（测试数据库、测试客户端、测试用户）
   - tests/unit/ — 单元测试
   - tests/integration/ — 集成测试

2. 编写 conftest.py：
   - 使用内存 SQLite 作为测试数据库
   - 创建 TestClient
   - 提供 test_user, test_admin, test_reviewer fixtures
   - 每个测试用例自动清理数据库

3. 编写核心测试（至少覆盖）：
   - tests/test_auth.py — 登录、注册、token 验证、权限检查
   - tests/test_articles.py — CRUD 操作、分页、筛选
   - tests/test_clues.py — CRUD 操作、AI 分析
   - tests/test_security.py — 未认证访问被拒绝、安全头存在

4. 添加 pytest 配置到 pyproject.toml

## 前端任务
1. 安装 Vitest + @testing-library/react + @testing-library/jest-dom + jsdom
2. 创建 frontend/src/__tests__/ 目录
3. 编写工具函数测试：
   - utils/format.test.ts — formatRelativeTime, formatNumber
   - utils/tags.test.ts — getCategoryTag, getStatusTag
4. 编写 Hook 测试：
   - hooks/useAuth.test.ts
5. 添加 vitest.config.ts 和 package.json test 脚本

## 约束
- 后端使用 pytest + httpx.AsyncClient
- 前端使用 Vitest + @testing-library/react
- 测试数据库使用内存 SQLite，不依赖外部服务
- 目标：至少覆盖认证流程、核心 CRUD、权限检查
```

### 5.5 提示词五：工程化完善

**适用场景：完善 Docker、CI/CD、代码规范配置**

```
你是一个 DevOps 和前端工程化专家。请帮我完善项目的工程化配置。

## 项目背景
新闻采编系统，FastAPI + React + TypeScript + Docker。
项目根目录路径：项目根目录/

## 任务一：Docker 安全加固
1. 修改 backend/Dockerfile：
   - 添加非 root 用户（RUN useradd -m appuser + USER appuser）
   - 创建 backend/.dockerignore（排除 venv/, __pycache__/, .env, data/, .git/）
   - 移除 CMD 中的 --reload（生产环境）

2. 修改 frontend/Dockerfile：
   - 添加 HEALTHCHECK 指令
   - 切换到非 root 用户

3. 修改 docker-compose.yml：
   - 数据库密码改为环境变量 ${POSTGRES_PASSWORD}
   - DEBUG 改为 ${DEBUG:-false}
   - 添加资源限制（mem_limit, cpus）
   - PostgreSQL 端口仅在开发环境暴露

## 任务二：CI/CD 增强
修改 .github/workflows/ci.yml：
1. 添加 backend-test job（pytest）
2. 添加 frontend-lint job（ESLint）
3. 添加 security-scan job（pip3-audit + npm audit）
4. 添加 pip3 缓存配置

## 任务三：前端代码规范
1. 添加 .eslintrc.cjs（@typescript-eslint/recommended + react-hooks + react-refresh）
2. 添加 .prettierrc.json（分号、单引号、2空格缩进）
3. 在 package.json 添加 lint/format/type-check 脚本
4. 添加 .nvmrc 文件（Node 20）

## 任务四：后端依赖管理
1. 锁定 requirements.txt 中所有未锁定版本的依赖
2. 将 python-jose 迁移到 PyJWT（修改 core/auth.py 中的 import）
3. 创建 .env.example 的完整版本（包含所有配置项和注释）

## 约束
- 不修改业务逻辑代码
- 保持现有 Docker Compose 的服务编排结构
- CI 配置兼容 GitHub Actions
```

### 5.6 提示词六：性能与 API 优化

**适用场景：解决 N+1 查询、集成缓存/限流、路由懒加载**

```
你是一个全栈性能优化专家。请帮我优化项目的性能问题。

## 项目背景
新闻采编系统，FastAPI + React + TypeScript。
后端路径：backend/app/，前端路径：frontend/src/

## 后端任务
1. 替换 subprocess + curl（backend/app/services/clue_service.py 第427-449行）：
   - 使用 httpx.AsyncClient 替代 subprocess.run(['curl',...])
   - 删除重复的搜索方法（_search_bing/_baidu/_sogou 各定义了两次）

2. 集成 AI 缓存（backend/app/services/ai_service.py）：
   - cache_service.py 已实现 AIResponseCache
   - 在 analyze_clue/generate_content/improve_content 方法中集成缓存
   - 相同输入的请求直接返回缓存结果

3. 集成速率限制（backend/app/services/rate_limiter.py）：
   - rate_limiter.py 已实现令牌桶限流器
   - 在 AIAPICaller.call_with_retry 中集成 check_rate_limit

4. 配置数据库连接池（backend/app/database.py）：
   - 使用 config.py 中定义的 DATABASE_POOL_SIZE/MAX_OVERFLOW/POOL_TIMEOUT/POOL_RECYCLE

5. 将数据库初始化移入 lifespan（backend/app/main.py）：
   - Base.metadata.create_all 从模块级移入 lifespan 函数

## 前端任务
1. 路由懒加载（frontend/src/App.tsx）：
   - 使用 React.lazy() + Suspense 对所有页面组件做代码分割
   - 采编端、审核端、读者端分别打包

2. 修复 N+1 请求（frontend/src/pages/editor/Analytics.tsx）：
   - 后端添加 /api/feedback/batch 端点
   - 前端改为单次批量请求

3. 添加请求取消机制：
   - 在 useEffect cleanup 中使用 AbortController 取消未完成请求

4. 移除生产环境 mock 数据回退：
   - API 失败时显示错误提示而非静默展示假数据

## 约束
- 不改变现有 API 接口签名
- 保持现有 UI 和交互不变
- 后端优先使用已有的 httpx 依赖
```
