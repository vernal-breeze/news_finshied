from sqlalchemy.orm import Session

class ClueService:
    def __init__(self, db: Session):
        self.db = db
