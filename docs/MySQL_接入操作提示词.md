# MySQL 数据库接入操作提示词

## 任务目标

将新闻内容采编系统的数据从 SQLite 迁移到 MySQL，实现以下功能：

1. ✅ 删除现有数据库表
2. ✅ 创建 MySQL 数据库和表结构
3. ✅ 插入可用的虚拟测试数据
4. ✅ 配置项目连接 MySQL
5. ✅ 测试系统正常运行
6. ✅ 确保数据能够长期保存

---

## 第一步：准备工作

### 1.1 确认 MySQL 已安装

```bash
# 检查 MySQL 版本
mysql --version

# 如果没有安装，使用 Docker 快速启动
docker run -d \
  --name news_editor_mysql \
  -e MYSQL_ROOT_PASSWORD=rootpass \
  -e MYSQL_DATABASE=news_editor \
  -e MYSQL_USER=news_editor \
  -e MYSQL_PASSWORD=apppass123 \
  -p 3306:3306 \
  mysql:8.0 \
  --character-set-server=utf8mb4 \
  --collation-server=utf8mb4_unicode_ci

# 等待 MySQL 启动（约30秒）
docker ps | grep news_editor_mysql
```

### 1.2 安装 Python 依赖

```bash
cd backend

# 安装 PyMySQL 驱动
pip install pymysql cryptography

# 验证安装
python3 -c "import pymysql; print('PyMySQL OK')"
```

---

## 第二步：创建数据库和表

### 2.1 登录 MySQL

```bash
mysql -u root -prootpass

# 或使用 Docker
docker exec -it news_editor_mysql mysql -u root -prootpass
```

### 2.2 创建数据库（如果不存在）

```sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS news_editor
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE news_editor;

-- 验证
SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = 'news_editor';
```

### 2.3 删除旧表（如需要重建）

```sql
USE news_editor;

-- 关闭外键检查（必须步骤）
SET FOREIGN_KEY_CHECKS = 0;

-- 删除所有表（按依赖顺序）
DROP TABLE IF EXISTS feedbacks;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS articles;
DROP TABLE IF EXISTS topics;
DROP TABLE IF EXISTS collections;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS clues;
DROP TABLE IF EXISTS users;

-- 开启外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 验证所有表已删除
SHOW TABLES;
```

### 2.4 创建所有表

```sql
USE news_editor;
SET FOREIGN_KEY_CHECKS = 0;

-- 1. 用户表
CREATE TABLE users (
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
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 线索表（无外键依赖）
CREATE TABLE clues (
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
    INDEX idx_status (status),
    INDEX idx_category (category),
    INDEX idx_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 选题表
CREATE TABLE topics (
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
    INDEX idx_status (status),
    INDEX idx_editor (editor_id),
    FOREIGN KEY (editor_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 文章表
CREATE TABLE articles (
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
    INDEX idx_author (author_id),
    INDEX idx_status (status),
    INDEX idx_category (category),
    INDEX idx_created (created_at DESC),
    INDEX idx_status_created (status, created_at DESC),
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL,
    FOREIGN KEY (clue_id) REFERENCES clues(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. 审核记录表
CREATE TABLE reviews (
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
    INDEX idx_article (article_id),
    INDEX idx_reviewer (reviewer_id),
    INDEX idx_status (status),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. 反馈统计表
CREATE TABLE feedbacks (
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
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. 站内消息表
CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    content TEXT,
    sender VARCHAR(50) DEFAULT 'system',
    type VARCHAR(30) DEFAULT 'system',
    is_read TINYINT(1) DEFAULT 0,
    related_id INT NULL,
    related_type VARCHAR(50) DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME NULL,
    INDEX idx_type (type),
    INDEX idx_read (is_read),
    INDEX idx_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. 采集任务表
CREATE TABLE collections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) DEFAULT '',
    keywords VARCHAR(500) DEFAULT '',
    channels VARCHAR(200) DEFAULT 'news',
    status VARCHAR(30) DEFAULT 'pending',
    result_count INT DEFAULT 0,
    error_msg TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;

-- 验证所有表已创建
SHOW TABLES;
```

---

## 第三步：插入虚拟测试数据

### 3.1 创建测试用户

