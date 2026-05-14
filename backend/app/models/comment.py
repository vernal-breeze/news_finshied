"""评论模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime, timezone

from app.models.base import Base


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, nullable=False, index=True)
    parent_id = Column(Integer, nullable=True, index=True)  # 父评论ID，支持嵌套回复
    author = Column(String(100), default="匿名")
    reply_to_name = Column(String(100), nullable=True)  # 被回复者名称
    content = Column(Text, nullable=False)
    is_approved = Column(Boolean, default=True)  # 默认无需审核
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
