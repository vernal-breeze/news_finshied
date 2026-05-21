"""统一响应 Schema"""
from typing import TypeVar, Generic, Optional, List, Any
from pydantic import BaseModel


T = TypeVar("T")


class BaseResponse(BaseModel):
    code: int = 200
    message: str = "success"


class DataResponse(BaseResponse, Generic[T]):
    data: Optional[T] = None
    total: Optional[int] = None


class PaginationResponse(DataResponse[List[Any]]):
    page: int = 1
    page_size: int = 20


def create_data_response(data: Any, total: Optional[int] = None, message: str = "success") -> dict:
    result = {"code": 200, "message": message, "data": data}
    if total is not None:
        result["total"] = total
    return result


def create_pagination_response(data: Any, total: int, page: int = 1, page_size: int = 20) -> dict:
    return {
        "code": 200,
        "message": "success",
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
