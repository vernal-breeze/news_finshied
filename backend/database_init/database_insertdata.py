#!/usr/bin/env python3
"""
一键生成测试数据 - 使用 Faker 生成中文假数据

用法:
    cd backend
    python database_init/database_insertdata.py

生成内容:
    - 20+ 普通用户 (role=reporter) + 1 审核员 (role=reviewer) + 1 管理员 (role=admin)
    - 每个用户 3-5 篇稿件，覆盖全部状态
    - 30+ 条线索
    - 10+ 条选题
    - 20+ 条审核记录
    - 10+ 条反馈数据
    - 10+ 条站内消息

密码: 所有测试账号统一密码为 Test123456
      使用 bcrypt 加密（若 bcrypt 不可用则回退到 sha256）

依赖:
    pip install faker bcrypt
"""

import sys
import os
import json
import random
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _setup_project_path():
    """确保 CWD 在 backend/ 目录，并设置 sys.path，创建必要的数据目录"""
    script_dir = Path(__file__).resolve().parent          # database_init/
    backend_dir = script_dir.parent                        # backend/

    os.chdir(str(backend_dir))

    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    data_dir = backend_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    return backend_dir


# ── 必须在任何 app.* 导入之前调用 ──
_backend_dir = _setup_project_path()

from app.database import SessionLocal
from app.models.user import User
from app.models.article import Article, ArticleStatus
from app.models.clue import Clue
from app.models.topic import Topic
from app.models.review import Review
from app.models.feedback import Feedback
from app.models.message import Message
from app.models.collection import Collection

# ── 密码工具 ────────────────────────────────────────────

TEST_PASSWORD = "Test123456"


def _get_password_hash(password: str) -> str:
    """密码哈希 - 优先 bcrypt，回退 sha256"""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        print("[WARN] bcrypt 未安装，回退到 sha256 (pip install bcrypt 以使用更安全的哈希)")
        return hashlib.sha256(password.encode()).hexdigest()


# ── Faker 初始化 ────────────────────────────────────────

try:
    from faker import Faker
    fake = Faker("zh_CN")
    FAKER_OK = True
except ImportError:
    print("[ERROR] Faker 未安装！请执行: pip install faker")
    sys.exit(1)


# ── 辅助数据 ────────────────────────────────────────────

CATEGORIES = ["科技", "财经", "社会", "教育", "体育", "娱乐", "健康", "军事", "国际", "环保"]
ARTICLE_STATUSES = [
    ArticleStatus.DRAFT,
    ArticleStatus.PENDING_REVIEW,
    ArticleStatus.REVIEWING,
    ArticleStatus.APPROVED,
    ArticleStatus.PUBLISHED,
    ArticleStatus.REJECTED,
]
NEWS_SOURCES = ["新华网", "人民日报", "央视新闻", "腾讯新闻", "新浪新闻", "网易新闻", "凤凰网", "澎湃新闻", "Bing搜索"]
TOPIC_STATUSES = ["draft", "active", "completed", "cancelled"]
REVIEW_RESULTS = ["pending", "approved", "rejected", "revision"]
REVIEW_LEVELS = ["first", "second", "final"]

# 中文标题与内容模板
TITLE_TEMPLATES = [
    "{keyword}技术取得重大突破，行业迎来新变革",
    "{keyword}领域竞争加剧：多家企业布局新赛道",
    "{keyword}政策正式落地，影响深远",
    "{keyword}市场规模持续扩大，预计将超万亿",
    "深度解读：{keyword}如何改变我们的生活",
    "{keyword}行业面临新挑战：专家呼吁加强监管",
    "全球{keyword}发展报告发布：中国位居前列",
    "从0到1：{keyword}创业者的成功之道",
    "{keyword}+传统行业：融合创新案例盘点",
    "未来已来：{keyword}将重塑哪些行业格局？",
]

CONTENT_PARAGRAPHS = [
    "随着技术的不断进步，{keyword}领域正迎来前所未有的发展机遇。业内专家表示，未来五年将是该领域的关键窗口期。",
    "据权威机构统计，{keyword}相关市场规模在过去一年中增长了30%以上，预计到明年将达到新的高度。",
    "多家科技巨头已宣布加大对{keyword}的投入力度。业内人士分析认为，这标志着行业正进入加速发展期。",
    "政府相关部门近期发布了关于{keyword}的指导意见，明确了未来发展方向和重点任务。",
    "在采访中，多位行业专家对{keyword}的前景表示乐观。他们认为，技术创新将是推动行业发展的核心动力。",
    "值得注意的是，{keyword}发展也带来了一系列新的挑战，包括数据安全、隐私保护等问题亟待解决。",
    "从国际视角来看，{keyword}已成为全球科技竞争的焦点领域，各国纷纷加大研发投入。",
]

