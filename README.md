# 基于大模型的新闻内容采编系统

> NewsFinshied 是一个面向新闻采编业务的毕业设计项目，围绕“新闻线索采集、AI 辅助写稿、稿件审核发布、读者反馈分析”构建完整业务闭环。

## 项目简介

本系统面向新闻机构、校园媒体和内容采编团队，解决传统采编流程中线索分散、写稿耗时、审核流转不清晰、发布后反馈难沉淀的问题。

系统不是单纯的 CMS，也不是单点 AI 写作工具，而是把采编业务拆成可追踪的流程：

```text
线索采集 -> 选题策划 -> AI 稿件生成 -> 稿件管理 -> 审核发布 -> 读者反馈分析
```

## 核心功能

### 采编端

- 新闻线索采集：支持按关键词从有效来源采集线索，线索只保存到当前账号。
- 有效信源选择：新闻门户、热点 API、科技媒体、搜索发现分开选择，避免来源混用。
- 选题策划：支持选题创建、编辑、状态管理，以及选题与稿件关联。
- AI 稿件生成：支持标题、关键词、正文要求和自定义提示词一起提交给 AI。
- 稿件管理：支持稿件创建、编辑、提交审核、状态流转和发布。
- 数据统计：展示线索、稿件、审核和发布相关指标。

![采编端首页](img/user_header.png)

![新闻线索采集](img/news_search.png)

![AI 稿件生成](img/gernrate_news.png)

### 审核端

- 待审队列：集中展示待审核稿件。
- 审核处理：支持通过、拒绝、退回修改。
- AI 预审：提供辅助评分和内容质量提示，当前以规则评分和 AI 配置状态为基础。
- 发布联动：审核通过后稿件进入已发布状态，并进入反馈分析范围。

![审核端](img/reviewer_header.png)

### 读者端

- 文章浏览：展示已发布稿件。
- 搜索筛选：支持读者按标题、内容和分类检索。
- 阅读互动：支持浏览、点赞、评论、分享等反馈数据记录。

![读者端首页](img/reader_header.png)

![文章浏览](img/pages_read.png)

### 管理员端
![admin](img/admin.png)
- 用户查看：查看编辑/记者账号信息。
- 稿件查看：查看编辑发布和投稿的稿件信息。
- 账号管理：支持删除编辑账号、修改编辑密码。
- 管理功能按页面拆分，减少一个页面过度集中。

## 当前线索来源

系统只展示当前后端实际支持并可返回线索的来源。

| 类型 | 来源 | 说明 |
|------|------|------|
| 新闻门户 | 腾讯新闻、新浪新闻 | 只走对应门户源，不会自动混入 Bing 搜索结果 |
| 热点 API | 知乎日报、B站热门 | 用于获取热点或视频类内容 |
| 科技媒体 | IT之家、36氪、少数派、开源中国、极客公园 | 通过 Bing `site:` 定向搜索对应站点 |
| 搜索发现 | Bing搜索 | 仅在主动选择“搜索发现”时使用 |

注意：Bing 是搜索通道，不作为新闻真实来源显示。系统会根据结果 URL 识别真实来源，例如百度百科、IT之家、36氪、腾讯新闻等。

## 反馈分析口径

反馈分析以“已发布稿件”为准。只要稿件已经发布，即使阅读量、点赞、评论、分享都是 0，也会进入反馈分析列表。

反馈指标包括：

- 总阅读量
- 总点赞数
- 总评论数
- 总分享数
- 已发布稿件反馈列表

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18、TypeScript、Vite、Ant Design |
| 后端 | FastAPI、SQLAlchemy、Pydantic |
| 数据库 | MySQL 8.0 |
| AI 服务 | DeepSeek / SiliconFlow / OpenAI 兼容接口 |
| 认证 | JWT |
| 启动方式 | `./start.sh` 一键启动 |

## 本地运行

### 1. 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0+

### 2. 配置环境变量

复制后端环境变量模板：

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，按本地环境填写数据库连接和 AI Key。

```env
DATABASE_URL=mysql+pymysql://news_editor:change-me-db-password@localhost:3306/news_editor?charset=utf8mb4
SECRET_KEY=replace-with-a-long-random-string
DEEPSEEK_API_KEY=
SILICONFLOW_API_KEY=
OPENAI_API_KEY=
AI_MODEL=deepseek-chat
```

复制前端环境变量模板：

```bash
cp frontend/.env.example frontend/.env
```

如使用默认代理，`VITE_API_BASE_URL` 可以保持为空。

### 3. 一键启动

```bash
./start.sh
```

启动后访问：

- 前端：http://localhost:3000
- 后端：http://localhost:8000
- API 文档：http://localhost:8000/docs

常用命令：

```bash
./start.sh backend
./start.sh frontend
./start.sh restart
./start.sh stop
./start.sh status
./start.sh logs backend
```

后端默认使用 2 个 worker，并将线索采集放入线程池，减少采编端采集时对审核端的阻塞。

## 手动启动

后端：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
```

## 项目结构

```text
news_finshied/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 应用入口
│   │   ├── database.py          # 数据库连接
│   │   ├── core/                # 配置、安全、日志
│   │   ├── models/              # SQLAlchemy 模型
│   │   ├── routers/             # API 路由
│   │   ├── schemas/             # Pydantic 模型
│   │   └── services/            # AI 与业务服务
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/               # 采编端、审核端、读者端页面
│   │   ├── components/          # 公共组件
│   │   ├── services/            # API 请求封装
│   │   ├── types/               # TypeScript 类型
│   │   └── utils/               # 工具函数
│   ├── package.json
│   └── .env.example
├── img/                         # README 展示图片
├── README.md
├── 架构文档.md
├── 调整清单.md
├── 对象问题创新点.md
└── 项目总文档.md
```

## 核心数据表

| 表名 | 说明 |
|------|------|
| `users` | 用户、角色、账号状态 |
| `clues` | 新闻线索 |
| `topics` | 选题策划 |
| `articles` | 稿件内容与发布状态 |
| `reviews` | 审核记录 |
| `feedbacks` | 阅读、点赞、评论、分享等反馈数据 |
| `messages` | 站内消息 |
| `collections` | 采集任务 |

## 角色说明

| 角色 | 主要功能 |
|------|----------|
| 采编/记者 | 采集线索、AI 写稿、管理稿件、提交审核 |
| 审核员 | 查看待审稿件、审核通过/退回/拒绝 |
| 管理员 | 查看用户和稿件信息、管理编辑账号 |
| 读者 | 浏览已发布稿件并产生反馈数据 |

## GitHub 展示注意事项

- 不要提交真实 `.env` 文件。
- 不要提交真实 API Key、数据库密码或生产密钥。
- 本仓库只保留 `.env.example` 作为配置模板。
- 上传文件、依赖目录、构建产物和本地数据库文件已通过 `.gitignore` 排除。

