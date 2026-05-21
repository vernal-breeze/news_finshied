"""站内消息模型"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from datetime import datetime, timezone

from app.models.base import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, default="")
    sender = Column(String(50), default="system")
    type = Column(String(30), default="system")  # system, notification, reply
    is_read = Column(Boolean, default=False)

    # 关联
    related_id = Column(Integer, nullable=True)
    related_type = Column(String(50), default="")
    recipient_id = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    read_at = Column(DateTime, nullable=True)
