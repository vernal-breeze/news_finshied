"""
完整数据种子脚本
按逻辑关系插入几十条模拟数据，确保增删改查可验证
"""
import json
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import (
    User, UserRole, get_password_hash,
    Article, Clue, Review, Topic, Feedback, Message, Collection,
)


def seed_all():
    db = SessionLocal()
    try:
        _seed_users(db)
        _seed_clues(db)
        _seed_topics(db)
        _seed_articles(db)
        _seed_reviews(db)
        _seed_feedback(db)
        _seed_messages(db)
        _seed_collections(db)
        db.commit()
        print("✅ 所有数据种子写入完成")
    except Exception as e:
        db.rollback()
        print(f"❌ 种子写入失败: {e}")
        raise
    finally:
        db.close()


def _seed_users(db):
    """创建 10 个用户"""
    existing = db.query(User).count()
    if existing > 0:
        print("  用户已存在，跳过")
        return

    users = [
        {"username": "admin", "password": "admin123", "role": "USER",
         "nickname": "管理员", "email": "admin@news.com", "full_name": "系统管理员"},
        {"username": "chief_editor", "password": "chief123", "role": "USER",
         "nickname": "主编", "email": "chief@news.com", "full_name": "李主编"},
        {"username": "editor1", "password": "editor123", "role": "USER",
         "nickname": "张编辑", "email": "zhang@news.com", "full_name": "张小明"},
        {"username": "editor2", "password": "editor123", "role": "USER",
         "nickname": "王编辑", "email": "wang@news.com", "full_name": "王丽华"},
        {"username": "reporter1", "password": "reporter123", "role": "USER",
         "nickname": "刘记者", "email": "liu@news.com", "full_name": "刘伟"},
        {"username": "reporter2", "password": "reporter123", "role": "USER",
         "nickname": "陈记者", "email": "chen@news.com", "full_name": "陈芳"},
        {"username": "reporter3", "password": "reporter123", "role": "USER",
         "nickname": "赵记者", "email": "zhao@news.com", "full_name": "赵强"},
        {"username": "reviewer", "password": "reviewer123", "role": "REVIEWER",
         "nickname": "初审", "email": "review@news.com", "full_name": "周审核"},
        {"username": "reviewer2", "password": "reviewer123", "role": "REVIEWER",
         "nickname": "复审", "email": "review2@news.com", "full_name": "吴复审"},
        {"username": "user", "password": "user123", "role": "USER",
         "nickname": "读者甲", "email": "reader@news.com", "full_name": "普通读者"},
    ]
    for u in users:
        user = User(
            username=u["username"],
            email=u["email"],
            password_hash=get_password_hash(u["password"]),
            full_name=u["full_name"],
            nickname=u["nickname"],
            role=u["role"],
            is_active=True,
        )
        db.add(user)
    db.flush()
    # Assign user_ids
    for u in users:
        user_obj = db.query(User).filter(User.username == u["username"]).first()
        u["id"] = user_obj.id
    print(f"  创建 {len(users)} 个用户")


