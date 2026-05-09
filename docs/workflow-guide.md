# 新闻采编系统 — 完善工作流程全记录

> 本文档记录了项目从初始状态到最终完善状态的完整工作流程，涵盖目录结构重构、安全审查、代码质量提升三个阶段。

---

## 一、项目背景

**项目名称**：基于大模型的新闻内容智能化采集、生成、编辑和发布系统

**技术栈**：
- 后端：Python 3.12 + FastAPI + SQLAlchemy + SQLite/PostgreSQL
- 前端：React 18 + TypeScript + Ant Design 5 + Vite 5
- 部署：Docker + Docker Compose

**初始状态问题**：
- `main.py` 臃肿至 1830 行，包含所有路由
- `schemas/__init__.py` 595 行，所有 Pydantic Schema 混在一个文件
- `models.py` 437 行，10 个模型 + 7 个枚举 + 密码工具全在一个文件
- 前端 `pages/` 目录扁平，缺少分层组织
- 缺少 `.gitignore`、测试、代码规范等工程化配置

---

## 二、阶段一：目录结构重构

### 2.1 任务理解

将臃肿的单文件拆分为按业务域组织的模块化结构，遵循 FastAPI 和 React TypeScript 的最佳实践。

### 2.2 后端重构

#### 步骤 1：创建新目录结构

```
backend/app/
├── core/          # 核心模块（auth, security, exceptions, logging）
├── enums/         # 枚举类型（按业务域拆分）
├── models/        # SQLAlchemy 模型（按业务域拆分）
├── schemas/       # Pydantic Schema（按业务域拆分）
├── middleware/    # 中间件（request_id, logging, security_headers）
├── utils/         # 工具函数（permissions, clue_collector）
├── migrations/    # 数据库迁移（schema_migrations, seed）
└── routers/       # API 路由（按业务域拆分）
```

#### 步骤 2：拆分枚举类型 → `enums/`

从 `models.py` 中提取 7 个枚举类型，按业务域分到 5 个文件：

| 文件 | 枚举 |
|------|------|
| `enums/user.py` | `UserRole` |
| `enums/article.py` | `ArticleStatus` |
| `enums/review.py` | `ReviewLevel`, `ReviewResult` |
| `enums/topic.py` | `TopicStatus` |
| `enums/collection.py` | `CollectionStatus`, `MaterialType` |

**关键决策**：枚举从 `models.py` 独立到 `enums/`，避免 Schema 导入枚举时产生循环依赖。

#### 步骤 3：拆分 SQLAlchemy 模型 → `models/`

将 437 行的单文件拆分为 8 个模型文件 + 1 个基类文件：

| 文件 | 模型 |
|------|------|
| `models/base.py` | `BaseModel` + `get_beijing_time()` |
| `models/user.py` | `User` |
| `models/clue.py` | `NewsClue` |
| `models/article.py` | `Article`, `ArticleComment` |
| `models/review.py` | `Review` |
| `models/topic.py` | `TopicPlanning`, `topic_article_association` |
| `models/feedback.py` | `PublicationFeedback` |
| `models/collection.py` | `CollectionTask`, `CollectedMaterial` |
| `models/message.py` | `Message` |

**向后兼容**：`models/__init__.py` 统一导出所有模型和枚举，原 `models.py` 删除。现有代码中 `from app.models import ...` 无需修改。

#### 步骤 4：拆分 Pydantic Schemas → `schemas/`

将 595 行的 `__init__.py` 拆分为 9 个子模块：

| 文件 | Schema |
|------|--------|
| `schemas/base.py` | 分页、响应包装（保持不变） |
| `schemas/clue.py` | 新闻线索 CRUD |
| `schemas/article.py` | 稿件 CRUD |
| `schemas/review.py` | 审核 |
| `schemas/topic.py` | 选题 + 关联请求 |
| `schemas/feedback.py` | 反馈 + 统计 |
| `schemas/collection.py` | 采集任务/素材 |
| `schemas/ai.py` | AI 分析/生成/评估 |
| `schemas/content.py` | 内容编辑/搜索 |
| `schemas/comment.py` | 读者评论 |

