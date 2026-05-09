# 新闻采编系统 — 目录结构重构计划

## 摘要

对项目进行全面目录结构重构，使前后端代码按业务域清晰组织。后端核心是将臃肿的 `main.py`（1830行）和 `schemas/__init__.py`（595行）拆分为按业务域组织的模块；前端核心是将扁平的 `pages/` 目录按角色（auth/editor/review/reader）分组，并将 API 调用从 `utils/` 提取到 `services/`。

---

## 当前状态分析

### 后端 `backend/app/` 问题
| 问题 | 详情 |
|------|------|
| `main.py` 臃肿 | 1830行，包含所有 API 路由、中间件、异常处理、权限辅助函数 |
| `routers/` 不完整 | 仅有 `auth.py` 和 `messages.py`，其余路由全在 `main.py` |
| `schemas/__init__.py` 臃肿 | 595行，所有 Pydantic schema 在一个文件 |
| `models.py` 单文件 | 437行，10个模型+7个枚举+密码工具 |
| 根目录杂乱 | `ai_service.py`、`auth.py`、`clue_collector.py` 等散落 |
| 缺少目录 | `core/`、`middleware/`、`utils/`、`enums/`、`migrations/` |

### 前端 `frontend/src/` 问题
| 问题 | 详情 |
|------|------|
| `pages/` 混杂 | 采编端页面与 `review/`、`reader/` 子目录混在一起 |
| 缺少 `services/` | API 调用逻辑在 `utils/` 中 |
| 缺少 `layouts/` | 布局组件放在 `components/` 下 |
| 缺少 `constants/` | 常量定义分散 |
| CSS 散落 | 各页面目录中独立 CSS 文件 |

### 根目录问题
- `docs/` 在 `backend/` 下，应提升到项目根目录
- `run_backend.sh`、`start.sh` 散落在根目录
- 缺少 `.github/`、`scripts/` 目录

---

## 目标目录结构

### 后端目标结构
```
backend/
  app/
    __init__.py
    main.py                          # 精简入口（<100行）
    config.py                        # 保持不变
    database.py                      # 保持不变
    dependencies.py                  # 新建：公共依赖注入

    core/                            # 核心工具模块
      __init__.py
      auth.py                        # ← app/auth.py
      security.py                    # ← models.py 中密码哈希函数
      exceptions.py                  # ← app/exceptions.py
      logging_config.py              # ← app/logging_config.py

    enums/                           # 枚举类型
      __init__.py                    # 统一导出
      user.py                        # UserRole
      article.py                     # ArticleStatus
      review.py                      # ReviewLevel, ReviewResult
      topic.py                       # TopicStatus
      collection.py                  # CollectionStatus, MaterialType

    models/                          # 按业务域拆分
      __init__.py                    # 统一导出（向后兼容）
      base.py                        # BaseModel + get_beijing_time
      user.py                        # User
      clue.py                        # NewsClue
      article.py                     # Article, ArticleComment
      review.py                      # Review
      topic.py                       # TopicPlanning, topic_article_association
      feedback.py                    # PublicationFeedback
      collection.py                  # CollectionTask, CollectedMaterial
      message.py                     # Message

    schemas/                         # 按业务域拆分
      __init__.py                    # 统一重导出（向后兼容）
      base.py                        # 保持不变
      clue.py                        # NewsClue 相关
      article.py                     # Article 相关
      review.py                      # Review 相关
      topic.py                       # TopicPlanning 相关
      feedback.py                    # PublicationFeedback + 统计
      collection.py                  # CollectionTask/CollectedMaterial
      ai.py                          # AI 分析/生成/评估
      content.py                     # 内容编辑/搜索请求
      comment.py                     # 读者评论

    routers/                         # 按业务域拆分
      __init__.py                    # 统一导出所有 router
      auth.py                        # 保持不变
      messages.py                    # 保持不变
      clues.py                       # ← main.py 线索路由
      articles.py                    # ← main.py 稿件路由
      topics.py                      # ← main.py 选题路由
      reviews.py                     # ← main.py 审核路由
      feedback.py                    # ← main.py 反馈路由
      content.py                     # ← main.py AI内容路由
      public.py                      # ← main.py 公开接口
      collection.py                  # ← main.py 采集路由
      stats.py                       # ← main.py 统计路由
      health.py                      # ← main.py 健康检查

    middleware/
      __init__.py
      request_id.py                  # ← main.py 中间件
      logging.py                     # ← logging_config.py 中 LoggingMiddleware

    services/                        # 保持不变（已按业务域拆分）
      __init__.py
      ai_service.py
      article_service.py
      cache_service.py
      clue_service.py
      collection_service.py
      feedback_service.py
      rate_limiter.py
      review_service.py
      task_queue.py
      topic_service.py

    utils/                           # 工具函数
      __init__.py
      clue_collector.py              # ← app/clue_collector.py
      permissions.py                 # ← main.py 中 _get_*_for_editor

    migrations/                      # 数据库迁移
      __init__.py
      schema_migrations.py           # ← main.py 中 _ensure_sqlite_schema_migrations
      seed.py                        # ← main.py 中 init_default_users

  scripts/
    generate_ai_articles.py          # ← backend/ 根目录
    seed_data.py                     # ← backend/ 根目录
  docs/                              # 保持不变
  .env.example
  Dockerfile
  requirements.txt
  requirements_simple.txt
```

