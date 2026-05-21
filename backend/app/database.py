"""数据库连接 - 支持 SQLite / MySQL 双模式"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import get_settings
from app.models.base import Base

settings = get_settings()


def _build_engine():
    """根据 DATABASE_URL 自动选择引擎配置"""
    url = settings.DATABASE_URL

    if url.startswith("sqlite"):
        # SQLite 模式
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
    else:
        # MySQL 模式（带连接池）
        return create_engine(
            url,
            pool_size=10,           # 常驻连接数
            max_overflow=20,        # 峰值溢出连接
            pool_pre_ping=True,     # 连接前 ping 检测（防断连）
            pool_recycle=3600,      # 1 小时回收空闲连接
            echo=False,
        )


engine = _build_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI 依赖：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