# 选题标题模板
TOPIC_TITLE_TEMPLATES = [
    "{keyword}深度报道策划",
    "{keyword}专题：从现象到本质",
    "人物专访：{keyword}领域的先行者",
    "{keyword}系列报道（一）",
    "{keyword}年度盘点",
    "独家调查：{keyword}背后的故事",
    "科技前沿：{keyword}最新动态",
    "数据新闻：{keyword}可视化分析",
    "观点争鸣：{keyword}的机遇与挑战",
    "{keyword}产业地图",
]

# 消息模板
MESSAGE_TEMPLATES = [
    "您的稿件《{title}》已提交审核，请耐心等待",
    "稿件《{title}》审核通过，已发布",
    "稿件《{title}》需要修改，请查看审核意见",
    "您有新任务：请完成{title}相关报道",
    "系统通知：{title}选题已分配给您",
    "{username} 评论了您的稿件《{title}》",
    "您的稿件《{title}》阅读量突破{count}",
]


def _random_keyword() -> str:
    """生成随机中文关键词"""
    keywords = [
        "人工智能", "5G通信", "区块链", "新能源", "量子计算", "数字经济",
        "芯片制造", "自动驾驶", "生物医药", "碳中和", "元宇宙", "航天科技",
        "云计算", "物联网", "机器人", "基因编辑", "新材料", "智慧城市",
        "无人机", "虚拟现实",
    ]
    return random.choice(keywords)


def _random_datetime(days_back: int = 90) -> datetime:
    """生成过去 N 天内的随机时间"""
    now = datetime.now(timezone.utc)
    delta = timedelta(days=random.randint(1, days_back))
    return now - delta


def _random_tags() -> str:
    """生成随机标签（逗号分隔）"""
    all_tags = ["科技", "创新", "政策", "产业", "数据", "趋势", "AI", "数字化", "市场", "资本"]
    n = random.randint(2, 4)
    return ",".join(random.sample(all_tags, n))


# ── 数据生成函数 ────────────────────────────────────────


def _get_or_create_user(db, username: str, email: str, password_hash: str,
                        nickname: str, full_name: str, role: str) -> User:
    """幂等创建用户 — 已存在则复用并刷新密码，不存在则新建"""
    existing = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing:
        # 刷新密码为 Test123456，更新角色/状态确保一致
        existing.password_hash = password_hash
        existing.nickname = nickname
        existing.full_name = full_name
        existing.role = role
        existing.is_active = True
        print(f"  [{role}] 已存在 → 复用: 用户名={existing.username} 密码={TEST_PASSWORD}")
        return existing
    else:
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            nickname=nickname,
            full_name=full_name,
            role=role,
            is_active=True,
            avatar="",
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        print(f"  [{role}] 新建: 用户名={username} 密码={TEST_PASSWORD}")
        return user


def _ensure_unique_username(db, base_username: str) -> str:
    """确保用户名唯一 — 若冲突则加随机后缀"""
    max_retries = 20
    for _ in range(max_retries):
        if not db.query(User).filter(User.username == base_username).first():
            return base_username
        base_username = base_username.rstrip("0123456789") + str(random.randint(10, 99))
    return base_username + str(random.randint(1000, 9999))


def seed_users(db) -> tuple:
    """
    幂等生成用户数据:
    - 20 个普通用户 (reporter)
    - 1 个审核员 (reviewer)
    - 1 个管理员 (admin)
    返回 (reporter_ids, reviewer_id, admin_id, all_users)
    """
    print("\n[SEED] 生成用户数据...")
    password_hash = _get_password_hash(TEST_PASSWORD)
    users = []

    # 管理员（幂等）
    admin = _get_or_create_user(
        db, "admin", "admin@news-editor.com",
        password_hash, "系统管理员", "Admin", "admin"
    )
    users.append(admin)

    # 审核员（幂等）
    reviewer = _get_or_create_user(
        db, "reviewer", "reviewer@news-editor.com",
        password_hash, "审核编辑-张明", "张明", "reviewer"
    )
    users.append(reviewer)

    # 普通用户 (reporter)
    reporter_ids = []
    for i in range(1, 21):
        name = fake.name()
        username = _ensure_unique_username(db, fake.user_name() + str(random.randint(10, 99)))
        email_domain = random.choice(["qq.com", "163.com", "gmail.com", "sina.com"])

        reporter = _get_or_create_user(
            db, username, f"{username}@{email_domain}",
            password_hash, name, name, "reporter"
        )
        users.append(reporter)
        reporter_ids.append(reporter)
        if i <= 5 or i % 5 == 0:
            print(f"  [reporter {i:2d}] 用户名={reporter.username} 昵称={reporter.nickname}")

    db.flush()  # 刷新以获取 ID
    print(f"  [SEED] 共 {len(users)} 个用户 "
          f"(admin=1, reviewer=1, reporter={len(reporter_ids)})")

    return reporter_ids, reviewer.id, admin.id, users


