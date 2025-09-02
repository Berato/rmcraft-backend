from sqlalchemy.orm import Session
from app.models.theme import ThemePackage, Theme

def get_theme_packages(db: Session, skip: int = 0, limit: int = 100):
    return db.query(ThemePackage).offset(skip).limit(limit).all()

def get_theme_package_by_id(db: Session, theme_package_id: str):
    return db.query(ThemePackage).filter(ThemePackage.id == theme_package_id).first()

def get_themes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Theme).offset(skip).limit(limit).all()

def get_theme_by_id(db: Session, theme_id: str):
    return db.query(Theme).filter(Theme.id == theme_id).first()
