"""数据模型统一导出"""
from app.models.base import Base
from app.models.user import User, get_password_hash, verify_password
from app.models.article import Article, ArticleStatus
from app.models.clue import Clue, NewsClue
from app.models.review import Review
from app.models.feedback import Feedback
from app.models.message import Message
from app.models.topic import Topic
from app.models.collection import Collection
from app.models.comment import Comment

# 简单的 UserRole 别名
class UserRole:
    ADMIN = "admin"
    CHIEF_EDITOR = "chief_editor"
    REVIEWER = "reviewer"
    EDITOR = "editor"
    REPORTER = "reporter"
    USER = "reporter"

__all__ = [
    "Base",
    "User",
    "UserRole",
    "get_password_hash",
    "verify_password",
    "Article",
    "ArticleStatus",
    "Clue",
    "NewsClue",
    "Review",
    "Feedback",
    "Message",
    "Topic",
    "Collection",
    "Comment",
]