def seed_clues(db, count: int = 35) -> list:
    """生成线索数据，返回所有 Clue 对象"""
    print(f"\n[SEED] 生成 {count}+ 条线索...")

    clues = []
    for i in range(count):
        keyword = _random_keyword()
        title = fake.sentence(nb_words=random.randint(5, 12)).rstrip("。")
        clue = Clue(
            title=title,
            content=fake.paragraph(nb_sentences=random.randint(2, 5)),
            source=random.choice(NEWS_SOURCES),
            source_url=fake.url(),
            keywords=json.dumps([keyword], ensure_ascii=False),
            status=random.choice(["pending", "pending", "pending", "processing"]),
            news_value_score=round(random.uniform(30, 90), 1),
            propagation_potential=round(random.uniform(25, 80), 1),
            collected_by="system",
            category=random.choice(CATEGORIES),
            channel=random.choice(["news", "social", "government", "weibo"]),
            created_at=_random_datetime(30),
            processed_at=_random_datetime(7) if random.random() > 0.5 else None,
        )
        db.add(clue)
        clues.append(clue)

    db.flush()
    print(f"  [SEED] 共生成 {len(clues)} 条线索")
    return clues


def seed_topics(db, count: int = 15) -> list:
    """生成选题数据，返回所有 Topic 对象"""
    print(f"\n[SEED] 生成 {count}+ 条选题...")

    topics = []
    for i in range(count):
        keyword = _random_keyword()
        title_tpl = random.choice(TOPIC_TITLE_TEMPLATES)
        title = title_tpl.format(keyword=keyword)

        topic = Topic(
            title=title,
            description=fake.paragraph(nb_sentences=random.randint(2, 4)),
            category=random.choice(CATEGORIES),
            status=random.choice(TOPIC_STATUSES),
            editor=fake.name(),
            ref_clue_ids="[]",
            planned_date=_random_datetime(60).date() if random.random() > 0.3 else None,
            ai_score=round(random.uniform(5, 9.5), 1),
            ai_suggestion=f"建议从{keyword}角度深度挖掘",
            performance_score=round(random.uniform(60, 95), 1) if random.random() > 0.5 else None,
            created_at=_random_datetime(60),
        )
        db.add(topic)
        topics.append(topic)

    db.flush()
    print(f"  [SEED] 共生成 {len(topics)} 条选题")
    return topics


def seed_articles(db, reporter_ids: list, topics: list, clues: list) -> list:
    """每个用户生成 3-5 篇稿件，覆盖全部状态。返回所有 Article 对象"""
    print(f"\n[SEED] 生成稿件数据（每用户 3-5 篇）...")

    articles = []
    status_counter = {s: 0 for s in ARTICLE_STATUSES}

    for user in reporter_ids:
        n = random.randint(3, 5)
        for j in range(n):
            keyword = _random_keyword()
            title_tpl = random.choice(TITLE_TEMPLATES)
            title = title_tpl.format(keyword=keyword)

            status = random.choice(ARTICLE_STATUSES)
            status_counter[status] += 1

            # 正文
            paragraphs = random.sample(CONTENT_PARAGRAPHS, k=random.randint(2, 4))
            content = "\n\n".join(p.format(keyword=keyword) for p in paragraphs)

            article = Article(
                title=title,
                content=content,
                summary=fake.sentence(nb_words=random.randint(10, 25)),
                status=status.value,
                cover_image=f"https://picsum.photos/800/400?random={random.randint(1, 1000)}",
                tags=_random_tags(),
                category=random.choice(CATEGORIES),
                view_count=random.randint(0, 5000) if status == ArticleStatus.PUBLISHED else 0,
                like_count=random.randint(0, 200) if status == ArticleStatus.PUBLISHED else 0,
                quality_score=round(random.uniform(60, 98), 1),
                ai_score=round(random.uniform(5, 9.8), 1),
                author_id=user.id,
                topic_id=random.choice(topics).id if random.random() > 0.3 else None,
                clue_id=random.choice(clues).id if random.random() > 0.5 else None,
                created_at=_random_datetime(30),
                published_at=(
                    _random_datetime(7) if status == ArticleStatus.PUBLISHED else None
                ),
            )
            db.add(article)
            articles.append(article)

    db.flush()
    print(f"  [SEED] 共生成 {len(articles)} 篇稿件")
    for s, c in status_counter.items():
        print(f"         {s.value}: {c} 篇")
    return articles


