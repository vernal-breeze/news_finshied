from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ClueBase(BaseModel):
    title: str
    content: str
    source: Optional[str] = None

class ClueCreate(ClueBase):
    pass

class ClueResponse(ClueBase):
    id: int
    status: str
    created_at: datetime
    class Config:
        from_attributes = True