```sql
USE news_editor;

-- 插入用户（密码都是 '123456' 的 SHA256 哈希）
INSERT INTO users (username, email, password_hash, nickname, full_name, role, is_active) VALUES
('admin', 'admin@news.local', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', '管理员', '系统管理员', 'admin', 1),
('editor_zhang', 'zhang@news.local', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', '张编辑', '张明', 'editor', 1),
('editor_li', 'li@news.local', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', '李编辑', '李华', 'editor', 1),
('reviewer_wang', 'wang@news.local', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', '王审核', '王芳', 'reviewer', 1),
('reporter_chen', 'chen@news.local', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', '陈记者', '陈伟', 'reporter', 1),
('reporter_liu', 'liu@news.local', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', '刘记者', '刘强', 'reporter', 1);

-- 验证用户
SELECT id, username, role FROM users;
```

### 3.2 创建测试选题

```sql
USE news_editor;

INSERT INTO topics (title, description, category, status, editor_id, planned_date) VALUES
('人工智能技术突破', '报道国内外 AI 领域的重大技术进展和产品发布', '科技', 'active', 2, DATE_ADD(NOW(), INTERVAL 7 DAY)),
('新能源产业观察', '跟踪新能源汽车、储能、光伏等产业链动态', '财经', 'active', 3, DATE_ADD(NOW(), INTERVAL 14 DAY)),
('国际重大新闻', '报道国际政治、经济、文化领域的重大事件', '国际', 'draft', NULL, NULL);

-- 验证选题
SELECT id, title, status, editor_id FROM topics;
```

### 3.3 创建测试线索

```sql
USE news_editor;

INSERT INTO clues (title, content, source, source_url, keywords, status, news_value_score, propagation_potential, category, collected_by) VALUES
('OpenAI 发布 GPT-5 新功能', 'OpenAI 在今日凌晨发布了 GPT-5 的多项新功能，包括更强的推理能力和多模态支持', 'IT之家', 'https://www.ithome.com/news', 'AI,GPT-5,OpenAI', 'pending', 88.5, 82.3, '科技', 'system'),
('特斯拉自动驾驶事故调查', '美国国家公路交通安全管理局对特斯拉自动驾驶系统展开调查', '36氪', 'https://36kr.com/news', '特斯拉,自动驾驶,安全', 'pending', 75.2, 68.9, '科技', 'system'),
('国内新能源车销量创新高', '最新数据显示，3 月国内新能源汽车销量同比增长 45%', '财经网', 'https://caijing.com.cn', '新能源,汽车,销量', 'verified', 92.1, 88.7, '财经', 'reporter_chen'),
('SpaceX 成功发射星舰', 'SpaceX 于昨日成功完成星舰的第七次试飞', '科技日报', 'https://stdaily.com', 'SpaceX,航天,火箭', 'pending', 85.3, 79.5, '科技', 'system'),
('欧盟通过 AI 监管法案', '欧洲议会通过全球首个全面 AI 监管法规', 'BBC', 'https://bbc.com/news', 'AI,欧盟,监管', 'pending', 78.9, 72.4, '国际', 'system');

-- 验证线索
SELECT id, title, status, news_value_score FROM clues;
```

### 3.4 创建测试文章

```sql
USE news_editor;

INSERT INTO articles (title, content, summary, status, tags, category, author_id, topic_id, clue_id, view_count, like_count, quality_score) VALUES
('OpenAI 推出 GPT-5：AI 能力再次飞跃', 'OpenAI 在今日凌晨举办的春季发布会上正式推出 GPT-5，新版本在推理、多模态、代码生成等方面均有显著提升...', 'OpenAI 发布 GPT-5，性能大幅提升', 'published', 'AI,GPT-5,OpenAI', '科技', 5, 1, 1, 1256, 89, 88.5),
('特斯拉自动驾驶安全争议持续发酵', '特斯拉全自动驾驶系统（FSD）近日在美国多地引发交通事故，美国国家公路交通安全管理局已展开正式调查...', 'NHTSA 对特斯拉 FSD 展开调查', 'pending_review', '特斯拉,FSD,自动驾驶', '科技', 5, NULL, 2, 345, 12, 72.3),
('新能源车销量暴涨：行业迎来黄金期', '最新数据显示，3 月份国内新能源汽车销量突破 80 万辆，同比增长 45%，创下历史新高...', '3 月新能源车销量同比增长 45%', 'draft', '新能源,汽车,销量', '财经', 6, 2, 3, 0, 0, 85.2),
('SpaceX 星舰第七次试飞成功', 'SpaceX 于昨日成功完成星舰的第七次试飞任务，这次试飞首次实现了助推器的回收复用...', 'SpaceX 星舰试飞再获成功', 'approved', 'SpaceX,航天,火箭', '科技', 6, 1, 4, 2341, 167, 91.2);

-- 验证文章
SELECT id, title, status, author_id FROM articles;
```