def _seed_clues(db):
    """创建 15 条线索"""
    existing = db.query(Clue).count()
    if existing > 0:
        print("  线索已存在，跳过")
        return

    clues_data = [
        {"title": "AI大模型在新闻行业的应用趋势", "content": "2026年全球AI大模型在新闻采编领域的渗透率预计将达到65%，多家主流媒体已开始部署AI辅助写作系统。", "source": "路透社", "status": "verified"},
        {"title": "本市地铁新线规划出炉", "content": "市规划局今日发布轨道交通第五期建设规划草案，涉及3条新线路，总里程约120公里。", "source": "市规划局官网", "status": "new"},
        {"title": "新能源汽车出口数据创历史新高", "content": "据海关总署最新数据，一季度我国新能源汽车出口量同比增长82%，达到45.6万辆。", "source": "海关总署", "status": "verified"},
        {"title": "社区食堂可持续发展调查", "content": "记者走访了全市12个社区食堂发现，经营状况两极分化，部分食堂日均客流不足50人次。", "source": "实地采访", "status": "processing"},
        {"title": "2026年高校毕业生就业形势分析", "content": "教育部数据显示，2026届高校毕业生达1250万人，再创历史新高。IT和新能源行业需求旺盛。", "source": "教育部", "status": "verified"},
        {"title": "跨境电商综试区扩容政策解读", "content": "国务院常务会议决定新设一批跨境电商综合试验区，覆盖中西部主要城市。", "source": "新华社", "status": "new"},
        {"title": "本地文化遗产保护项目启动", "content": "市文旅局宣布启动'古城记忆'数字化保护工程，首批涉及10处历史建筑。", "source": "市文旅局", "status": "processing"},
        {"title": "夏季用电高峰保供措施", "content": "国家电网发布迎峰度夏工作方案，预计今年最大负荷将达13.8亿千瓦。", "source": "国家电网", "status": "verified"},
        {"title": "人工智能医疗影像诊断新突破", "content": "某三甲医院AI辅助诊断系统通过国家医疗器械注册认证，肺结节检出率达98.5%。", "source": "科技日报", "status": "new"},
        {"title": "老旧小区加装电梯推进难点", "content": "记者调查发现，本市老旧小区加装电梯意愿率达80%，但实际安装率不足20%。", "source": "实地调查", "status": "processing"},
        {"title": "首届全球数字贸易博览会筹备", "content": "数贸会将于下月在本市举办，已有60余国确认参展，预计专业观众超10万人次。", "source": "市商务局", "status": "new"},
        {"title": "直播带货行业监管新政", "content": "市场监管总局拟出台直播带货分级分类管理办法，将主播划分为三个信用等级。", "source": "市场监管总局", "status": "verified"},
        {"title": "城市口袋公园建设成果", "content": "去年全市新建口袋公园86处，人均公园绿地面积提升至15.6平方米。", "source": "市园林局", "status": "verified"},
        {"title": "考研报名人数三年来首次下降", "content": "2026年全国硕士研究生报名人数为438万，较去年减少56万人，就业导向分流明显。", "source": "教育部", "status": "new"},
        {"title": "智慧农业赋能乡村振兴", "content": "某县推广智慧农业项目后，农民人均收入增长23%，农产品损耗率降低15%。", "source": "农业农村部", "status": "processing"},
    ]
    for c in clues_data:
        clue = Clue(
            title=c["title"],
            content=c["content"],
            source=c["source"],
            status=c["status"],
        )
        db.add(clue)
    db.flush()
    print(f"  创建 {len(clues_data)} 条线索")


def _seed_topics(db):
    """创建 8 个选题"""
    existing = db.query(Topic).count()
    if existing > 0:
        print("  选题已存在，跳过")
        return

    topics_data = [
        {"name": "AI与新闻业变革", "description": "探讨人工智能在新闻生产、分发、审核等环节的应用与影响", "status": "active"},
        {"name": "城市交通发展", "description": "轨道交通、智慧交通、共享出行等城市交通话题", "status": "active"},
        {"name": "新能源产业观察", "description": "新能源汽车、光伏、储能等新能源领域深度报道", "status": "active"},
        {"name": "民生保障系列", "description": "教育、就业、养老、住房等民生话题", "status": "active"},
        {"name": "文化传承创新", "description": "传统文化保护、数字文化、文化创意产业", "status": "active"},
        {"name": "数字经济发展", "description": "跨境电商、数字贸易、直播经济等数字经济业态", "status": "assigned"},
        {"name": "生态环保专题", "description": "城市绿化、碳达峰碳中和、垃圾分类", "status": "active"},
        {"name": "乡村振兴纪实", "description": "农业现代化、农村电商、乡村治理", "status": "assigned"},
    ]
    for t in topics_data:
        topic = Topic(
            name=t["name"],
            description=t["description"],
            status=t["status"],
        )
        db.add(topic)
    db.flush()
    print(f"  创建 {len(topics_data)} 个选题")


