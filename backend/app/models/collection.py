"""采集任务模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime, timezone

from app.models.base import Base


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), default="")
    keywords = Column(String(500), default="")
    channels = Column(String(200), default="news")  # news, weibo, wechat, etc.
    status = Column(String(30), default="pending")  # pending, running, completed, failed
    result_count = Column(Integer, default=0)
    error_msg = Column(Text, default="")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