### 3.5 创建审核记录

```sql
USE news_editor;

INSERT INTO reviews (article_id, reviewer_id, level, result, status, comment, score) VALUES
(1, 4, 'first', 'approved', 'completed', '文章内容详实，数据准确，建议发布', 92),
(2, 4, 'first', 'revision', 'completed', '需要补充事故具体细节和官方回应', 75),
(4, 4, 'first', 'approved', 'completed', '航天类报道专业性强，符合发布标准', 95);

-- 验证审核
SELECT id, article_id, result FROM reviews;
```

### 3.6 创建反馈数据

```sql
USE news_editor;

INSERT INTO feedbacks (article_id, view_count, like_count, comment_count, share_count, engagement_rate, trending_score) VALUES
(1, 1256, 89, 45, 23, 0.125, 85.3),
(4, 2341, 167, 89, 56, 0.133, 92.7);

-- 验证反馈
SELECT id, article_id, view_count FROM feedbacks;
```

### 3.7 创建消息数据

```sql
USE news_editor;

INSERT INTO messages (content, sender, type, is_read, related_id, related_type) VALUES
('系统已成功启动，欢迎使用新闻内容采编系统！', 'system', 'system', 1, NULL, NULL),
('您有一篇新文章待审核：《特斯拉自动驾驶安全争议持续发酵》', 'system', 'notification', 0, 2, 'article'),
('文章《OpenAI 推出 GPT-5：AI 能力再次飞跃》审核已通过，恭喜！', 'system', 'notification', 1, 1, 'article');

-- 验证消息
SELECT id, sender, type, is_read FROM messages;
```

### 3.8 创建采集任务数据

```sql
USE news_editor;

INSERT INTO collections (name, keywords, channels, status, result_count) VALUES
('科技新闻采集', 'AI,人工智能,科技', 'ithome,36kr', 'completed', 45),
('财经资讯监控', '新能源,电动车,股市', 'baidu_hot,toutiao', 'running', 23),
('国际新闻追踪', '国际,外交,峰会', 'solidot,oschina', 'pending', 0);

-- 验证采集任务
SELECT id, name, status, result_count FROM collections;
```

### 3.9 验证所有数据

```sql
USE news_editor;

SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL SELECT 'clues', COUNT(*) FROM clues
UNION ALL SELECT 'topics', COUNT(*) FROM topics
UNION ALL SELECT 'articles', COUNT(*) FROM articles
UNION ALL SELECT 'reviews', COUNT(*) FROM reviews
UNION ALL SELECT 'feedbacks', COUNT(*) FROM feedbacks
UNION ALL SELECT 'messages', COUNT(*) FROM messages
UNION ALL SELECT 'collections', COUNT(*) FROM collections;
```

预期输出：
```
table_name    count
users         6
clues         5
topics        3
articles      4
reviews       3
feedbacks     2
messages      3
collections   3
```

---

## 第四步：配置项目连接 MySQL

### 4.1 修改 .env 文件

```bash
# 编辑 backend/.env 文件
nano backend/.env

# 或者直接用 sed 替换
sed -i '' 's|DATABASE_URL=sqlite:///./data/news_editor.db|DATABASE_URL=mysql+pymysql://news_editor:apppass123@localhost:3306/news_editor?charset=utf8mb4|' backend/.env

# 验证修改
grep DATABASE_URL backend/.env
```

### 4.2 验证配置

```bash
cd backend

# 测试配置读取
python3 -c "
from app.core.config import get_settings
s = get_settings()
print(f'DATABASE_URL: {s.DATABASE_URL}')
print(f'Starts with mysql: {s.DATABASE_URL.startswith(\"mysql\")}')
"
```

---

## 第五步：启动并测试系统

### 5.1 启动后端服务

```bash
# 方式1：使用 start.sh 脚本
./start.sh backend

# 方式2：直接启动
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5.2 测试 API 端点

```bash
# 健康检查
curl http://localhost:8000/health

# 获取线索列表
curl http://localhost:8000/api/clues | python3 -m json.tool | head -20

# 获取选题列表
curl http://localhost:8000/api/topics | python3 -m json.tool | head -20

