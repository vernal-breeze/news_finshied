# 基于大模型的新闻内容采编系统
## 完整架构设计与开发实施指南

> 版本：v1.0 | 技术栈：FastAPI + React 18 + TypeScript + SQLite + OpenAI API

---

## 目录

1. [项目总览](#1-项目总览)
2. [三端角色定义](#2-三端角色定义)
3. [完整技术架构](#3-完整技术架构)
4. [数据库设计](#4-数据库设计)
5. [后端 API 完整设计](#5-后端-api-完整设计)
6. [前端三端页面设计](#6-前端三端页面设计)
7. [核心工作流设计](#7-核心工作流设计)
8. [AI 服务模块设计](#8-ai-服务模块设计)
9. [权限与认证体系](#9-权限与认证体系)
10. [开发实施步骤](#10-开发实施步骤)
11. [项目目录结构](#11-项目目录结构)
12. [环境配置说明](#12-环境配置说明)
13. [部署方案](#13-部署方案)

---

## 1. 项目总览

### 1.1 系统定位

本系统是一个面向新闻机构的**全流程智能采编平台**，集成大模型能力，将新闻生产从线索发现到内容发布的全链路数字化、智能化。

系统分为三个独立端：

| 端 | 用户 | 访问方式 | 核心职能 |
|---|---|---|---|
| **采编端** | 记者、编辑 | 需登录（JWT） | 线索采集、稿件创作、AI 辅助写作 |
| **审核端** | 审核员、主编 | 需登录（JWT） | 多级审核、发布管理、质量把控 |
| **客户端** | 读者/公众 | 公开访问 | 新闻浏览、搜索、个性化推荐 |

### 1.2 核心亮点

- **AI 全程介入**：线索分析、内容生成、摘要提取、事实核查、配图建议均由大模型驱动
- **稿件全生命周期管理**：从草稿到发布，版本控制 + 状态流转 + 审核日志
- **多级审核机制**：支持一级/二级/三级审核，审核意见可回退
- **多模态内容处理**：文本 + 图像融合，跨模态内容生成

---

## 2. 三端角色定义

### 2.1 采编端（Editor Portal）

**访问路径**：`/editor/*`

**用户角色**：记者（Reporter）、编辑（Editor）

**核心功能模块**：

| 模块 | 功能说明 |
|---|---|
| 线索管理 | 从 URL/文本采集线索，AI 自动分析新闻价值和传播潜力 |
| 稿件管理 | 创建、编辑、删除稿件，查看历史版本 |
| AI 辅助创作 | 一键生成标题/摘要/关键词，AI 续写、改写、润色 |
| 选题策划 | 选题创建与稿件关联，策划会议记录 |
| 多模态处理 | 生成配图建议，文本转图像描述 |
| 数据面板 | 个人稿件统计、发布量、退稿率 |

### 2.2 审核端（Review Portal）

**访问路径**：`/review/*`

**用户角色**：一级审核员（Reviewer1）、二级审核员（Reviewer2）、主编（ChiefEditor）

**核心功能模块**：

| 模块 | 功能说明 |
|---|---|
| 待审队列 | 按级别、优先级、时间排序展示待审稿件 |
| 稿件审阅 | 富文本预览、AI 辅助检查报告（语法/事实/风格） |
| 审核操作 | 通过、拒绝（附原因）、退回修改、降级/升级审核 |
| 发布管理 | 定时发布、立即发布、下线管理 |
| 权限管理 | 用户角色分配，审核权限配置 |
| 审核统计 | 审核量、通过率、平均审核时长 |

### 2.3 客户端（Reader Portal）

**访问路径**：`/`（根路径，公开访问）

**用户角色**：匿名读者（可选注册）

**核心功能模块**：

| 模块 | 功能说明 |
|---|---|
| 新闻列表 | 按分类、时间、热度浏览已发布新闻 |
| 文章详情 | 图文阅读，字体调节，分享、收藏 |
| 搜索功能 | 全文搜索 + 关键词过滤 |
| 个性化推荐 | 基于浏览记录的 AI 推荐（可选） |
| 评论互动 | 留言、点赞、举报功能（可选） |
| 热点专题 | 编辑推荐专题聚合页 |

---

## 3. 完整技术架构

### 3.1 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    前端层（React 18 + TypeScript）         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   采编端      │  │   审核端      │  │   客户端      │   │
│  │ /editor/*    │  │ /review/*    │  │  /（公开）    │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
└─────────┼─────────────────┼─────────────────┼───────────┘
          │                 │                 │
          └─────────────────▼─────────────────┘
                       Axios HTTP
┌─────────────────────────────────────────────────────────┐
│                  后端层（FastAPI）                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │           统一 API 入口（/api/v1）                │   │
│  │  认证中间件（JWT）  │  CORS 中间件  │  日志中间件  │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ 用户模块  │ │ 线索模块  │ │ 稿件模块  │ │ 审核模块  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ AI 服务   │ │ 内容生成  │ │ 多模态   │ │ 统计模块  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   SQLite DB     OpenAI API    外部新闻源
  (SQLAlchemy)  (大模型服务)  (RSS/爬虫)
```

### 3.2 前端技术栈

| 技术 | 版本 | 用途 |
|---|---|---|
| React | 18.x | UI 框架 |
| TypeScript | 5.x | 类型安全 |
| Ant Design | 5.x | UI 组件库 |
| React Router | 6.x | 路由管理 |
| Axios | 1.x | HTTP 请求 |
| Vite | 5.x | 构建工具 |
| dayjs | 1.x | 日期处理 |

### 3.3 后端技术栈

| 技术 | 版本 | 用途 |
|---|---|---|
| FastAPI | 0.100+ | Web 框架 |
| SQLAlchemy | 2.x | ORM |
| Pydantic | 2.x | 数据校验 |
| python-jose | - | JWT 处理 |
| passlib | - | 密码加密 |
| OpenAI SDK | - | AI 服务调用 |
| BeautifulSoup4 | - | 网页内容解析 |
| httpx | - | 异步 HTTP |
| uvicorn | - | ASGI 服务器 |

---

## 4. 数据库设计

### 4.1 用户表（users）

```sql
CREATE TABLE users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    VARCHAR(50) UNIQUE NOT NULL,
    email       VARCHAR(100) UNIQUE NOT NULL,
    password    VARCHAR(255) NOT NULL,           -- bcrypt 哈希
    full_name   VARCHAR(100),
    role        VARCHAR(20) NOT NULL DEFAULT 'reporter',
                -- reporter | editor | reviewer1 | reviewer2 | chief_editor | admin
    is_active   BOOLEAN DEFAULT TRUE,
    avatar_url  VARCHAR(255),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 新闻线索表（clues）

```sql
CREATE TABLE clues (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           VARCHAR(200) NOT NULL,
    content         TEXT,
    source_url      VARCHAR(500),
    source_type     VARCHAR(50),     -- manual | rss | crawl | social
    category        VARCHAR(50),     -- 时政 | 社会 | 经济 | 科技 | 文化 | 体育
    status          VARCHAR(20) DEFAULT 'pending',
                    -- pending | analyzing | analyzed | adopted | rejected
    news_value      FLOAT,           -- AI 评分 0-10
    spread_potential FLOAT,          -- AI 传播潜力评分 0-10
    ai_analysis     TEXT,            -- AI 分析结论（JSON）
    keywords        TEXT,            -- 关键词列表（JSON 数组）
    creator_id      INTEGER REFERENCES users(id),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 4.3 稿件表（articles）

```sql
CREATE TABLE articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           VARCHAR(300) NOT NULL,
    content         TEXT,
    summary         TEXT,            -- AI 生成摘要
    keywords        TEXT,            -- JSON 数组
    category        VARCHAR(50),
    tags            TEXT,            -- JSON 数组
    cover_image     VARCHAR(500),    -- 封面图 URL
    author_id       INTEGER REFERENCES users(id),
    topic_id        INTEGER REFERENCES topics(id),
    clue_id         INTEGER REFERENCES clues(id),
    status          VARCHAR(30) DEFAULT 'draft',
                    -- draft | pending_review | reviewing | approved | rejected | published | offline
    review_level    INTEGER DEFAULT 1,   -- 当前审核级别 1/2/3
    word_count      INTEGER DEFAULT 0,
    view_count      INTEGER DEFAULT 0,
    publish_at      DATETIME,            -- 定时发布时间
    published_at    DATETIME,            -- 实际发布时间
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 4.4 稿件版本表（article_versions）

```sql
CREATE TABLE article_versions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id  INTEGER REFERENCES articles(id),
    version     INTEGER NOT NULL,
    title       VARCHAR(300),
    content     TEXT,
    summary     TEXT,
    change_note VARCHAR(500),        -- 版本备注
    created_by  INTEGER REFERENCES users(id),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 4.5 审核记录表（reviews）

```sql
CREATE TABLE reviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id      INTEGER REFERENCES articles(id),
    reviewer_id     INTEGER REFERENCES users(id),
    review_level    INTEGER NOT NULL,    -- 1 | 2 | 3
    action          VARCHAR(20) NOT NULL,
                    -- approve | reject | return | escalate
    comment         TEXT,                -- 审核意见
    ai_check_result TEXT,               -- AI 审核结果（JSON）
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 4.6 选题表（topics）

```sql
CREATE TABLE topics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    category    VARCHAR(50),
    priority    INTEGER DEFAULT 0,      -- 优先级 0-5
    deadline    DATETIME,
    creator_id  INTEGER REFERENCES users(id),
    status      VARCHAR(20) DEFAULT 'active',
                -- active | completed | cancelled
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 4.7 系统配置表（system_configs）

```sql
CREATE TABLE system_configs (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    key     VARCHAR(100) UNIQUE NOT NULL,
    value   TEXT,
    remark  VARCHAR(255),
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. 后端 API 完整设计

### 5.1 认证模块 `/api/auth`

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| POST | `/api/auth/login` | 用户登录，返回 JWT | 公开 |
| POST | `/api/auth/logout` | 登出（客户端清除 Token） | 登录 |
| GET | `/api/auth/me` | 获取当前用户信息 | 登录 |
| PUT | `/api/auth/me` | 更新个人信息 | 登录 |
| POST | `/api/auth/change-password` | 修改密码 | 登录 |

### 5.2 用户管理 `/api/users`

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| GET | `/api/users` | 获取用户列表 | admin |
| POST | `/api/users` | 创建用户 | admin |
| GET | `/api/users/{id}` | 获取用户详情 | admin |
| PUT | `/api/users/{id}` | 修改用户信息/角色 | admin |
| DELETE | `/api/users/{id}` | 禁用用户 | admin |

### 5.3 线索管理 `/api/clues`

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| GET | `/api/clues` | 获取线索列表（支持过滤/分页） | 采编 |
| POST | `/api/clues` | 手动创建线索 | 采编 |
| GET | `/api/clues/{id}` | 获取线索详情 | 采编 |
| PUT | `/api/clues/{id}` | 更新线索 | 采编 |
| DELETE | `/api/clues/{id}` | 删除线索 | 采编 |
| POST | `/api/clues/{id}/analyze` | AI 分析线索价值 | 采编 |
| POST | `/api/clues/collect` | 从 URL 采集线索 | 采编 |
| POST | `/api/clues/{id}/adopt` | 将线索转为稿件 | 采编 |

### 5.4 稿件管理 `/api/articles`

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| GET | `/api/articles` | 获取稿件列表（status 过滤） | 按角色 |
| POST | `/api/articles` | 创建稿件 | 采编 |
| GET | `/api/articles/{id}` | 获取稿件详情 | 按角色 |
| PUT | `/api/articles/{id}` | 更新稿件内容 | 采编（本人） |
| DELETE | `/api/articles/{id}` | 删除稿件（草稿状态） | 采编（本人） |
| POST | `/api/articles/{id}/submit` | 提交审核 | 采编 |
| POST | `/api/articles/{id}/version` | 保存新版本 | 采编 |
| GET | `/api/articles/{id}/versions` | 获取版本历史 | 采编 |
| GET | `/api/articles/{id}/versions/{v}` | 获取指定版本 | 采编 |
| POST | `/api/articles/{id}/publish` | 发布稿件 | 审核 |
| POST | `/api/articles/{id}/offline` | 下线稿件 | 审核/admin |
| GET | `/api/articles/public` | 获取已发布文章（客户端用） | 公开 |
| GET | `/api/articles/public/{id}` | 获取已发布文章详情 | 公开 |

### 5.5 审核管理 `/api/reviews`

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| GET | `/api/reviews/queue` | 获取待审队列 | 审核 |
| POST | `/api/reviews` | 提交审核结果（通过/拒绝/退回） | 审核 |
| GET | `/api/reviews/article/{id}` | 获取稿件审核历史 | 采编/审核 |
| GET | `/api/reviews/stats` | 审核统计数据 | 审核 |

### 5.6 内容生成 `/api/content`

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| POST | `/api/content/generate` | AI 生成新闻草稿 | 采编 |
| POST | `/api/content/title` | AI 生成标题建议 | 采编 |
| POST | `/api/content/summary` | AI 生成摘要 | 采编 |
| POST | `/api/content/keywords` | AI 提取关键词 | 采编 |
| POST | `/api/content/polish` | AI 润色/改写 | 采编 |
| POST | `/api/content/check` | AI 语法/事实检查 | 采编/审核 |

### 5.7 多模态 `/api/multimodal`

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| POST | `/api/multimodal/generate` | 生成多模态内容描述 | 采编 |
| POST | `/api/multimodal/image-suggest` | 为文章生成配图建议 | 采编 |
| POST | `/api/multimodal/upload` | 上传图片到文章 | 采编 |

### 5.8 选题管理 `/api/topics`

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| GET | `/api/topics` | 获取选题列表 | 采编 |
| POST | `/api/topics` | 创建选题 | 采编 |
| GET | `/api/topics/{id}` | 获取选题详情 | 采编 |
| PUT | `/api/topics/{id}` | 更新选题 | 采编 |
| GET | `/api/topics/{id}/articles` | 获取选题下的稿件 | 采编 |

### 5.9 统计面板 `/api/dashboard`

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| GET | `/api/dashboard/editor` | 采编端统计（个人） | 采编 |
| GET | `/api/dashboard/review` | 审核端统计 | 审核 |
| GET | `/api/dashboard/public` | 客户端统计（文章热度） | 公开 |

---

## 6. 前端三端页面设计

### 6.1 采编端页面结构

```
/editor
├── /login                  登录页
├── /dashboard              首页/数据面板
├── /clues                  线索列表页
│   ├── /clues/new          新建线索
│   └── /clues/:id          线索详情（含 AI 分析）
├── /articles               稿件列表页
│   ├── /articles/new       新建稿件（富文本编辑器）
│   └── /articles/:id       稿件详情/编辑（版本历史）
├── /topics                 选题策划页
│   ├── /topics/new         新建选题
│   └── /topics/:id         选题详情
└── /profile                个人设置
```

**关键组件**：

- `RichTextEditor`：富文本编辑器（推荐 Quill 或 TipTap），支持 AI 内联辅助
- `AIAssistPanel`：侧边 AI 助手面板（生成标题/摘要/关键词）
- `ClueCard`：线索卡片，展示新闻价值评分、传播潜力
- `VersionHistory`：版本历史抽屉组件
- `StatusBadge`：稿件状态标签（草稿/待审/已发布等）

### 6.2 审核端页面结构

```
/review
├── /login                  登录页（与采编端共用，按角色跳转）
├── /dashboard              审核统计首页
├── /queue                  待审队列页
│   └── /queue/:id          稿件审阅页（核心页）
│       ├── 稿件预览（全文）
│       ├── AI 检查报告（语法/事实/风格）
│       ├── 版本对比
│       └── 审核操作区（通过/退回/拒绝）
├── /history                已处理记录
├── /published              发布管理（定时/立即/下线）
└── /settings               系统配置（admin）
    ├── /settings/users     用户权限管理
    └── /settings/system    系统参数配置
```

**关键组件**：

- `ReviewQueue`：待审稿件队列（支持优先级排序、级别过滤）
- `ArticlePreview`：稿件全文预览，支持对比上一版本
- `AICheckReport`：AI 检查报告卡片（语法错误/疑似事实问题/风格建议）
- `ReviewActionBar`：审核操作栏（通过/退回/拒绝 + 意见输入框）
- `PublishScheduler`：定时发布设置组件

### 6.3 客户端页面结构

```
/（根路径）
├── /                       首页（热门/推荐/分类）
├── /category/:slug         分类列表页
├── /article/:id            文章详情页
├── /search                 搜索结果页
├── /topic/:id              专题聚合页
└── /about                  关于页面
```

**关键组件**：

- `NewsCard`：新闻卡片（封面图 + 标题 + 摘要 + 发布时间）
- `ArticleReader`：文章阅读器（字体调节、目录、分享）
- `SearchBar`：搜索栏（关键词 + 分类过滤）
- `CategoryNav`：分类导航栏
- `RecommendList`：推荐文章列表（AI 推荐）

---

## 7. 核心工作流设计

### 7.1 稿件状态流转

```
创建草稿
    │
    ▼
  draft（草稿）
    │  记者提交审核
    ▼
pending_review（待审核）
    │  审核员认领
    ▼
 reviewing（审核中）
    │
    ├── 通过 ──────────────────► approved（已通过）
    │                                │
    ├── 退回修改 ──► draft（草稿）    │  主编发布
    │                                ▼
    └── 拒绝 ──────► rejected    published（已发布）
                                     │
                                     │  下线
                                     ▼
                                  offline（已下线）
```

### 7.2 多级审核流程

```
一级审核（Reviewer1）
    │
    ├── 通过 ──► 二级审核（Reviewer2）
    │               │
    │               ├── 通过 ──► 主编审核（ChiefEditor）
    │               │               │
    │               │               ├── 通过 ──► 发布
    │               │               └── 拒绝/退回
    │               └── 拒绝/退回
    └── 拒绝/退回（直接退回记者）
```

**说明**：

- 退回操作需填写意见，稿件重回 `draft` 状态，记者修改后可再次提交
- 每次审核操作均写入 `reviews` 表，形成完整的审核日志
- 主编有权跳过级别，直接终审

### 7.3 AI 辅助线索采集流程

```
输入来源：URL / 文本 / RSS Feed
    │
    ▼
内容抓取（BeautifulSoup4 / httpx）
    │
    ▼
AI 预处理：
    ├── 提取核心信息（5W1H）
    ├── 评估新闻价值（0-10分）
    ├── 评估传播潜力（0-10分）
    ├── 分类标注（时政/社会/经济/科技等）
    └── 提取关键词
    │
    ▼
存入 clues 表（status: analyzed）
    │
    ▼
采编人员审阅 → 采纳 → 创建稿件
```

### 7.4 AI 稿件生成流程

```
输入：线索 ID 或 主题描述
    │
    ▼
构建 Prompt（包含新闻体裁、字数要求、风格指令）
    │
    ▼
OpenAI API 调用（Stream 流式输出）
    │
    ▼
前端实时展示生成内容
    │
    ▼
记者审阅修改 → 保存草稿
```

---

## 8. AI 服务模块设计

### 8.1 模块结构

```python
# backend/app/ai_service.py

class AIService:
    # 线索相关
    async def analyze_clue(clue_text: str) -> ClueAnalysis
    async def collect_from_url(url: str) -> ClueData

    # 内容生成
    async def generate_article(topic: str, style: str) -> str
    async def generate_title(content: str) -> list[str]
    async def generate_summary(content: str) -> str
    async def extract_keywords(content: str) -> list[str]
    async def polish_content(content: str, instruction: str) -> str

    # 质量检查
    async def check_grammar(content: str) -> GrammarReport
    async def check_facts(content: str) -> FactCheckReport
    async def check_style(content: str) -> StyleReport

    # 多模态
    async def generate_image_description(content: str) -> list[str]
    async def suggest_images(article: Article) -> list[ImageSuggestion]
```

### 8.2 Prompt 模板设计

**新闻生成 Prompt**：

```
你是一名专业新闻记者，请根据以下线索撰写一篇{style}风格的新闻稿件。
要求：
- 字数约 {word_count} 字
- 遵循新闻写作的倒金字塔结构
- 第一段需包含 5W（何时/何地/何人/何事/为何）
- 语言简洁客观，避免主观表达
- 确保信息准确，不臆测

线索信息：
{clue_content}
```

**AI 审核检查 Prompt**：

```
请对以下新闻稿件进行专业审查，返回 JSON 格式的检查报告：
检查项目：
1. 语法错误（列出具体位置和建议）
2. 疑似事实错误（标注需核实的陈述）
3. 风格建议（是否符合新闻规范）
4. 总体评分（0-100）

稿件内容：
{article_content}

请只返回 JSON，格式如下：
{"grammar_issues": [], "fact_issues": [], "style_suggestions": [], "score": 0}
```

### 8.3 流式输出实现

```python
from fastapi.responses import StreamingResponse

@router.post("/api/content/generate")
async def generate_content(request: GenerateRequest):
    async def stream():
        async for chunk in ai_service.stream_generate(request.topic):
            yield f"data: {chunk}\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream")
```

---

## 9. 权限与认证体系

### 9.1 角色权限矩阵

| 操作 | reporter | editor | reviewer1 | reviewer2 | chief_editor | admin |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 创建/编辑线索 | ✅ | ✅ | | | | ✅ |
| 创建/编辑稿件 | ✅ | ✅ | | | | ✅ |
| 提交稿件审核 | ✅ | ✅ | | | | ✅ |
| 一级审核 | | | ✅ | ✅ | ✅ | ✅ |
| 二级审核 | | | | ✅ | ✅ | ✅ |
| 终审/发布 | | | | | ✅ | ✅ |
| 下线文章 | | | | | ✅ | ✅ |
| 用户管理 | | | | | | ✅ |
| 系统配置 | | | | | | ✅ |

### 9.2 JWT 认证实现

```python
# backend/app/auth.py

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict) -> str:
    """生成 JWT Token，payload 包含 user_id 和 role"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """JWT 依赖注入，验证 Token 并返回当前用户"""
    ...

def require_role(*roles):
    """角色权限装饰器"""
    async def checker(current_user = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return current_user
    return checker

# 使用示例
@router.post("/api/reviews")
async def create_review(
    user = Depends(require_role("reviewer1", "reviewer2", "chief_editor", "admin"))
):
    ...
```

### 9.3 前端路由守卫

```typescript
// frontend/src/router/guards.tsx

const EditorRoute = ({ children }) => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/editor/login" />;
  if (!["reporter", "editor", "admin"].includes(user.role)) {
    return <Navigate to="/403" />;
  }
  return children;
};

const ReviewRoute = ({ children }) => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/review/login" />;
  if (!["reviewer1", "reviewer2", "chief_editor", "admin"].includes(user.role)) {
    return <Navigate to="/403" />;
  }
  return children;
};
```

---

## 10. 开发实施步骤

### 第一阶段：基础搭建（第 1-2 周）

#### 步骤 1：完善后端用户认证

```bash
# 安装依赖
pip install python-jose[cryptography] passlib[bcrypt]
```

需要完成的文件：
- `backend/app/auth.py`：JWT 生成/验证逻辑
- `backend/app/models.py`：添加 `User` 模型（含 `role` 字段）
- `backend/app/schemas.py`：添加 `UserCreate`、`Token`、`LoginRequest` 等 Schema
- `backend/app/routers/auth.py`：实现 `/api/auth/login`、`/api/auth/me` 接口

初始化默认用户（在 `main.py` 中）：
```python
# 系统启动时创建默认管理员账号
admin_user = User(
    username="admin",
    email="admin@news.com",
    password=hash_password("admin123"),
    role="admin"
)
```

#### 步骤 2：完善数据库模型

在 `backend/app/models.py` 中添加/完善：
- `User` 表（参考第 4.1 节）
- `ArticleVersion` 表（稿件版本）
- 确保 `Article` 表有 `review_level`、`publish_at` 字段
- 确保 `Review` 表有 `review_level`、`ai_check_result` 字段

#### 步骤 3：前端项目初始化

```bash
cd frontend
npm install
```

创建目录结构：
```
src/
├── components/         # 共用组件
├── pages/
│   ├── editor/         # 采编端页面
│   ├── review/         # 审核端页面
│   └── reader/         # 客户端页面
├── hooks/              # 自定义 Hooks
├── store/              # 状态管理（Context 或 Zustand）
├── utils/
│   ├── request.ts      # Axios 封装（含拦截器）
│   └── auth.ts         # Token 存取工具
└── router/
    ├── index.tsx        # 路由总入口
    └── guards.tsx       # 路由守卫
```

配置 Axios 拦截器（`src/utils/request.ts`）：
```typescript
// 请求拦截：自动附加 JWT
request.interceptors.request.use(config => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 响应拦截：401 跳转登录
request.interceptors.response.use(null, error => {
  if (error.response?.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "/editor/login";
  }
  return Promise.reject(error);
});
```

---

### 第二阶段：采编端核心功能（第 3-4 周）

#### 步骤 4：实现线索管理功能

后端（`backend/app/routers/clues.py`）：
- 实现线索 CRUD 接口
- 实现 `POST /api/clues/collect`（URL 采集）
- 实现 `POST /api/clues/{id}/analyze`（AI 分析）

前端（`src/pages/editor/clues/`）：
- `ClueListPage`：线索列表，包含状态过滤、搜索
- `ClueDetailPage`：线索详情，展示 AI 分析报告
- `ClueCard` 组件：显示评分进度条（新闻价值 / 传播潜力）

#### 步骤 5：实现稿件编辑功能

安装富文本编辑器：
```bash
npm install @tiptap/react @tiptap/starter-kit @tiptap/extension-placeholder
```

前端（`src/pages/editor/articles/`）：
- `ArticleListPage`：稿件列表（含状态标签、字数统计）
- `ArticleEditPage`：核心编辑页，左侧编辑器 + 右侧 AI 助手面板
- `VersionHistoryDrawer`：版本历史抽屉

AI 助手面板功能：
- 一键生成标题（返回 3 个候选）
- 一键生成摘要
- 提取关键词
- 内容润色（通用 / 正式化 / 简洁化）

#### 步骤 6：实现稿件提交审核

后端：
- `POST /api/articles/{id}/submit`：将状态改为 `pending_review`，创建版本快照
- 提交时需验证：稿件有标题、有正文、字数 ≥ 200

前端：
- 提交确认 Modal（含字数统计、版本备注输入）
- 提交后跳转到稿件列表，显示"已提交"状态

---

### 第三阶段：审核端功能（第 5-6 周）

#### 步骤 7：实现待审队列

后端（`backend/app/routers/reviews.py`）：
- `GET /api/reviews/queue`：根据审核员角色返回对应级别待审稿件
  - `reviewer1` → 返回 `review_level=1` 的稿件
  - `reviewer2` → 返回 `review_level=2` 的稿件
  - `chief_editor` → 返回 `review_level=3` 的稿件

前端（`src/pages/review/queue/`）：
- `QueuePage`：待审列表，支持按分类/时间/优先级排序
- `QueueItem` 组件：显示稿件标题、作者、字数、等待时长

#### 步骤 8：实现稿件审阅页

前端（`src/pages/review/queue/ReviewDetailPage.tsx`）：

页面布局：
```
┌─────────────────────────────────────────────┐
│  稿件标题 | 作者 | 提交时间 | 版本          │
├─────────────────────┬───────────────────────┤
│                     │  AI 检查报告          │
│   稿件全文预览       │  ├── 语法检查         │
│   （支持与上版本     │  ├── 事实核查         │
│    对比高亮）        │  └── 风格建议         │
│                     ├───────────────────────┤
│                     │  审核操作区           │
│                     │  意见输入框           │
│                     │  [退回] [拒绝] [通过] │
└─────────────────────┴───────────────────────┘
```

后端 `POST /api/reviews` 逻辑：
```python
# 通过：更新 review_level 或状态
if action == "approve":
    if article.review_level < max_level:
        article.review_level += 1
        article.status = "pending_review"  # 进入下一级
    else:
        article.status = "approved"  # 终审通过

# 退回：重置为草稿
elif action == "return":
    article.status = "draft"
    article.review_level = 1

# 拒绝：终止流程
elif action == "reject":
    article.status = "rejected"
```

#### 步骤 9：实现发布管理

后端：
- `POST /api/articles/{id}/publish`：立即发布（设置 `published_at = now`）
- 定时发布：保存 `publish_at` 时间戳，后端定时任务检查并发布

定时任务（使用 APScheduler）：
```bash
pip install apscheduler
```

```python
# backend/app/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job("interval", minutes=1)
async def auto_publish():
    """每分钟检查定时发布任务"""
    articles = db.query(Article).filter(
        Article.status == "approved",
        Article.publish_at <= datetime.now()
    ).all()
    for article in articles:
        article.status = "published"
        article.published_at = datetime.now()
    db.commit()
```

---

### 第四阶段：客户端（第 7 周）

#### 步骤 10：实现读者端

后端：
- `GET /api/articles/public`：返回 `status=published` 的文章列表，支持分类/关键词过滤/分页
- `GET /api/articles/public/{id}`：返回单篇文章详情（同时更新 `view_count`）
- `GET /api/articles/public/search`：全文搜索

前端（`src/pages/reader/`）：
- `HomePage`：首页，展示轮播图（热门）+ 分类导航 + 文章列表
- `CategoryPage`：分类文章列表
- `ArticleDetailPage`：文章详情阅读页
- `SearchPage`：搜索结果页

---

### 第五阶段：完善与优化（第 8 周）

#### 步骤 11：数据统计面板

采编端首页显示：
- 本月发稿数、通过率、退稿率
- 个人稿件状态分布饼图

审核端首页显示：
- 待审总数、本日处理量、平均审核时长
- 各级别审核通过率趋势图

#### 步骤 12：系统测试与优化

- 接口联调：前后端完整流程测试
- 权限边界测试：确保各角色只能访问授权资源
- AI 接口异常处理：超时、限流、无效响应的降级处理
- 前端性能：懒加载路由、图片懒加载、列表虚拟滚动

---

## 11. 项目目录结构

```
project/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 入口，注册路由和中间件
│   │   ├── database.py          # SQLAlchemy 数据库连接
│   │   ├── models.py            # 所有数据模型定义
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   ├── auth.py              # JWT 认证逻辑
│   │   ├── ai_service.py        # AI 服务封装（OpenAI 调用）
│   │   ├── clue_collector.py    # 线索采集（URL 抓取）
│   │   ├── scheduler.py         # 定时任务（定时发布）
│   │   ├── config.py            # 配置读取（pydantic-settings）
│   │   └── routers/
│   │       ├── auth.py          # 认证接口
│   │       ├── users.py         # 用户管理接口
│   │       ├── clues.py         # 线索接口
│   │       ├── articles.py      # 稿件接口
│   │       ├── reviews.py       # 审核接口
│   │       ├── content.py       # AI 内容生成接口
│   │       ├── multimodal.py    # 多模态接口
│   │       ├── topics.py        # 选题接口
│   │       └── dashboard.py     # 统计面板接口
│   ├── requirements.txt
│   └── .env
│
└── frontend/
    ├── src/
    │   ├── components/          # 共用组件
    │   │   ├── StatusBadge.tsx  # 稿件状态标签
    │   │   ├── AIPanel.tsx      # AI 助手面板
    │   │   ├── RichEditor.tsx   # 富文本编辑器封装
    │   │   └── PageLayout.tsx   # 三端通用布局
    │   ├── pages/
    │   │   ├── editor/          # 采编端
    │   │   │   ├── Dashboard.tsx
    │   │   │   ├── clues/
    │   │   │   ├── articles/
    │   │   │   └── topics/
    │   │   ├── review/          # 审核端
    │   │   │   ├── Dashboard.tsx
    │   │   │   ├── queue/
    │   │   │   ├── published/
    │   │   │   └── settings/
    │   │   └── reader/          # 客户端
    │   │       ├── Home.tsx
    │   │       ├── Category.tsx
    │   │       ├── ArticleDetail.tsx
    │   │       └── Search.tsx
    │   ├── hooks/
    │   │   ├── useAuth.ts       # 认证 Hook
    │   │   └── useAI.ts         # AI 调用 Hook
    │   ├── store/
    │   │   └── AuthContext.tsx  # 全局用户状态
    │   ├── utils/
    │   │   ├── request.ts       # Axios 封装
    │   │   └── auth.ts          # Token 工具
    │   ├── router/
    │   │   ├── index.tsx        # 路由配置
    │   │   └── guards.tsx       # 路由守卫
    │   ├── App.tsx
    │   └── main.tsx
    ├── package.json
    ├── vite.config.ts
    └── tsconfig.json
```

---

## 12. 环境配置说明

### 12.1 后端 `.env` 完整配置

```env
# 数据库
DATABASE_URL=sqlite:///./data/news_editor.db

# JWT 认证
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480   # 8 小时

# OpenAI / 大模型
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini          # 默认模型

# 应用配置
APP_NAME=新闻内容采编系统
APP_VERSION=1.0.0
DEBUG=false
HOST=0.0.0.0
PORT=8000
WORKERS=2

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# 新闻采集
CRAWL_INTERVAL=3600               # 自动采集间隔（秒）
CRAWL_MAX_ITEMS=50               # 每次最多采集条数
```

### 12.2 前端 `.env` 配置

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=新闻内容采编系统
```

---

## 13. 部署方案

### 13.1 开发环境启动

```bash
# 启动后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # 填入 OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000

# 启动前端（新终端）
cd frontend
npm install
npm run dev             # 访问 http://localhost:3000
```

### 13.2 生产环境部署（简单版）

```bash
# 后端：使用 gunicorn
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# 前端：构建静态文件
npm run build           # 生成 dist/
# 使用 Nginx 托管 dist/ 目录
```

### 13.3 Nginx 配置参考

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 流式 API（Server-Sent Events）
    location /api/content/generate {
        proxy_pass http://127.0.0.1:8000;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

---

## 附录：关键依赖版本

### 后端 `requirements.txt`

```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
openai>=1.0.0
httpx>=0.25.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
apscheduler>=3.10.0
aiofiles>=23.0.0
python-multipart>=0.0.6
```

### 前端 `package.json` 核心依赖

```json
{
  "dependencies": {
    "antd": "^5.15.0",
    "axios": "^1.6.7",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.22.0",
    "dayjs": "^1.11.20",
    "@tiptap/react": "^2.3.0",
    "@tiptap/starter-kit": "^2.3.0",
    "@ant-design/charts": "^2.0.0"
  }
}
```

---

*文档版本：v1.0 | 最后更新：2026-04-03*