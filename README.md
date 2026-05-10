# 基于大模型的新闻内容采编系统

> 版本：v1.0 | 技术栈：FastAPI + React 18 + TypeScript + MySQL 8.0 + OpenAI API

一个面向新闻机构的**全流程智能采编平台**，集成大模型能力，将新闻生产从线索发现到内容发布的全链路数字化、智能化。

---

## 项目结构

```
news_finshied/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py            # 主应用入口，路由注册
│   │   ├── database.py        # 数据库连接（SQLite/MySQL 双模式）
│   │   ├── core/
│   │   │   └── config.py      # 应用配置（pydantic-settings）
│   │   ├── models/            # SQLAlchemy 数据模型
│   │   │   ├── user.py        # 用户模型
│   │   │   ├── article.py     # 文章模型
│   │   │   ├── clue.py        # 线索模型
│   │   │   ├── topic.py       # 选题模型
│   │   │   ├── review.py      # 审核模型
│   │   │   ├── feedback.py    # 反馈模型
│   │   │   ├── message.py     # 消息模型
│   │   │   └── collection.py  # 采集任务模型
│   │   ├── services/          # 业务逻辑层
│   │   ├── routers/           # API 路由
│   │   └── schemas/           # Pydantic 请求/响应模型
│   ├── init.sql               # MySQL 初始化脚本（建表+默认数据）
│   ├── requirements.txt       # Python 依赖（含 pymysql）
│   ├── Dockerfile             # 后端容器镜像
│   └── .env.example           # 环境变量模板
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
│   │   │   └── reader/        # 读者端页面（公开）
│   │   └── utils/             # 工具函数
│   ├── nginx.conf             # Nginx 配置（SPA 路由 + API 代理）
│   ├── Dockerfile             # 前端容器镜像（构建+Nginx）
│   └── package.json
├── docs/                      # 开发文档
│   ├── MySQL_Migration_Architecture.md  # MySQL 迁移架构设计
│   └── MySQL_接入操作提示词.md           # MySQL 接入操作指南
├── docker-compose.yml         # Docker Compose 编排（MySQL + Backend + Frontend）
├── docker.sh                  # Docker 一键操作脚本
└── .env.example               # 根目录环境变量模板
```

---

## 快速启动

### 方式一：Docker Compose 一键部署（推荐）

```bash
# 1. 克隆项目后，进入目录
cd news_finshied

# 2. 一键启动（自动创建 .env、拉取镜像、构建、启动）
chmod +x docker.sh
./docker.sh start

# 3. 等待服务 healthy（约 30-60 秒）
./docker.sh status
```

启动后访问：
- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- Swagger 文档：http://localhost:8000/docs
- MySQL：localhost:3306

### 方式二：手动分别启动

**前置条件：** 需要本地安装 MySQL 8.0 或使用 Docker 单独启动 MySQL。

```bash
# 1. 启动 MySQL（Docker 方式）
docker run -d \
  --name news_editor_mysql \
  -e MYSQL_ROOT_PASSWORD=rootpass123 \
  -e MYSQL_DATABASE=news_editor \
  -e MYSQL_USER=news_editor \
  -e MYSQL_PASSWORD=apppass123 \
  -p 3306:3306 \
  mysql:8.0 \
  --character-set-server=utf8mb4 \
  --collation-server=utf8mb4_unicode_ci

# 2. 等待 MySQL 就绪（约 30 秒），然后初始化表结构
docker exec -i news_editor_mysql mysql -u root -prootpass123 < backend/init.sql

# 3. 安装后端依赖并启动
cd backend
pip3 install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 8000

# 4. 安装前端依赖并启动（新终端）
cd frontend
npm install
npm run dev
```

### 常用 Docker 操作

```bash
./docker.sh start      # 启动全部服务
./docker.sh stop       # 停止全部服务
./docker.sh status     # 查看服务状态
./docker.sh logs       # 查看后端日志
./docker.sh logs mysql # 查看 MySQL 日志
./docker.sh mysql      # 进入 MySQL 命令行
./docker.sh backup     # 备份数据库
./docker.sh rebuild    # 重新构建并启动
./docker.sh clean      # 清除所有容器和数据（⚠️ 危险）
```

---

## 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| `admin` | `admin123` | 系统管理员 |

> 首次使用请通过注册接口创建新用户，或使用 init.sql 中的默认管理员账号登录。

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

---

## 技术架构

