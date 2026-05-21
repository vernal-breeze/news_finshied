"""审核记录模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.models.base import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    reviewer = Column(String(50), default="")
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    level = Column(String(20), default="first")  # first, second, final
    result = Column(String(30), default="pending")  # pending, approved, rejected, revision
    status = Column(String(30), default="pending")
    comment = Column(Text, default="")
    score = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关系
    article = relationship("Article", back_populates="reviews")
