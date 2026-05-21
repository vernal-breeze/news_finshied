from pydantic import BaseModel

class FeedbackCreate(BaseModel):
    content: str

class FeedbackResponse(BaseModel):
    id: int
    content: str
    class Config:
        from_attributes = True
