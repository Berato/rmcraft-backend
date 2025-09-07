from pydantic import BaseModel
from typing import Optional


class ThemeTemplate(BaseModel):
    """Represents a single document template (Jinja2 + CSS)."""
    template: str
    styles: str


class ThemeSchema(BaseModel):
    """In-memory representation combining resume + cover letter templates.

    This does NOT replace the existing SQLAlchemy Theme/ThemePackage persistence
    model (which stores each template independently and links them). It is used
    for validation of agent outputs and for PDF rendering convenience.
    """
    name: str
    description: Optional[str] = None
    resume_template: ThemeTemplate
    cover_letter_template: ThemeTemplate
    # Optional preview (uploaded PDF) URLs
    resume_preview_url: Optional[str] = None
    cover_letter_preview_url: Optional[str] = None

    class Config:
        orm_mode = True


class ThemePackageWithTemplates(BaseModel):
    id: str
    name: str
    description: Optional[str]
    resumeTemplate: ThemeTemplate
    coverLetterTemplate: ThemeTemplate
