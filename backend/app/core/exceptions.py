"""自定义异常"""
from typing import Optional


class BaseAPIException(Exception):
    """API 异常基类"""
    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: Optional[str] = None, status_code: Optional[int] = None):
        self.detail = detail or self.detail
        self.status_code = status_code or self.status_code
        super().__init__(self.detail)


class BadRequestException(BaseAPIException):
    status_code = 400
    detail = "Bad request"


class NotFoundException(BaseAPIException):
    status_code = 404
    detail = "Not found"


class UnauthorizedException(BaseAPIException):
    status_code = 401
    detail = "Unauthorized"


class ForbiddenException(BaseAPIException):
    status_code = 403
    detail = "Forbidden"


class AIServiceError(BaseAPIException):
    status_code = 503
    detail = "AI service error"


class RateLimitException(BaseAPIException):
    status_code = 429
    detail = "Rate limit exceeded"


def raise_bad_request(detail: str = "Bad request"):
    raise BadRequestException(detail=detail)


def raise_not_found(detail: str = "Not found"):
    raise NotFoundException(detail=detail)
