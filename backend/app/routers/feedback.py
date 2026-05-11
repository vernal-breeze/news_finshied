"""反馈路由：反馈统计、趋势、记录互动"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.feedback import Feedback
from app.models.article import Article

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])


def _feedback_summary(article: Article, feedback: Optional[Feedback] = None) -> dict:
    view_count = max(article.view_count or 0, feedback.view_count or 0) if feedback else (article.view_count or 0)
    like_count = max(article.like_count or 0, feedback.like_count or 0) if feedback else (article.like_count or 0)
    comment_count = feedback.comment_count if feedback else 0
    share_count = feedback.share_count if feedback else 0
    engagement_rate = feedback.engagement_rate if feedback else 0
    trending_score = feedback.trending_score if feedback else 0
    return {
        "id": feedback.id if feedback else article.id,
        "article_id": article.id,
        "view_count": view_count,
        "like_count": like_count,
        "comment_count": comment_count,
        "share_count": share_count,
        "engagement_rate": engagement_rate,
        "trending_score": trending_score,
        "created_at": feedback.created_at.isoformat() if feedback and feedback.created_at else article.created_at.isoformat() if article.created_at else "",
        "updated_at": feedback.updated_at.isoformat() if feedback and feedback.updated_at else article.updated_at.isoformat() if article.updated_at else "",
    }


def _upsert_feedback(db: Session, article: Article) -> Feedback:
    feedback = db.query(Feedback).filter(Feedback.article_id == article.id).first()
    if not feedback:
        feedback = Feedback(article_id=article.id)
        db.add(feedback)
    feedback.view_count = max(article.view_count or 0, feedback.view_count or 0)
    feedback.like_count = max(article.like_count or 0, feedback.like_count or 0)
    feedback.engagement_rate = round(((feedback.like_count or 0) + (feedback.comment_count or 0) + (feedback.share_count or 0)) / max(feedback.view_count or 1, 1) * 100, 2)
    feedback.trending_score = round(min(100.0, (feedback.view_count or 0) * 0.5 + (feedback.like_count or 0) * 3 + (feedback.comment_count or 0) * 4 + (feedback.share_count or 0) * 5), 2)
    article.view_count = feedback.view_count
    article.like_count = feedback.like_count
    return feedback


@router.get("/stats")
async def get_feedback_stats(days: int = 7, db: Session = Depends(get_db)):
    articles = db.query(Article).all()
    feedback_rows = {row.article_id: row for row in db.query(Feedback).all()}
    enriched = [_feedback_summary(article, feedback_rows.get(article.id)) for article in articles]
    total_views = sum(item["view_count"] for item in enriched)
    total_likes = sum(item["like_count"] for item in enriched)
    total_comments = sum(item["comment_count"] for item in enriched)
    total_shares = sum(item["share_count"] for item in enriched)
    avg_engagement = round(
        sum(item["engagement_rate"] for item in enriched) / len(enriched), 2
    ) if enriched else 0
    top_articles = sorted(enriched, key=lambda item: (item["trending_score"], item["view_count"]), reverse=True)[:5]
    return {
        "code": 200,
        "data": {
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "avg_engagement_rate": avg_engagement,
            "top_articles": [
                {
                    "id": item["article_id"],
                    "title": next((a.title for a in articles if a.id == item["article_id"]), ""),
                    "views": item["view_count"],
                    "trending_score": item["trending_score"],
                }
                for item in top_articles
            ],
            "period_days": days,
        },
    }


@router.get("/trends")
async def get_feedback_trends(days: int = 7, db: Session = Depends(get_db)):
    today = datetime.now(timezone.utc).date()
    start_day = today - timedelta(days=days - 1)
    articles = db.query(Article).all()
    feedback_rows = {row.article_id: row for row in db.query(Feedback).all() if row.article_id is not None}
    buckets = {}
    order = []
    for i in range(days):
        day = (start_day + timedelta(days=i)).isoformat()
        buckets[day] = {"date": day, "views": 0, "likes": 0, "comments": 0}
        order.append(day)

    for article in articles:
        day_source = article.updated_at or article.created_at
        if not day_source:
            continue
        day = day_source.date().isoformat()
        if day < start_day.isoformat() or day > today.isoformat():
            continue
        bucket = buckets.get(day)
        if not bucket:
            continue
        feedback = feedback_rows.get(article.id)
        bucket["views"] += article.view_count or 0
        bucket["likes"] += max(article.like_count or 0, feedback.like_count or 0 if feedback else 0)
        bucket["comments"] += feedback.comment_count if feedback else 0
    return {
        "code": 200,
        "data": {
            "days": days,
            "views": [dict(buckets[day]) for day in order],
            "likes": [dict(buckets[day]) for day in order],
            "comments": [dict(buckets[day]) for day in order],
        },
    }


@router.get("/{article_id}")
async def get_feedback_by_article(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    feedback = db.query(Feedback).filter(Feedback.article_id == article_id).first()
    return {"code": 200, "data": _feedback_summary(article, feedback)}


@router.post("/{article_id}/view")
async def record_view(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    feedback = _upsert_feedback(db, article)
    current_view = max(article.view_count or 0, feedback.view_count or 0) + 1
    article.view_count = current_view
    feedback.view_count = current_view
    _upsert_feedback(db, article)
    db.commit()
    db.refresh(article)
    db.refresh(feedback)
    return {"code": 200, "message": "已记录", "data": _feedback_summary(article, feedback)}


@router.post("/{article_id}/like")
async def record_like(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    feedback = _upsert_feedback(db, article)
    current_like = max(article.like_count or 0, feedback.like_count or 0) + 1
    article.like_count = current_like
    feedback.like_count = current_like
    _upsert_feedback(db, article)
    db.commit()
    db.refresh(article)
    db.refresh(feedback)
    return {"code": 200, "message": "点赞成功", "data": _feedback_summary(article, feedback)}


@router.post("/{article_id}/share")
async def record_share(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    feedback = _upsert_feedback(db, article)
    feedback.share_count = (feedback.share_count or 0) + 1
    _upsert_feedback(db, article)
    db.commit()
    db.refresh(feedback)
    return {"code": 200, "message": "已记录", "data": _feedback_summary(article, feedback)}


@router.post("/{article_id}/comment")
async def record_comment(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    feedback = _upsert_feedback(db, article)
    feedback.comment_count = (feedback.comment_count or 0) + 1
    _upsert_feedback(db, article)
    db.commit()
    db.refresh(feedback)
    return {"code": 200, "message": "已记录", "data": _feedback_summary(article, feedback)}
