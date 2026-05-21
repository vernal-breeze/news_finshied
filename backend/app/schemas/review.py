from pydantic import BaseModel
from typing import Optional

class ReviewCreate(BaseModel):
    article_id: int
    comment: Optional[str] = None
    status: str = "pending"

class ReviewResponse(BaseModel):
    id: int
    article_id: int
    status: str
    class Config:
        from_attributes = True
