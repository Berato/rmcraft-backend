from sqlalchemy.orm import Session
from app.models.resume import Resume

def get_resumes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Resume).offset(skip).limit(limit).all()


def get_resume(db: Session, resume_id: str):
    return db.query(Resume).filter(Resume.id == resume_id).first()
