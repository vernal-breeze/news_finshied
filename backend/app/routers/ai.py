"""AI 路由：速率限制状态、缓存统计等"""
from fastapi import APIRouter

from app.schemas.base import DataResponse, create_data_response
from app.services.rate_limiter import get_rate_limiter
from app.services.cache_service import get_ai_cache

router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.get("/rate-limit-status", response_model=DataResponse, summary="AI 速率限制状态")
async def rate_limit_status():
    """获取当前 AI API 调用的速率限制状态"""
    limiter = get_rate_limiter()
    return create_data_response(
        data={
            "tokens_per_minute": limiter.tokens_per_minute,
            "burst_size": limiter.burst_size,
            "available_tokens": int(limiter.tokens),
            "rate_limited": limiter.tokens <= 0,
        }
    )


@router.get("/cache-stats", response_model=DataResponse, summary="AI 缓存统计")
async def cache_stats():
    """获取 AI 响应缓存的统计信息"""
    cache = get_ai_cache()
    total_entries = len(cache._cache)
    active_entries = sum(1 for k, v in cache._cache.items() if v[1] + cache._ttl > __import__('time').time())

    return create_data_response(
        data={
            "total_entries": total_entries,
            "active_entries": active_entries,
            "expired_entries": total_entries - active_entries,
            "ttl_seconds": cache._ttl,
        }
    )
