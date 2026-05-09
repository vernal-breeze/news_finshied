# 🔑 获取 AI API Key 完整指南

## 问题诊断
当前 API Key 已失效，系统显示："Api key is invalid"

## 解决步骤

### 1. 注册硅基流动账号
1. 访问官网：https://cloud.siliconflow.cn
2. 使用手机号注册账号
3. 完成实名认证（必须）

### 2. 获取 API Key
1. 登录后进入控制台
2. 点击左侧菜单 "API 密钥"
3. 点击 "创建新的 API Key"
4. 复制生成的 Key（格式：`sk-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`）

### 3. 更新配置文件
编辑 `/Users/fanqie/Desktop/all/毕业论文/code/backend/.env` 文件：

```bash
# 将这一行改为你的真实 API Key
SILICONFLOW_API_KEY=sk-你的真实 API_KEY
```

### 4. 重启后端服务
```bash
cd /Users/fanqie/Desktop/all/毕业论文/code/backend
source venv/bin/activate
# 按 Ctrl+C 停止当前服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 测试 AI 生成
运行测试脚本验证：
```bash
python test_ai_generation.py
```

## 免费额度说明
- 新用户注册送 2000 万 token
- 约可生成 2000-3000 篇新闻稿件
- 完全够用，不用担心额度问题

## 备用方案

如果不想使用硅基流动，也可以使用其他 AI 服务：

### 方案 2：使用 OpenAI
```bash
OPENAI_API_KEY=sk-你的 OpenAI_KEY
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 方案 3：使用智谱 AI
```bash
ZHIPU_API_KEY=你的智谱_KEY
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
```

## 测试验证
成功配置后，在 AI 稿件页面：
1. 点击"新建稿件"
2. 选择 1-3 条线索
3. 点击"生成并保存"
4. 等待 AI 生成内容
5. 查看生成的稿件

## 常见问题

### Q: API Key 无效？
A: 确保复制完整，没有多余空格

### Q: 调用超时？
A: 首次调用可能较慢，耐心等待 10-30 秒

### Q: 额度用完？
A: 硅基流动有免费额度，用完可充值或切换其他服务
