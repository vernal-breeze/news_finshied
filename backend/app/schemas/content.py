from pydantic import BaseModel

class ContentCreate(BaseModel):
    title: str
    content: str
