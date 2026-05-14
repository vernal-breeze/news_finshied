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
from app.models.feedback import Feedback
from app.models.user import User
from app.routers.auth import get_optional_user

router = APIRouter(prefix="/api/stats", tags=["Stats"])


def _scope_article_query(query, current_user: User | None):
    if current_user and current_user.role in ("reporter", "user"):
        query = query.filter(Article.author_id == current_user.id)
    return query


def _scope_clue_query(query, current_user: User | None):
    if current_user and current_user.role in ("reporter", "user"):
        query = query.filter(Clue.creator_id == current_user.id)
    return query


@router.get("/dashboard")
async def get_dashboard(
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    article_query = _scope_article_query(db.query(Article), current_user)
    clue_query = _scope_clue_query(db.query(Clue), current_user)

    total_articles = article_query.count()
    published = article_query.filter(Article.status == "published").count()
    draft = article_query.filter(Article.status == "draft").count()
    pending_review = article_query.filter(Article.status == "pending_review").count()
    reviewing = article_query.filter(Article.status == "reviewing").count()
    total_clues = clue_query.count()
    pending_clues = clue_query.filter(Clue.status.in_(["pending", "new", "processing"])).count()
    processed_clues = clue_query.filter(Clue.status.in_(["processed", "verified"])).count()
    total_topics = db.query(Topic).count()
    active_topics = db.query(Topic).filter(Topic.status.in_(["draft", "planning", "in_progress", "active", "assigned"])).count()
    total_reviews = db.query(Review).count()
    pending_reviews = db.query(Review).filter(Review.status == "pending").count()
    total_views = article_query.with_entities(func.sum(Article.view_count)).scalar() or 0
    total_likes = article_query.with_entities(func.sum(Article.like_count)).scalar() or 0

    since = datetime.now(timezone.utc) - timedelta(days=7)
    recent_clues = clue_query.filter(Clue.created_at >= since).count()
    recent_articles = article_query.filter(Article.created_at >= since).count()

    categories = (
        _scope_article_query(db.query(Article.category, func.count(Article.id)), current_user)
        .filter(Article.category.isnot(None))
        .group_by(Article.category)
        .all()
    )
    feedback_articles = article_query.filter(Article.status == "published").all()
    feedback_rows = {
        row.article_id: row
        for row in db.query(Feedback).filter(Feedback.article_id.in_([a.id for a in feedback_articles])).all()
    } if feedback_articles else {}
    total_comments = sum((feedback_rows.get(article.id).comment_count or 0) for article in feedback_articles if feedback_rows.get(article.id))
    total_shares = sum((feedback_rows.get(article.id).share_count or 0) for article in feedback_articles if feedback_rows.get(article.id))
    top_articles = []
    for article in feedback_articles:
        feedback = feedback_rows.get(article.id)
        view_count = max(article.view_count or 0, feedback.view_count or 0) if feedback else (article.view_count or 0)
        like_count = max(article.like_count or 0, feedback.like_count or 0) if feedback else (article.like_count or 0)
        comment_count = feedback.comment_count if feedback else 0
        share_count = feedback.share_count if feedback else 0
        engagement_rate = feedback.engagement_rate if feedback else 0
        trending_score = feedback.trending_score if feedback else 0
        top_articles.append(
            {
                "id": article.id,
                "title": article.title,
                "views": view_count,
                "likes": like_count,
                "comments": comment_count,
                "shares": share_count,
                "engagement_rate": engagement_rate,
                "trending_score": trending_score,
            }
        )
    top_articles.sort(key=lambda item: (item["trending_score"], item["views"]), reverse=True)

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
                "total_comments": total_comments,
                "total_shares": total_shares,
                "avg_engagement_rate": round(
                    sum(item["engagement_rate"] for item in top_articles) / len(top_articles), 2
                ) if top_articles else 0,
                "top_articles": top_articles[:5],
            },
        },
    }