**向后兼容**：`schemas/__init__.py` 改为通配符重导出。

#### 步骤 5：拆分 API 路由 → `routers/`

将 `main.py` 中 1830 行的路由按业务域拆分到 13 个文件：

| 文件 | 路由前缀 | 端点数 |
|------|---------|--------|
| `routers/health.py` | `/health` | 4 |
| `routers/clues.py` | `/api/clues` | 10 |
| `routers/topics.py` | `/api/topics` | 12 |
| `routers/articles.py` | `/api/articles` | 9 |
| `routers/content.py` | `/api/content` | 7 |
| `routers/reviews.py` | `/api/reviews` | 4 |
| `routers/feedback.py` | `/api/feedback` | 7 |
| `routers/public.py` | `/api/public` | 4 |
| `routers/collection.py` | `/api/collection` | 3 |
| `routers/stats.py` | `/api/stats` | 1 |

**每个路由文件的标准结构**：
```python
from fastapi import APIRouter, Depends
from app.core.auth import get_current_user, TokenData
from app.schemas.xxx import ...
from app.services.xxx_service import XxxService

router = APIRouter(prefix="/api/xxx", tags=["XXX"])
xxx_service = XxxService()

@router.get("/")
def list_xxx(current_user: TokenData = Depends(get_current_user), ...):
    ...
```

#### 步骤 6：精简 `main.py`

重构后 `main.py` 从 **1830 行 → 169 行**，仅保留：
- FastAPI 实例创建
- 中间件注册（CORS、请求 ID、安全头、TrustedHost）
- 路由注册（统一从 `routers/__init__.py` 导入）
- 全局异常处理
- `lifespan` 启动/关闭事件

#### 步骤 7：移动核心模块到 `core/`

| 原位置 | 新位置 |
|--------|--------|
| `app/auth.py` | `app/core/auth.py` |
| `app/exceptions.py` | `app/core/exceptions.py` |
| `app/logging_config.py` | `app/core/logging_config.py` |
| `models.py` 中密码函数 | `app/core/security.py` |

原位置保留重导出文件确保向后兼容。

### 2.3 前端重构

#### 目录重组

```
frontend/src/
├── components/
│   ├── common/        # 通用组件（Toast）
│   ├── layouts/       # 布局组件（MainLayout, ReviewLayout）
│   └── reader/        # 读者端组件
├── pages/
│   ├── auth/          # 认证页面（Login, Register）
│   ├── editor/        # 采编端页面（Home, Clues, Articles, Topics, Analytics, AIArticle）
│   ├── review/        # 审核端页面
│   └── reader/        # 读者端页面
├── services/          # API 调用层（api, apiBase, authClient, readerApi）
├── hooks/             # 自定义 Hooks
├── utils/             # 纯工具函数（url）
├── types/             # TypeScript 类型定义
└── constants/         # 常量（路由路径、API 端点）
```

#### 关键变更

1. **页面按角色分组**：`auth/`（认证）、`editor/`（采编）、`review/`（审核）、`reader/`（读者）
2. **API 调用从 `utils/` 提取到 `services/`**：职责分离
3. **布局组件独立到 `layouts/`**：`MainLayout`、`ReviewLayout`
4. **新增 `constants/`**：集中管理路由路径和 API 端点
5. **每个子目录创建 `index.ts`**：统一导出，简化 import

### 2.4 根目录重构

| 操作 | 说明 |
|------|------|
| `docs/` 提升到项目根目录 | 从 `backend/docs/` 移出 |
| 创建 `scripts/` | 归档 `run_backend.sh`、`start.sh` |
| 创建 `.github/workflows/ci.yml` | 基础 CI（后端 import + 前端构建） |

