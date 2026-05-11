# 新闻内容采编系统 - MySQL 数据库迁移架构设计

> 最后更新: 2026-05-10（实施完成：2026-05-11）
> 基于实际代码模型校验
> 所有步骤已在 M1 Mac (macOS 26.2) 上验证通过

## 一、迁移背景与目标

### 1.1 当前状态
- **数据库类型**: SQLite（单文件数据库）
- **存储位置**: `backend/data/news_editor.db`
- **ORM**: SQLAlchemy 2.0.35 + declarative_base
- **优势**: 零配置、部署简单、适合开发
- **局限**: 不支持并发写入、无用户权限管理、数据量过万后性能下降

### 1.2 迁移目标
- **目标数据库**: MySQL 8.0+
- **驱动**: PyMySQL (pure Python, 无需编译)
- **优势**: 支持高并发、完善的权限系统、成熟的运维生态
- **兼容性**: 保持现有 SQLAlchemy ORM 代码不变，仅通过 `DATABASE_URL` 配置切换

---

## 二、现有数据模型分析（基于实际代码校验）

### 2.1 核心实体关系图

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Users     │────<│  Articles   │────<│  Reviews    │
│  (users)    │     │ (articles)  │     │ (reviews)   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │
       │                   ├─── topic_id ──>┌─────────────┐
       │                   │                │   Topics    │
       │                   │                │  (topics)   │
       │                   ├─── clue_id ──> │             │
       │                   │                └─────────────┘
       │                   ▼
       │             ┌─────────────┐     ┌─────────────┐
       │             │  Feedbacks  │     │ Collections │
       │             │(feedbacks)  │     │(collections)│
       │             └─────────────┘     └─────────────┘
       │                                       │
       ▼                                       ▼
