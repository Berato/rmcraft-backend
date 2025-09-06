from sqlalchemy.orm import Session
from app.models.resume import Resume
from typing import Dict, Any
from datetime import datetime

from app.schemas.ResumeSchemas import ResumeResponse


def get_resumes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Resume).offset(skip).limit(limit).all()


def get_resume(db: Session, resume_id: str):
    return db.query(Resume).filter(Resume.id == resume_id).first()

def create_resume_v2(resume_data: ResumeResponse):
    """
    Inserting a new resume into the MongoDB collection.
    """
    
    

def create_resume(db: Session, resume_data: Dict[str, Any]):
    """
    Create a new resume in the database.
    """
    import uuid
    
    # Handle userId - if None or empty, use the system user ID
    if not resume_data.get("userId"):
        # Use the system user ID for anonymous uploads
        resume_data["userId"] = "00000000-0000-0000-0000-000000000000"
        
    # Create a new Resume instance
    db_resume = Resume(
        id=resume_data.get("id"),
        userId=resume_data.get("userId"),
        name=resume_data.get("name"),
        summary=resume_data.get("summary"),
        personalInfo=resume_data.get("personalInfo"),
        experience=resume_data.get("experience"),
        education=resume_data.get("education"),
        skills=resume_data.get("skills"),
        projects=resume_data.get("projects"),
        jobDescription=resume_data.get("jobDescription"),
        jobProfileId=resume_data.get("jobProfileId"),
        themeId=resume_data.get("themeId"),
        createdAt=resume_data.get("createdAt") or datetime.now(),
        updatedAt=resume_data.get("updatedAt") or datetime.now(),
    )
    
    # Add to database
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)
    
    return db_resume
