"""公共路由：读者端文章、评论"""
from pathlib import Path
from uuid import uuid4
from typing import Optional

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.article import Article
from app.models.user import User
from app.models.comment import Comment
from app.models.message import Message
from app.models.feedback import Feedback
from app.routers.auth import get_optional_user

router = APIRouter(prefix="/api/public", tags=["Public"])
upload_router = APIRouter(prefix="/api/upload", tags=["Upload"])
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _tags_to_list(tags: Optional[str]) -> list:
    if not tags:
        return []
    return [t.strip() for t in tags.split(",") if t.strip()]


def _format_article(a: Article, db: Session = None) -> dict:
    """将 Article ORM 转为前端友好格式"""
    author_name = ""
    if db and a.author_id:
        user = db.query(User).filter(User.id == a.author_id).first()
        if user:
            author_name = user.nickname or user.full_name or user.username
    return {
        "id": a.id,
        "title": a.title,
        "content": a.content,
        "summary": a.summary or "",
        "abstract": a.summary or "",
        "cover_image": a.cover_image or f"https://picsum.photos/800/400?random={a.id}",
        "status": a.status,
        "category": a.category or "",
        "tags": _tags_to_list(a.tags),
        "author_id": a.author_id,
        "author": author_name,
        "like_count": a.like_count or 0,
        "view_count": a.view_count or 0,
        "created_at": a.created_at.isoformat() if a.created_at else "",
        "updated_at": a.updated_at.isoformat() if a.updated_at else "",
        "published_at": a.updated_at.isoformat() if a.updated_at else "",
    }


def _upsert_feedback(db: Session, article: Article) -> Feedback:
    feedback = db.query(Feedback).filter(Feedback.article_id == article.id).first()
    if not feedback:
        feedback = Feedback(article_id=article.id)
        db.add(feedback)
        db.flush()
    feedback.view_count = max(article.view_count or 0, feedback.view_count or 0)
    feedback.like_count = max(article.like_count or 0, feedback.like_count or 0)
    feedback.engagement_rate = round(
        ((feedback.like_count or 0) + (feedback.comment_count or 0) + (feedback.share_count or 0))
        / max(feedback.view_count or 1, 1)
        * 100,
        2,
    )
    feedback.trending_score = round(
        min(
            100.0,
            (feedback.view_count or 0) * 0.5
            + (feedback.like_count or 0) * 3
            + (feedback.comment_count or 0) * 4
            + (feedback.share_count or 0) * 5,
        ),
        2,
    )
    article.view_count = feedback.view_count
    article.like_count = feedback.like_count
    return feedback


@router.get("/articles")
async def list_public_articles(
    page: int = 1,
    page_size: int = 10,
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Article).filter(Article.status == "published")
    if category:
        q = q.filter(Article.category == category)
    if search:
        like = f"%{search}%"
        q = q.filter(Article.title.ilike(like))
    total = q.count()
    items = q.order_by(desc(Article.updated_at)).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 200,
        "data": [_format_article(a, db) for a in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/articles/{article_id}")
async def get_public_article(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id, Article.status == "published").first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在或未发布")
    feedback = _upsert_feedback(db, article)
    current_view = max(article.view_count or 0, feedback.view_count or 0) + 1
    article.view_count = current_view
    feedback.view_count = current_view
    _upsert_feedback(db, article)
    db.commit()
    db.refresh(article)
    return {"code": 200, "data": _format_article(article, db)}


@router.get("/articles/{article_id}/comments")
async def list_comments(article_id: int, db: Session = Depends(get_db)):
    comments = (
        db.query(Comment)
        .filter(Comment.article_id == article_id, Comment.is_approved == True)
        .order_by(desc(Comment.created_at))
        .all()
    )
    data = [
        {
            "id": c.id,
            "article_id": c.article_id,
            "parent_id": c.parent_id,
            "author_name": c.author,
            "reply_to_name": c.reply_to_name,
            "content": c.content,
            "created_at": c.created_at.isoformat() if c.created_at else "",
        }
        for c in comments
    ]
    return {"code": 200, "data": data, "total": len(data)}


class CommentCreate(BaseModel):
    content: str
    author_name: Optional[str] = None
    parent_id: Optional[int] = None


@router.post("/articles/{article_id}/comments")
async def post_comment(
    article_id: int,
    body: CommentCreate,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    author_name = (
        (current_user.nickname or current_user.full_name or current_user.username)
        if current_user
        else (body.author_name or "匿名")
    )
    # 如果是回复，获取被回复者名称
    reply_to_name = None
    if body.parent_id:
        parent = db.query(Comment).filter(Comment.id == body.parent_id).first()
        if parent:
            reply_to_name = parent.author
    comment = Comment(
        article_id=article_id,
        parent_id=body.parent_id,
        author=author_name,
        reply_to_name=reply_to_name,
        content=body.content,
    )
    db.add(comment)
    feedback = _upsert_feedback(db, article)
    feedback.comment_count = (feedback.comment_count or 0) + 1
    _upsert_feedback(db, article)

    if article.author_id and (not current_user or current_user.id != article.author_id):
        db.add(
            Message(
                sender=author_name,
                type="notification",
                recipient_id=article.author_id,
                content=f"「{author_name}」在《{article.title}》下发表了评论：{body.content[:100]}",
                related_type="article",
                related_id=article.id,
            )
        )

    db.commit()
    db.refresh(comment)
    return {
        "code": 200,
        "message": "评论成功",
        "data": {
            "id": comment.id,
            "article_id": comment.article_id,
            "parent_id": comment.parent_id,
            "author_name": comment.author,
            "reply_to_name": comment.reply_to_name,
            "content": comment.content,
            "created_at": comment.created_at.isoformat() if comment.created_at else "",
        },
    }


@upload_router.post("/image")
async def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    suffix = Path(file.filename or "").suffix.lower()
    safe_suffix = suffix if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"} else ""
    filename = f"{uuid4().hex}{safe_suffix}"
    target = UPLOAD_DIR / filename

    async with aiofiles.open(target, "wb") as out:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="上传文件为空")
        await out.write(content)

    return {
        "code": 200,
        "message": "上传成功",
        "data": {
            "url": f"/uploads/{filename}",
            "filename": filename,
            "content_type": file.content_type,
        },
    }
