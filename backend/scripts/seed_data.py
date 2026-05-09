#!/usr/bin/env python3
"""
数据库种子数据脚本
用于初始化测试数据：新闻线索、稿件、选题、用户反馈等
使用方法:
    python seed_data.py              # 创建所有示例数据
    python seed_data.py --clues      # 仅创建线索数据
    python seed_data.py --articles   # 仅创建稿件数据
    python seed_data.py --topics     # 仅创建选题数据
    python seed_data.py --clean      # 清除所有数据
"""
import sys
import os
import argparse
from datetime import datetime, timedelta
import random
from typing import List

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models import (
    NewsClue,
    Article,
    ArticleStatus,
    TopicPlanning,
    TopicStatus,
    PublicationFeedback,
    Review,
    ReviewResult,
    ReviewLevel,
)
from app.config import get_settings

settings = get_settings()

# ============================================================
# 示例数据定义
# ============================================================

SAMPLE_CLUES = [
    {
        "title": "人工智能技术在新闻编辑领域的最新应用",
        "content": "随着 AI 技术的快速发展，越来越多的新闻媒体开始采用人工智能辅助新闻编辑工作。据报道，多家主流媒体已引入 AI 编辑系统，实现自动摘要、智能配图等功能，大幅提升编辑效率。",
        "source": "科技日报",
        "category": "科技",
        "keywords": ["人工智能", "新闻编辑", "AI技术", "媒体创新"],
        "news_value_score": 85,
        "propagation_potential": 80,
    },
    {
        "title": "全球芯片短缺问题持续缓解，供应链逐步恢复",
        "content": "经过近两年的紧张局面，全球芯片供应链终于出现积极信号。最新数据显示，芯片交付周期已显著缩短，多个行业的芯片短缺问题正在逐步缓解。",
        "source": "经济参考报",
        "category": "财经",
        "keywords": ["芯片短缺", "供应链", "全球经济", "半导体"],
        "news_value_score": 78,
        "propagation_potential": 82,
    },
    {
        "title": "教育部发布新版义务教育课程方案",
        "content": "教育部今日正式发布《义务教育课程方案和课程标准（2024年版）》，此次修订涉及课程设置、课时安排、课程内容等多个方面，旨在进一步提升教育质量。",
        "source": "新华社",
        "category": "社会",
        "keywords": ["教育改革", "义务教育", "课程标准", "教育部"],
        "news_value_score": 90,
        "propagation_potential": 88,
    },
    {
        "title": "国产新能源汽车销量再创新高，市场份额突破 60%",
        "content": "最新汽车销售数据显示，国产新能源汽车品牌继续保持强劲增长势头，整体市场份额已突破 60%，创历史新高。",
        "source": "中国汽车报",
        "category": "财经",
        "keywords": ["新能源汽车", "电动汽车", "国产汽车", "市场份额"],
        "news_value_score": 82,
        "propagation_potential": 75,
    },
    {
        "title": "多地楼市调控政策出现松动迹象",
        "content": "近期，多个城市的房地产市场调控政策出现微妙变化。部分地区相继出台支持性措施，业内人士分析认为这可能意味着楼市政策底的到来。",
        "source": "第一财经",
        "category": "财经",
        "keywords": ["房地产", "楼市调控", "房价", "政策变化"],
        "news_value_score": 88,
        "propagation_potential": 90,
    },
    {
        "title": "神舟十八号载人飞船成功发射",
        "content": "今日上午，神舟十八号载人飞船在酒泉卫星发射中心成功发射，三名航天员将前往中国空间站执行为期六个月的任务。",
        "source": "人民日报",
        "category": "科技",
        "keywords": ["神舟飞船", "航天", "空间站", "载人航天"],
        "news_value_score": 95,
        "propagation_potential": 92,
    },
    {
        "title": "跨境电商新规即将实施，进口商品价格或受影响",
        "content": "海关总署宣布的跨境电商零售进口新规将于下月正式实施。业内人士分析，新规将对部分进口商品的定价和配送时间产生影响。",
        "source": "国际商报",
        "category": "财经",
        "keywords": ["跨境电商", "海关", "进口商品", "电子商务"],
        "news_value_score": 72,
        "propagation_potential": 68,
    },
    {
        "title": "全国多地高温预警，电网负荷创新高",
        "content": "受持续高温天气影响，全国多地电网负荷连续创下新高。电力部门已启动应急响应，全力保障居民用电和工业生产。",
        "source": "中国电力报",
        "category": "社会",
        "keywords": ["高温天气", "电力", "电网", "民生"],
        "news_value_score": 75,
        "propagation_potential": 78,
    },
    {
        "title": "字节跳动发布新一代 AI 大模型",
        "content": "字节跳动今日正式发布其自主研发的新一代人工智能大模型，该模型在文本生成、代码编写等方面展现出优异性能，已开始内测。",
        "source": "36氪",
        "category": "科技",
        "keywords": ["字节跳动", "AI大模型", "人工智能", "技术创新"],
        "news_value_score": 88,
        "propagation_potential": 85,
    },
    {
        "title": "我国科学家成功实现千公里量子密钥分发",
        "content": "中国科学技术大学潘建伟团队在量子通信领域取得重大突破，成功实现了超过1000公里的量子密钥分发实验，刷新世界纪录。",
        "source": "光明日报",
        "category": "科技",
        "keywords": ["量子通信", "量子密钥", "科技创新", "中科大"],
        "news_value_score": 92,
        "propagation_potential": 80,
    },
    {
        "title": "全国医保支付方式改革全面启动",
        "content": "国家医保局宣布，DRG/DIP 支付方式改革将在今年内全面推广，届时医保基金的使用效率将得到进一步提升。",
        "source": "健康报",
        "category": "社会",
        "keywords": ["医保改革", "DRG", "医疗保障", "民生"],
        "news_value_score": 85,
        "propagation_potential": 82,
    },
    {
        "title": "上海自贸区推出新一轮金融开放政策",
        "content": "上海自贸试验区今日发布金融改革开放新举措，涉及跨境投融资、人民币国际化等多个领域，进一步扩大对外开放。",
        "source": "解放日报",
        "category": "财经",
        "keywords": ["自贸区", "金融开放", "上海", "改革开放"],
        "news_value_score": 83,
        "propagation_potential": 76,
    },
]

