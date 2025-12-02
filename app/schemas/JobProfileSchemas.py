from beanie import Document
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any, Literal
from datetime import datetime
from app.schemas.ResumeSchemas import JobProfileDetails, JobProfileAnalysis, JobProfileInsights, CompanyResearch, SkillsMatch

class JobProfile(Document):
    id: str = Field(alias="_id")
    name: str
    userId: str
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)
    jobDetails: JobProfileDetails
    analysis: JobProfileAnalysis
    insights: JobProfileInsights
    companyResearch: CompanyResearch
    skillsMatch: SkillsMatch
    status: Literal["draft", "complete", "archived"] = "draft"

    class Settings:
        name = "job_profiles"
    
    model_config = ConfigDict(populate_by_name=True)

class JobProfileCreate(BaseModel):
    name: str
    userId: str
    jobDetails: JobProfileDetails
    analysis: JobProfileAnalysis
    insights: JobProfileInsights
    companyResearch: CompanyResearch
    skillsMatch: SkillsMatch
    status: Literal["draft", "complete", "archived"] = "draft"

class JobProfileUpdate(BaseModel):
    name: Optional[str] = None
    jobDetails: Optional[JobProfileDetails] = None
    analysis: Optional[JobProfileAnalysis] = None
    insights: Optional[JobProfileInsights] = None
    companyResearch: Optional[CompanyResearch] = None
    skillsMatch: Optional[SkillsMatch] = None
    status: Optional[Literal["draft", "complete", "archived"]] = None

class JobProfileResponse(BaseModel):
    id: str = Field(alias="_id")
    name: str
    userId: str
    createdAt: datetime
    updatedAt: datetime
    jobDetails: JobProfileDetails
    analysis: JobProfileAnalysis
    insights: JobProfileInsights
    companyResearch: CompanyResearch
    skillsMatch: SkillsMatch
    status: Literal["draft", "complete", "archived"]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
