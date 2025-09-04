# Theme Generator Database Integration Guide

## Overview
This document provides complete instructions for implementing database persistence in the theme generator workflow. The theme generator currently creates structured theme data using Google ADK agents but does not persist the results to the database.

## Current State
The theme generator workflow (`app/features/theme_generator.py`) successfully:
1. Orchestrates three ADK agents (`theme_analyst_agent`, `resume_theme_agent`, `cover_letter_theme_agent`)
2. Generates structured theme data with proper JSON schemas
3. Returns a dictionary matching the `ThemePackage` schema
4. **Does NOT save to database** - all database code is commented out

## Required Implementation

### 1. Database Models
The following models need to be implemented or verified in `app/models/`:

#### Theme Model (`app/models/theme.py`)
```python
from sqlalchemy import Column, Integer, String, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum

Base = declarative_base()

class ThemeType(str, Enum):
    RESUME = "resume"
    COVER_LETTER = "cover_letter"

class Theme(Base):
    __tablename__ = "themes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(SQLEnum(ThemeType), nullable=False)
    template = Column(Text, nullable=False)  # Jinja2 template string
    styles = Column(Text, nullable=False)    # CSS styles string
```

#### ThemePackage Model (`app/models/theme.py`)
```python
class ThemePackage(Base):
    __tablename__ = "theme_packages"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    resume_template_id = Column(Integer, ForeignKey("themes.id"), nullable=False)
    cover_letter_template_id = Column(Integer, ForeignKey("themes.id"), nullable=False)
    
    # Relationships
    resume_template = relationship("Theme", foreign_keys=[resume_template_id])
    cover_letter_template = relationship("Theme", foreign_keys=[cover_letter_template_id])
```

### 2. Database Service Functions
Create or implement in `app/services/theme_service.py`:

#### create_theme Function
```python
from sqlalchemy.orm import Session
from app.models.theme import Theme, ThemeType, ThemePackage
from app.db.session import get_db

async def create_theme(
    db: Session,
    name: str,
    description: str,
    type: ThemeType,
    template: str,
    styles: str
) -> Theme:
    """
    Create a new theme in the database.
    
    Args:
        db: Database session
        name: Theme name
        description: Theme description
        type: Theme type (RESUME or COVER_LETTER)
        template: Jinja2 template string
        styles: CSS styles string
    
    Returns:
        Created Theme object
    """
    theme = Theme(
        name=name,
        description=description,
        type=type,
        template=template,
        styles=styles
    )
    db.add(theme)
    db.commit()
    db.refresh(theme)
    return theme
```

#### create_theme_package Function
```python
async def create_theme_package(
    db: Session,
    name: str,
    description: str,
    resume_template_id: int,
    cover_letter_template_id: int
) -> ThemePackage:
    """
    Create a new theme package linking resume and cover letter themes.
    
    Args:
        db: Database session
        name: Package name
        description: Package description
        resume_template_id: ID of the resume theme
        cover_letter_template_id: ID of the cover letter theme
    
    Returns:
        Created ThemePackage object
    """
    package = ThemePackage(
        name=name,
        description=description,
        resume_template_id=resume_template_id,
        cover_letter_template_id=cover_letter_template_id
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    return package
```

### 3. Schema Updates
Ensure `app/schemas/ResumeSchemas.py` contains the proper response schemas:

#### ThemePackage Response Schema
```python
from pydantic import BaseModel
from typing import Dict, Any

class ThemeResponse(BaseModel):
    id: int
    name: str
    description: str
    type: str
    template: str
    styles: str
    
    class Config:
        from_attributes = True

class ThemePackage(BaseModel):
    id: int
    name: str
    description: str
    resumeTemplate: ThemeResponse
    coverLetterTemplate: ThemeResponse
    
    class Config:
        from_attributes = True
```

### 4. Update Theme Generator
In `app/features/theme_generator.py`, uncomment and modify the database saving section:

#### Add Required Imports
```python
from app.services.theme_service import create_theme, create_theme_package
from app.models.theme import ThemeType
from app.db.session import get_db
from sqlalchemy.orm import Session
```

