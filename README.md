# 基于大模型的新闻内容采编系统

> 项目名称：NewsFinshied  
> 技术栈：FastAPI + React 18 + TypeScript + MySQL 8.0 + DeepSeek / SiliconFlow API

NewsFinshied 是一个面向新闻采编场景的全流程智能平台，覆盖“线索采集、选题策划、AI 稿件生成、稿件管理、审核发布、读者反馈”完整链路。系统通过大模型能力辅助新闻生产，提高线索发现、内容生成和审核预审效率。

## 项目定位

本项目主要面向新闻机构、校园媒体和内容采编团队，解决传统采编流程中的三个问题：

- 线索分散：热点和新闻素材散落在不同平台，人工筛选成本高。
- 写稿耗时：标题、摘要、关键词、初稿和润色存在大量重复劳动。
- 审核不透明：稿件从提交到发布缺少统一状态记录和可追踪意见。

相比普通 CMS 或单点 AI 写作工具，本系统更强调“线索 → AI 写稿 → 审核 → 发布 → 反馈”的完整业务闭环。

## 核心功能

### 采编端

- 新闻线索：从有效来源采集新闻线索，并通过 AI 分析新闻价值和传播潜力。

![新闻线索采集](img/news_search.png)

- 选题策划：支持选题创建、编辑、状态管理，以及选题与稿件关联。

![选题策划](img/select_scheme.png)

- AI 稿件生成：支持输入标题、关键词、正文要求和自定义提示词，一起发送给 AI 生成稿件。

![AI 稿件生成](img/gernrate_news.png)

- 稿件管理：支持稿件创建、编辑、状态流转、提交审核和发布。

![稿件管理](img/check_report.png)

- 数据统计：展示稿件数量、线索数量、发布数量、待审核数量等核心指标。

![采编端首页](img/user_header.png)

### 审核端

- 待审队列：集中展示待审核稿件。
- AI 预审：大模型辅助判断内容质量、风险和审核建议。
- 审核流转：支持通过、拒绝、退回修改。
- 发布管理：审核通过后可发布到读者端。

![审核端](img/reviewer_header.png)

### 读者端

- 文章浏览：展示已发布稿件。
- 搜索筛选：支持按标题、内容和分类检索。
- 阅读互动：支持字号调整、评论、点赞等读者反馈能力。

![读者端首页](img/reader_header.png)

![文章浏览](img/pages_read.png)

![字号调整](img/Size_text.png)

![反馈分析](img/feedback_analyze.png)

## 本地运行

### 1. 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0+

### 2. 后端配置

复制后端环境变量模板：

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`：

```bash
DATABASE_URL=mysql+pymysql://news_editor:your-password@localhost:3306/news_editor?charset=utf8mb4
SECRET_KEY=replace-with-a-long-random-string
DEEPSEEK_API_KEY=<your-api-key>
AI_MODEL=deepseek-chat
```

也可以改用 SiliconFlow：

```bash
SILICONFLOW_API_KEY=<your-api-key>
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
AI_MODEL=deepseek-ai/DeepSeek-V3
```

### 3. 初始化数据库

先在 MySQL 中创建数据库和用户，然后执行初始化 SQL：

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS news_editor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p news_editor < backend/init.sql
```

### 4. 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端访问：

- API：http://localhost:8000
- Swagger 文档：http://localhost:8000/docs

### 5. 启动前端

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

前端访问：

- http://localhost:3000
- 如果 Vite 使用默认端口，则访问 http://localhost:5173

## 项目结构

```text
news_finshied/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── main.py          # 应用入口和路由注册
│   │   ├── database.py      # 数据库连接
│   │   ├── core/            # 配置、认证、安全能力
│   │   ├── models/          # SQLAlchemy 数据模型
│   │   ├── routers/         # API 路由
│   │   ├── schemas/         # Pydantic 请求响应模型
│   │   └── services/        # 业务服务
│   ├── init.sql             # MySQL 初始化脚本
│   ├── requirements.txt     # Python 依赖
│   └── .env.example         # 后端环境变量模板
├── frontend/                # React + TypeScript 前端
│   ├── src/
│   │   ├── pages/           # 页面
│   │   ├── services/        # API 请求
│   │   └── utils/           # 工具函数
│   ├── package.json
│   └── .env.example         # 前端环境变量模板
├── README.md
├── 架构文档.md
├── 调整清单.md
└── 对象问题创新点.md
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Vite + Ant Design |
| 后端 | FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| 数据库 | MySQL 8.0 |
| AI 服务 | DeepSeek API / SiliconFlow API |
| 认证 | JWT |
| 本地运行 | Python venv + npm |

## 核心数据表

| 表名 | 说明 |
|------|------|
| `users` | 用户与角色 |
| `clues` | 新闻线索 |
| `topics` | 选题策划 |
| `articles` | 新闻稿件 |
| `reviews` | 审核记录 |
| `feedbacks` | 读者反馈统计 |
| `messages` | 站内消息 |
| `collections` | 采集任务 |

## GitHub 展示说明

- 真实环境变量文件不会提交，请根据 `backend/.env.example` 和 `frontend/.env.example` 自行创建本地 `.env`。
- `backend/uploads/` 只保留目录结构，不提交运行时上传文件。
- 前端构建产物、依赖目录和本地数据库文件均已通过 `.gitignore` 排除。