def _seed_articles(db):
    """创建 25 篇文章，覆盖各种状态"""
    existing = db.query(Article).count()
    if existing > 0:
        print("  文章已存在，跳过")
        return

    # 获取作者和编辑的 ID
    reporter1 = db.query(User).filter(User.username == "reporter1").first()
    reporter2 = db.query(User).filter(User.username == "reporter2").first()
    reporter3 = db.query(User).filter(User.username == "reporter3").first()
    editor1 = db.query(User).filter(User.username == "editor1").first()
    editor2 = db.query(User).filter(User.username == "editor2").first()

    now = datetime.utcnow()

    articles_data = [
        # 草稿（draft）
        {"title": "AI辅助写作工具在编辑部的应用调查", "content": "随着ChatGPT等大语言模型的普及，越来越多的新闻编辑部开始尝试使用AI辅助写作工具。据调查，超过70%的记者表示使用过AI工具辅助资料搜集和初稿撰写，但对其准确性和版权问题仍存疑虑。\n\n## 普及现状\n在受访的50家媒体机构中，42家已部署或正在测试AI写作工具。使用频率最高的功能包括：自动摘要（85%）、数据可视化（62%）、多语言翻译（58%）。\n\n## 挑战与争议\n然而，AI生成内容的准确性仍是一大挑战。业内人士指出，AI工具在事实核查方面存在明显短板，需要人工编辑严格把关。", "status": "draft", "category": "科技", "author_id": reporter1.id, "editor_id": editor1.id},

        {"title": "周末文化艺术活动指南", "content": "本周末全市将举办包括美术馆新展开幕、户外音乐节、非遗市集等在内的20余场文化活动。以下为精选推荐。\n\n## 展览\n市美术馆'水墨新境'当代艺术展将展出80位艺术家的200余件作品。\n\n## 演出\n奥林匹克公园将举办为期三天的城市音乐节。", "status": "draft", "category": "文化", "author_id": reporter2.id, "editor_id": None},

        {"title": "春季蔬菜价格走势分析", "content": "据市发改委价格监测中心数据，本周蔬菜均价较上周下降8.2%，实现连续三周回落。\n\n其中叶菜类降幅最为明显，菠菜、油菜价格分别下降15.3%和12.8%。", "status": "draft", "category": "民生", "author_id": reporter3.id, "editor_id": editor2.id},

        # 待审核（pending_review）
        {"title": "本市地铁新线规划详细解读", "content": "市规划局今日正式发布轨道交通第五期建设规划草案，面向社会公开征求意见。本次规划涉及3条新线路，分别为8号线东延、12号线和15号线一期。\n\n## 线路详情\n8号线东延全长18.6公里，设站9座，连通东部新城核心区。\n12号线为南北向骨干线路，全长32公里，设站15座。\n15号线一期全长22.3公里，串联高新技术开发区。\n\n## 预计工期\n三条线路计划于2027年陆续开工，力争2031年前建成通车。", "status": "pending_review", "category": "交通", "author_id": reporter1.id, "editor_id": editor1.id},

        {"title": "一季度新能源汽车出口增长82%", "content": "据海关总署最新发布的数据，2026年一季度我国新能源汽车出口量达45.6万辆，同比增长82%。其中纯电动汽车占比72%，插电混动占比28%。\n\n## 主要市场\n出口前五大市场分别为：欧盟（占比35%）、东南亚（22%）、中东（18%）、拉美（12%）、非洲（8%）。\n\n## 品牌表现\n比亚迪、上汽集团、吉利汽车分列出口量前三名，合计占比超过60%。", "status": "pending_review", "category": "财经", "author_id": reporter2.id, "editor_id": editor2.id},

        {"title": "社区食堂经营现状深度调查", "content": "记者近日走访了全市12家社区食堂，发现经营状况呈现明显两极分化。位于大型居住区的食堂日均客流超过300人次，而部分老旧小区食堂日均客流不足50人次。\n\n## 成功经验\n某社区食堂负责人介绍，成功的秘诀在于'三定'政策：定址于人流密集区、定位于老年人需求、定制适合老年人口味的菜谱。\n\n## 存在问题\n部分社区食堂面临运营成本高企、客流不足等挑战。在走访的12家食堂中，7家实现微利或盈亏平衡，5家处于亏损状态。", "status": "pending_review", "category": "民生", "author_id": reporter3.id, "editor_id": editor1.id},

        {"title": "人工智能医疗影像诊断获重大突破", "content": "国家药品监督管理局今日宣布，某三甲医院联合科技企业研发的AI辅助肺结节诊断系统正式通过三类医疗器械注册认证。该系统在临床试验中肺结节检出率达到99.2%，误诊率低于0.5%。\n\n## 技术特点\n该AI系统基于深度学习算法，通过学习超过50万例肺部CT影像数据，能够在3秒内完成结节检测和良恶性初步判断。\n\n## 临床意义\n专家表示，该系统的推广将大幅提高早期肺癌筛查效率，尤其适用于基层医疗机构的影像诊断辅助。", "status": "pending_review", "category": "科技", "author_id": reporter1.id, "editor_id": editor2.id},

        {"title": "老旧小区加装电梯为何推进缓慢", "content": "据统计，本市符合加装条件的老旧小区单元楼约1.2万栋，目前已加装电梯的仅约2000栋，安装率不足20%。\n\n## 主要困难\n1. 居民意见不统一，特别是低楼层居民反对声音较大\n2. 资金分摊方案难以达成共识\n3. 部分楼栋受地下管线等条件限制\n\n## 解决方案\n市住建局表示，将出台新版指导意见，进一步明确低层补偿标准，并探索'代建租赁'等新模式。", "status": "pending_review", "category": "民生", "author_id": reporter2.id, "editor_id": editor1.id},

        # 已发布（published）
        {"title": "2026年高校毕业生就业形势报告", "content": "2026届高校毕业生达1250万人，再创历史新高。从专业来看，人工智能、数据科学、新能源等新兴专业就业率超过95%，而部分传统文科专业就业率不足80%。\n\n## 行业需求\nIT/互联网行业依然是吸纳高校毕业生的主力军，占比达28%。新能源、生物医药、高端制造等行业需求增长明显。\n\n## 薪资水平\n2026届毕业生平均签约薪资为6850元/月，较去年增长6.2%。其中AI相关岗位平均薪资达1.2万元/月。", "status": "published", "category": "教育", "author_id": reporter1.id, "editor_id": editor1.id,
         "view_count": 2847, "summary": "2026届高校毕业生达1250万，IT、新能源行业需求旺盛，AI岗位薪资领先。"},

        {"title": "直播带货监管新政出台", "content": "市场监管总局今日正式发布《直播带货分级分类管理办法》，将主播划分为A、B、C三个信用等级。\n\n## 分级标准\nA级主播：年销售额超1亿元，投诉率低于0.1%，获得金牌认证。\nB级主播：年销售额超1000万元，投诉率低于0.5%。\nC级主播：其余主播，需接受更严格的监管措施。\n\n## 新规亮点\n要求直播间显著位置公示主播信用等级，建立先行赔付机制。", "status": "published", "category": "财经", "author_id": reporter3.id, "editor_id": editor2.id,
         "view_count": 1562, "summary": "直播带货新规将主播分三级管理，要求公示信用等级。"},

        {"title": "城市口袋公园建设获市民点赞", "content": "市园林绿化局公布数据，去年全市新建口袋公园86处，总面积达23.5万平方米。截至目前，全市口袋公园总数已达420处。\n\n## 分布特点\n新建口袋公园重点分布在老旧城区和新建居住区周边，实现了'300米见绿、500米见园'的目标。\n\n## 市民反馈\n随机采访的50位市民中，48位对口袋公园建设表示满意。'下楼就有小公园，散步方便多了'，家住朝阳区的李先生说。", "status": "published", "category": "民生", "author_id": reporter2.id, "editor_id": editor1.id,
         "view_count": 923, "summary": "去年新建口袋公园86处，420处口袋公园实现300米见绿目标。"},

        {"title": "全球数字经济大会圆满落幕", "content": "为期三天的全球数字经济大会今日落下帷幕，共签订合作项目126个，总金额达580亿元。\n\n## 亮点回顾\n大会发布了全球数字经济白皮书，与会各国共同启动了'数字丝绸之路'合作倡议。\n\n## 成果数据\n参会人数超过5万人，线上线下同步直播观看人次达1200万。", "status": "published", "category": "财经", "author_id": reporter1.id, "editor_id": editor2.id,
         "view_count": 2104, "summary": "三天大会签下126个项目，总金额580亿元。"},

        {"title": "智慧农业助力乡村振兴", "content": "走进某县智慧农业示范基地，无人机正在空中巡视作物长势，传感器实时监测土壤墒情，智能灌溉系统根据数据自动调节水量。\n\n## 效益数据\n该县自推广智慧农业项目以来，农民人均收入增长23%，农产品损耗率降低15%，用水量节约30%。\n\n## 推广前景\n该项目已成为全省智慧农业示范区，计划明年将智慧农业覆盖率达到80%以上。", "status": "published", "category": "农业", "author_id": reporter3.id, "editor_id": editor1.id,
         "view_count": 678, "summary": "智慧农业使农民增收23%，损耗率降低15%。"},

        {"title": "考研人数三年来首次下降意味着什么", "content": "教育部数据显示，2026年全国硕士研究生报名人数为438万，较去年减少56万人，降幅达11.3%。\n\n## 下降原因\n多位教育专家分析，考研人数下降的主要原因是：\n1. 就业市场回暖，更多毕业生选择直接就业\n2. 专硕扩招吸引力下降\n3. 考研成本上升\n\n## 影响分析\n考研降温或将缓解研究生学历贬值趋势，有利于提高研究生培养质量。", "status": "published", "category": "教育", "author_id": reporter2.id, "editor_id": editor2.id,
         "view_count": 4301, "summary": "考研报名438万，同比减少56万，三年来首次下降。"},

        # 已退回（rejected）
        {"title": "夏季用电高峰来临", "content": "随着高温天气持续，全市用电负荷连续三日突破历史极值。电力部门启动应急响应机制。", "status": "rejected", "category": "民生", "author_id": reporter1.id, "editor_id": editor1.id,
         "view_count": 0},

        {"title": "某小区垃圾分类调查", "content": "记者随机走访了5个小区发现，垃圾分类准确率较去年有所提升。", "status": "rejected", "category": "环保", "author_id": reporter3.id, "editor_id": None,
         "view_count": 0},
    ]

    for a in articles_data:
        tags_map = {
            "科技": "AI,人工智能,大模型",
            "交通": "地铁,轨道交通,规划",
            "财经": "新能源,出口,贸易",
            "民生": "社区,就业,医疗",
            "教育": "考研,毕业生,就业",
            "文化": "展览,音乐,艺术",
            "农业": "智慧农业,乡村振兴",
            "环保": "垃圾分类,环保",
        }
        article = Article(
            title=a["title"],
            content=a["content"],
            status=a["status"],
            category=a.get("category"),
            tags=tags_map.get(a.get("category", ""), ""),
            author_id=a["author_id"],
            editor_id=a.get("editor_id"),
            view_count=a.get("view_count", 0),
            summary=a.get("summary"),
        )
        db.add(article)
    db.flush()
    print(f"  创建 {len(articles_data)} 篇文章")