### 2.5 验证方式

```bash
# 后端验证
cd backend && python -c "from app.main import app; print(f'Routes: {len(app.routes)}')"
# 输出: Routes: 80

# 前端验证
cd frontend && npm run build  # TypeScript 编译无错误
```

---

## 三、阶段二：安全审查与修复

### 3.1 安全审查方法论

使用 **security-best-practices** Skill，加载 FastAPI 和 React 的安全参考文档，按规则逐一检查。

#### 审查维度

| 维度 | 后端检查项 | 前端检查项 |
|------|-----------|-----------|
| 认证 | JWT 验证、密码存储 | Token 存储、路由守卫 |
| 授权 | 对象级权限、路由认证 | 前端角色校验 |
| 输入验证 | SQL 注入、文件上传 | XSS、文件上传校验 |
| 配置安全 | CORS、Host 验证、DEBUG 模式 | 客户端密钥暴露 |
| 响应安全 | 敏感数据泄露、安全头 | 开放重定向、CSRF |
| 部署安全 | 密钥管理、默认密码 | — |

### 3.2 发现的问题

| 严重级别 | 数量 | 关键问题 |
|---------|------|---------|
| CRITICAL | 1 | content/collection/reviews 路由完全无认证 |
| HIGH | 5 | 弱密码哈希、缺少安全头、硬编码密钥、localStorage 存 token |
| MEDIUM | 9 | OpenAPI 暴露、文件上传验证不足、缺少 Host 验证等 |
| LOW | 2 | f-string SQL（硬编码）、.env.example |
| PASS | 11 | JWT 验证、CORS、SQL 注入防护、XSS 防护等 |

### 3.3 修复措施

#### CRITICAL：路由认证

为 `content.py`、`collection.py`、`reviews.py` 中缺失认证的路由添加 `get_current_user` 依赖：

```python
@router.post("/generate")
def generate_content(
    data: ContentGenerateRequest,
    current_user: TokenData = Depends(get_current_user),  # 新增
    db: Session = Depends(get_db),
):
    ...
```

#### HIGH：密码哈希迁移

```python
# 之前（不安全）
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

# 之后（安全）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

**注意**：需安装 `bcrypt==4.0.1`（passlib 与 bcrypt 5.x 不兼容）。

#### HIGH：安全响应头中间件

```python
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

#### HIGH：生产环境强制安全密钥

```python
@model_validator(mode="after")
def validate_settings(self):
    if not self.DEBUG:
        if self.SECRET_KEY == "dev-secret-key-change-in-production":
            raise RuntimeError("生产环境必须设置安全密钥")
    return self
```

#### 其他修复

- OpenAPI 文档仅在 DEBUG 模式暴露
- 添加 `TrustedHostMiddleware`
- 前端路由守卫增加角色校验（`ReviewRoute` 检查 `role === 'reviewer'`）
- 前端文件上传添加 `file.type` 和 `file.size` 校验

### 3.4 验证方式

```bash
# 未认证请求应被拒绝
curl -s http://localhost:8001/api/stats/dashboard
# 输出: {"detail": "Not authenticated"}

# 已认证请求正常返回
curl -s -X POST http://localhost:8001/api/auth/login -d "username=user&password=user123"
# 输出: {"access_token": "eyJ...", "token_type": "bearer"}
```

---

## 四、阶段三：代码质量提升

### 4.1 分析方法论

从三个维度并行分析：
1. **后端代码质量**：错误处理、代码重复、类型安全、数据库查询、配置管理
2. **前端代码质量**：组件设计、状态管理、性能、错误处理、可访问性
3. **项目工程化**：文档、Docker、代码规范、Git、CI/CD、数据库管理

### 4.2 发现的问题（按优先级）

#### P0 紧急

