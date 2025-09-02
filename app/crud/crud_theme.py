from sqlalchemy.orm import Session
from app.models.theme import ThemePackage

def get_theme_packages(db: Session, skip: int = 0, limit: int = 100):
    return db.query(ThemePackage).offset(skip).limit(limit).all()