def _seed_reviews(db):
    """为审核中和已发布的文章创建审核记录"""
    existing = db.query(Review).count()
    if existing > 0:
        print("  审核记录已存在，跳过")
        return

    reviewer = db.query(User).filter(User.username == "reviewer").first()
    reviewer2 = db.query(User).filter(User.username == "reviewer2").first()
    articles = db.query(Article).filter(Article.status.in_(["published", "rejected"])).all()

    reviews_data = []
    for a in articles:
        if a.status == "published":
            reviews_data.append({
                "article_id": a.id,
                "reviewer_id": reviewer.id,
                "comment": "内容充实，数据准确，同意发布。" if a.id % 2 == 0 else "稿件质量符合要求，审核通过。",
                "status": "approved",
            })
        elif a.status == "rejected":
            reviews_data.append({
                "article_id": a.id,
                "reviewer_id": reviewer2.id,
                "comment": "内容深度不足，建议重新采写。",
                "status": "rejected",
            })

    for r in reviews_data:
        review = Review(
            article_id=r["article_id"],
            reviewer_id=r["reviewer_id"],
            comment=r["comment"],
            status=r["status"],
        )
        db.add(review)
    db.flush()
    print(f"  创建 {len(reviews_data)} 条审核记录")


def _seed_feedback(db):
    """创建用户反馈"""
    existing = db.query(Feedback).count()
    if existing > 0:
        print("  反馈已存在，跳过")
        return

    feedbacks = [
        {"content": "希望看到更多本地新闻的深度报道", "user_id": 10},
        {"content": "网站加载速度有点慢，建议优化", "user_id": 10},
        {"content": "文章配图质量很好，保持！", "user_id": None},
        {"content": "能不能增加夜间模式？", "user_id": None},
        {"content": "评论功能很好，建议增加点赞回复", "user_id": 10},
    ]
    for f in feedbacks:
        feedback = Feedback(content=f["content"], user_id=f["user_id"])
        db.add(feedback)
    db.flush()
    print(f"  创建 {len(feedbacks)} 条反馈")


