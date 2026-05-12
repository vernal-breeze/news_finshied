"""文章路由：文章 CRUD、版本管理、发布、提交审核"""
from typing import Optional, List, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.article import Article

router = APIRouter(prefix="/api/articles", tags=["Articles"])


def _tags_to_str(tags: Union[str, List[str], None]) -> Optional[str]:
    """将 tags 统一转为逗号分隔字符串存储"""
    if tags is None:
        return None
    if isinstance(tags, list):
        return ",".join(t.strip() for t in tags if t.strip())
    if isinstance(tags, str):
        return tags
    return str(tags)


def _tags_to_list(tags: Optional[str]) -> List[str]:
    """将逗号分隔字符串转为列表"""
    if not tags:
        return []
    return [t.strip() for t in tags.split(",") if t.strip()]


def _format_article(article: Article, db: Session = None) -> dict:
    """将 Article ORM 转为前端友好的 dict"""
    author_name = ""
    if db and article.author_id:
        from app.models.user import User
        user = db.query(User).filter(User.id == article.author_id).first()
        if user:
            author_name = user.nickname or user.full_name or user.username
    d = {
        "id": article.id,
        "title": article.title,
        "content": article.content,
        "summary": article.summary or "",
        "abstract": article.summary or "",
        "cover_image": article.cover_image or f"https://picsum.photos/800/400?random={article.id}",
        "status": article.status,
        "category": article.category or "",
        "tags": _tags_to_list(article.tags),
        "tags_str": article.tags or "",
        "author_id": article.author_id,
        "author": author_name,
        "editor_id": getattr(article, 'editor_id', None),
        "clue_id": article.clue_id,
        "topic_id": article.topic_id,
        "like_count": article.like_count or 0,
        "view_count": article.view_count or 0,
        "created_at": article.created_at.isoformat() if article.created_at else "",
        "updated_at": article.updated_at.isoformat() if article.updated_at else "",
        "published_at": article.updated_at.isoformat() if article.updated_at else "",
    }
    return d


class ArticleCreate(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[Union[str, List[str]]] = None
    clue_id: Optional[int] = None
    topic_id: Optional[int] = None
    author: Optional[str] = None

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v):
        return _tags_to_str(v)


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[Union[str, List[str]]] = None
    status: Optional[str] = None
    clue_id: Optional[int] = None
    topic_id: Optional[int] = None
    author_id: Optional[int] = None

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v):
        return _tags_to_str(v)


@router.get("")
async def list_articles(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Article)
    if status:
        q = q.filter(Article.status == status)
    if category:
        q = q.filter(Article.category == category)
    if search:
        like = f"%{search}%"
        q = q.filter(Article.title.ilike(like) | Article.content.ilike(like))
    total = q.count()
    items = q.order_by(desc(Article.updated_at)).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 200,
        "data": [_format_article(a, db) for a in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{article_id}")
async def get_article(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return {"code": 200, "data": _format_article(article, db)}


@router.post("")
async def create_article(body: ArticleCreate, db: Session = Depends(get_db)):
    article = Article(
        title=body.title,
        content=body.content,
        summary=body.summary,
        category=body.category,
        tags=body.tags,
        status="draft",
        clue_id=body.clue_id,
        topic_id=body.topic_id,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return {"code": 200, "message": "创建成功", "data": _format_article(article, db)}


@router.put("/{article_id}")
async def update_article(article_id: int, body: ArticleUpdate, db: Session = Depends(get_db)):
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise HTTPException(status_code=404, detail="文章不存在")
        payload = body.model_dump(exclude_none=True)
        if "title" in payload and payload["title"] is None:
            payload.pop("title")
        for k, v in payload.items():
            setattr(article, k, v)
        db.commit()
        db.refresh(article)
        return {"code": 200, "message": "更新成功", "data": _format_article(article, db)}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[update_article] ERROR: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"文章更新失败: {str(e)}")


@router.delete("/{article_id}")
async def delete_article(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    db.delete(article)
    db.commit()
    return {"code": 200, "message": "删除成功"}


@router.post("/{article_id}/publish")
async def publish_article(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    article.status = "published"
    db.commit()
    return {"code": 200, "message": "发布成功"}


@router.post("/{article_id}/submit-review")
async def submit_review(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    article.status = "pending_review"
    db.commit()
    return {"code": 200, "message": "已提交审核"}
