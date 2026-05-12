"""
路由模块统一导出
"""
from app.routers.auth import router as auth_router
from app.routers.messages import router as messages_router
from app.routers.health import router as health_router
from app.routers.clues import router as clues_router
from app.routers.topics import router as topics_router
from app.routers.articles import router as articles_router
from app.routers.content import router as content_router
from app.routers.reviews import router as reviews_router
from app.routers.reviews import article_reviews_router as article_reviews_router
from app.routers.feedback import router as feedback_router
from app.routers.public import router as public_router
from app.routers.public import upload_router as upload_router
from app.routers.collection import router as collection_router
from app.routers.stats import router as stats_router
from app.routers.text import router as text_router
from app.routers.ai import router as ai_router
from app.routers.users import router as users_router
from app.routers.settings import router as settings_router

__all__ = [
    "auth_router",
    "messages_router",
    "health_router",
    "clues_router",
    "topics_router",
    "articles_router",
    "content_router",
    "reviews_router",
    "article_reviews_router",
    "feedback_router",
    "public_router",
    "upload_router",
    "collection_router",
    "stats_router",
    "ai_router",
    "text_router",
    "users_router",
    "settings_router",
]
