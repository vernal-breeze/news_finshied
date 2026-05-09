# 安全最佳实践审查报告

**项目**: 新闻内容智能化采编系统  
**技术栈**: Python FastAPI (后端) + React TypeScript Vite (前端)  
**审查日期**: 2026-04-28  

---

## 执行摘要

本次安全审查共发现 **1 个严重 (CRITICAL)**、**5 个高危 (HIGH)**、**9 个中危 (MEDIUM)** 和 **2 个低危 (LOW)** 问题。最关键的问题是多个 API 路由完全缺少认证保护，以及密码哈希方案不符合现代安全标准。建议优先修复 CRITICAL 和 HIGH 级别的问题。

---

## CRITICAL 严重

### #1 FASTAPI-AUTHZ-001: 多个路由完全缺少认证

**位置**: `app/routers/content.py`, `app/routers/collection.py`, `app/routers/reviews.py`, `app/routers/feedback.py`

**影响**: 未认证用户可以消耗 AI API 配额（经济损失）、创建/查看采集任务和审核记录（数据泄露）、操纵反馈统计数据。

**修复**: 为所有路由添加 `current_user: TokenData = Depends(get_current_user)` 参数。

---

## HIGH 高危

### #2 FASTAPI-AUTH-003: 密码存储使用弱哈希方案

**位置**: `app/core/security.py` 第 5 行  
**证据**: `pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")`  
**修复**: 迁移到 Argon2id (`pip3 install argon2-cffi`)，改为 `schemes=["argon2id"]`。

### #3 FASTAPI-HEADERS-001: 完全缺少安全响应头

**位置**: `app/main.py`  
**修复**: 添加中间件设置 `X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、`Referrer-Policy`、`Content-Security-Policy` 等安全头。

### #4 敏感信息泄露: 硬编码默认 SECRET_KEY

**位置**: `app/config.py` 第 83 行  
**证据**: `SECRET_KEY: str = Field(default="dev-secret-key-change-in-production")`  
**修复**: 移除默认值，生产环境强制设置强密钥（启动时抛异常而非 warning）。

### #5 敏感信息泄露: 硬编码默认用户弱密码

**位置**: `app/migrations/seed.py` 第 24、35 行  
**证据**: `reviewer/reviewer123`、`user/user123`  
**修复**: 首次启动时生成随机密码并打印到日志，要求首次登录后修改。

### #6 REACT-AUTH-001: JWT Token 存储在 localStorage

**位置**: `frontend/src/pages/auth/Login.tsx`、`frontend/src/services/api.ts`  
**修复**: 将 token 迁移到内存存储或 httpOnly cookie，使用 refresh token 机制。

---

## MEDIUM 中危

### #7 FASTAPI-OPENAPI-001: 生产环境未禁用 OpenAPI 文档

**位置**: `app/main.py` 第 46-53 行  
**修复**: `docs_url="/docs" if settings.DEBUG else None`

### #8 FASTAPI-FILES-001: 文件上传仅通过扩展名验证类型

**位置**: `app/routers/public.py` 第 93-110 行  
**修复**: 使用 `python-magic` 检查文件 magic bytes。

### #9 FASTAPI-UPLOAD-001: 文件读取后检查大小，存在 DoS 风险

**位置**: `app/routers/public.py` 第 106-108 行  
**修复**: 先检查 `Content-Length` header，使用流式读取。

### #10 FASTAPI-HOST-001: 缺少 Host 头验证

**位置**: `app/main.py`  
**修复**: 添加 `TrustedHostMiddleware`。

### #11 FASTAPI-LIMITS-001: 缺少全局请求体大小限制

**位置**: `app/main.py`  
**修复**: 在 uvicorn 启动参数中添加 `--limit-max-request-size`。

### #12 FASTAPI-DEPLOY-002: .env.example 中 DEBUG=true

**位置**: `backend/.env.example` 第 7 行  
**修复**: 改为 `DEBUG=false`。

### #13 JWT Token 过期时间偏长 (8小时)

**位置**: `app/core/auth.py`  
**修复**: 缩短至 30-60 分钟，配合 refresh token。

### #14 REACT-AUTHZ-001: 前端路由守卫不校验用户角色

**位置**: `frontend/src/App.tsx` 第 13-27 行  
**修复**: 在路由守卫中增加角色检查，确认后端 API 有独立权限控制。

### #15 REACT-FILE-001: 前端文件上传缺少类型/大小校验

**位置**: `frontend/src/pages/editor/Articles.tsx` 第 304-322 行  
**修复**: 在 `beforeUpload` 中添加 `file.type` 和 `file.size` 校验。

### #16 REACT-URL-001: 外部链接未做域名验证

**位置**: `frontend/src/utils/url.ts`  
**修复**: 添加域名白名单或用户确认机制。

---

## LOW 低危

### #17 FASTAPI-INJECT-001: f-string SQL 拼接（硬编码常量）

**位置**: `app/migrations/schema_migrations.py`  
**说明**: 仅用于硬编码常量，无实际风险。

### #18 .env.example 占位符

**位置**: `backend/.env.example`  
**说明**: 占位符值可接受，但 DEBUG 默认值应改为 false。

---

## 通过项 (PASS)

| 检查项 | 说明 |
|--------|------|
| FASTAPI-AUTH-004 JWT 验证 | 使用算法白名单，验证签名和 exp |
| FASTAPI-CORS-001 CORS 配置 | 未使用通配符+凭证组合 |
| FASTAPI-RESP-001 响应数据 | 未暴露 password_hash |
| FASTAPI-INJECT-001 SQL 注入 | 使用 ORM，无用户输入拼接 |
| REACT-XSS-001 XSS | 未使用 dangerouslySetInnerHTML |
| REACT-DOM-001 DOM XSS | 未使用 innerHTML 等 |
| REACT-CONFIG-001 密钥暴露 | 前端环境变量无敏感信息 |
| REACT-NET-001 数据泄露 | 无跨域凭据发送 |
| REACT-REDIRECT-001 开放重定向 | 已有白名单防护 |
| REACT-CSRF-001 CSRF | 不适用（Bearer token 认证） |
| 日志敏感信息 | 未记录密码或密钥 |