SAMPLE_TOPICS = [
    {
        "title": "人工智能时代的新闻业变革",
        "description": "深入探讨 AI 技术如何重塑新闻采集、编辑、发布全流程，分析传统媒体数字化转型路径。",
        "category": "科技",
        "priority": "high",
        "suggested_keywords": ["人工智能", "新闻业", "数字化转型", "媒体融合"],
        "target_audience": "媒体从业者、科技爱好者、政策制定者",
        "planned_articles": 5,
    },
    {
        "title": "新能源汽车产业发展现状与趋势",
        "description": "全面梳理国内外新能源汽车市场发展态势，分析技术路线竞争格局，展望产业发展方向。",
        "category": "财经",
        "priority": "high",
        "suggested_keywords": ["新能源汽车", "电动汽车", "碳中和", "汽车产业"],
        "target_audience": "投资者、汽车行业从业者、消费者",
        "planned_articles": 4,
    },
    {
        "title": "后疫情时代的教育改革",
        "description": "分析疫情对教育模式的影响，探讨在线教育与线下教育的融合发展路径。",
        "category": "社会",
        "priority": "medium",
        "suggested_keywords": ["教育改革", "在线教育", "教育公平", "教育技术"],
        "target_audience": "教育工作者、家长、学生",
        "planned_articles": 3,
    },
    {
        "title": "半导体产业链安全与国产替代",
        "description": "深度分析全球半导体产业链格局，探讨中国半导体产业自主可控的发展路径。",
        "category": "科技",
        "priority": "high",
        "suggested_keywords": ["半导体", "芯片", "国产替代", "产业链安全"],
        "target_audience": "科技行业从业者、投资者、政策研究者",
        "planned_articles": 6,
    },
    {
        "title": "房地产市场走势与调控政策",
        "description": "研判当前房地产市场形势，分析调控政策效果，展望未来市场走向。",
        "category": "财经",
        "priority": "high",
        "suggested_keywords": ["房地产", "楼市调控", "房价走势", "住房保障"],
        "target_audience": "购房者、投资者、房地产从业者",
        "planned_articles": 4,
    },
]

