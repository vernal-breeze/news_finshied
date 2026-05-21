#!/usr/bin/env python3
"""
生成AI文章脚本
为reader创建一些AI生成的文章
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.ai_service import EnhancedAIService
from app.services.article_service import ArticleService
from app.models import ArticleStatus
from app.schemas import ContentGenerationRequest, ArticleCreate

def generate_ai_articles():
    """生成AI文章"""
    db: Session = SessionLocal()
    ai_service = EnhancedAIService()
    article_service = ArticleService()
    
    # 文章主题和分类
    article_topics = [
        {"topic": "人工智能在医疗领域的应用", "category": "科技", "keywords": ["人工智能", "医疗", "诊断", "治疗"]},
        {"topic": "2026年全球经济发展趋势", "category": "财经", "keywords": ["经济", "趋势", "全球化", "投资"]},
        {"topic": "新能源汽车市场分析", "category": "汽车", "keywords": ["新能源", "电动汽车", "市场", "技术"]},
        {"topic": "健康生活方式的重要性", "category": "健康", "keywords": ["健康", "生活方式", "运动", "饮食"]},
        {"topic": "教育数字化转型", "category": "教育", "keywords": ["教育", "数字化", "技术", "学习"]},
        {"topic": "太空探索的新进展", "category": "科技", "keywords": ["太空", "探索", "科技", "未来"]},
        {"topic": "全球气候变化应对策略", "category": "环保", "keywords": ["气候变化", "环保", "可持续发展", "政策"]},
        {"topic": "元宇宙的发展与应用", "category": "科技", "keywords": ["元宇宙", "虚拟现实", "数字经济", "技术"]},
        {"topic": "传统文化的现代传承", "category": "文化", "keywords": ["传统文化", "传承", "现代", "文化"]},
        {"topic": "体育产业的发展趋势", "category": "体育", "keywords": ["体育", "产业", "发展", "趋势"]},
    ]
    
    generated_count = 0
    
    try:
        for article_info in article_topics:
            print(f"\n生成文章：{article_info['topic']}")
            
            # 生成内容
            request = ContentGenerationRequest(
                topic=article_info['topic'],
                keywords=article_info['keywords'],
                length="medium",
                style="formal",
                tone="professional",
                audience="大众读者",
                title_count=3
            )
            
            result = ai_service.generate_content(db, request=request)
            
            if result and result.draft_content:
                # 创建文章
                article_in = ArticleCreate(
                    title=result.suggested_titles[0] if result.suggested_titles else article_info['topic'],
                    content=result.draft_content,
                    category=article_info['category'],
                    tags=article_info['keywords'],
                    status=ArticleStatus.PUBLISHED,
                    abstract=result.draft_content[:200] + "...",
                    author="AI助手"
                )
                
                article = article_service.create_article(
                    db, 
                    article_in=article_in,
                    creator_user_id=1  # 默认用户ID
                )
                
                print(f"✓ 文章创建成功：{article.title}")
                generated_count += 1
            else:
                print(f"✗ 生成失败：{article_info['topic']}")
                
    except Exception as e:
        print(f"错误：{e}")
        db.rollback()
    finally:
        db.close()
    
    print(f"\n生成完成！成功生成 {generated_count} 篇文章")

if __name__ == "__main__":
    generate_ai_articles()
