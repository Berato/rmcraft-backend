from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid
import enum

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class ThemeType(enum.Enum):
    RESUME = "RESUME"
    COVER_LETTER = "COVER_LETTER"

class Theme(Base):
    __tablename__ = "themes"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, index=True)
    description = Column(String)
    type = Column(Enum(ThemeType))
    template = Column(String)
    styles = Column(String)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ThemePackage(Base):
    __tablename__ = "theme_packages"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, index=True)
    description = Column(String)
    resume_template_id = Column(String, ForeignKey("themes.id"))
    cover_letter_template_id = Column(String, ForeignKey("themes.id"))
    
    resume_template = relationship("Theme", foreign_keys=[resume_template_id])
    cover_letter_template = relationship("Theme", foreign_keys=[cover_letter_template_id])
    
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
