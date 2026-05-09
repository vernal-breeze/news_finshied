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
    article.view_count = (article.view_count or 0) + 1
    db.commit()
    db.refresh(article)
    return {"code": 200, "data": _format_article(article, db)}


@router.get("/articles/{article_id}/comments")
async def list_comments(article_id: int, db: Session = Depends(get_db)):
    return {"code": 200, "data": [], "total": 0}


class CommentCreate(BaseModel):
    content: str
    author_name: Optional[str] = None
    parent_id: Optional[int] = None


@router.post("/articles/{article_id}/comments")
async def post_comment(article_id: int, body: CommentCreate, db: Session = Depends(get_db)):
    return {"code": 200, "message": "评论成功", "data": {"id": 0}}


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