def seed_reviews(db, articles: list, reviewer_id: int) -> list:
    """为已提交审核的稿件生成审核记录"""
    print(f"\n[SEED] 生成审核记录...")

    # 筛选需要审核的稿件（status != draft）
    reviewable = [
        a for a in articles
        if a.status in [
            ArticleStatus.PENDING_REVIEW.value,
            ArticleStatus.REVIEWING.value,
            ArticleStatus.APPROVED.value,
            ArticleStatus.REJECTED.value,
            ArticleStatus.PUBLISHED.value,
        ]
    ]

    reviews = []
    for article in reviewable[:30]:  # 最多 30 条
        # 可能有多重审核
        n_reviews = random.randint(1, 2)
        for level_idx in range(n_reviews):
            review = Review(
                article_id=article.id,
                reviewer=fake.name(),
                reviewer_id=reviewer_id,
                level=REVIEW_LEVELS[level_idx % 3],
                result=random.choice(REVIEW_RESULTS),
                status="completed" if random.random() > 0.2 else "pending",
                comment=_generate_review_comment(article.title),
                score=random.randint(60, 98),
                created_at=_random_datetime(14),
            )
            db.add(review)
            reviews.append(review)

    db.flush()
    print(f"  [SEED] 共生成 {len(reviews)} 条审核记录")
    return reviews


def _generate_review_comment(title: str) -> str:
    """生成审核评语"""
    comments = [
        f"《{title}》内容详实，观点明确，建议通过。",
        f"稿件质量良好，但数据来源需要补充。",
        f"建议加强{title}相关的背景介绍，增加读者理解。",
        f"标题可进一步优化，使其更具吸引力。",
        f"内容逻辑清晰，符合发布标准。",
        f"部分段落需要精简，建议控制在2000字以内。",
        f"角度新颖，但事实核查需要更充分。",
    ]
    return random.choice(comments)


def seed_feedbacks(db, articles: list):
    """为已发布稿件生成反馈数据"""
    print(f"\n[SEED] 生成反馈数据...")

    published = [a for a in articles if a.status == ArticleStatus.PUBLISHED.value]
    feedbacks = []

    # 为已发布的稿件生成 feedback（最多 12 条）
    for article in published[:12]:
        view_count = random.randint(100, 10000)
        like_count = random.randint(10, 500)
        comment_count = random.randint(0, 50)
        share_count = random.randint(0, 200)

        # 计算互动率
        engagement_rate = round(
            (like_count + comment_count + share_count) / max(view_count, 1) * 100, 2
        )

        feedback = Feedback(
            article_id=article.id,
            view_count=view_count,
            like_count=like_count,
            comment_count=comment_count,
            share_count=share_count,
            engagement_rate=engagement_rate,
            trending_score=round(random.uniform(0, 100), 1),
            created_at=_random_datetime(7),
        )
        db.add(feedback)
        feedbacks.append(feedback)

    db.flush()
    print(f"  [SEED] 共生成 {len(feedbacks)} 条反馈数据")
    return feedbacks


def seed_messages(db, users: list, articles: list):
    """生成站内消息"""
    print(f"\n[SEED] 生成消息数据...")

    messages = []
    for _ in range(15):
        article = random.choice(articles) if articles else None
        user = random.choice(users) if users else None
        title = article.title if article else "某稿件"
        tpl = random.choice(MESSAGE_TEMPLATES)

        content = tpl.format(
            title=title,
            username=user.nickname if user else "系统",
            count=random.randint(100, 9999),
        )

        msg = Message(
            content=content,
            sender="system",
            type=random.choice(["system", "notification", "reply"]),
            is_read=random.random() > 0.6,
            related_id=article.id if article else None,
            related_type="article" if article else "",
            created_at=_random_datetime(14),
            read_at=_random_datetime(7) if random.random() > 0.5 else None,
        )
        db.add(msg)
        messages.append(msg)

    db.flush()
    print(f"  [SEED] 共生成 {len(messages)} 条消息")
    return messages


