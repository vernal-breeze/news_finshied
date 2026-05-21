-- ============================================================
-- 新闻内容采编系统 - MySQL 初始化脚本
-- Docker 容器首次启动时自动执行
-- ============================================================

-- 确保使用正确的数据库
USE news_editor;

-- 设置字符集
ALTER DATABASE news_editor
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

-- 创建用户表
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

-- 创建线索表
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

-- 创建选题表
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

-- 创建文章表
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
    INDEX idx_articles_status_created (status, created_at DESC),
    CONSTRAINT fk_articles_author FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_articles_topic FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL,
    CONSTRAINT fk_articles_clue FOREIGN KEY (clue_id) REFERENCES clues(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建审核记录表
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
    CONSTRAINT fk_reviews_article FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    CONSTRAINT fk_reviews_reviewer FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建反馈统计表
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

-- 创建站内消息表
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

-- 创建采集任务表
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

-- 插入默认管理员账号 (密码: admin123, SHA256 哈希)
INSERT IGNORE INTO users (username, email, password_hash, nickname, role, is_active)
VALUES (
    'admin',
    'admin@news-editor.local',
    '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
    '系统管理员',
    'admin',
    1
);
