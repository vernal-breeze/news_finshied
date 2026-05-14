"""消息路由：读者端消息"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.article import Article
from app.models.message import Message
from app.models.user import User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/reader/messages", tags=["Messages"])


class ReplyMessageRequest(BaseModel):
    content: str


def _serialize_message(item: Message) -> dict:
    return {
        "id": item.id,
        "content": item.content,
        "sender": item.sender or "",
        "type": item.type or "system",
        "is_read": bool(item.is_read),
        "created_at": item.created_at.isoformat() if item.created_at else "",
        "read_at": item.read_at.isoformat() if item.read_at else None,
        "related_id": item.related_id,
        "related_type": item.related_type,
        "recipient_id": item.recipient_id,
    }


def _scoped_message_query(db: Session, current_user: User):
    # 消息中心只返回当前账号自己的定向消息，避免不同用户之间串号。
    return db.query(Message).filter(Message.recipient_id == current_user.id)


def _find_user_id_by_name(db: Session, name: Optional[str]) -> Optional[int]:
    normalized = (name or "").strip()
    if not normalized or normalized.lower() == "system":
        return None

    user = db.query(User).filter(User.username == normalized).first()
    if user:
        return user.id

    user = db.query(User).filter(User.nickname == normalized).first()
    if user:
        return user.id

    user = db.query(User).filter(User.full_name == normalized).first()
    if user:
        return user.id

    return None


def _active_reviewer_ids(db: Session) -> list[int]:
    return [
        user.id
        for user in db.query(User).filter(User.role == "reviewer", User.is_active.is_(True)).all()
        if user.id
    ]


def _resolve_reply_recipient_ids(db: Session, original: Message, current_user: User) -> list[int]:
    recipient_ids: list[int] = []

    sender_user_id = _find_user_id_by_name(db, original.sender)
    if sender_user_id and sender_user_id != current_user.id:
        recipient_ids.append(sender_user_id)

    if recipient_ids:
        return recipient_ids

    if original.related_type == "message" and original.related_id:
        parent = db.query(Message).filter(Message.id == original.related_id).first()
        if parent:
            parent_sender_id = _find_user_id_by_name(db, parent.sender)
            if parent_sender_id and parent_sender_id != current_user.id:
                recipient_ids.append(parent_sender_id)
            elif parent.recipient_id and parent.recipient_id != current_user.id:
                recipient_ids.append(parent.recipient_id)

    if recipient_ids:
        return list(dict.fromkeys(recipient_ids))

    if original.related_type == "article" and original.related_id:
        article = db.query(Article).filter(Article.id == original.related_id).first()
        if article:
            if current_user.role == "reviewer":
                if article.author_id and article.author_id != current_user.id:
                    recipient_ids.append(article.author_id)
            else:
                recipient_ids.extend(
                    reviewer_id
                    for reviewer_id in _active_reviewer_ids(db)
                    if reviewer_id != current_user.id
                )

    return list(dict.fromkeys(recipient_ids))


@router.get("")
async def list_messages(
    page: int = 1,
    page_size: int = 20,
    is_read: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _scoped_message_query(db, current_user)
    if is_read is not None:
        q = q.filter(Message.is_read == is_read)
    total = q.count()
    items = (
        q.order_by(desc(Message.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "code": 200,
        "data": [_serialize_message(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/unread-count")
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = _scoped_message_query(db, current_user).filter(Message.is_read.is_(False)).count()
    return {"code": 200, "data": count}


@router.put("/{message_id}/read")
async def mark_read(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _scoped_message_query(db, current_user).filter(Message.id == message_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="消息不存在")
    item.is_read = True
    item.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return {"code": 200, "message": "已标记已读", "data": _serialize_message(item)}


@router.post("/{message_id}/reply")
async def reply_message(
    message_id: int,
    body: ReplyMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    original = _scoped_message_query(db, current_user).filter(Message.id == message_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="消息不存在")

    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="回复内容不能为空")

    original.is_read = True
    original.read_at = datetime.now(timezone.utc)

    sender_name = current_user.nickname or current_user.full_name or current_user.username
    related_type = original.related_type or "message"
    related_id = original.related_id if original.related_type else original.id
    recipient_ids = _resolve_reply_recipient_ids(db, original, current_user)
    if not recipient_ids:
        raise HTTPException(status_code=400, detail="暂时无法确定回复接收人")

    for recipient_id in recipient_ids:
        db.add(
            Message(
                content=f"{sender_name} 回复：{content}",
                sender=sender_name,
                type="interaction",
                is_read=False,
                related_id=related_id,
                related_type=related_type,
                recipient_id=recipient_id,
            )
        )

    db.commit()
    return {"code": 200, "message": "回复成功"}
