"""统计路由：仪表盘统计数据"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.article import Article
from app.models.clue import Clue
from app.models.review import Review
from app.models.topic import Topic

router = APIRouter(prefix="/api/stats", tags=["Stats"])


@router.get("/dashboard")
async def get_dashboard(db: Session = Depends(get_db)):
    total_articles = db.query(Article).count()
    published = db.query(Article).filter(Article.status == "published").count()
    draft = db.query(Article).filter(Article.status == "draft").count()
    pending_review = db.query(Article).filter(Article.status == "pending_review").count()
    reviewing = db.query(Article).filter(Article.status == "reviewing").count()
    total_clues = db.query(Clue).count()
    pending_clues = db.query(Clue).filter(Clue.status.in_(["pending", "new", "processing"])).count()
    processed_clues = db.query(Clue).filter(Clue.status.in_(["processed", "verified"])).count()
    total_topics = db.query(Topic).count()
    active_topics = db.query(Topic).filter(Topic.status.in_(["draft", "planning", "in_progress", "active", "assigned"])).count()
    total_reviews = db.query(Review).count()
    pending_reviews = db.query(Review).filter(Review.status == "pending").count()
    total_views = db.query(func.sum(Article.view_count)).scalar() or 0
    total_likes = db.query(func.sum(Article.like_count)).scalar() or 0

    since = datetime.now(timezone.utc) - timedelta(days=7)
    recent_clues = db.query(Clue).filter(Clue.created_at >= since).count()
    recent_articles = db.query(Article).filter(Article.created_at >= since).count()

    categories = (
        db.query(Article.category, func.count(Article.id))
        .filter(Article.category.isnot(None))
        .group_by(Article.category)
        .all()
    )

    return {
        "code": 200,
        "data": {
            "clues": {
                "total": total_clues,
                "pending": pending_clues,
                "processed": processed_clues,
            },
            "articles": {
                "total": total_articles,
                "by_status": {
                    "draft": draft,
                    "pending_review": pending_review,
                    "reviewing": reviewing,
                    "published": published,
                },
                "recent_7_days": recent_articles,
            },
            "recent_activity": {
                "new_clues_7days": recent_clues,
                "new_articles_7days": recent_articles,
            },
            "categories": [
                {"category": category or "未分类", "count": count}
                for category, count in categories
            ],
            "topics": {
                "total": total_topics,
                "active": active_topics,
            },
            "reviews": {
                "total": total_reviews,
                "pending": pending_reviews,
            },
            "feedback": {
                "total_views": total_views,
                "total_likes": total_likes,
            },
        },
    }
