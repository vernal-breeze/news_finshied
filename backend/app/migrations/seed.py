"""
数据库种子数据
创建默认用户和角色
"""
from app.database import SessionLocal
from app.models import User, UserRole, get_password_hash
from app.core.logging_config import get_logger


DEFAULT_USERS = [
    {"username": "admin", "password": "admin123", "role": "USER", "nickname": "管理员", "email": "admin@news.local"},
    {"username": "reporter", "password": "reporter123", "role": "USER", "nickname": "记者", "email": "reporter@news.local"},
    {"username": "editor", "password": "editor123", "role": "USER", "nickname": "编辑", "email": "editor@news.local"},
    {"username": "reviewer", "password": "reviewer123", "role": "REVIEWER", "nickname": "审核员", "email": "reviewer@news.local"},
]


def init_default_users() -> None:
    """初始化默认用户（仅当不存在时创建）"""
    db = SessionLocal()
    try:
        for user_data in DEFAULT_USERS:
            existing = db.query(User).filter(User.username == user_data["username"]).first()
            if not existing:
                user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    password_hash=get_password_hash(user_data["password"]),
                    role=user_data["role"],
                    nickname=user_data["nickname"],
                )
                db.add(user)
        db.commit()
        get_logger(__name__).info("Default users initialized")
    except Exception as exc:
        db.rollback()
        get_logger(__name__).warning("Seed skipped: %s", exc)
    finally:
        db.close()