def seed_collections(db):
    """生成采集任务记录"""
    print(f"\n[SEED] 生成采集任务记录...")

    collections = []
    keywords_list = ["人工智能", "新能源", "数字经济", "5G", "芯片"]

    for kw in keywords_list:
        for i in range(random.randint(1, 2)):
            coll = Collection(
                name=f"{kw}线索采集-{fake.date_this_year()}",
                keywords=kw,
                channels="news,social,weibo",
                status=random.choice(["pending", "completed", "completed", "running"]),
                result_count=random.randint(0, 10),
                error_msg="",
                created_at=_random_datetime(30),
            )
            db.add(coll)
            collections.append(coll)

    db.flush()
    print(f"  [SEED] 共生成 {len(collections)} 条采集任务")
    return collections


def run_seed():
    """主入口：执行所有数据生成并写入 docs/user_data.md"""
    db = SessionLocal()

    try:
        print("\n" + "=" * 60)
        print("  新闻内容采编系统 - 测试数据生成器")
        print("=" * 60)
        print(f"  数据库:   {db.get_bind().url}")
        print(f"  统一密码: {TEST_PASSWORD}")
        print(f"  Faker:    {fake.name()} (zh_CN)")
        print("=" * 60)

        # 1. 用户
        reporter_ids, reviewer_id, admin_id, all_users = seed_users(db)

        # 2. 线索
        clues = seed_clues(db)

        # 3. 选题
        topics = seed_topics(db)

        # 4. 稿件
        articles = seed_articles(db, reporter_ids, topics, clues)

        # 5. 审核记录
        seed_reviews(db, articles, reviewer_id)

        # 6. 反馈
        seed_feedbacks(db, articles)

        # 7. 消息
        seed_messages(db, all_users, articles)

        # 8. 采集任务
        seed_collections(db)

        db.commit()

        # ── 统计 ──────────────────────────────────────
        print("\n" + "=" * 60)
        print("  📊 数据生成完毕，统计：")
        print(f"      用户:     {db.query(User).count()}")
        print(f"      稿件:     {db.query(Article).count()}")
        print(f"      线索:     {db.query(Clue).count()}")
        print(f"      选题:     {db.query(Topic).count()}")
        print(f"      审核记录: {db.query(Review).count()}")
        print(f"      反馈:     {db.query(Feedback).count()}")
        print(f"      消息:     {db.query(Message).count()}")
        print(f"      采集任务: {db.query(Collection).count()}")
        print("=" * 60)

        # ── 生成文档 ──────────────────────────────────
        _generate_user_doc(all_users, reporter_ids, reviewer_id, admin_id)

    except Exception as e:
        db.rollback()
        print(f"\n❌ 错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


def _generate_user_doc(all_users, reporter_ids, reviewer_id, admin_id):
    """生成 docs/user_data.md 文档"""
    docs_dir = _backend_dir / "docs"
    os.makedirs(docs_dir, exist_ok=True)
    filepath = os.path.join(docs_dir, "user_data.md")

    lines = []
    lines.append("# 测试账号数据")
    lines.append("")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> 统一密码: `{TEST_PASSWORD}`")
    lines.append(f"> 密码加密: bcrypt (优先) / sha256 (回退)")
    lines.append("")
    lines.append("## 特殊账号")
    lines.append("")
    lines.append("| 角色 | 用户名 | 密码 | 昵称 | 邮箱 |")
    lines.append("|------|--------|------|------|------|")

    # 找到 admin 和 reviewer
    for user in all_users:
        if user.id == admin_id:
            lines.append(
                f"| 管理员 | `admin` | `{TEST_PASSWORD}` | {user.nickname} | {user.email} |"
            )
        elif user.id == reviewer_id:
            lines.append(
                f"| 审核员 | `reviewer` | `{TEST_PASSWORD}` | {user.nickname} | {user.email} |"
            )

    lines.append("")
    lines.append("## 普通用户（记者/编辑）")
    lines.append("")
    lines.append("| 序号 | 用户名 | 昵称 | 角色 | 邮箱 |")
    lines.append("|------|--------|------|------|------|")

    for i, user in enumerate(reporter_ids, 1):
        lines.append(
            f"| {i} | `{user.username}` | {user.nickname} | reporter | {user.email} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 使用说明")
    lines.append("")
    lines.append("### 登录")
    lines.append("")
    lines.append(f"- 所有账号密码均为 `{TEST_PASSWORD}`")
    lines.append("- 管理员: `admin`")
    lines.append("- 审核员: `reviewer`")
    lines.append("- 普通用户: 见上表，任选一个")
    lines.append("")
    lines.append("### 重新生成数据")
    lines.append("")
    lines.append("```bash")
    lines.append("cd backend")
    lines.append("python database_init/database_init.py --all")
    lines.append("```")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\n📄 账号文档已生成: {filepath}")


if __name__ == "__main__":
    run_seed()
