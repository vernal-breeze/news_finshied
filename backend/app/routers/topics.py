"""选题路由：选题 CRUD、AI 分析、指派等"""
from datetime import datetime
import json
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.topic import Topic
from app.models.article import Article

router = APIRouter(prefix="/api/topics", tags=["Topics"])


class TopicCreate(BaseModel):
    title: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    editor: Optional[str] = None
    planned_date: Optional[datetime] = None
    status: Optional[str] = None
    ref_clue_ids: Optional[List[int]] = None

    @model_validator(mode="after")
    def validate_title(self):
        if not (self.title or self.name):
            raise ValueError("选题标题不能为空")
        return self


class TopicUpdate(BaseModel):
    title: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    editor: Optional[str] = None
    planned_date: Optional[datetime] = None
    status: Optional[str] = None
    ai_score: Optional[float] = None
    performance_score: Optional[float] = None
    assigned_user_id: Optional[int] = None
    ai_suggestion: Optional[str] = None
    ref_clue_ids: Optional[List[int]] = None


class AssignBody(BaseModel):
    editor: str
    assigned_user_id: Optional[int] = None


def _parse_ref_clue_ids(raw: Optional[str]) -> List[int]:
    if not raw:
        return []
    try:
      parsed = json.loads(raw)
      if isinstance(parsed, list):
          return [int(x) for x in parsed if isinstance(x, (int, float, str)) and str(x).isdigit()]
    except Exception:
        pass
    try:
        return [int(x.strip()) for x in raw.split(",") if str(x).strip().isdigit()]
    except Exception:
        return []


def _serialize_topic(topic: Topic) -> dict:
    status_map = {
        "active": "planning",
        "assigned": "in_progress",
        "draft": "draft",
        "planning": "planning",
        "in_progress": "in_progress",
        "completed": "completed",
        "cancelled": "cancelled",
    }
    return {
        "id": topic.id,
        "title": topic.name,
        "name": topic.name,
        "description": topic.description or "",
        "category": topic.category or "",
        "editor": topic.editor or "",
        "planned_date": topic.planned_date.isoformat() if topic.planned_date else None,
        "status": status_map.get(topic.status or "", topic.status or "draft"),
        "ref_clue_ids": _parse_ref_clue_ids(topic.ref_clue_ids),
        "ai_score": topic.ai_score,
        "ai_suggestion": topic.ai_suggestion or "",
        "assigned_user_id": topic.assigned_user_id,
        "performance_score": topic.performance_score,
        "creator_id": None,
        "created_at": topic.created_at.isoformat() if topic.created_at else "",
        "updated_at": topic.updated_at.isoformat() if getattr(topic, "updated_at", None) else "",
    }


def _serialize_article(article: Article) -> dict:
    return {
        "id": article.id,
        "title": article.title,
        "content": article.content,
        "summary": article.summary or "",
        "abstract": article.summary or "",
        "cover_image": article.cover_image or f"https://picsum.photos/800/400?random={article.id}",
        "status": article.status,
        "category": article.category or "",
        "tags": [t.strip() for t in (article.tags or "").split(",") if t.strip()],
        "author_id": article.author_id,
        "editor_id": article.editor_id,
        "clue_id": article.clue_id,
        "topic_id": article.topic_id,
        "author": "",
        "like_count": article.like_count or 0,
        "view_count": article.view_count or 0,
        "created_at": article.created_at.isoformat() if article.created_at else "",
        "updated_at": article.updated_at.isoformat() if article.updated_at else "",
        "published_at": article.updated_at.isoformat() if article.updated_at else "",
    }


