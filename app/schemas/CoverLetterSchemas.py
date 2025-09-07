import pydantic
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from beanie import Document
from bson import ObjectId

class StrategicCoverLetterRequest(BaseModel):
    """Request model for strategic cover letter generation"""
    resumeId: str
    jobDescriptionUrl: str
    prompt: Optional[str] = None
    saveToDb: bool = True


class JobProfileDetails(BaseModel):
    """Job profile details schema"""
    title: str = ""
    company: str = ""
    url: str = ""


class StrategicCoverLetterResponse(BaseModel):
    """Response model for strategic cover letter"""
    title: str
    jobDetails: JobProfileDetails
    openingParagraph: str
    bodyParagraphs: list[str]
    companyConnection: Optional[str] = None
    closingParagraph: str
    tone: str
    resumeId: str
    jobProfileId: Optional[str] = None
    createdAt: str
    updatedAt: str
    wordCount: int = 0
    coverLetterId: Optional[str] = None
    persistenceError: Optional[str] = None


class CoverLetterAPIResponse(BaseModel):
    """API envelope for cover letter responses"""
    status: int
    message: str
    data: StrategicCoverLetterResponse


class CoverLetterFull(Document):
    """Full cover letter payload for single fetch (Mongo-friendly)

    Accepts MongoDB `_id` alias, tolerates extra fields from DB, and
    coerces ObjectId to string for `id`.
    """
    # Accept either MongoDB-style "_id" or "id"; store as str
    id: Optional[str] = Field(default=None, alias="_id")
    title: Optional[str] = ""
    jobDetails: Optional[Dict[str, Any]] = Field(default_factory=dict)
    openingParagraph: Optional[str] = ""
    bodyParagraphs: List[str] = Field(default_factory=list)
    companyConnection: Optional[str] = None
    closingParagraph: Optional[str] = ""
    tone: Optional[str] = "professional"
    resumeId: Optional[str] = None
    userId: Optional[str] = None
    themeId: Optional[str] = None
    jobProfileId: Optional[str] = None
    wordCount: int = 0
    metadata: Optional[Dict[str, Any]] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

    # Be tolerant of DB shapes and allow population by name (so alias "_id" works)
    model_config = pydantic.ConfigDict(from_attributes=True, extra="allow", populate_by_name=True)

    @pydantic.field_validator("id", mode="before")
    def _coerce_objectid_to_str(cls, v: Any):
        if v is None:
            return None
        try:
            if isinstance(v, ObjectId):
                return str(v)
        except Exception:
            pass
        if isinstance(v, str):
            return v
        return str(v)

    class Settings:
        name = "cover_letters"


class CoverLetterSingleResponse(BaseModel):
    status: int
    message: str
    data: CoverLetterFull


class CoverLetterSummary(BaseModel):
    """Summary model for cover letter listing"""
    id: str
    title: str
    clientName: str
    hiringManager: Optional[str] = None
    jobDetails: Dict[str, Any]
    resumeId: str
    jobProfileId: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    wordCount: int
    openingParagraph: Optional[str] = None
    bodyParagraphs: Optional[List[str]] = None
    companyConnection: Optional[str] = None
    closingParagraph: Optional[str] = None


class CoverLetterListMeta(BaseModel):
    """Pagination metadata for cover letter list"""
    page: int
    perPage: int
    total: int
    totalPages: int


class CoverLetterListData(BaseModel):
    """Data structure for cover letter list"""
    items: List[CoverLetterSummary]
    meta: CoverLetterListMeta


class CoverLetterListResponse(BaseModel):
    """Response model for cover letter list endpoint"""
    status: int
    message: str
    data: CoverLetterListData