### 前端目标结构
```
frontend/
  src/
    main.tsx
    App.tsx                          # 更新 import 路径
    App.css
    index.css
    vite-env.d.ts

    components/
      common/                        # 通用组件
        Toast.tsx                    # ← components/Toast.tsx
      layouts/                       # 布局组件
        MainLayout.tsx               # ← components/Layout.tsx
        ReviewLayout.tsx             # ← components/review/Layout.tsx
        ReviewLayout.css             # ← components/review/Layout.css
      reader/                        # 保持不变
        ReaderHeader.tsx
        ReaderHeader.css

    pages/
      auth/                          # 认证页面
        Login.tsx                    # ← pages/Login.tsx
        Login.css                    # ← pages/Login.css
        Register.tsx                 # ← pages/Register.tsx
        index.ts                     # 统一导出
      editor/                        # 采编端页面
        Home.tsx                     # ← pages/Home.tsx
        Clues.tsx                    # ← pages/Clues.tsx
        Articles.tsx                 # ← pages/Articles.tsx
        Topics.tsx                   # ← pages/Topics.tsx
        Analytics.tsx                # ← pages/Analytics.tsx
        AIArticle.tsx                # ← pages/AIArticle.tsx
        index.ts                     # 统一导出
      review/                        # 保持不变
        ...
      reader/                        # 保持不变
        ...

    services/                        # API 调用层
      index.ts                       # 统一导出
      api.ts                         # ← utils/api.ts
      apiBase.ts                     # ← utils/apiBase.ts
      authClient.ts                  # ← utils/authClient.ts
      readerApi.ts                   # ← utils/readerApi.ts

    hooks/
      useAuthSnapshot.ts             # 保持不变
    utils/
      url.ts                         # 保持不变
    types/
      index.ts                       # 保持不变
    constants/
      index.ts                       # 新建：路由路径、API 端点常量
```

### 根目录目标结构
```
项目根目录/
  .github/
    workflows/
      ci.yml                         # 新建
  docs/                              # ← backend/docs/ + graduate_work.md
  scripts/                           # 新建
    run_backend.sh                   # ← 根目录
    start.sh                         # ← 根目录
  backend/
    ...
  frontend/
    ...
  README.md
  docker-compose.yml
```

---

## 详细实施步骤

### 阶段一：后端重构

#### 1.1 创建新目录结构
创建 `core/`、`enums/`、`models/`、`middleware/`、`utils/`、`migrations/`、`scripts/` 目录及 `__init__.py`。

#### 1.2 拆分枚举类型 → `enums/`
- 从 `models.py` 提取 `UserRole`、`ArticleStatus`、`ReviewLevel`、`ReviewResult`、`TopicStatus`、`CollectionStatus`、`MaterialType`
- 按业务域分到 `user.py`、`article.py`、`review.py`、`topic.py`、`collection.py`
- `__init__.py` 统一导出

#### 1.3 拆分 SQLAlchemy 模型 → `models/`
- `base.py`：`BaseModel` + `get_beijing_time()`
- `user.py`：`User`
- `clue.py`：`NewsClue`
- `article.py`：`Article`、`ArticleComment`
- `review.py`：`Review`
- `topic.py`：`TopicPlanning`、`topic_article_association`
- `feedback.py`：`PublicationFeedback`
- `collection.py`：`CollectionTask`、`CollectedMaterial`
- `message.py`：`Message`
- 原 `models.py` 改为纯重导出文件（向后兼容）

#### 1.4 拆分 Pydantic Schemas → `schemas/`
- `base.py`：保持不变
- `clue.py`：`NewsClueBase/Create/Update/NewsClue`
- `article.py`：`ArticleBase/Create/Update/Article` + `_coerce_article_status_value`
- `review.py`：`ReviewBase/Create/Update/Review`
- `topic.py`：`TopicPlanningBase/Create/Update/TopicPlanning` + 关联请求 Schema
- `feedback.py`：`PublicationFeedback*` + `FeedbackStats` + `TrendDataPoint`
- `collection.py`：`CollectionTask*` + `CollectedMaterial*`
- `ai.py`：AI 分析/生成/评估相关 Schema
- `content.py`：内容编辑/搜索相关 Schema
- `comment.py`：`ReaderCommentCreate`、`ReaderCommentOut`
- 原 `__init__.py` 改为统一重导出（向后兼容）

