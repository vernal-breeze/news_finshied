"""
安全中间件 — 添加安全响应头
"""
from starlette.requests import Request
from starlette.responses import Response


async def add_security_headers(request: Request, call_next):
    """添加安全响应头"""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
