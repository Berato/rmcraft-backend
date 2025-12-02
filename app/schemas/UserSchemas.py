from beanie import Document
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime

class User(Document):
    id: str = Field(alias="_id")
    email: EmailStr
    name: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    location: Optional[str] = None
    onboardingComplete: bool = False
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "users"
    
    model_config = ConfigDict(populate_by_name=True)

class UserCreate(BaseModel):
    id: str
    email: EmailStr
    name: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    location: Optional[str] = None
    onboardingComplete: bool = False

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    location: Optional[str] = None
    onboardingComplete: Optional[bool] = None

class UserResponse(BaseModel):
    id: str = Field(alias="_id")
    email: str
    name: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    location: Optional[str] = None
    onboardingComplete: bool
    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