SAMPLE_ARTICLES = [
    {
        "title": "AI 赋能新闻编辑：传统媒体数字化转型的新路径",
        "content": """## 引言

人工智能技术正在深刻改变新闻业的运作方式。从内容采集到编辑分发，AI 的应用正在重塑新闻生产的每个环节。

## AI 在新闻编辑中的应用现状

### 1. 智能内容生成

多家主流媒体已采用 AI 系统自动生成财报摘要、体育赛事报道等结构化新闻。这类应用大幅提升了编辑效率，让记者能够专注于更具深度的调查报道。

### 2. 自动摘要与改写

AI 技术能够快速从长篇文章中提取核心观点，生成不同长度的摘要，满足不同平台和用户的需求。

### 3. 智能配图与视频剪辑

通过图像识别和自然语言处理，AI 可以自动为文章匹配相关图片，甚至生成短视频内容。

## 挑战与思考

尽管 AI 带来了效率提升，但也引发了关于新闻真实性、算法偏见等问题的讨论。如何在技术创新的同时坚守新闻伦理，是每个媒体从业者需要思考的问题。

## 结论

AI 不是要取代记者，而是成为记者的得力助手。善用 AI 工具，新闻业将迎来更大的发展机遇。""",
        "category": "科技",
        "author": "张明",
        "status": ArticleStatus.PUBLISHED,
    },
    {
        "title": "全球芯片供应链：从短缺到平衡的演变",
        "content": """## 背景

持续近两年的全球芯片短缺终于出现缓解迹象。这场始于疫情的供应链危机，深刻影响了汽车、电子等多个行业。

## 短缺原因分析

1. **需求激增**：疫情带动宅经济兴起，消费电子需求爆发式增长
2. **产能受限**：工厂停工、物流受阻导致供给端收缩
3. **囤货心理**：恐慌性囤货进一步加剧短缺

## 复苏信号

最新数据显示，芯片交付周期已从峰值 52 周缩短至约 30 周，多个品类的芯片价格开始回落。

## 对中国的启示

中国作为全球最大的芯片消费市场，需要加快实现关键环节的自主可控。

## 展望

随着新增产能逐步释放，预计 2025 年全球芯片供应链将基本恢复平衡。""",
        "category": "财经",
        "author": "李华",
        "status": ArticleStatus.PUBLISHED,
    },
    {
        "title": "神舟十八号：中国人太空逐梦的新里程碑",
        "content": """## 发射任务概述

今日上午，神舟十八号载人飞船在酒泉卫星发射中心成功发射。这标志着中国空间站进入新的建设阶段。

## 任务亮点

### 1. 航天员配置

本次任务由三名航天员组成，包括一名第二批航天员和两名第三批航天员。

### 2. 主要任务

- 完成空间站空间科学实验
- 实施出舱活动
- 进行舱外设施维护

### 3. 技术创新

新一代飞船在生命保障系统、能源供应等方面均有升级。

## 意义深远

神舟十八号任务的成功，将进一步巩固中国在载人航天领域的地位，为人类和平利用太空贡献中国力量。""",
        "category": "科技",
        "author": "王强",
        "status": ArticleStatus.PUBLISHED,
    },
    {
        "title": "国产新能源汽车市场份额突破 60%",
        "content": """## 市场概况

最新汽车销售数据显示，国产新能源汽车品牌继续保持强劲增长势头，整体市场份额已突破 60%，创历史新高。

## 增长原因

1. **技术进步**：电池技术、智能驾驶等核心技术不断突破
2. **政策支持**：国家对新能源汽车的补贴和扶持政策
3. **消费者认可**：产品质量和用户体验显著提升

## 未来趋势

预计到 2030 年，新能源汽车将占中国汽车市场的 80% 以上，成为主流选择。""",
        "category": "财经",
        "author": "陈静",
        "status": ArticleStatus.PUBLISHED,
    },
    {
        "title": "教育部发布新版义务教育课程方案",
        "content": """## 方案要点

教育部今日正式发布《义务教育课程方案和课程标准（2024年版）》，此次修订涉及课程设置、课时安排、课程内容等多个方面。

## 主要变化

1. **加强德育**：将德育融入各学科教学
2. **注重实践**：增加实践课程比重
3. **科技创新**：强化科学素养和创新能力培养

## 实施时间

新方案将于今年秋季学期开始在全国范围内实施。""",
        "category": "社会",
        "author": "刘老师",
        "status": ArticleStatus.PUBLISHED,
    },
    {
        "title": "多地楼市调控政策出现松动迹象",
        "content": """## 政策变化

近期，多个城市的房地产市场调控政策出现微妙变化。部分地区相继出台支持性措施，业内人士分析认为这可能意味着楼市政策底的到来。

## 具体措施

1. **降低首付比例**：首套房首付比例下调至 20%
2. **贷款利率优惠**：首套房贷款利率降至 4.0% 以下
3. **放松限购**：部分城市调整限购政策

## 市场反应

政策出台后，多地楼市成交量明显回升，市场信心有所恢复。""",
        "category": "财经",
        "author": "房地产分析师",
        "status": ArticleStatus.PUBLISHED,
    },
    {
        "title": "字节跳动发布新一代 AI 大模型",
        "content": """## 发布详情

字节跳动今日正式发布其自主研发的新一代人工智能大模型，该模型在文本生成、代码编写等方面展现出优异性能，已开始内测。

## 技术特点

1. **多语言支持**：支持 100+ 种语言
2. **代码能力**：精通多种编程语言
3. **多模态**：支持文本、图像、视频等多种模态

## 应用场景

该模型将应用于抖音、今日头条等产品，为用户提供更智能的服务。""",
        "category": "科技",
        "author": "技术记者",
        "status": ArticleStatus.PUBLISHED,
    },
    {
        "title": "全国多地高温预警，电网负荷创新高",
        "content": """## 天气状况

受持续高温天气影响，全国多地电网负荷连续创下新高。电力部门已启动应急响应，全力保障居民用电和工业生产。

## 应对措施

1. **错峰用电**：工业企业实行错峰生产
2. **增加供电**：火电厂满负荷运行
3. **节能倡议**：倡导居民节约用电

## 预计影响

高温天气预计将持续一周，电力部门提醒市民合理安排用电时间。""",
        "category": "社会",
        "author": "气象记者",
        "status": ArticleStatus.PUBLISHED,
    },
    {
        "title": "上海自贸区推出新一轮金融开放政策",
        "content": """## 政策内容

上海自贸试验区今日发布金融改革开放新举措，涉及跨境投融资、人民币国际化等多个领域，进一步扩大对外开放。

## 重点措施

1. **跨境金融**：放宽跨境融资限制
2. **金融市场**：扩大金融市场准入
3. **人民币国际化**：推进人民币跨境使用

## 意义

这些措施将进一步提升上海国际金融中心的地位，推动中国金融市场的国际化进程。""",
        "category": "财经",
        "author": "金融分析师",
        "status": ArticleStatus.PUBLISHED,
    },
    {
        "title": "我国科学家成功实现千公里量子密钥分发",
        "content": """## 技术突破

中国科学技术大学潘建伟团队在量子通信领域取得重大突破，成功实现了超过1000公里的量子密钥分发实验，刷新世界纪录。

## 技术意义

1. **安全性**：量子密钥分发具有绝对安全性
2. **通信距离**：突破了传统量子通信的距离限制
3. **实用化**：为量子通信的实用化奠定基础

## 应用前景

该技术将在国防、金融、政务等领域发挥重要作用，保障信息安全。""",
        "category": "科技",
        "author": "科技记者",
        "status": ArticleStatus.PUBLISHED,
    },
]


