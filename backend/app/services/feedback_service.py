from sqlalchemy.orm import Session

class FeedbackService:
    def __init__(self, db: Session):
        self.db = db