| 层次 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Vite + Ant Design |
| 后端 | FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| 数据库 | MySQL 8.0（生产）/ SQLite（本地快速开发） |
| 驱动 | PyMySQL（纯 Python，无需编译 C 扩展） |
| AI 服务 | SiliconFlow API（DeepSeek-V3） |
| 认证 | JWT（python-jose + passlib） |
| 部署 | Docker Compose（MySQL + Backend + Frontend） |

---

## 数据库

### MySQL 表结构

系统共 8 张核心表：

| 表名 | 说明 | 主要外键 |
|------|------|----------|
| `users` | 用户表 | - |
| `clues` | 线索表 | - |
| `topics` | 选题表 | editor_id → users |
| `articles` | 文章表 | author_id → users, topic_id → topics, clue_id → clues |
| `reviews` | 审核记录表 | article_id → articles, reviewer_id → users |
| `feedbacks` | 反馈统计表 | article_id → articles |
| `messages` | 站内消息表 | - |
| `collections` | 采集任务表 | - |

### 切换 SQLite ↔ MySQL

编辑 `backend/.env` 中的 `DATABASE_URL`：

```bash
# SQLite（本地快速开发，无需数据库服务）
DATABASE_URL=sqlite:///./data/news_editor.db

# MySQL（Docker Compose 或本地 MySQL）
DATABASE_URL=mysql+pymysql://news_editor:apppass123@localhost:3306/news_editor?charset=utf8mb4
```

Docker Compose 环境下由 `docker-compose.yml` 自动注入 MySQL 连接串，无需手动配置。

### 详细文档

- [MySQL 迁移架构设计](docs/MySQL_Migration_Architecture.md) — 表结构、索引、迁移方案、性能优化
- [MySQL 接入操作指南](docs/MySQL_接入操作提示词.md) — 从零开始的 MySQL 接入步骤

---

## 环境变量

### 根目录 .env（Docker Compose 使用）

```bash
# MySQL 配置
MYSQL_ROOT_PASSWORD=rootpass123
MYSQL_DATABASE=news_editor
MYSQL_USER=news_editor
MYSQL_PASSWORD=apppass123
MYSQL_PORT=3306

# 后端配置
DEBUG=true
ENVIRONMENT=development
SECRET_KEY=your-secret-key

# AI API
SILICONFLOW_API_KEY=your-api-key
AI_MODEL=deepseek-ai/DeepSeek-V3

# 端口
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

### 后端 .env（本地开发使用）

```bash
DATABASE_URL=mysql+pymysql://news_editor:apppass123@localhost:3306/news_editor?charset=utf8mb4
SECRET_KEY=your-secret-key
SILICONFLOW_API_KEY=your-api-key
AI_MODEL=deepseek-ai/DeepSeek-V3
```

---

## API 文档

启动后端后访问：

- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

主要接口前缀：

| 模块 | 前缀 |
|------|------|
| 认证 | `POST /api/auth/login`, `POST /api/auth/register` |
| 线索 | `GET/POST /api/clues` |
| 选题 | `GET/POST /api/topics` |
| 稿件 | `GET/POST /api/articles` |
| 内容生成 | `POST /api/content/generate` |
| 审核 | `GET/POST /api/reviews` |
| 反馈 | `GET/POST /api/feedback` |
| 消息 | `GET /api/messages` |
| 采集 | `GET/POST /api/collections` |
| 统计 | `GET /api/stats` |
| 读者端 | `GET /api/public/articles` |
| 健康检查 | `GET /health` |

---

## M1/M2 Mac 注意事项

- `docker-compose.yml` 已设置 `platform: linux/arm64/v8`，兼容 Apple Silicon
- PyMySQL 是纯 Python 驱动，无需编译 C 扩展
- MySQL 8.0 官方镜像已原生支持 ARM64
- 如遇镜像拉取慢，可配置 Docker 镜像加速器

---

## 常见问题

### Q: MySQL 连接失败？
```bash
# 检查 MySQL 是否启动
docker compose ps

# 检查 MySQL 日志
docker compose logs mysql

# 手动测试连接
docker compose exec mysql mysql -u news_editor -papppass123 -e "SELECT 1" news_editor
```

### Q: 表不存在？
```bash
# 手动执行初始化脚本
docker compose exec -T mysql mysql -u root -prootpass123 < backend/init.sql
```

### Q: 如何重置数据库？
```bash
# 停止服务并删除数据卷
docker compose down -v
# 重新启动
docker compose up -d
```

### Q: 如何切换回 SQLite？
编辑 `backend/.env`，将 DATABASE_URL 改为：
```
DATABASE_URL=sqlite:///./data/news_editor.db
```
重启后端即可。