# ============================================================
# 种子数据生成函数
# ============================================================

def create_tables():
    """创建所有数据库表"""
    print("[INFO] 创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("[OK] 数据库表创建完成")


def seed_clues(db, count: int = None) -> int:
    """创建新闻线索数据"""
    print(f"[INFO] 创建新闻线索数据...")
    
    clues_to_create = SAMPLE_CLUES[:count] if count else SAMPLE_CLUES
    created = 0
    
    for i, clue_data in enumerate(clues_to_create):
        # 随机生成一些变体
        is_variant = random.choice([True, False])
        
        clue = NewsClue(
            title=clue_data["title"],
            content=clue_data["content"],
            source=clue_data["source"],
            source_url=f"https://example.com/news/{i+1}",
            category=clue_data["category"],
            keywords=clue_data["keywords"],
            news_value_score=clue_data["news_value_score"] + random.randint(-5, 5),
            propagation_potential=clue_data["propagation_potential"] + random.randint(-5, 5),
            status=random.choice(["pending", "pending", "processed"]),
            created_at=datetime.now() - timedelta(days=random.randint(0, 30)),
        )
        
        db.add(clue)
        created += 1
    
    db.commit()
    print(f"[OK] 创建了 {created} 条新闻线索")
    return created


def seed_articles(db, count: int = None) -> int:
    """创建稿件数据"""
    print(f"[INFO] 创建稿件数据...")
    
    articles_to_create = SAMPLE_ARTICLES[:count] if count else SAMPLE_ARTICLES
    created = 0
    
    for i, article_data in enumerate(articles_to_create):
        article = Article(
            title=article_data["title"],
            content=article_data["content"],
            abstract=article_data["content"][:200] + "...",
            category=article_data["category"],
            author=article_data["author"],
            status=article_data["status"],
            created_at=datetime.now() - timedelta(days=random.randint(0, 30)),
            updated_at=datetime.now() - timedelta(days=random.randint(0, 10)),
        )
        
        db.add(article)
        db.flush()  # 先刷新获取文章ID
        created += 1
        
        # 为已发布的文章添加反馈数据
        if article_data["status"] == ArticleStatus.PUBLISHED:
            feedback = PublicationFeedback(
                article_id=article.id,
                view_count=random.randint(100, 10000),
                like_count=random.randint(10, 500),
                share_count=random.randint(5, 200),
                comment_count=random.randint(0, 50),
            )
            db.add(feedback)
    
    db.commit()
    print(f"[OK] 创建了 {created} 篇稿件")
    return created


def seed_topics(db, count: int = None) -> int:
    """创建选题数据"""
    print(f"[INFO] 创建选题数据...")
    
    topics_to_create = SAMPLE_TOPICS[:count] if count else SAMPLE_TOPICS
    created = 0
    
    for topic_data in topics_to_create:
        topic = TopicPlanning(
            title=topic_data["title"],
            description=topic_data["description"],
            category=topic_data["category"],
            editor=f"编辑{random.randint(1, 5)}",
            status=random.choice([TopicStatus.PLANNING, TopicStatus.IN_PROGRESS]),
            created_at=datetime.now() - timedelta(days=random.randint(0, 30)),
        )
        
        db.add(topic)
        created += 1
    
    db.commit()
    print(f"[OK] 创建了 {created} 个选题")
    return created


def seed_reviews(db) -> int:
    """创建审核记录"""
    print("[INFO] 创建审核记录...")
    
    # 获取待审核的稿件
    pending_articles = db.query(Article).filter(
        Article.status == ArticleStatus.PENDING_REVIEW
    ).all()
    
    created = 0
    for article in pending_articles:
        review = Review(
            article_id=article.id,
            reviewer=f"审核员{random.randint(1, 3)}",
            review_level=random.choice([ReviewLevel.FIRST, ReviewLevel.SECOND]),
            result=random.choice([ReviewResult.APPROVED, ReviewResult.APPROVED, ReviewResult.NEED_REVISION]),
            comments="内容充实，逻辑清晰，建议发布。" if random.random() > 0.3 else "需要补充相关数据支撑。",
            reviewed_at=datetime.now() - timedelta(hours=random.randint(1, 48)),
        )
        
        db.add(review)
        created += 1
        
        # 更新稿件状态
        if review.result == ReviewResult.APPROVED:
            article.status = ArticleStatus.APPROVED
        elif review.result == ReviewResult.NEED_REVISION:
            article.status = ArticleStatus.DRAFT
    
    db.commit()
    print(f"[OK] 创建了 {created} 条审核记录")
    return created


def clean_database(db):
    """清除所有数据"""
    print("[WARN] 清除所有数据...")
    
    db.query(PublicationFeedback).delete()
    db.query(Review).delete()
    db.query(Article).delete()
    db.query(NewsClue).delete()
    db.query(TopicPlanning).delete()
    
    db.commit()
    print("[OK] 数据清除完成")


def show_statistics(db):
    """显示数据库统计"""
    print("\n" + "="*50)
    print("数据库统计")
    print("="*50)
    
    clue_count = db.query(NewsClue).count()
    article_count = db.query(Article).count()
    topic_count = db.query(TopicPlanning).count()
    review_count = db.query(Review).count()
    feedback_count = db.query(PublicationFeedback).count()
    
    print(f"新闻线索: {clue_count} 条")
    print(f"稿件: {article_count} 篇")
    print(f"  - 待审核: {db.query(Article).filter(Article.status == ArticleStatus.PENDING_REVIEW).count()}")
    print(f"  - 已发布: {db.query(Article).filter(Article.status == ArticleStatus.PUBLISHED).count()}")
    print(f"选题: {topic_count} 个")
    print(f"审核记录: {review_count} 条")
    print(f"反馈数据: {feedback_count} 条")
    print("="*50 + "\n")


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="新闻采编系统 - 数据库种子数据工具")
    parser.add_argument("--clues", action="store_true", help="仅创建线索数据")
    parser.add_argument("--articles", action="store_true", help="仅创建稿件数据")
    parser.add_argument("--topics", action="store_true", help="仅创建选题数据")
    parser.add_argument("--reviews", action="store_true", help="仅创建审核数据")
    parser.add_argument("--clean", action="store_true", help="清除所有数据")
    parser.add_argument("--stats", action="store_true", help="显示数据库统计")
    parser.add_argument("--clue-count", type=int, default=None, help="线索数量")
    parser.add_argument("--article-count", type=int, default=None, help="稿件数量")
    parser.add_argument("--topic-count", type=int, default=None, help="选题数量")
    
    args = parser.parse_args()
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 确保数据目录存在
        os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
        
        # 创建表
        create_tables()
        
        if args.clean:
            clean_database(db)
            return
        
        if args.stats:
            show_statistics(db)
            return
        
        # 根据参数决定创建哪些数据
        if args.clues:
            seed_clues(db, args.clue_count)
        elif args.articles:
            seed_articles(db, args.article_count)
        elif args.topics:
            seed_topics(db, args.topic_count)
        elif args.reviews:
            seed_reviews(db)
        else:
            # 创建所有数据
            seed_clues(db, args.clue_count)
            seed_articles(db, args.article_count)
            seed_topics(db, args.topic_count)
            seed_reviews(db)
        
        # 显示统计
        show_statistics(db)
        
        print("[OK] 种子数据创建完成！")
        print("\n提示：")
        print("  - 使用 --stats 查看详细统计")
        print("  - 使用 --clean 清除所有数据")
        print("  - 使用 --clues/--articles/--topics 只创建特定类型数据")
        
    except Exception as e:
        print(f"[ERROR] 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