┌─────────────┐                         ┌─────────────┐
│  Messages   │                         │    Clues    │
│ (messages)  │                         │  (clues)    │
└─────────────┘                         └─────────────┘
```

### 2.2 各表字段详细分析

> 以下字段信息均与 `backend/app/models/*.py` 源码对齐

#### 2.2.1 用户表 (users)
源码: `app/models/user.py` → `class User(Base)`

| 字段名 | SQLAlchemy 类型 | MySQL 类型 | 约束 | 说明 |
|--------|----------------|-----------|------|------|
| id | Integer | INT | PK, AUTO_INCREMENT | 主键 |
| username | String(50) | VARCHAR(50) | UNIQUE, NOT NULL, INDEX | 用户名 |
| email | String(100) | VARCHAR(100) | UNIQUE, NOT NULL | 邮箱 |
| password_hash | String(255) | VARCHAR(255) | NOT NULL | 密码哈希 (SHA256) |
| nickname | String(50) | VARCHAR(50) | DEFAULT '' | 昵称 |
| full_name | String(100) | VARCHAR(100) | DEFAULT '' | 全名 |
| role | String(20) | VARCHAR(20) | DEFAULT 'reporter' | 角色 |
| is_active | Boolean | TINYINT(1) | DEFAULT 1 | 是否激活 |
| avatar | String(500) | VARCHAR(500) | DEFAULT '' | 头像URL |
| created_at | DateTime | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DateTime | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**索引设计**:
```sql
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
```

**角色枚举** (UserRole in `__init__.py`): admin, chief_editor, reviewer, editor, reporter

**关系**:
- `articles` → 一对多 Article (back_populates="author", foreign_keys="Article.author_id")

---

#### 2.2.2 文章表 (articles)
源码: `app/models/article.py` → `class Article(Base)`

| 字段名 | SQLAlchemy 类型 | MySQL 类型 | 约束 | 说明 |
|--------|----------------|-----------|------|------|
| id | Integer | INT | PK, AUTO_INCREMENT | 主键 |
| title | String(300) | VARCHAR(300) | NOT NULL | 标题 |
| content | Text | TEXT | DEFAULT '' | 正文内容 |
| summary | Text | TEXT | DEFAULT '' | 摘要 |
| status | String(30) | VARCHAR(30) | DEFAULT 'draft', INDEX | 状态 |
| cover_image | String(500) | VARCHAR(500) | DEFAULT '' | 封面图URL |
| tags | String(500) | VARCHAR(500) | DEFAULT '' | 标签（逗号分隔） |
| category | String(50) | VARCHAR(50) | DEFAULT '' | 分类 |
| view_count | Integer | INT | DEFAULT 0 | 阅读量 |
| like_count | Integer | INT | DEFAULT 0 | 点赞数 |
| quality_score | Float | FLOAT | DEFAULT 0.0 | 质量分 |
| ai_score | Float | FLOAT | DEFAULT 0.0 | AI评分 |
| author_id | Integer | INT | FK → users.id, NULLABLE | 作者ID |
| topic_id | Integer | INT | FK → topics.id, NULLABLE | 选题ID |
| clue_id | Integer | INT | FK → clues.id, NULLABLE | 线索ID |
| created_at | DateTime | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DateTime | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |
| published_at | DateTime | DATETIME | NULLABLE | 发布时间 |

**索引设计**:
```sql
CREATE INDEX idx_articles_author ON articles(author_id);
CREATE INDEX idx_articles_status ON articles(status);
CREATE INDEX idx_articles_category ON articles(category);
CREATE INDEX idx_articles_created ON articles(created_at DESC);
CREATE INDEX idx_articles_topic ON articles(topic_id);
CREATE INDEX idx_articles_clue ON articles(clue_id);
```

**状态枚举** (ArticleStatus): draft, pending_review, reviewing, approved, rejected, published, archived

**关系**:
- `author` → 多对一 User (back_populates="articles")
- `reviews` → 一对多 Review (cascade="all, delete-orphan")
- `feedback` → 一对一 Feedback (uselist=False, cascade="all, delete-orphan")

---

#### 2.2.3 线索表 (clues)
源码: `app/models/clue.py` → `class Clue(Base)`

| 字段名 | SQLAlchemy 类型 | MySQL 类型 | 约束 | 说明 |
|--------|----------------|-----------|------|------|
| id | Integer | INT | PK, AUTO_INCREMENT | 主键 |
| title | String(300) | VARCHAR(300) | NOT NULL | 标题 |
| content | Text | TEXT | DEFAULT '' | 内容 |
| source | String(200) | VARCHAR(200) | DEFAULT '' | 来源 |
| source_url | String(500) | VARCHAR(500) | DEFAULT '' | 原文链接 |
| keywords | String(500) | VARCHAR(500) | DEFAULT '' | 关键词 |
| status | String(30) | VARCHAR(30) | DEFAULT 'pending', INDEX | 状态 |
| news_value_score | Float | FLOAT | DEFAULT 0.0 | 新闻价值分 |
| propagation_potential | Float | FLOAT | DEFAULT 0.0 | 传播潜力分 |
| collected_by | String(50) | VARCHAR(50) | DEFAULT 'system' | 采集来源 |
| category | String(50) | VARCHAR(50) | DEFAULT '' | 分类 |
| channel | String(50) | VARCHAR(50) | DEFAULT '' | 频道 |
| created_at | DateTime | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DateTime | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |
| processed_at | DateTime | DATETIME | NULLABLE | 处理时间 |

**索引设计**:
```sql
CREATE INDEX idx_clues_status ON clues(status);
CREATE INDEX idx_clues_category ON clues(category);
CREATE INDEX idx_clues_created ON clues(created_at DESC);
CREATE INDEX idx_clues_source ON clues(source);
```

**状态枚举**: pending, processing, verified, converted, discarded

**兼容别名**: `NewsClue = Clue`

---

#### 2.2.4 选题表 (topics)
源码: `app/models/topic.py` → `class Topic(Base)`

| 字段名 | SQLAlchemy 类型 | MySQL 类型 | 约束 | 说明 |
|--------|----------------|-----------|------|------|
| id | Integer | INT | PK, AUTO_INCREMENT | 主键 |
| title | String(300) | VARCHAR(300) | DEFAULT '' | 标题 |
| description | Text | TEXT | DEFAULT '' | 描述 |
| category | String(50) | VARCHAR(50) | DEFAULT '' | 分类 |
| status | String(30) | VARCHAR(30) | DEFAULT 'draft', INDEX | 状态 |
| editor | String(50) | VARCHAR(50) | DEFAULT '' | 指派编辑名 |
| editor_id | Integer | INT | FK → users.id, NULLABLE | 指派编辑ID |
| ref_clue_ids | String(500) | VARCHAR(500) | DEFAULT '' | 关联线索IDs（逗号分隔） |
| planned_date | DateTime | DATETIME | NULLABLE | 计划日期 |
| created_at | DateTime | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DateTime | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**索引设计**:
```sql
CREATE INDEX idx_topics_status ON topics(status);
CREATE INDEX idx_topics_editor ON topics(editor_id);
```

**状态枚举**: draft, active, completed, cancelled

---

#### 2.2.5 审核记录表 (reviews)
源码: `app/models/review.py` → `class Review(Base)`

| 字段名 | SQLAlchemy 类型 | MySQL 类型 | 约束 | 说明 |
|--------|----------------|-----------|------|------|
| id | Integer | INT | PK, AUTO_INCREMENT | 主键 |
| article_id | Integer | INT | FK → articles.id, NOT NULL, INDEX | 文章ID |
| reviewer | String(50) | VARCHAR(50) | DEFAULT '' | 审核人名称 |
| reviewer_id | Integer | INT | FK → users.id, NULLABLE | 审核人ID |
| level | String(20) | VARCHAR(20) | DEFAULT 'first' | 审核级别 |
| result | String(30) | VARCHAR(30) | DEFAULT 'pending' | 审核结果 |
| status | String(30) | VARCHAR(30) | DEFAULT 'pending' | 状态 |
| comment | Text | TEXT | DEFAULT '' | 审核意见 |
| score | Integer | INT | DEFAULT 0 | 评分 |
| created_at | DateTime | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DateTime | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**索引设计**:
```sql
CREATE INDEX idx_reviews_article ON reviews(article_id);
CREATE INDEX idx_reviews_reviewer ON reviews(reviewer_id);
CREATE INDEX idx_reviews_status ON reviews(status);
```

**审核级别**: first, second, final
**审核结果**: pending, approved, rejected, revision

**关系**:
- `article` → 多对一 Article (back_populates="reviews")

---

#### 2.2.6 反馈统计表 (feedbacks)
源码: `app/models/feedback.py` → `class Feedback(Base)`

| 字段名 | SQLAlchemy 类型 | MySQL 类型 | 约束 | 说明 |
|--------|----------------|-----------|------|------|
| id | Integer | INT | PK, AUTO_INCREMENT | 主键 |
| article_id | Integer | INT | FK → articles.id, UNIQUE, INDEX | 文章ID (一对一) |
| view_count | Integer | INT | DEFAULT 0 | 阅读量 |
| like_count | Integer | INT | DEFAULT 0 | 点赞数 |
| comment_count | Integer | INT | DEFAULT 0 | 评论数 |
| share_count | Integer | INT | DEFAULT 0 | 分享数 |
| engagement_rate | Float | FLOAT | DEFAULT 0.0 | 互动率 |
| trending_score | Float | FLOAT | DEFAULT 0.0 | 热度分 |
| created_at | DateTime | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DateTime | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**关系**:
- `article` → 多对一 Article (back_populates="feedback")

---

#### 2.2.7 站内消息表 (messages)
源码: `app/models/message.py` → `class Message(Base)`

| 字段名 | SQLAlchemy 类型 | MySQL 类型 | 约束 | 说明 |
|--------|----------------|-----------|------|------|
| id | Integer | INT | PK, AUTO_INCREMENT | 主键 |
| content | Text | TEXT | DEFAULT '' | 消息内容 |
| sender | String(50) | VARCHAR(50) | DEFAULT 'system' | 发送者 |
| type | String(30) | VARCHAR(30) | DEFAULT 'system', INDEX | 消息类型 |
| is_read | Boolean | TINYINT(1) | DEFAULT 0, INDEX | 是否已读 |
| related_id | Integer | INT | NULLABLE | 关联ID |
| related_type | String(50) | VARCHAR(50) | DEFAULT '' | 关联类型 |
| created_at | DateTime | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| read_at | DateTime | DATETIME | NULLABLE | 阅读时间 |

**消息类型**: system, notification, reply

---

#### 2.2.8 采集任务表 (collections)
源码: `app/models/collection.py` → `class Collection(Base)`

| 字段名 | SQLAlchemy 类型 | MySQL 类型 | 约束 | 说明 |
|--------|----------------|-----------|------|------|
| id | Integer | INT | PK, AUTO_INCREMENT | 主键 |
| name | String(100) | VARCHAR(100) | DEFAULT '' | 任务名称 |
| keywords | String(500) | VARCHAR(500) | DEFAULT '' | 关键词 |
| channels | String(200) | VARCHAR(200) | DEFAULT 'news' | 采集渠道 |
| status | String(30) | VARCHAR(30) | DEFAULT 'pending', INDEX | 状态 |
| result_count | Integer | INT | DEFAULT 0 | 结果数量 |
| error_msg | Text | TEXT | DEFAULT '' | 错误信息 |
| created_at | DateTime | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DateTime | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**采集状态**: pending, running, completed, failed

---

## 三、完整建表 SQL（可直接执行）

```sql
-- ============================================================
-- 新闻内容采编系统 MySQL 完整建表脚本
-- 适用于 MySQL 8.0+
-- ============================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS news_editor
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE news_editor;

-- 1. 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(50) DEFAULT '',
    full_name VARCHAR(100) DEFAULT '',
    role VARCHAR(20) DEFAULT 'reporter',
    is_active TINYINT(1) DEFAULT 1,
    avatar VARCHAR(500) DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_username (username),
    INDEX idx_users_email (email),
    INDEX idx_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 线索表 (无外键依赖，先创建)
CREATE TABLE IF NOT EXISTS clues (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    content TEXT,
    source VARCHAR(200) DEFAULT '',
    source_url VARCHAR(500) DEFAULT '',
    keywords VARCHAR(500) DEFAULT '',
    status VARCHAR(30) DEFAULT 'pending',
    news_value_score FLOAT DEFAULT 0.0,
    propagation_potential FLOAT DEFAULT 0.0,
    collected_by VARCHAR(50) DEFAULT 'system',
    category VARCHAR(50) DEFAULT '',
    channel VARCHAR(50) DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    processed_at DATETIME NULL,
    INDEX idx_clues_status (status),
    INDEX idx_clues_category (category),
    INDEX idx_clues_created (created_at DESC),
    INDEX idx_clues_source (source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 选题表
CREATE TABLE IF NOT EXISTS topics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(300) DEFAULT '',
    description TEXT,
    category VARCHAR(50) DEFAULT '',
    status VARCHAR(30) DEFAULT 'draft',
    editor VARCHAR(50) DEFAULT '',
    editor_id INT NULL,
    ref_clue_ids VARCHAR(500) DEFAULT '',
    planned_date DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_topics_status (status),
    INDEX idx_topics_editor (editor_id),
    CONSTRAINT fk_topics_editor FOREIGN KEY (editor_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 文章表
CREATE TABLE IF NOT EXISTS articles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    content TEXT,
    summary TEXT,
    status VARCHAR(30) DEFAULT 'draft',
    cover_image VARCHAR(500) DEFAULT '',
    tags VARCHAR(500) DEFAULT '',
    category VARCHAR(50) DEFAULT '',
    view_count INT DEFAULT 0,
    like_count INT DEFAULT 0,
    quality_score FLOAT DEFAULT 0.0,
    ai_score FLOAT DEFAULT 0.0,
    author_id INT NULL,
    topic_id INT NULL,
    clue_id INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    published_at DATETIME NULL,
    INDEX idx_articles_author (author_id),
    INDEX idx_articles_status (status),
    INDEX idx_articles_category (category),
    INDEX idx_articles_created (created_at DESC),
    INDEX idx_articles_topic (topic_id),
    INDEX idx_articles_clue (clue_id),
    -- 复合索引：列表页常用查询
    INDEX idx_articles_status_created (status, created_at DESC),
    CONSTRAINT fk_articles_author FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_articles_topic FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL,
    CONSTRAINT fk_articles_clue FOREIGN KEY (clue_id) REFERENCES clues(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 审核记录表
CREATE TABLE IF NOT EXISTS reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    article_id INT NOT NULL,
    reviewer VARCHAR(50) DEFAULT '',
    reviewer_id INT NULL,
    level VARCHAR(20) DEFAULT 'first',
    result VARCHAR(30) DEFAULT 'pending',
    status VARCHAR(30) DEFAULT 'pending',
    comment TEXT,
    score INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_reviews_article (article_id),
    INDEX idx_reviews_reviewer (reviewer_id),
    INDEX idx_reviews_status (status),
    INDEX idx_reviews_article_status (article_id, status),
    CONSTRAINT fk_reviews_article FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    CONSTRAINT fk_reviews_reviewer FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. 反馈统计表
CREATE TABLE IF NOT EXISTS feedbacks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    article_id INT NOT NULL UNIQUE,
    view_count INT DEFAULT 0,
    like_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    share_count INT DEFAULT 0,
    engagement_rate FLOAT DEFAULT 0.0,
    trending_score FLOAT DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_feedbacks_article (article_id),
    CONSTRAINT fk_feedbacks_article FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. 站内消息表
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    content TEXT,
    sender VARCHAR(50) DEFAULT 'system',
    type VARCHAR(30) DEFAULT 'system',
    is_read TINYINT(1) DEFAULT 0,
    related_id INT NULL,
    related_type VARCHAR(50) DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME NULL,
    INDEX idx_messages_type (type),
    INDEX idx_messages_read (is_read),
    INDEX idx_messages_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. 采集任务表
CREATE TABLE IF NOT EXISTS collections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) DEFAULT '',
    keywords VARCHAR(500) DEFAULT '',
    channels VARCHAR(200) DEFAULT 'news',
    status VARCHAR(30) DEFAULT 'pending',
    result_count INT DEFAULT 0,
    error_msg TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_collections_status (status),
    INDEX idx_collections_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 四、双数据库切换机制

### 4.1 修改 database.py 支持连接池

当前 `backend/app/database.py` 只有基础连接，迁移 MySQL 需要增强：

```python
"""数据库连接 - 支持 SQLite / MySQL 双模式"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import get_settings
from app.models.base import Base

settings = get_settings()

def _build_engine():
    """根据 DATABASE_URL 自动选择引擎配置"""
    url = settings.DATABASE_URL

    if url.startswith("sqlite"):
        # SQLite 模式
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
    else:
        # MySQL 模式（带连接池）
        return create_engine(
            url,
            pool_size=10,           # 常驻连接数
            max_overflow=20,        # 峰值溢出连接
            pool_pre_ping=True,     # 连接前 ping 检测（防断连）
            pool_recycle=3600,      # 1 小时回收空闲连接
            echo=False,
        )

engine = _build_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI 依赖：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """创建所有表（首次启动或迁移时调用）"""
    Base.metadata.create_all(bind=engine)
```

### 4.2 .env 配置切换

```bash
# === 开发环境 (SQLite，当前默认) ===
DATABASE_URL=sqlite:///./data/news_editor.db

# === 生产环境 (MySQL) ===
# DATABASE_URL=mysql+pymysql://news_editor:YOUR_PASSWORD@localhost:3306/news_editor?charset=utf8mb4
```

只需注释/取消注释一行即可切换，ORM 代码零改动。

### 4.3 config.py 无需修改

当前 `app/core/config.py` 已经通过 `pydantic-settings` 从 `.env` 读取 `DATABASE_URL`，天然支持切换。

---

## 五、MySQL 安装与初始化

### 5.1 macOS 安装（M1 Mac 推荐 Docker 方案）

```bash
# --- 方案 A：Docker（推荐，环境隔离，M1 兼容）---
# M1 Mac 需要指定 platform: linux/arm64/v8
docker run -d \
  --name news_editor_mysql \
  --platform linux/arm64/v8 \
  -e MYSQL_ROOT_PASSWORD=rootpass123 \
  -e MYSQL_DATABASE=news_editor \
  -e MYSQL_USER=news_editor \
  -e MYSQL_PASSWORD=apppass123 \
  -p 3306:3306 \
  -v news_mysql_data:/var/lib/mysql \
  mysql:8.0 \
  --character-set-server=utf8mb4 \
  --collation-server=utf8mb4_unicode_ci \
  --default-authentication-plugin=mysql_native_password

# 或使用一键脚本
./docker.sh start

# --- 方案 B：Homebrew（不推荐 M1，兼容性差）---
# brew install mysql@8.0
# brew services start mysql@8.0
```

### 5.2 初始化脚本 (backend/init.sql)

项目根目录 `backend/init.sql` 已包含完整的初始化 SQL，Docker 容器首次启动时自动执行：

```sql
-- backend/init.sql
CREATE DATABASE IF NOT EXISTS news_editor
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE news_editor;

-- 创建管理员用户 (密码: admin123)
INSERT INTO users (username, email, password_hash, nickname, role, is_active)
VALUES ('admin', 'admin@example.com',
  SHA2('admin123', 256),
  '系统管理员', 'admin', 1)
ON DUPLICATE KEY UPDATE role='admin';

-- 8 张表建表语句（见第三章）
-- ...
```

### 5.3 验证 MySQL 连接

```bash
# 1. 验证容器健康
docker ps | grep news_editor_mysql

# 2. 验证数据库和表
docker exec -it news_editor_mysql mysql -u news_editor -papppass123 \
  -e "SHOW TABLES;" news_editor

# 3. Python 连接测试
cd backend
python3 -c "
from sqlalchemy import create_engine, text
engine = create_engine('mysql+pymysql://news_editor:apppass123@localhost:3306/news_editor?charset=utf8mb4')
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM users'))
    print(f'Users: {result.scalar()}')
    result = conn.execute(text('SHOW TABLES'))
    for row in result:
        print(f'  Table: {row[0]}')
"
```

---

## 六、数据迁移方案

### 6.1 方案选择

| 方案 | 适用场景 | 复杂度 | 推荐度 |
|------|---------|--------|--------|
| SQLAlchemy create_all | 全新部署，无历史数据 | ★☆☆ | ✅ 开发阶段推荐 |
| Alembic 自动迁移 | 持续迭代，需要版本管理 | ★★☆ | ✅ 生产推荐 |
| 手动 SQL + 数据导入 | SQLite 存量数据迁入 MySQL | ★★★ | 仅存量迁移 |

### 6.2 方案一：SQLAlchemy 自动建表（开发环境快速启动）

```bash
# 1. 修改 .env 为 MySQL 连接串
# DATABASE_URL=mysql+pymysql://news_editor:apppass123@localhost:3306/news_editor?charset=utf8mb4

# 2. 启动后端，自动建表
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

SQLAlchemy 的 `Base.metadata.create_all(bind=engine)` 会在首次启动时自动创建所有表。

### 6.3 方案二：Alembic 版本化迁移（生产推荐）

```bash
cd backend

# 1. 初始化 Alembic
alembic init alembic

# 2. 编辑 alembic/env.py，在 target_metadata 赋值
#    from app.models import Base
#    target_metadata = Base.metadata
#
#    # 动态读取 DATABASE_URL
#    from app.core.config import get_settings
#    config = alembic.context.config
#    config.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL)

# 3. 生成初始迁移脚本
alembic revision --autogenerate -m "init: create all tables"

# 4. 执行迁移
alembic upgrade head

# 后续修改模型后：
alembic revision --autogenerate -m "add field xxx"
alembic upgrade head

# 回滚一步
alembic downgrade -1
```

### 6.4 方案三：SQLite 存量数据迁入 MySQL

```python
#!/usr/bin/env python3
"""
backend/scripts/migrate_sqlite_to_mysql.py
将 SQLite 数据完整迁移到 MySQL
"""
import sqlite3
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session

# ---- 配置 ----
SQLITE_PATH = "data/news_editor.db"
MYSQL_URL = "mysql+pymysql://news_editor:apppass123@localhost:3306/news_editor?charset=utf8mb4"

# 迁移顺序（遵循外键依赖）
TABLE_ORDER = [
    "users",
    "clues",
    "topics",
    "articles",
    "reviews",
    "feedbacks",
    "messages",
    "collections",
]


def migrate():
    # 1. 连接
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    mysql_engine = create_engine(MYSQL_URL, pool_pre_ping=True)

    # 2. 先建表（如果不存在）
    from app.models.base import Base
    Base.metadata.create_all(bind=mysql_engine)

    # 3. 逐表迁移
    with Session(mysql_engine) as session:
        for table_name in TABLE_ORDER:
            print(f"\n--- 迁移表: {table_name} ---")

            # 读取 SQLite 数据
            cursor = sqlite_conn.execute(f"SELECT * FROM {table_name}")
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            if not rows:
                print(f"  [跳过] {table_name} 无数据")
                continue

            # 构建 INSERT 语句
            placeholders = ", ".join([f":{col}" for col in columns])
            col_names = ", ".join(columns)
            insert_sql = text(f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})")

            # 批量插入
            batch_size = 500
            total = 0
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                records = []
                for row in batch:
                    record = {}
                    for col in columns:
                        val = row[col]
                        # SQLite 空字符串 vs MySQL NULL 处理
                        if val == "" and col.endswith("_id"):
                            val = None
                        record[col] = val
                    records.append(record)

                session.execute(insert_sql, records)
                total += len(records)

            session.commit()
            print(f"  [完成] {table_name}: {total} 行")

    sqlite_conn.close()
    print("\n✅ 迁移完成!")


if __name__ == "__main__":
    migrate()
```

使用方式：
```bash
cd backend
# 先确保 MySQL 已启动且表已建好
python scripts/migrate_sqlite_to_mysql.py
```

---

## 七、Docker Compose 一键部署（已验证）

项目根目录已包含以下文件：
- `docker-compose.yml` — 三服务编排（MySQL + Backend + Frontend）
- `docker.sh` — Docker 便捷操作脚本（start/stop/restart/logs/clean）
- `start.sh` — 一键启动脚本（自动检测 MySQL/后端/前端）
- `backend/Dockerfile` — 后端容器镜像
- `backend/init.sql` — MySQL 首次启动初始化

### 7.1 docker-compose.yml（M1 Mac 兼容）

```yaml
# docker-compose.yml — 项目根目录
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    platform: linux/arm64/v8     # M1 Mac 必须指定
    container_name: news_editor_mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: rootpass123
      MYSQL_DATABASE: news_editor
      MYSQL_USER: news_editor
      MYSQL_PASSWORD: apppass123
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./backend/init.sql:/docker-entrypoint-initdb.d/01-init.sql
    command: >
      --character-set-server=utf8mb4
      --collation-server=utf8mb4_unicode_ci
      --default-authentication-plugin=mysql_native_password
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-prootpass123"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: news_editor_backend
    restart: unless-stopped
    depends_on:
      mysql:
        condition: service_healthy
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: mysql+pymysql://news_editor:apppass123@mysql:3306/news_editor?charset=utf8mb4
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: news_editor_frontend
    restart: unless-stopped
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  mysql_data:
```

### 7.2 docker.sh 便捷脚本

```bash
#!/bin/bash
# docker.sh — Docker 便捷操作

case "${1:-status}" in
  start)
    docker compose up -d mysql
    echo "等待 MySQL healthy..."
    until docker compose exec mysql mysqladmin ping -h localhost -u root -prootpass123 --silent 2>/dev/null; do
      sleep 2
    done
    echo "MySQL 已就绪!"
    docker compose up -d backend frontend
    ;;
  stop)
    docker compose down
    ;;
  restart)
    docker compose restart backend frontend
    ;;
  logs)
    docker compose logs -f --tail=50 ${2:-}
    ;;
  clean)
    docker compose down -v
    echo "数据卷已清除"
    ;;
  status)
    docker compose ps
    ;;
  *)
    echo "用法: ./docker.sh {start|stop|restart|logs|clean|status}"
    ;;
esac
```

### 7.3 start.sh 一键启动

```bash
#!/bin/bash
# start.sh — 一键启动脚本（自动启动 MySQL + Backend + Frontend）

set -e

# 1. 启动 MySQL（如未运行）
if ! docker ps --format '{{.Names}}' | grep -q '^news_editor_mysql$'; then
  echo "[1/3] 启动 MySQL..."
  docker compose up -d mysql
fi

# 2. 启动后端
echo "[2/3] 启动后端 (port 8000)..."
cd backend
source venv/bin/activate 2>/dev/null || true
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# 3. 启动前端
echo "[3/3] 启动前端 (port 3000)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ 系统启动完成!"
echo "   后端: http://localhost:8000"
echo "   前端: http://localhost:3000"
echo "   MySQL: localhost:3306 (news_editor / apppass123)"
echo ""
echo "Ctrl+C 停止服务"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
```

### 7.4 Python 依赖 (backend/requirements.txt)

```
# MySQL 驱动（M1 Mac 推荐）
pymysql>=1.1.0
cryptography>=41.0.0   # pymysql 密码认证必需

# 可选：数据库迁移
# alembic>=1.14.0
```

> **注意**：`cryptography` 是 PyMySQL 的密码认证依赖，M1 Mac 上推荐 41.0+ 版本以避免编译问题。

---

## 八、性能优化

### 8.1 连接池参数调优

| 参数 | 开发环境 | 生产环境 | 说明 |
|------|---------|---------|------|
| pool_size | 5 | 10-20 | 常驻连接数 |
| max_overflow | 10 | 20-50 | 峰值溢出 |
| pool_recycle | 3600 | 1800 | 回收周期(秒) |
| pool_pre_ping | True | True | 断连检测 |

### 8.2 查询优化

```sql
-- 慢查询日志（在 MySQL 配置 my.cnf 中启用）
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 1

-- 常见优化
-- 1. 文章列表页：覆盖索引
CREATE INDEX idx_articles_list ON articles(status, created_at DESC, id, title, category);

-- 2. 审核查询：复合索引
CREATE INDEX idx_reviews_pending ON reviews(status, created_at);

-- 3. 游标分页代替 OFFSET（大数据量时）
-- 慢: SELECT * FROM articles ORDER BY id LIMIT 20 OFFSET 10000;
-- 快: SELECT * FROM articles WHERE id > :last_seen_id ORDER BY id LIMIT 20;
```

### 8.3 后续可选：Redis 缓存层

```python
# 热点数据缓存
# - 用户 session (JWT 校验)
# - 文章列表页 (前 N 页)
# - 选题/线索看板统计
# - 公开文章详情 (已发布的)
```

---

## 九、备份策略

### 9.1 自动备份脚本

```bash
#!/bin/bash
# scripts/backup_mysql.sh
# 用法: crontab -e → 0 3 * * * /path/to/backup_mysql.sh

BACKUP_DIR="/data/backups/mysql"
DATE=$(date +%Y%m%d_%H%M%S)
KEEP_DAYS=30

mkdir -p "$BACKUP_DIR"

# 全量备份
mysqldump -u news_editor -p'apppass123' \
  --single-transaction \
  --routines \
  --triggers \
  news_editor | gzip > "$BACKUP_DIR/news_editor_${DATE}.sql.gz"

# 清理旧备份
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +${KEEP_DAYS} -delete

echo "[$(date)] Backup completed: news_editor_${DATE}.sql.gz"
```

### 9.2 恢复

```bash
# 恢复全量备份
gunzip < /data/backups/mysql/news_editor_20260510_030000.sql.gz | \
  mysql -u news_editor -p'apppass123' news_editor
```

---

## 十、回滚方案

### 10.1 快速回滚

```bash
# 1. 停止后端
# 2. 修改 .env 切回 SQLite
DATABASE_URL=sqlite:///./data/news_editor.db
# 3. 重启后端
```

SQLite 数据库文件从未删除，回滚零风险。

### 10.2 MySQL → SQLite 反向迁移（如需要）

```python
# 类似正向迁移，读 MySQL 写 SQLite
# 注意: SQLite 没有 DATETIME DEFAULT CURRENT_TIMESTAMP 语法差异
```

---

## 十一、迁移检查清单

### 迁移前
- [x] 备份现有 SQLite: `cp backend/data/news_editor.db backend/data/news_editor_backup.db`
- [x] MySQL 服务已启动，可连接（Docker 容器 `news_editor_mysql`）
- [x] PyMySQL + cryptography 已安装
- [x] .env 已配置 MySQL DATABASE_URL
- [x] 读完本文档，理解回滚方案

### 迁移中
- [x] 建表成功: `SHOW TABLES;` 显示 8 张表
- [x] 外键约束: `SHOW CREATE TABLE articles;` 确认 FK 正确
- [x] 字符集: `SHOW CREATE DATABASE news_editor;` 确认 utf8mb4
- [x] 种子数据已插入（admin 用户 + 示例数据）

### 迁移后
- [x] 后端启动无报错（uvicorn port 8000）
- [x] 注册/登录功能正常
- [x] 创建文章 → 审核 → 发布流程正常
- [x] 线索采集任务正常运行（90% 源可用率）
- [x] 数据统计页面显示正常（/api/stats/dashboard, /api/feedback/stats）
- [x] 前端代理正确指向 localhost:8000

---

## 十二、线索采集存储设计

### 12.1 线索表 (clues) 存储策略

线索表是系统中写入最频繁的表。每次多渠道采集都会批量写入。

```sql
-- 线索去重：按 title+source 唯一性（应用层）
-- 不在数据库层用 UNIQUE 约束，因为 title 可能部分相同
-- 而是在 collect_multichannel() 入库前先查询：
SELECT id FROM clues WHERE title = :title AND source = :source LIMIT 1;

-- 如果存在 → 跳过插入
-- 如果不存在 → INSERT
```

**写入流程**：
```
多源采集 → 关键词过滤 → 相关性排序 → 去重(title+source) → INSERT → 返回
                                              ↓
                                      已有条目 → 跳过
```

### 12.2 采集统计表 (collections)

每次 `collect_multichannel` 调用都会记录一次采集任务：

```sql
INSERT INTO collections (name, keywords, channels, status, result_count)
VALUES ('手动采集', '人工智能', 'ithome,36kr', 'completed', 12);
```

### 12.3 采集频率控制

```python
# 限速策略（在 clues.py 中实现）
# 1. 同源请求间隔：0.3~3.0 秒随机延迟
# 2. 源间请求间隔：1.0~3.0 秒
# 3. 所有请求超时：8 秒
# 4. 单次采集最大结果：200 条（5 个源 × 40 条/源）
```

### 12.4 当前已配置的采集源

| 分类 | 源 | 状态 | 说明 |
|------|-----|------|------|
| RSS | ithome (IT之家) | ✅ | RSS XML, 关键词过滤 + 回退 |
| RSS | 36kr (36氪) | ✅ | RSS XML, 关键词过滤 + 回退 |
| RSS | sspai (少数派) | ✅ | RSS XML, 已修复二次过滤 bug |
| RSS | oschina (开源中国) | ✅ | RSS XML |
| RSS | solidot (奇客) | ✅ | RSS XML |
| API | zhihu_daily (知乎日报) | ✅ | JSON API, 不过滤关键词 |
| API | baidu_hot (百度热搜) | ✅ | JSON API, 不过滤关键词 |
| API | toutiao_hot (今日头条热门) | ✅ | JSON API, 不过滤关键词 |
| API | bilibili_hot (B站热门) | ✅ | JSON API, 不过滤关键词 |
| 搜索 | sogou_news (搜狗新闻) | ⚠️ | HTML 抓取, 关键词严格过滤 |

### 12.5 线索生命周期

```
采集(news) → 待处理(pending) → 验证(verified) → 转化为选题/文章(converted)
     ↓              ↓               ↓
   丢弃(discarded) ← 审核不通过 ← 处理中(processing)
```

### 12.6 性能考量

| 指标 | 当前值 | 建议 |
|------|--------|------|
| 单次采集超时 | ~60s (5源串行) | 可接受 |
| 去重查询 | 1 SELECT/clue | 批量查询可优化 |
| clues 表日增量 | ~50-200 条 | < 1000 条/天，无需分区 |
| 索引 | status, category, source | 已满足当前查询 |

---

## 十三、后续运维建议

### 13.1 定时采集任务

```bash
# crontab -e
# 每天 8:00、12:00、16:00、20:00 自动采集（关键词：AI、科技、互联网）
0 8,12,16,20 * * * curl -s "http://localhost:8000/api/clues/collect/multichannel?keywords=AI,%E7%A7%91%E6%8A%80,%E4%BA%92%E8%81%94%E7%BD%91&max_results=20"
```

### 13.2 定期清理

```sql
-- 每月清理 > 90 天且状态为 'discarded' 的线索
DELETE FROM clues
WHERE status = 'discarded'
  AND created_at < DATE_SUB(NOW(), INTERVAL 90 DAY)
LIMIT 1000;

-- 每次执行后 OPTIMIZE TABLE
OPTIMIZE TABLE clues;
```

### 13.3 监控 SQL

```sql
-- 每日线索采集量
SELECT DATE(created_at) as date, COUNT(*) as count
FROM clues
GROUP BY DATE(created_at)
ORDER BY date DESC LIMIT 7;

-- 各源采集成功率
SELECT
  SUBSTRING_INDEX(source, '(', 1) as source_name,
  COUNT(*) as total,
  SUM(CASE WHEN status = 'verified' THEN 1 ELSE 0 END) as verified,
  ROUND(SUM(CASE WHEN status = 'verified' THEN 1 ELSE 0 END)/COUNT(*)*100, 1) as rate
FROM clues
WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY source_name
ORDER BY total DESC;

-- 线索转化率
SELECT
  COUNT(DISTINCT c.id) as total_clues,
  COUNT(DISTINCT a.clue_id) as converted_clues,
  ROUND(COUNT(DISTINCT a.clue_id)/COUNT(DISTINCT c.id)*100, 1) as conversion_rate
FROM clues c
LEFT JOIN articles a ON a.clue_id = c.id
WHERE c.created_at > DATE_SUB(NOW(), INTERVAL 30 DAY);
```

---

## 十四、已知注意事项 & 技术备忘录

1. **SQLite 不删文件**: 切换到 MySQL 后，SQLite 的 `.db` 文件保留不动，随时可回滚
2. **时区**: ORM 层使用 `datetime.now(timezone.utc)`，MySQL 建议 `SET time_zone = '+00:00'`
3. **TEXT 字段索引**: MySQL 的 TEXT 字段不能直接建索引，如需全文搜索可改用 `FULLTEXT` 索引
4. **Boolean 字段**: MySQL 用 `TINYINT(1)` 存储，SQLAlchemy 自动处理转换
5. **外键约束**: SQLite 默认关闭外键检查 (`PRAGMA foreign_keys = OFF`)，MySQL 默认开启，迁移时需确保数据引用完整性
6. **AUTO_INCREMENT**: MySQL 的 `id` 字段迁移后会从已有最大值继续递增，如需重置: `ALTER TABLE xxx AUTO_INCREMENT = 1;`