#### 1.5 拆分 API 路由 → `routers/`
从 `main.py` 按业务域提取路由到独立文件：

| 文件 | 源行号 | 路由前缀 |
|------|--------|---------|
| `clues.py` | 488-749 | `/api/clues` |
| `articles.py` | 1016-1221 | `/api/articles` |
| `topics.py` | 752-1013 | `/api/topics` |
| `reviews.py` | 1338-1426 | `/api/reviews` |
| `feedback.py` | 1428-1529 | `/api/feedback` |
| `content.py` | 1223-1336 | `/api/content` |
| `public.py` | 1531-1682 | `/api/public` |
| `collection.py` | 1685-1761 | `/api/collection` |
| `stats.py` | 1763-1820 | `/api/stats` |
| `health.py` | 367-486 | `/health` |

#### 1.6 移动核心模块 → `core/`
- `auth.py` → `core/auth.py`
- `exceptions.py` → `core/exceptions.py`
- `logging_config.py` → `core/logging_config.py`
- 新建 `core/security.py`：密码哈希函数
- 原位置保留重导出文件

#### 1.7 移动中间件 → `middleware/`
- `request_id.py`：从 `main.py` 提取
- `logging.py`：从 `logging_config.py` 提取 `LoggingMiddleware`

#### 1.8 移动工具模块 → `utils/`
- `clue_collector.py` → `utils/clue_collector.py`
- 新建 `permissions.py`：`_get_*_for_editor` 权限辅助函数

#### 1.9 移动迁移逻辑 → `migrations/`
- `schema_migrations.py`：`_ensure_sqlite_schema_migrations`
- `seed.py`：`init_default_users`

#### 1.10 精简 `main.py`
重构后仅保留：FastAPI 实例创建、中间件注册、路由注册、异常处理、启动事件。

#### 1.11 移动后端脚本 → `scripts/`
- `generate_ai_articles.py`、`seed_data.py`

#### 1.12 全局更新 import 路径
更新所有受影响文件的 import 语句。

### 阶段二：前端重构

#### 2.1 创建新目录
`components/common/`、`components/layouts/`、`pages/auth/`、`pages/editor/`、`services/`、`constants/`

#### 2.2 重组页面目录
- `pages/Login.tsx` + `Register.tsx` → `pages/auth/`
- `pages/Home.tsx` + `Clues.tsx` + `Articles.tsx` + `Topics.tsx` + `Analytics.tsx` + `AIArticle.tsx` → `pages/editor/`
- 每个子目录创建 `index.ts` 统一导出

#### 2.3 重组组件目录
- `components/Toast.tsx` → `components/common/Toast.tsx`
- `components/Layout.tsx` → `components/layouts/MainLayout.tsx`
- `components/review/Layout.tsx` → `components/layouts/ReviewLayout.tsx`

#### 2.4 提取 API 服务层
- `utils/api.ts`、`apiBase.ts`、`authClient.ts`、`readerApi.ts` → `services/`
- 创建 `services/index.ts` 统一导出

#### 2.5 创建常量文件
- `constants/index.ts`：路由路径、API 端点

#### 2.6 更新 `App.tsx` import 路径

#### 2.7 全局更新前端 import 路径

### 阶段三：根目录重构

#### 3.1 提升 `docs/` 到项目根目录
#### 3.2 创建 `scripts/` 目录
#### 3.3 创建 `.github/workflows/ci.yml`

---

## 假设与决策

1. **向后兼容优先**：所有移动操作在原位置保留重导出文件，确保现有 import 不中断
2. **服务实例化方式**：保持模块级单例（与现有 `auth.py`、`messages.py` 一致）
3. **`app/ai_service.py` 处理**：移动到 `utils/` 或删除（`main.py` 使用的是 `services/ai_service.py` 的 `EnhancedAIService`）
4. **`database.py` 位置**：保持在 `app/` 根目录不动（路径解析依赖）
5. **前端路径别名**：在 `vite.config.ts` 和 `tsconfig.json` 中配置 `@/` 别名简化 import

---

## 验证步骤

1. **后端验证**：
   - `cd backend && python -c "from app.main import app"` — 确认无 import 错误
   - `python -m uvicorn app.main:app --port 8000` — 确认服务正常启动
   - 访问 `/docs` 确认所有 API 端点正常注册
   - 访问 `/health` 确认健康检查正常

2. **前端验证**：
   - `cd frontend && npm run build` — 确认 TypeScript 编译无错误
   - `npm run dev` — 确认开发服务器正常启动
   - 浏览器访问各页面确认路由正常

3. **集成验证**：
   - `docker-compose up -d --build` — 确认 Docker 部署正常
   - 测试采编端、审核端、读者端核心功能
