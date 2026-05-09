# 基于大模型的新闻内容采编系统

> 版本：v1.0 | 技术栈：FastAPI + React 18 + TypeScript + SQLite + OpenAI API

一个面向新闻机构的**全流程智能采编平台**，集成大模型能力，将新闻生产从线索发现到内容发布的全链路数字化、智能化。

---

## 项目结构

```
news_editor/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py            # 主应用入口，路由注册
│   │   ├── models.py          # SQLAlchemy 数据模型
│   │   ├── database.py        # 数据库连接
│   │   ├── clue_collector.py  # 新闻线索采集器（含 news-aggregator-skill 集成）
│   │   ├── ai_service.py      # AI 服务层
│   │   ├── services/          # 业务逻辑层
│   │   ├── repositories/      # 数据访问层
│   │   ├── routers/           # API 路由
│   │   └── schemas/           # Pydantic 请求/响应模型
│   ├── data/                  # SQLite 数据库
│   │   └── news_editor.db     # 数据库文件（首次运行自动创建）
│   ├── requirements.txt
│   ├── run_backend.sh         # 后端启动脚本
│   └── seed_data.py           # 数据初始化
├── frontend/                  # React + TypeScript 前端
│   ├── src/
│   │   ├── pages/             # 页面组件
│   │   │   ├── Login.tsx      # 采编端登录
│   │   │   ├── Home.tsx       # 采编端首页
│   │   │   ├── Clues.tsx      # 线索管理
│   │   │   ├── Articles.tsx   # 稿件管理
│   │   │   ├── AIArticle.tsx  # AI 辅助写作
│   │   │   ├── Analytics.tsx  # 数据统计
│   │   │   ├── review/        # 审核端页面
│   │   │   │   ├── Login.tsx  # 审核端登录
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   ├── Queue.tsx  # 审核队列
│   │   │   │   ├── Published.tsx
│   │   │   │   └── Settings.tsx
│   │   │   └── reader/        # 读者端页面（公开）
│   │   │       ├── Home.tsx
│   │   │       ├── Category.tsx
│   │   │       ├── Search.tsx
│   │   │       ├── ArticleDetail.tsx
│   │   │       └── Messages.tsx
│   │   └── utils/             # 工具函数
│   └── package.json
├── skills/                    # OpenClaw Agent Skills
│   └── news-aggregator-skill/ # 新闻聚合技能（28+ 信源）
│       ├── scripts/           # 采集脚本
│       │   ├── fetch_news.py  # HackerNews/GitHub/HuggingFace 等
│       │   ├── daily_briefing.py
│       │   └── ...
│       └── instructions/      # 早报模板
├── docs/                      # 开发文档
│   ├── API_KEY_SETUP.md
│   └── AI_ARTICLE_GUIDE.md
└── docker-compose.yml         # Docker 部署
```

---

## 快速启动

### 方式一：一键启动（推荐）

```bash
# macOS / Linux
chmod +x start.sh
./start.sh

# Windows
start.bat
```

### 方式二：手动启动

**后端：**

```bash
cd backend
pip3 install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

**前端：**

```bash
cd frontend
npm install
npm run dev
```

访问：http://localhost:3000

---

## 默认账号

| 端 | 用户名 | 密码 | 角色 |
|---|---|---|---|
| 采编端 | `user` | `user123` | 投稿用户 |
| 审核端 | `reviewer` | `reviewer123` | 审核员 |

> 读者端无需登录，直接访问 http://localhost:3000/reader

---

## 核心功能

### 采编端（Editor）

- **线索管理**：多渠道采集（HackerNews / GitHub / 华尔街见闻 / 微博热搜 / V2EX），AI 分析新闻价值与传播潜力
- **稿件管理**：创建、编辑、版本控制、状态流转（草稿→待审核→审核中→已发布）
- **AI 辅助写作**：一键生成标题/摘要/关键词、AI 续写/改写/润色、内容质量评估
- **选题策划**：选题与稿件关联、策划会议记录

### 审核端（Review）

- **待审队列**：按级别、优先级、时间排序
- **AI 预审**：大模型自动评分，给出通过/需复核/不通过建议
- **多级审核**：一级/二级/三级审核，审核意见可回退
- **发布管理**：通过、拒绝、退回修改

### 读者端（Reader）

- **公开访问**：已发布稿件浏览、分类筛选、全文搜索
- **互动**：评论、点赞、分享

### 早报生成（通过 news-aggregator-skill）

```python
from app.clue_collector import ClueCollector

c = ClueCollector()

# 5 种早报模板
c.collect_daily_briefing(profile='general')   # 综合早报
c.collect_daily_briefing(profile='finance')   # 财经早报
c.collect_daily_briefing(profile='tech')      # 科技早报
c.collect_daily_briefing(profile='ai_daily')   # AI 日报
c.collect_daily_briefing(profile='social')     # 社交早报
```

---

## 技术架构

| 层次 | 技术 |
|---|---|
| 前端 | React 18 + TypeScript + Vite |
| 后端 | FastAPI + SQLAlchemy + Pydantic |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） |
| AI 服务 | SiliconFlow API（DeepSeek-V3） |
| 认证 | JWT（python-jose + passlib） |
| 新闻采集 | news-aggregator-skill（28+ 结构化信源） |

---

## API 文档

启动后端后访问：

- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

主要接口前缀：

| 模块 | 前缀 |
|---|---|
| 线索 | `POST/GET /api/clues` |
| 稿件 | `POST/GET /api/articles` |
| 内容生成 | `/api/content/generate` |
| 审核 | `/api/reviews` |
| 读者端 | `/api/public/articles` |

---

## 新闻信源（news-aggregator-skill）

| 信源 | 说明 |
|---|---|
| Hacker News | Algolia API，含关键词搜索 |
| GitHub Trending | 结构化 API |
| 华尔街见闻 | 财经新闻 |
| 微博热搜 | 实时热搜 |
| V2EX | 技术社区 |
| HuggingFace Papers | AI 学术论文 |
| AI Newsletters | AI 资讯聚合 |

---

## 数据库

数据库文件：`backend/data/news_editor.db`

首次启动自动创建表结构和默认用户。

---

## 环境变量（backend/.env）

```env
DATABASE_URL=sqlite:///./data/news_editor.db
SECRET_KEY=your-secret-key-here
SILICONFLOW_API_KEY=your-api-key-here
AI_MODEL=deepseek-ai/DeepSeek-V3
```
