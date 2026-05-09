from pydantic import BaseModel
from typing import Optional

class TopicCreate(BaseModel):
    name: str
    description: Optional[str] = None

class TopicResponse(BaseModel):
    id: int
    name: str
    status: str
    class Config:
        from_attributes = True
