from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Enum, Index, UniqueConstraint, func
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
    # Prisma: themes.name is UNIQUE
    name = Column(String, unique=True)
    # Optional description
    description = Column(String)
    type = Column(Enum(ThemeType))
    template = Column(String)
    styles = Column(String)
    # New optional preview image URL, mapped to camelCase DB column name
    previewImageUrl = Column('previewImageUrl', String, nullable=True)
    # Timestamps: prefer server-managed, but also provide client-side defaults to satisfy NOT NULL without DB defaults
    createdAt = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updatedAt = Column(DateTime, default=datetime.utcnow, server_default=func.now(), onupdate=func.now())

class ThemePackage(Base):
    __tablename__ = "theme_packages"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, index=True)
    description = Column(String)
    # Keep Python attrs snake_case but map to camelCase DB columns explicitly
    resume_template_id = Column(
        'resumeTemplateId',
        String,
        ForeignKey("themes.id", ondelete='RESTRICT', onupdate='CASCADE'),
        nullable=False
    )
    cover_letter_template_id = Column(
        'coverLetterTemplateId',
        String,
        ForeignKey("themes.id", ondelete='RESTRICT', onupdate='CASCADE'),
        nullable=False
    )
    __table_args__ = (
        # Unique pair constraint to mirror Prisma
        UniqueConstraint('resumeTemplateId', 'coverLetterTemplateId', name='uq_resume_cover_pair'),
        # Helpful indexes
        Index('idx_resume_template', 'resumeTemplateId'),
        Index('idx_cover_letter_template', 'coverLetterTemplateId'),
    )
    
    resume_template = relationship("Theme", foreign_keys=[resume_template_id])
    cover_letter_template = relationship("Theme", foreign_keys=[cover_letter_template_id])
    
    # Expose camelCase accessors to align with API response schema (Pydantic from_attributes)
    @property
    def resumeTemplate(self):  # noqa: N802
        return self.resume_template

    @property
    def coverLetterTemplate(self):  # noqa: N802
        return self.cover_letter_template

    # Timestamps: prefer server-managed, but also provide client-side defaults to satisfy NOT NULL without DB defaults
    createdAt = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updatedAt = Column(DateTime, default=datetime.utcnow, server_default=func.now(), onupdate=func.now())