#### Update Function Signature
```python
async def create_and_save_theme(
    design_prompt: str, 
    image_data: bytes, 
    image_mime_type: str, 
    user_id: str,
    db: Session  # Add database session parameter
):
```

#### Replace the Return Section (lines ~107-145)
```python
    # 4. Package the Theme and Save to Database
    if not all([theme_brief, resume_theme_data, cover_letter_theme_data]):
        raise Exception("Theme generation failed. One or more agents did not produce output.")

    # Create individual Theme records for resume and cover letter
    new_resume_theme = await create_theme(
        db=db,
        name=f"{theme_brief.get('name')} - Resume",
        description=theme_brief.get('description'),
        type=ThemeType.RESUME,
        template=resume_theme_data.get('template'),
        styles=resume_theme_data.get('styles')
    )

    new_cover_letter_theme = await create_theme(
        db=db,
        name=f"{theme_brief.get('name')} - Cover Letter",
        description=theme_brief.get('description'),
        type=ThemeType.COVER_LETTER,
        template=cover_letter_theme_data.get('template'),
        styles=cover_letter_theme_data.get('styles')
    )

    # Create the ThemePackage that links them
    saved_theme_package = await create_theme_package(
        db=db,
        name=theme_brief.get('name'),
        description=theme_brief.get('description'),
        resume_template_id=new_resume_theme.id,
        cover_letter_template_id=new_cover_letter_theme.id
    )

    print("✅ Theme package saved to database successfully.")
    return saved_theme_package
```

### 5. Update API Endpoint
In `app/api/v1/endpoints/themes.py`, add database dependency:

#### Update Endpoint Function
```python
@router.post("/create", status_code=status.HTTP_201_CREATED, response_model=ThemePackage)
async def create_theme_endpoint(
    design_prompt: str = Body(..., embed=True),
    inspiration_image: UploadFile = File(...),
    user_id: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db)  # Add database dependency
):
    """
    Agentically generates and saves a new resume and cover letter theme
    based on a text prompt and an inspiration image.
    """
    image_data = await inspiration_image.read()
    image_mime_type = inspiration_image.content_type
    
    # If user_id is not provided, generate a new one.
    effective_user_id = user_id if user_id else str(uuid.uuid4())

    # The orchestrator runs the full workflow and returns a saved ThemePackage
    saved_theme = await create_and_save_theme(
        design_prompt=design_prompt, 
        image_data=image_data, 
        image_mime_type=image_mime_type,
        user_id=effective_user_id,
        db=db  # Pass database session
    )
    
    return saved_theme
```

### 6. Data Structure Mapping
The agent outputs follow this structure:

#### theme_brief (from theme_analyst_agent)
```python
{
    "name": "Monaco Professional",
    "description": "A detailed description...",
    "color_palette": [
        {"role": "primary", "hex_code": "#FFFFFF"},
        {"role": "accent", "hex_code": "#000000"}
    ],
    "google_fonts": ["Lato", "Roboto Slab"]
}
```

#### resume_theme/cover_letter_theme (from respective agents)
```python
{
    "template": "<!DOCTYPE html><html>...", # Complete Jinja2 template
    "styles": "body { font-family: ... }"   # Complete CSS styles
}
```

### 7. Error Handling
Add proper error handling for database operations:

```python
try:
    # Database operations here
    saved_theme_package = await create_theme_package(...)
    return saved_theme_package
except Exception as e:
    print(f"❌ Database error: {e}")
    # Optionally rollback transaction
    db.rollback()
    raise Exception(f"Failed to save theme to database: {str(e)}")
```

### 8. Testing Considerations
- Test with valid agent outputs to ensure proper data mapping
- Test error scenarios (missing fields, database connection issues)
- Verify foreign key relationships are properly established
- Ensure database sessions are properly managed and closed

## Implementation Order
1. Create/verify database models
2. Implement service functions
3. Update schemas if needed
4. Modify theme generator function
5. Update API endpoint
6. Test end-to-end functionality

## Notes
- The database session management should follow the existing patterns in your application
- Make sure to handle the async/await patterns consistently
- Consider adding validation for required fields from agent outputs
- The current agent outputs should provide all necessary data for database persistence
