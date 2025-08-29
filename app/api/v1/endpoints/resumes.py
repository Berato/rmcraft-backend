from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Any, Dict, Optional, Union
from pydantic import BaseModel, Field
from app.crud import crud_resume
from app.schemas.ResumeSchemas import ResumeResponse, ResumeListResponse, ResumeSingleResponse
from app.db.session import get_db
from app.services.resume_normalization import (
    ensure_list_of_dicts,
    normalize_skills,
    normalize_projects,
    normalize_personal_info,
)
from app.agents.resume.strategic.strategic_resume_agent import strategic_resume_agent

router = APIRouter()


class StrategicResumeRequest(BaseModel):
    resume_id: str
    job_description_url: str
    design_prompt: str


class StrategicResumeResponse(BaseModel):
    status: int
    message: str
    # Use Union to allow multiple types, including dict, list, string, or None
    data: Optional[Union[Dict[str, Any], List[Any], str]] = None


# normalization helpers moved to app.services.resume_normalization
@router.get("/", response_model=ResumeListResponse)
def read_resumes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    resumes = crud_resume.get_resumes(db, skip=skip, limit=limit)

    normalized = []
    for r in resumes:
        # r is a SQLAlchemy model with JSON columns; coerce into predictable dict
        item: Dict[str, Any] = {
            "id": getattr(r, "id", ""),
            "userId": getattr(r, "userId", ""),
            "name": getattr(r, "name", ""),
            "summary": getattr(r, "summary", "") or "",
                "personalInfo": normalize_personal_info(getattr(r, "personalInfo", None)),
                "experience": ensure_list_of_dicts(getattr(r, "experience", None)),
                "education": ensure_list_of_dicts(getattr(r, "education", None)),
                "skills": normalize_skills(getattr(r, "skills", None)),
                "projects": normalize_projects(getattr(r, "projects", None)),
            "jobDescription": getattr(r, "jobDescription", None),
            "jobProfileId": getattr(r, "jobProfileId", None),
            "themeId": getattr(r, "themeId", None),
            "createdAt": getattr(r, "createdAt", None),
            "updatedAt": getattr(r, "updatedAt", None),
        }
        normalized.append(item)

    return {"status": 200, "message": "Resumes returned successfully", "data": normalized}


@router.get("/{resume_id}", response_model=ResumeSingleResponse)
def read_resume(resume_id: str, db: Session = Depends(get_db)):
    r = crud_resume.get_resume(db, resume_id)
    if not r:
        return {"status": 404, "message": "Resume not found", "data": None}

    item: Dict[str, Any] = {
        "id": getattr(r, "id", ""),
        "userId": getattr(r, "userId", ""),
        "name": getattr(r, "name", ""),
        "summary": getattr(r, "summary", "") or "",
    "personalInfo": normalize_personal_info(getattr(r, "personalInfo", None)),
    "experience": ensure_list_of_dicts(getattr(r, "experience", None)),
    "education": ensure_list_of_dicts(getattr(r, "education", None)),
    "skills": normalize_skills(getattr(r, "skills", None)),
    "projects": normalize_projects(getattr(r, "projects", None)),
        "jobDescription": getattr(r, "jobDescription", None),
        "jobProfileId": getattr(r, "jobProfileId", None),
        "themeId": getattr(r, "themeId", None),
        "createdAt": getattr(r, "createdAt", None),
        "updatedAt": getattr(r, "updatedAt", None),
    }

    return {"status": 200, "message": "Resume returned successfully", "data": item}


@router.post("/strategic-analysis", response_model=StrategicResumeResponse)
async def strategic_resume_analysis(
    request: StrategicResumeRequest,
    inspiration_image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Analyze a resume strategically against a job description using AI agents and generate a custom PDF design.
    
    This endpoint uses Google ADK agents to:
    - Parse and analyze the resume content
    - Extract relevant information from the job description URL
    - Match relevant experience, skills, and projects
    - Provide strategic recommendations for resume optimization
    - Generate a custom PDF design based on inspiration image and design prompt
    - Upload the PDF to Cloudinary and return the secure URL
    """
    try:
        # Validate that the resume exists
        resume = crud_resume.get_resume(db, request.resume_id)
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Read the uploaded image file
        try:
            inspiration_image_data = await inspiration_image.read()
            inspiration_image_mime_type = inspiration_image.content_type
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading uploaded image: {str(e)}")
        
        # Call the strategic resume agent with new parameters
        result = await strategic_resume_agent(
            resume_id=request.resume_id,
            job_description_url=request.job_description_url,
            design_prompt=request.design_prompt,
            inspiration_image_data=inspiration_image_data,
            inspiration_image_mime_type=inspiration_image_mime_type
        )
        
        return {
            "status": 200,
            "message": "Strategic analysis and PDF generation completed successfully",
            "data": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
