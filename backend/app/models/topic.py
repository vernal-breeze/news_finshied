"""选题模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime, timezone

from app.models.base import Base


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), default="")
    description = Column(Text, default="")
    category = Column(String(50), default="")
    status = Column(String(30), default="draft", index=True)  # draft, active, completed, cancelled

    # 指派
    editor = Column(String(50), default="")
    editor_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # 关联线索
    ref_clue_ids = Column(String(500), default="")

    # 时间
    planned_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