# 获取文章列表
curl http://localhost:8000/api/articles | python3 -m json.tool | head -20

# 获取系统状态
curl http://localhost:8000/status | python3 -m json.tool
```

### 5.3 测试登录功能

```bash
# 注册新用户
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@test.com","password":"123456","nickname":"测试用户"}'

# 使用虚拟数据中的用户登录（密码: 123456）
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=123456"
```

预期输出：返回 JWT token

### 5.4 使用浏览器测试

```
前端地址: http://localhost:3000
后端地址: http://localhost:8000
API 文档: http://localhost:8000/docs
```

---

## 第六步：数据持久化验证

### 6.1 确认数据写入 MySQL

```bash
mysql -u news_editor -papppass123 news_editor -e "SELECT COUNT(*) as article_count FROM articles;"
```

### 6.2 重启后端，验证数据不丢失

```bash
# 停止后端
./start.sh stop

# 重新启动
./start.sh backend

# 检查数据
curl http://localhost:8000/api/articles | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Articles count: {d.get(\"total\", 0)}')"
```

### 6.3 测试数据增删改

```bash
# 创建新线索
curl -X POST http://localhost:8000/api/clues \
  -H "Content-Type: application/json" \
  -d '{"title":"测试线索","content":"这是一条测试线索","source":"测试来源"}'

# 验证数据增加
mysql -u news_editor -papppass123 news_editor -e "SELECT COUNT(*) as clue_count FROM clues;"

# 删除测试线索（通过 API）
# 先获取刚创建的线索 ID
curl http://localhost:8000/api/clues | python3 -c "import sys,json; d=json.load(sys.stdin); ids=[x['id'] for x in d.get('data',[])]; print('Clue IDs:', ids[-3:])"
```

---

## 第七步：完整验证清单

### 功能测试

- [ ] 后端启动无报错
- [ ] 健康检查 `/health` 返回 200
- [ ] 线索列表 `/api/clues` 正常显示
- [ ] 选题列表 `/api/topics` 正常显示
- [ ] 文章列表 `/api/articles` 正常显示
- [ ] 用户登录 `/api/auth/login` 正常
- [ ] 用户注册 `/api/auth/register` 正常
- [ ] 创建线索成功
- [ ] 创建选题成功
- [ ] 创建文章成功

### 数据持久化测试

- [ ] 重启后端后数据不丢失
- [ ] MySQL 中数据与 API 返回一致
- [ ] 新增数据能正确保存
- [ ] 修改数据能正确保存
- [ ] 删除数据能正确保存

### 性能测试（可选）

```bash
# 测试响应时间
time curl http://localhost:8000/api/clues > /dev/null
time curl http://localhost:8000/api/articles > /dev/null
```

---

## 故障排除

### 错误1: 连接被拒绝

```bash
# 检查 MySQL 是否运行
docker ps | grep mysql

# 启动 MySQL
docker start news_editor_mysql

# 或直接安装的 MySQL
brew services start mysql
```

### 错误2: 权限不足

```sql
-- 登录 MySQL
mysql -u root -prootpass

-- 授权
GRANT ALL PRIVILEGES ON news_editor.* TO 'news_editor'@'%';
FLUSH PRIVILEGES;
```

### 错误3: 表已存在

```sql
-- 删除重建
DROP DATABASE news_editor;
CREATE DATABASE news_editor DEFAULT CHARACTER SET utf8mb4;
```

### 错误4: 外键约束失败

```sql
-- 检查数据完整性
SELECT * FROM articles WHERE author_id NOT IN (SELECT id FROM users);

-- 或先禁用外键检查
SET FOREIGN_KEY_CHECKS = 0;
-- 执行操作
SET FOREIGN_KEY_CHECKS = 1;
```

---

## 快速回滚（如需返回 SQLite）

```bash
# 1. 修改 .env 切回 SQLite
sed -i '' 's|DATABASE_URL=.*|DATABASE_URL=sqlite:///./data/news_editor.db|' backend/.env

# 2. 重启后端
./start.sh restart
```

---

## 总结

完成以上步骤后，你的新闻内容采编系统将：

✅ 使用 MySQL 数据库存储数据
✅ 支持高并发和大规模数据
✅ 测试数据完整可用
✅ 系统稳定运行
✅ 数据长期持久化保存

如需进一步优化，可参考 MySQL_Migration_Architecture.md 文档中的性能优化建议。
