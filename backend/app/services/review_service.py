from sqlalchemy.orm import Session

class ReviewService:
    def __init__(self, db: Session):
        self.db = db
