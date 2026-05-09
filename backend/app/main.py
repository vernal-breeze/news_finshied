"""FastAPI 应用入口"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.database import engine, Base
from app.models import *  # 确保所有模型被导入以便 create_all
from app.routers import (
    auth_router, health_router, clues_router, topics_router,
    articles_router, content_router, reviews_router, article_reviews_router,
    feedback_router, public_router, upload_router, messages_router,
    collection_router, stats_router, text_router, ai_router,
)

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    version="1.0.0",
)

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    """启动时创建数据库表"""
    Base.metadata.create_all(bind=engine)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": str(exc)},
    )


# 注册路由
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(clues_router)
app.include_router(topics_router)
app.include_router(articles_router)
app.include_router(content_router)
app.include_router(reviews_router)
app.include_router(article_reviews_router)
app.include_router(feedback_router)
app.include_router(public_router)
app.include_router(upload_router)
app.include_router(messages_router)
app.include_router(collection_router)
app.include_router(stats_router)
app.include_router(text_router)
app.include_router(ai_router)
