from sqlalchemy import Column, String, DateTime, JSON, Integer
from sqlalchemy.orm import relationship
from app.db.session import Base
from datetime import datetime
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class CoverLetter(Base):
    __tablename__ = "cover_letters"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String)
    jobDetails = Column(JSON)
    openingParagraph = Column(String)
    bodyParagraphs = Column(JSON)
    companyConnection = Column(String, nullable=True)
    closingParagraph = Column(String)
    tone = Column(String)
    finalContent = Column(String)
    resumeId = Column(String, index=True)
    jobProfileId = Column(String, nullable=True, index=True)
    wordCount = Column(Integer)
    atsScore = Column(Integer)
    metadata_json = Column('metadata', JSON, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow)
