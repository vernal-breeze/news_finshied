from pydantic import BaseModel

class CollectionCreate(BaseModel):
    name: str

class CollectionResponse(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True
