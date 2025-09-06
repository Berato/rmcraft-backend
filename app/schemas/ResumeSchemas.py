import pydantic
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Literal, Dict, Union
from datetime import datetime
import uuid
from enum import Enum
from typing import Optional, List
from beanie import Document
from bson import ObjectId

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
    degree: Optional[str]
    startDate: Optional[str]
    endDate: Optional[str]


class Project(BaseModel):
    id: str
    name: str
    description: str
    url: Optional[str] = None


class Skill(BaseModel):
    id: str
    name: str
    level: Optional[int] = None  # 1-5 proficiency level


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
    pass




# A concrete response model that matches the JSON shape returned by the DB/API
class ResumeResponse(Document):
    # Accept either MongoDB-style "_id" or "id"; be tolerant if fields are missing
    id: Optional[str] = Field(default=None, alias="_id")
    userId: Optional[str] = None
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
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    # allow from_attributes, extra fields, and population by field name (so alias "_id" works)
    model_config = pydantic.ConfigDict(from_attributes=True, extra="allow", populate_by_name=True)

    @pydantic.field_validator("id", mode="before")
    def _coerce_objectid_to_str(cls, v: Any):
        # Convert MongoDB ObjectId to string so Pydantic validation succeeds
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
        name = "resumes"

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
    tone: str
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

class ContactInfo(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None


class ExperienceAgentOutPutSchema(BaseModel):
    experience: List[Experience]

class SkillsAgentOutPutSchema(BaseModel):
    skills: List[Skill]
    additional_skills: Optional[List[str]] = None

class ProjectsAgentOutPutSchema(BaseModel):
    projects: List[Project]

class EducationAgentOutPutSchema(BaseModel):
    education: List[Education]

class ContactInfoAgentOutPutSchema(BaseModel):
    contact_info: List[ContactInfo]

class SummaryAgentOutPutSchema(BaseModel):
    summary: str


class NameAgentOutPutSchema(BaseModel):
    # Agent output for a simple name field. Keep optional behavior at assembler level.
    name: str


class DesignBriefOutputSchema(BaseModel):
    layout_description: str = Field(description="A detailed description of the resume layout (e.g., 'two-column, minimalist').")
    color_palette: Dict[str, str] = Field(description="A dictionary mapping color roles (e.g., 'primary', 'accent') to hex color codes.")
    google_fonts: List[str] = Field(description="A list of suggested Google Font names (e.g., ['Lato', 'Roboto Slab']).")
    design_prompt_for_developer: str = Field(description="A concise, regenerated prompt for the next agent to use.")


class DesignerAgentOutputSchema(BaseModel):
    jinja_template: str = Field(description="A complete Jinja2 template string for the resume.")
    css_styles: str = Field(description="A complete CSS string to style the resume.")
    
    
# class CoverLetterTone(str, Enum):
#     PROFESSIONAL = "professional"
#     CREATIVE = "creative"
#     ENTHUSIASTIC = "enthusiastic"
#     FORMAL = "formal"


class ThemeType(str, Enum):
    RESUME = "RESUME"
    COVER_LETTER = "COVER_LETTER"


class Theme(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    type: ThemeType
    template: str
    styles: str
    previewImageUrl: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

    model_config = pydantic.ConfigDict(from_attributes=True)


class ThemeComponent(BaseModel):
    template: str
    styles: str


class ThemePackage(BaseModel):
    id: str
    name: str
    description: str
    resumeTemplate: Theme
    coverLetterTemplate: Theme
    createdAt: datetime
    updatedAt: datetime

    model_config = pydantic.ConfigDict(from_attributes=True)


class ResumeAnalysisSchema(BaseModel):
    """Schema for strategic resume analysis response data"""
    experiences: List[Experience] = Field(default_factory=list)
    skills: List[Skill] = Field(default_factory=list) 
    projects: List[Project] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    contact_info: List[ContactInfo] = Field(default_factory=list)
    summary: str = ""
    name: str = ""

    model_config = pydantic.ConfigDict(from_attributes=True)
