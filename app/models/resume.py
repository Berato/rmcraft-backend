from sqlalchemy import Column, String, DateTime, JSON
from app.db.session import Base

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    userId = Column(String, index=True)
    summary = Column(String)
    personalInfo = Column(JSON)
    experience = Column(JSON)
    education = Column(JSON)
    skills = Column(JSON)
    projects = Column(JSON)
    jobDescription = Column(JSON, nullable=True)
    jobProfileId = Column(String, nullable=True)
    themeId = Column(String, nullable=True)
    createdAt = Column(DateTime)
    updatedAt = Column(DateTime)
