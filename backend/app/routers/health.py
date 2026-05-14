"""
健康检查路由
提供服务健康状态、就绪检查和存活探针接口
"""
import time
from typing import Dict, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.core.config import get_settings
from app.schemas.base import BaseResponse, DataResponse, create_data_response
from app.models import ArticleStatus, Article, NewsClue

settings = get_settings()

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=BaseResponse, summary="健康检查")
async def health_check():
    """检查服务是否正常运行"""
    return BaseResponse(code=200, message="服务运行正常")


@router.get("/health/detailed", response_model=DataResponse[Dict[str, Any]], summary="详细健康检查")
async def detailed_health_check(db: Session = Depends(get_db)):
    """详细系统状态检查"""
    import psutil
    import os
    from datetime import datetime
    from app.models import Article, NewsClue

    # 数据库连接测试
    db_status = "ok"
    db_error = None
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "error"
        db_error = str(e)

    # 统计数据
    try:
        article_count = db.query(Article).count()
        clue_count = db.query(NewsClue).count()
        pending_articles = db.query(Article).filter(
            Article.status == ArticleStatus.PENDING_REVIEW
        ).count()
    except Exception as e:
        article_count = clue_count = pending_articles = -1

    # 系统资源
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent(interval=0.1)

        system_info = {
            "cpu_percent": round(cpu_percent, 1),
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_percent": memory.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "used_percent": round(disk.percent, 1),
            },
        }
    except Exception:
        system_info = {"error": "无法获取系统资源信息"}

    # AI 服务状态
    ai_status = "configured" if settings.get_ai_api_key() else "mock"

    status_data = {
        "status": "healthy" if db_status == "ok" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "uptime": time.time(),
        "database": {
            "status": db_status,
            "error": db_error,
        },
        "statistics": {
            "articles": {"total": article_count, "pending_review": pending_articles},
            "clues": {"total": clue_count},
        },
        "system": system_info,
        "ai_service": {
            "status": ai_status,
            "model": settings.AI_MODEL,
            "provider": "deepseek" if settings.DEEPSEEK_API_KEY else ("siliconflow" if settings.SILICONFLOW_API_KEY else "mock"),
        },
        "version": {
            "app": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        },
    }

    return create_data_response(data=status_data)


@router.get("/health/ready", response_model=BaseResponse, summary="就绪检查")
async def readiness_check(db: Session = Depends(get_db)):
    """Kubernetes 就绪探针 - 检查所有依赖是否就绪"""
    checks = {}
    overall_ready = True

    # 1. 数据库就绪
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = {"ready": True}
    except Exception as e:
        checks["database"] = {"ready": False, "error": str(e)}
        overall_ready = False

    # 2. AI 服务就绪（检查 API Key）
    checks["ai"] = {
        "ready": True,
        "mode": "live" if settings.get_ai_api_key() else "mock",
    }

    status_code = 200 if overall_ready else 503
    status_text = "就绪" if overall_ready else "未就绪"

    return JSONResponse(
        status_code=status_code,
        content={
            "code": status_code,
            "message": f"服务{status_text}",
            "checks": checks,
        },
    )


@router.get("/health/live", response_model=BaseResponse, summary="存活检查")
async def liveness_check():
    """Kubernetes 存活探针 - 确认进程存活"""
    return BaseResponse(code=200, message="存活")


@router.get("/status", response_model=DataResponse[dict], summary="系统状态")
async def system_status(db: Session = Depends(get_db)):
    """获取系统运行状态摘要"""
    from app.models import Article, NewsClue
    from datetime import datetime

    article_count = db.query(Article).count()
    clue_count = db.query(NewsClue).count()

    return create_data_response(
        data={
            "status": "running",
            "name": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
            "articles": article_count,
            "clues": clue_count,
            "timestamp": datetime.now().isoformat(),
        }
    )