| # | 问题 | 影响 |
|---|------|------|
| 1 | 零测试覆盖 | 无法保证代码正确性 |
| 2 | 前端 Dockerfile 缺失 | `docker-compose up` 失败 |
| 3 | 项目根目录无 .gitignore | 敏感文件可能被提交 |
| 4 | Python 依赖无版本锁定 | 构建不可重复 |
| 5 | 前端重复文件未清理 | 维护混乱 |

#### P1 高优先

| # | 问题 | 影响 |
|---|------|------|
| 6 | 异常处理风格不统一 | `HTTPException` vs `BaseAPIException` 混用 |
| 7 | API 响应格式不一致 | 部分直接返回 dict/model |
| 8 | 裸 except 捕获 | 5 处裸 `except:` |
| 9 | Service 层返回值全标 Any | 28 处 `Any` 类型 |
| 10 | 组件严重臃肿 | AIArticle.tsx 1476 行 |
| 11 | 无 Error Boundary | 渲染错误导致白屏 |
| 12 | useState 过多 | AIArticle 30 个 useState |

### 4.3 修复措施

#### P0 修复

1. **删除 6 个前端重复文件**：`utils/api.ts`、`utils/apiBase.ts`、`utils/authClient.ts`、`utils/readerApi.ts`、`components/Toast.tsx`、`components/Layout.tsx`
2. **创建 `.gitignore`**：覆盖 Python、Node、IDE、数据库、日志等
3. **创建前端 Dockerfile**：多阶段构建（Node 构建 → Nginx 静态服务）+ `nginx.conf` + `.dockerignore`
4. **锁定 Python 依赖版本**：`requirements.txt` 中所有包添加具体版本号

#### P1 修复

5. **修复裸 except**：5 处 `except:` → `except Exception:`
6. **修复 `datetime.utcnow()` 弃用**：4 处 → `datetime.now(timezone.utc)`
7. **修复 `on_event("startup")` 弃用**：→ `lifespan` 上下文管理器
8. **修复硬编码 token 过期时间**：删除模块级常量，改为从 `settings.ACCESS_TOKEN_EXPIRE_MINUTES` 读取
9. **修复 `permissions.py` 中 Any 类型**：`current_user: Any` → `current_user: TokenData`
10. **创建 ErrorBoundary 组件**：全局错误边界，防止白屏
11. **创建 `useAuth` 公共 hook**：统一认证状态管理
12. **创建 `utils/tags.ts`**：提取重复的 `getCategoryTag`/`getStatusTag`/`CATEGORIES`
13. **创建 `utils/format.ts`**：提取重复的 `formatRelativeTime`/`formatNumber`
14. **创建 `.editorconfig` + `.gitattributes`**：统一代码风格

---

## 五、最终项目结构

```
项目根目录/
├── .github/workflows/ci.yml     # CI 配置
├── .gitignore                     # Git 忽略规则
├── .gitattributes                 # Git 属性配置
├── .editorconfig                  # 编辑器配置
├── docs/                          # 项目文档
├── scripts/                       # 项目脚本
├── docker-compose.yml             # Docker 编排
├── README.md                      # 项目说明
│
├── backend/
│   ├── app/
│   │   ├── main.py               # 精简入口（~170行）
│   │   ├── config.py             # 配置管理
│   │   ├── database.py           # 数据库连接
│   │   ├── core/                 # 核心模块
│   │   │   ├── auth.py           # JWT 认证
│   │   │   ├── security.py       # 密码哈希（bcrypt）
│   │   │   ├── exceptions.py     # 自定义异常
│   │   │   └── logging_config.py # 日志配置
│   │   ├── enums/                # 枚举类型（5个文件）
│   │   ├── models/               # 数据模型（8个文件）
│   │   ├── schemas/              # Pydantic Schema（10个文件）
│   │   ├── routers/              # API 路由（13个文件）
│   │   ├── middleware/           # 中间件
│   │   ├── services/             # 业务逻辑（10个服务）
│   │   ├── repositories/         # 数据访问层
│   │   ├── utils/                # 工具函数
│   │   └── migrations/           # 数据库迁移
│   ├── scripts/                   # 后端脚本
│   ├── Dockerfile
│   └── requirements.txt           # 锁定版本
│
└── frontend/
    ├── src/
    │   ├── App.tsx               # 应用入口（含 ErrorBoundary）
    │   ├── components/
    │   │   ├── common/            # Toast, ErrorBoundary
    │   │   ├── layouts/           # MainLayout, ReviewLayout
    │   │   └── reader/            # ReaderHeader
    │   ├── pages/
    │   │   ├── auth/              # Login, Register
    │   │   ├── editor/            # Home, Clues, Articles, Topics, Analytics, AIArticle
    │   │   ├── review/            # Dashboard, Queue, Published, Settings
    │   │   └── reader/            # Home, ArticleDetail, Search, Category, Messages
    │   ├── services/              # API 调用层
    │   ├── hooks/                 # useAuth, useAuthSnapshot
    │   ├── utils/                 # url, tags, format
    │   ├── types/                 # TypeScript 类型
    │   └── constants/             # 路由和 API 端点常量
    ├── Dockerfile                  # 多阶段构建
    ├── nginx.conf                  # Nginx 配置
    └── package.json
```

