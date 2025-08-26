import pydantic
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Literal, Dict, Union
from datetime import datetime
import uuid

class PersonalInfo(BaseModel):
    id: str
    firstName: str
    lastName: str
    email: str
    phone: str
    website: str
    linkedin: Optional[str] = None
    location: str
    title: Optional[str] = None
    profileImage: Optional[str] = None
    summary: Optional[str] = None


class UserProfile(BaseModel):
    # inherits PersonalInfo except 'email'
    id: str
    firstName: str
    lastName: str
    phone: str
    website: str
    linkedin: Optional[str] = None
    location: str
    title: Optional[str] = None
    profileImage: Optional[str] = None
    summary: Optional[str] = None
    profileComplete: Optional[bool] = None
    onboardingComplete: Optional[bool] = None


class Experience(BaseModel):
    id: str
    company: str
    position: str
    startDate: str
    endDate: str
    responsibilities: List[str] = Field(default_factory=list)


class Education(BaseModel):
    id: str
    institution: str
    degree: str
    startDate: str
    endDate: str


class Project(BaseModel):
    id: str
    name: str
    description: str
    url: str


class Skill(BaseModel):
    id: str
    name: str
    level: int  # 1-5 proficiency level


class JobDescription(BaseModel):
    id: str
    title: str
    company: str
    description: str
    requirements: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    location: str
    salary: Optional[str] = None
    source: Literal["manual", "web_search"]
    url: Optional[str] = None
    createdAt: datetime


class ResumeBase(BaseModel):
    name: str
    summary: str
    # allow flexible shapes (list or dict) for these fields since DB JSON
    # may store arrays or objects depending on the client
    personalInfo: Any
    experience: Any
    education: Any
    skills: Any
    projects: Any
    jobDescription: Optional[Any] = None
    jobProfileId: Optional[str] = None
    themeId: Optional[str] = None


class ResumeCreate(ResumeBase):
    userId: str


class Resume(ResumeBase):
    id: str
    userId: str
    createdAt: datetime
    updatedAt: datetime

    # pydantic v2: use model_config with ConfigDict to allow attribute access
    model_config = pydantic.ConfigDict(from_attributes=True)


# A concrete response model that matches the JSON shape returned by the DB/API
class ResumeResponse(BaseModel):
    id: str
    userId: str
    name: str
    summary: Optional[str] = ""
    # tolerate either fully-typed objects or loose dicts/partials from the DB
    personalInfo: Optional[Union[PersonalInfo, Dict[str, Any]]] = None
    experience: List[Union[Experience, Dict[str, Any]]] = Field(default_factory=list)
    education: List[Union[Education, Dict[str, Any]]] = Field(default_factory=list)
    # skills in DB appear as: list of Skill-like dicts (sometimes missing id), list of strings, or a dict of categories
    skills: Union[List[Union[Skill, Dict[str, Any], str]], Dict[str, List[str]]] = Field(default_factory=list)
    projects: List[Union[Project, Dict[str, Any]]] = Field(default_factory=list)
    jobDescription: Optional[Union[JobDescription, Dict[str, Any]]] = None
    jobProfileId: Optional[str] = None
    themeId: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

    model_config = pydantic.ConfigDict(from_attributes=True)


class ResumeListResponse(BaseModel):
    """Envelope response returned by GET /api/v1/resumes

    Keeps a stable shape for the frontend: { status, message, data }
    where data is the list of resumes.
    """
    status: int = 200
    message: str = "Resumes returned successfully"
    data: List[ResumeResponse] = Field(default_factory=list)

    model_config = pydantic.ConfigDict(from_attributes=True)


class ResumeSingleResponse(BaseModel):
    """Envelope response for single resume retrieval: { status, message, data }"""
    status: int = 200
    message: str = "Resume returned successfully"
    data: Optional[ResumeResponse] = None

    model_config = pydantic.ConfigDict(from_attributes=True)

class JobProfileDetails(BaseModel):
    title: str
    company: str
    location: str
    url: Optional[str] = None
    description: str
    requirements: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    experienceLevel: Optional[str] = None
    educationRequirements: List[str] = Field(default_factory=list)
    salary: Optional[str] = None
    source: Literal["manual", "url_scrape", "web_search"]

class BodyParagraph(BaseModel):
    pass

class CompanyConnection(BaseModel):
    pass

class CoverLetterTypes(BaseModel):
    id: str
    name: str
    updatedAt: datetime
    resumeId: str
    jobDetails: JobProfileDetails
    openingParagraph: str
    bodyParagraphs: List[BodyParagraph] = Field(default_factory=list)
    companyConnection: CompanyConnection
    closingParagraph: str
    tone: Literal["professional", "creative", "enthusiastic", "formal"]
    finalContent: str
    jobProfileId: Optional[str] = None


class CoverLetterWizardStep(BaseModel):
    id: str
    title: str
    subtitle: str
    component: Optional[Any] = None  # placeholder for a UI/component reference


# Job Profile Types
class SkillRequirement(BaseModel):
    skill: str
    importance: Literal["critical", "important", "preferred"]
    frequency: int


class ATSScore(BaseModel):
    score: int  # 0-100
    suggestions: List[str] = Field(default_factory=list)
    missingKeywords: List[str] = Field(default_factory=list)


class JobProfileAnalysis(BaseModel):
    keywords: List[str] = Field(default_factory=list)
    keyResponsibilities: List[str] = Field(default_factory=list)
    requiredSkills: List[SkillRequirement] = Field(default_factory=list)
    softSkills: List[str] = Field(default_factory=list)
    experienceLevel: Optional[str] = None
    educationLevel: Optional[str] = None
    industryKeywords: List[str] = Field(default_factory=list)
    atsOptimization: Optional[ATSScore] = None


class JobProfileInsights(BaseModel):
    motivation: Optional[str] = None
    companyConnection: Optional[str] = None
    valueProposition: Optional[str] = None
    strongestSkill: Optional[str] = None
    skillExample: Optional[str] = None
    gapAddressal: Optional[str] = None
    personalGoals: Optional[str] = None
    culturalFit: Optional[str] = None


class CompanyResearch(BaseModel):
    mission: Optional[str] = None
    values: List[str] = Field(default_factory=list)
    culture: Optional[str] = None
    recentNews: List[str] = Field(default_factory=list)
    leadership: Optional[str] = None
    projects: List[str] = Field(default_factory=list)
    industry: Optional[str] = None
    size: Optional[str] = None
    founded: Optional[str] = None


class SkillMatch(BaseModel):
    jobSkill: str
    resumeSkill: str
    confidence: int  # 0-100
    examples: List[str] = Field(default_factory=list)


class SkillGap(BaseModel):
    skill: str
    importance: Literal["critical", "important", "preferred"]
    learningPlan: Optional[str] = None
    alternativeExperience: Optional[str] = None


class SkillsMatch(BaseModel):
    strongMatches: List[SkillMatch] = Field(default_factory=list)
    partialMatches: List[SkillMatch] = Field(default_factory=list)
    gaps: List[SkillGap] = Field(default_factory=list)
    overallMatch: int  # 0-100


class JobProfile(BaseModel):
    id: str
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


class JobProfileWizardStep(BaseModel):
    id: str
    title: str
    subtitle: str
    component: Optional[Any] = None  # placeholder for a UI/component reference
