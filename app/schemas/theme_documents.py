from beanie import Document
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ThemeComponent(BaseModel):
    template: str
    styles: str


class ThemeDoc(Document):
    name: str
    description: Optional[str] = None
    type: str
    template: str
    styles: str
    previewImageUrl: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Settings:
        name = "themes"


class ThemePackageDoc(Document):
    name: str
    description: Optional[str] = None
    resumeTemplateId: str
    coverLetterTemplateId: str
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Settings:
        name = "theme_packages"

    def resume_template(self):
        # helper to fetch resume theme document
        from app.schemas.theme_documents import ThemeDoc
        return ThemeDoc.get(self.resumeTemplateId)

    def cover_letter_template(self):
        from app.schemas.theme_documents import ThemeDoc
        return ThemeDoc.get(self.coverLetterTemplateId)
