# AI API 配置说明

## 已配置的免费 API

本项目已配置使用**硅基流动（SiliconFlow）**的免费 API，集成**DeepSeek-V3**模型。

## 免费额度

- **新用户注册送 2000 万 token**
- 每月还有 100 万 token 的免费额度
- 约等于每天可以生成 300-500 篇新闻稿件

## 获取 API Key 步骤

### 1. 注册账号
访问官网：https://cloud.siliconflow.cn
- 点击右上角"Login"
- 使用手机号注册
- 完成实名认证（确保 API 调用权限）

### 2. 创建 API Key
- 登录后点击左侧"API 密钥"
- 点击"新建 API 密钥"
- 可以添加描述（非必填）
- 生成后鼠标悬停复制密钥

### 3. 配置到项目
将复制的 API Key 粘贴到 `backend/.env` 文件中：

```bash
SILICONFLOW_API_KEY=你的 API_KEY
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
```

### 4. 重启后端服务
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

## 支持的模型

- ✅ DeepSeek-V3（推荐）
- ✅ DeepSeek-R1
- ✅ Qwen2.5-72B-Instruct
- ✅ ChatGLM3-6B
- ✅ 更多模型请访问：https://cloud.siliconflow.cn/models

## 测试 AI 功能

1. 访问 AI 稿件页面：http://localhost:3000/ai-article
2. 点击"新建稿件"
3. 勾选要整合的新闻线索
4. 系统会自动调用 AI 生成并保存稿件

## 备用 API 服务

如果硅基流动 API 不可用，还可以使用以下免费服务：

### OpenRouter
- 官网：https://openrouter.ai
- 提供免费额度的多种模型

### 腾讯云
- 官网：https://cloud.tencent.com
- 搜索"混元大模型"

### 科大讯飞
- 官网：https://www.xfyun.cn
- 星火大模型 API

## 注意事项

1. **API Key 安全**：不要将 API Key 提交到代码仓库
2. **额度监控**：在硅基流动控制台查看使用情况
3. **网络问题**：国内访问可能需要使用加速器

## 故障排查

### AI 调用失败
- 检查 `.env` 文件中的 API Key 是否正确
- 确认后端服务已重启
- 查看后端日志中的错误信息

### 额度用尽
- 注册新账号获取额度
- 或切换到其他免费 API 服务

## 联系支持

如有问题，请访问：
- 硅基流动官网：https://cloud.siliconflow.cn
- 技术支持：support@siliconflow.cn
