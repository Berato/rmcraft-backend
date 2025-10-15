from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

class CoverLetterManualCreate(BaseModel):
    """Request model for manual cover letter creation"""
    title: str = Field(..., max_length=255, description="Title of the cover letter")
    resume_id: Optional[UUID] = Field(None, description="Optional reference to a Resume")
    job_profile_id: Optional[UUID] = Field(None, description="Optional reference to a Job Profile")
    raw_text: str = Field(..., min_length=1, description="Full cover letter content (plain text)")
    notes: Optional[str] = Field(None, description="Optional internal notes")
    user_id: Optional[UUID] = Field(None, description="Optional user ID if tracking owners")

class CoverLetterManualResponse(BaseModel):
    """Response model for manual cover letter creation"""
    id: UUID
    title: str
    resume_id: Optional[UUID] = None
    job_profile_id: Optional[UUID] = None
    content: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None