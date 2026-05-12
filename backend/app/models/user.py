"""用户模型"""
import hashlib
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.models.base import Base


def _try_bcrypt_hash(password: str) -> str:
    """尝试用 bcrypt 生成哈希，不可用时返回 None"""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except (ImportError, ModuleNotFoundError):
        return None


def get_password_hash(password: str) -> str:
    """获取密码哈希值（优先 bcrypt，不可用时回退 sha256）"""
    bcrypt_hash = _try_bcrypt_hash(password)
    if bcrypt_hash:
        return bcrypt_hash
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码 — 自动检测 bcrypt / sha256 格式"""
    # bcrypt 格式：$2b$ 或 $2a$ 开头
    if hashed_password.startswith("$2"):
        try:
            import bcrypt
            return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
        except (ImportError, ModuleNotFoundError, ValueError):
            return False
    # sha256 格式（legacy）
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50), default="")
    full_name = Column(String(100), default="")
    role = Column(String(20), default="reporter")  # admin, chief_editor, reviewer, editor, reporter
    is_active = Column(Boolean, default=True)
    avatar = Column(String(500), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关系
    articles = relationship("Article", back_populates="author", foreign_keys="Article.author_id")
