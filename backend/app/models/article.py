"""文章模型"""
import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.models.base import Base


class ArticleStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, default="")
    summary = Column(Text, default="")
    status = Column(String(30), default=ArticleStatus.DRAFT.value, index=True)
    cover_image = Column(String(500), default="")
    tags = Column(String(500), default="")
    category = Column(String(50), default="")

    # 统计
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)

    # 质量评估
    quality_score = Column(Float, default=0.0)
    ai_score = Column(Float, default=0.0)

    # 下线/驳回
    reject_reason = Column(String(1000), default="")

    # 关联
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    clue_id = Column(Integer, ForeignKey("clues.id"), nullable=True)

    # 时间
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    published_at = Column(DateTime, nullable=True)

    # 关系
    author = relationship("User", back_populates="articles", foreign_keys=[author_id])
    reviews = relationship("Review", back_populates="article", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="article", uselist=False, cascade="all, delete-orphan")
