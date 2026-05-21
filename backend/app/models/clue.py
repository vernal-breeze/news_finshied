"""线索模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from datetime import datetime, timezone

from app.models.base import Base


class Clue(Base):
    __tablename__ = "clues"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, default="")
    source = Column(String(200), default="")
    source_url = Column(String(500), default="")
    keywords = Column(String(500), default="")
    status = Column(String(30), default="pending", index=True)  # pending, processing, converted, discarded

    # 评分
    news_value_score = Column(Float, default=0.0)
    propagation_potential = Column(Float, default=0.0)

    # 收集由
    collected_by = Column(String(50), default="system")
    # 创建者（投稿端按用户隔离）
    creator_id = Column(Integer, nullable=True, index=True)

    # 新闻分类（如：科技、经济、社会等）
    category = Column(String(50), default="")
    channel = Column(String(50), default="")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime, nullable=True)


# 别名，兼容旧代码
NewsClue = Clue
