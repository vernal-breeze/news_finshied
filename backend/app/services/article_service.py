from sqlalchemy.orm import Session

class ArticleService:
    def __init__(self, db: Session):
        self.db = db
