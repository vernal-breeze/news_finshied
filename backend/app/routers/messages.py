"""消息路由：读者端消息"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.message import Message

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
    }


@router.get("")
async def list_messages(
    page: int = 1,
    page_size: int = 20,
    is_read: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Message)
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
async def unread_count(db: Session = Depends(get_db)):
    count = db.query(Message).filter(Message.is_read.is_(False)).count()
    return {"code": 200, "data": count}


@router.put("/{message_id}/read")
async def mark_read(message_id: int, db: Session = Depends(get_db)):
    item = db.query(Message).filter(Message.id == message_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="消息不存在")
    item.is_read = True
    item.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return {"code": 200, "message": "已标记已读", "data": _serialize_message(item)}


@router.post("/{message_id}/reply")
async def reply_message(message_id: int, body: ReplyMessageRequest, db: Session = Depends(get_db)):
    original = db.query(Message).filter(Message.id == message_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="消息不存在")

    original.is_read = True
    original.read_at = datetime.now(timezone.utc)

    reply = Message(
        content=body.content.strip(),
        sender="reader",
        type="interaction",
        is_read=True,
        related_id=original.id,
        related_type="message",
    )
    db.add(reply)
    db.commit()
    db.refresh(reply)
    return {"code": 200, "message": "回复成功", "data": _serialize_message(reply)}