@router.get("")
async def list_topics(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Topic)
    if status:
        q = q.filter(Topic.status == status)
    if search:
        q = q.filter(Topic.name.ilike(f"%{search}%") | Topic.description.ilike(f"%{search}%"))
    total = q.count()
    items = q.order_by(desc(Topic.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return {"code": 200, "data": [_serialize_topic(item) for item in items], "total": total, "page": page, "page_size": page_size}


@router.get("/{topic_id}")
async def get_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="选题不存在")
    return {"code": 200, "data": _serialize_topic(topic)}


@router.post("")
async def create_topic(body: TopicCreate, db: Session = Depends(get_db)):
    topic = Topic(
        name=body.title or body.name,
        description=body.description,
        category=body.category,
        editor=body.editor,
        planned_date=body.planned_date,
        status=body.status or "draft",
        ref_clue_ids=json.dumps(body.ref_clue_ids or [], ensure_ascii=False),
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return {"code": 200, "message": "创建成功", "data": _serialize_topic(topic)}


@router.put("/{topic_id}")
async def update_topic(topic_id: int, body: TopicUpdate, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="选题不存在")

    payload = body.model_dump(exclude_none=True)
    if "title" in payload:
        payload["name"] = payload.pop("title")
    if "ref_clue_ids" in payload:
        payload["ref_clue_ids"] = json.dumps(payload["ref_clue_ids"] or [], ensure_ascii=False)
    for k, v in payload.items():
        setattr(topic, k, v)
    db.commit()
    db.refresh(topic)
    return {"code": 200, "message": "更新成功", "data": _serialize_topic(topic)}


@router.delete("/{topic_id}")
async def delete_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="选题不存在")
    db.delete(topic)
    db.commit()
    return {"code": 200, "message": "删除成功"}


@router.post("/{topic_id}/ai-analyze")
async def ai_analyze_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="选题不存在")

    title = topic.name or "未命名选题"
    ai_score = min(9.5, max(5.0, (len(title) % 10) + 0.5))
    suggestions = [
        f"从{title}角度出发，深度分析事件背景",
        "采访关键人物获取一手信息",
        "关注主流媒体对该选题的报道角度",
    ]
    topic.ai_score = ai_score
    topic.ai_suggestion = "\n".join(suggestions)
    db.commit()
    db.refresh(topic)
    return {
        "code": 200,
        "data": {
            "score": ai_score,
            "suggestion": topic.ai_suggestion,
            "suggestions": suggestions,
        },
    }


@router.post("/{topic_id}/assign")
async def assign_topic(topic_id: int, body: AssignBody, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="选题不存在")
    topic.editor = body.editor
    topic.assigned_user_id = body.assigned_user_id
    topic.status = "in_progress"
    db.commit()
    db.refresh(topic)
    return {"code": 200, "message": f"已指派给 {body.editor}", "data": _serialize_topic(topic)}


@router.post("/{topic_id}/sync-feedback")
async def sync_feedback(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="选题不存在")
    articles = db.query(Article).filter(Article.topic_id == topic_id).all()
    if not articles:
        topic.performance_score = 0
        db.commit()
        return {"code": 200, "message": "反馈同步完成", "data": _serialize_topic(topic)}
    avg_views = sum(a.view_count or 0 for a in articles) / len(articles)
    avg_likes = sum(a.like_count or 0 for a in articles) / len(articles)
    topic.performance_score = round(min(10.0, (avg_views / 20.0) + (avg_likes / 10.0)), 2)
    db.commit()
    db.refresh(topic)
    return {"code": 200, "message": "反馈同步完成", "data": _serialize_topic(topic)}


@router.get("/{topic_id}/articles")
async def get_topic_articles(topic_id: int, db: Session = Depends(get_db)):
    items = db.query(Article).filter(Article.topic_id == topic_id).order_by(desc(Article.updated_at)).all()
    return {"code": 200, "data": [_serialize_article(item) for item in items], "total": len(items)}


@router.get("/{topic_id}/available-articles")
async def get_available_articles(
    topic_id: int,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Article).filter((Article.topic_id.is_(None)) | (Article.topic_id == topic_id))
    if search:
        q = q.filter(Article.title.ilike(f"%{search}%"))
    total = q.count()
    items = q.order_by(desc(Article.updated_at)).offset((page - 1) * page_size).limit(page_size).all()
    return {"code": 200, "data": [_serialize_article(item) for item in items], "total": total}


@router.post("/{topic_id}/articles")
async def link_article(topic_id: int, body: dict, db: Session = Depends(get_db)):
    article_id = body.get("article_id")
    if not article_id:
        raise HTTPException(status_code=400, detail="缺少 article_id")
    article = db.query(Article).filter(Article.id == int(article_id)).first()
    if not article:
        raise HTTPException(status_code=404, detail="稿件不存在")
    article.topic_id = topic_id
    db.commit()
    return {"code": 200, "message": "关联成功", "data": _serialize_article(article)}


@router.delete("/{topic_id}/articles/{article_id}")
async def unlink_article(topic_id: int, article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id, Article.topic_id == topic_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="稿件不存在")
    article.topic_id = None
    db.commit()
    return {"code": 200, "message": "取消关联成功", "data": _serialize_article(article)}
