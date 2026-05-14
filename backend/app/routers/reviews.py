"""审核路由：审核列表、待审队列"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.article import Article
from app.models.review import Review
from app.models.user import User

router = APIRouter(prefix="/api/reviews", tags=["Reviews"])
article_reviews_router = APIRouter(prefix="/api/articles", tags=["Article Reviews"])


class ReviewCreate(BaseModel):
    article_id: int
    reviewer: Optional[str] = None
    level: Optional[str] = "first"
    result: Optional[str] = None
    status: Optional[str] = None
    comment: Optional[str] = None


def _resolve_review_status(result: Optional[str], status: Optional[str]) -> str:
    raw = (result or status or "pending").strip().lower()
    mapping = {
        "approve": "approved",
        "approved": "approved",
        "reject": "rejected",
        "rejected": "rejected",
        "return": "need_revision",
        "need_revision": "need_revision",
        "pending": "pending",
    }
    return mapping.get(raw, "pending")


def _status_to_article_status(review_status: str) -> str:
    mapping = {
        "approved": "published",   # 审核通过直接发布
        "rejected": "rejected",
        "need_revision": "draft",
        "pending": "reviewing",
    }
    return mapping.get(review_status, "reviewing")


def _resolve_reviewer_id(db: Session, reviewer: Optional[str]) -> Optional[int]:
    name = (reviewer or "").strip()
    if not name:
        return None
    user = db.query(User).filter(User.username == name).first()
    if user:
        return user.id
    user = db.query(User).filter(User.nickname == name).first()
    if user:
        return user.id
    user = db.query(User).filter(User.full_name == name).first()
    if user:
        return user.id
    return None


def _serialize_review(db: Session, review: Review) -> dict:
    reviewer_name = "审核员"
    if review.reviewer_id:
        user = db.query(User).filter(User.id == review.reviewer_id).first()
        if user:
            reviewer_name = user.nickname or user.full_name or user.username or reviewer_name
    return {
        "id": review.id,
        "article_id": review.article_id,
        "reviewer": reviewer_name,
        "reviewer_id": review.reviewer_id,
        "level": "first",
        "result": review.status or "pending",
        "status": review.status or "pending",
        "comment": review.comment or "",
        "created_at": review.created_at.isoformat() if review.created_at else "",
    }


def _serialize_pending_article(db: Session, article: Article, latest_review: Optional[Review] = None) -> dict:
    author_name = "未署名"
    if article.author_id:
        user = db.query(User).filter(User.id == article.author_id).first()
        if user:
            author_name = user.nickname or user.full_name or user.username or author_name
    title = (article.title or "").strip() or f"稿件 #{article.id}"
    content = article.content or ""
    tags = [t.strip() for t in (article.tags or "").split(",") if t.strip()]
    submitted_at = latest_review.created_at if latest_review and latest_review.created_at else (article.updated_at or article.created_at)
    return {
        "id": article.id,
        "title": title,
        "author": author_name,
        "category": article.category or "未分类",
        "status": article.status or "pending_review",
        "review_level": 1,
        "word_count": len(content),
        "created_at": article.created_at.isoformat() if article.created_at else "",
        "submitted_at": submitted_at.isoformat() if submitted_at else "",
        "version": 1,
        "content": content,
        "abstract": article.summary or "",
        "tags": tags,
    }


@router.get("")
async def list_reviews(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Review)
    if status:
        q = q.filter(Review.status == status)
    total = q.count()
    items = q.order_by(desc(Review.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 200,
        "data": [_serialize_review(db, item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/pending")
async def get_pending(db: Session = Depends(get_db)):
    candidate_articles = (
        db.query(Article)
        .filter(Article.status.in_(["pending_review", "reviewing"]))
        .order_by(desc(Article.updated_at))
        .all()
    )
    latest_reviews = {}
    for row in db.query(Review).order_by(desc(Review.created_at)).all():
        if row.article_id is None:
            continue
        latest_reviews.setdefault(row.article_id, row)

    if not candidate_articles:
        pending_article_ids = [r.article_id for r in db.query(Review).filter(Review.status == "pending").all() if r.article_id]
        if pending_article_ids:
            candidate_articles = db.query(Article).filter(Article.id.in_(pending_article_ids)).order_by(desc(Article.updated_at)).all()

    payload = [_serialize_pending_article(db, article, latest_reviews.get(article.id)) for article in candidate_articles]
    return {"code": 200, "data": payload, "total": len(payload)}


@router.post("")
async def create_review(body: ReviewCreate, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == body.article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    review_status = _resolve_review_status(body.result, body.status)
    review = Review(
        article_id=body.article_id,
        reviewer_id=_resolve_reviewer_id(db, body.reviewer),
        comment=body.comment,
        status=review_status,
    )
    db.add(review)
    article.status = _status_to_article_status(review_status)
    db.commit()
    db.refresh(review)
    return {"code": 200, "message": "审核提交成功", "data": _serialize_review(db, review)}


@article_reviews_router.get("/{article_id}/reviews")
async def get_reviews_by_article(article_id: int, db: Session = Depends(get_db)):
    reviews = db.query(Review).filter(Review.article_id == article_id).order_by(desc(Review.created_at)).all()
    return {"code": 200, "data": [_serialize_review(db, row) for row in reviews]}
