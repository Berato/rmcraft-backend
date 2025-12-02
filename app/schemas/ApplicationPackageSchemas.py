from beanie import Document
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime

class ApplicationPackage(Document):
    id: str = Field(alias="_id")
    userId: str
    jobProfileId: str
    resumeId: Optional[str] = None
    coverLetterId: Optional[str] = None
    status: str = "draft"
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "application_packages"
    
    model_config = ConfigDict(populate_by_name=True)

class ApplicationPackageCreate(BaseModel):
    userId: str
    jobProfileId: str
    resumeId: Optional[str] = None
    coverLetterId: Optional[str] = None
    status: str = "draft"

class ApplicationPackageUpdate(BaseModel):
    resumeId: Optional[str] = None
    coverLetterId: Optional[str] = None
    status: Optional[str] = None

class ApplicationPackageResponse(BaseModel):
    id: str = Field(alias="_id")
    userId: str
    jobProfileId: str
    resumeId: Optional[str] = None
    coverLetterId: Optional[str] = None
    status: str
    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