---

## 六、关键设计决策

### 6.1 向后兼容策略

所有文件移动操作在原位置保留重导出文件：

```python
# app/auth.py（向后兼容重导出）
"""向后兼容 - 已迁移至 app.core.auth"""
from app.core.auth import *  # noqa: F401,F403
```

这确保了重构过程中现有代码不会因 import 路径变更而中断。

### 6.2 循环依赖避免

拆分模型和 Schema 时，枚举类型独立到 `enums/` 包：

```
schemas/article.py → app.enums.article.ArticleStatus（而非 app.models.ArticleStatus）
```

避免了 `models → enums → models` 的循环依赖。

### 6.3 密码哈希兼容性

从 `sha256_crypt` 迁移到 `bcrypt` 时，需要删除旧数据库（旧密码哈希无法验证）。生产环境应通过登录时自动升级实现平滑迁移。

### 6.4 bcrypt 版本锁定

`passlib` 与 `bcrypt >= 5.0` 不兼容，必须锁定 `bcrypt==4.0.1`。

---

## 七、验证清单

| 检查项 | 命令/方法 | 预期结果 |
|--------|----------|---------|
| 后端 import | `python -c "from app.main import app"` | 无错误 |
| 路由注册 | `len(app.routes)` | 80 个路由 |
| 登录认证 | `curl -X POST /api/auth/login` | 返回 JWT token |
| 未认证拒绝 | `curl /api/stats/dashboard` | 401 Not authenticated |
| 安全头 | 检查响应 headers | 包含 X-Content-Type-Options 等 |
| 前端编译 | `npm run build` | 无 TypeScript 错误 |
| Docker 构建 | `docker-compose build` | 三个服务构建成功 |

---

## 八、后续建议

以下问题已识别但未在本轮修复，建议后续迭代处理：

### 高优先
- [ ] 添加单元测试（pytest + vitest）
- [ ] 引入 Alembic 数据库迁移
- [ ] 拆分臃肿组件（AIArticle.tsx 1476行、Articles.tsx 1321行）
- [ ] 统一异常处理风格（HTTPException → BaseAPIException）
- [ ] 添加 ESLint + Prettier + Black/Ruff

### 中优先
- [ ] 消除权限检查函数重复（抽取通用函数）
- [ ] 修复 N+1 API 请求（Dashboard 逐一审核）
- [ ] 统一 API 响应格式
- [ ] Service 层返回值类型标注（消除 Any）
- [ ] 更新 README 项目结构说明

### 低优先
- [ ] 添加 Prometheus 指标导出
- [ ] 添加 CHANGELOG.md
- [ ] Docker 中使用非 root 用户
- [ ] 日志聚合方案（Loki/ELK）