def _seed_messages(db):
    """创建读者消息"""
    existing = db.query(Message).count()
    if existing > 0:
        print("  消息已存在，跳过")
        return

    messages = [
        {"content": "欢迎使用新闻内容采编系统！", "sender": "系统"},
        {"content": "您有一篇稿件待审核，请及时处理。", "sender": "系统"},
        {"content": "本周选题会议将于周五上午10点召开。", "sender": "主编"},
        {"content": "AI生成功能已接入，欢迎体验。", "sender": "系统"},
        {"content": "系统将于本周末进行维护升级。", "sender": "管理员"},
    ]
    for m in messages:
        msg = Message(content=m["content"], sender=m["sender"])
        db.add(msg)
    db.flush()
    print(f"  创建 {len(messages)} 条消息")


def _seed_collections(db):
    """创建采集任务"""
    existing = db.query(Collection).count()
    if existing > 0:
        print("  采集任务已存在，跳过")
        return

    collections = [
        {"name": "AI行业日报", "type": "daily"},
        {"name": "新能源政策汇编", "type": "topic"},
        {"name": "本地民生热点追踪", "type": "tracking"},
        {"name": "竞媒头条汇总", "type": "daily"},
    ]
    for c in collections:
        collection = Collection(name=c["name"], type=c["type"])
        db.add(collection)
    db.flush()
    print(f"  创建 {len(collections)} 个采集任务")


if __name__ == "__main__":
    seed_all()
