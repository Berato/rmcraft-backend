from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Any, Dict, Optional, Union
from pydantic import BaseModel, Field
import json
from app.crud import crud_resume
from app.schemas.ResumeSchemas import ResumeResponse, ResumeListResponse, ResumeSingleResponse
from app.workflows.resume.simple_resume_parser import parse_resume_simple
from app.db.session import get_db
from app.services.pdf_service import extract_text_from_pdf
from app.services.resume_normalization import (
    ensure_list_of_dicts,
    normalize_skills,
    normalize_projects,
    normalize_personal_info,
)
from app.agents.resume.strategic.strategic_resume_agent import strategic_resume_agent
from app.agents.resume.strategic.experience_agent import experience_agent_isolated
import asyncio

router = APIRouter()


class StrategicResumeResponse(BaseModel):
    status: int
    message: str
    # Use Union to allow multiple types, including dict, list, string, or None
    data: Optional[Union[Dict[str, Any], List[Any], str]] = None


class StrategicResumeRequest(BaseModel):
    resume_id: str = Field(..., description="The ID of the resume to analyze")
    job_description_url: str = Field(..., description="URL of the job description to analyze against")
    theme_id: Optional[str] = Field(None, description="Optional theme ID for PDF generation")


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
async def read_resume(resume_id: str, db: Session = Depends(get_db)):
    resume = await ResumeResponse.find_one({"_id": resume_id})

    if not resume:
        return {"status": 404, "message": "Resume not found", "data": None}

    return {"status": 200, "message": "Resume returned successfully", "data": resume}


@router.post("/strategic-analysis", response_model=StrategicResumeResponse)
async def strategic_resume_analysis(
    resume_id: str = Form(...),
    job_description_url: str = Form(...),
    theme_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Analyze a resume strategically against a job description using AI agents.
    
    This endpoint uses Google ADK agents to:
    - Parse and analyze the resume content
    - Extract relevant information from the job description URL
    - Match relevant experience, skills, and projects
    - Provide strategic recommendations for resume optimization
    """
    try:
        # Validate that the resume exists
        resume = await ResumeResponse.find_one({"_id": resume_id})
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Call the strategic resume agent with a safe timeout to avoid hanging requests
        try:
            result = await asyncio.wait_for(
                strategic_resume_agent(
                    resume=resume,
                    job_description_url=job_description_url
                ),
                timeout=65.0,
            )

            validated_result = None
            if result and isinstance(result, dict):  # Check if result is valid and is a dictionary
                validated_result = ResumeResponse.model_validate(result)  # Validate the result structure
                await validated_result.save()  # Insert into the database
        except asyncio.TimeoutError:
            # Agents didn't produce a final response in time — return a timeout to the client
            raise HTTPException(status_code=504, detail="Strategic analysis timed out; try again or check agent logs")
        
        return {
            "status": 200,
            "message": "Strategic analysis completed successfully",
            "data": validated_result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/test-experience-agent", response_model=StrategicResumeResponse)
async def test_experience_agent(
    resume_id: str = Form(...),
    job_description_url: str = Form(...),
):
    """
    Test the isolated experience agent against a job description.
    
    This endpoint uses the experience agent in isolation to:
    - Parse and analyze the resume content
    - Extract relevant information from the job description URL
    - Return plain text experience analysis
    """
    try:
        # Validate that the resume exists
        resume = await ResumeResponse.find_one({"_id": resume_id})
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Call the experience agent with a safe timeout
        try:
            result = await asyncio.wait_for(
                experience_agent_isolated(
                    resume=resume,
                    job_description_url=job_description_url
                ),
                timeout=65.0,
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Experience agent timed out; try again or check agent logs")
        
        return {
            "status": 200,
            "message": "Experience agent test completed successfully",
            "data": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/create-from-pdf", response_model=ResumeSingleResponse)
async def create_resume_from_pdf(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None, description="User ID to associate with the resume"),
):
    """
    Create a resume from a PDF file.
    
    Args:
        file: PDF file to extract resume data from
        user_id: Optional user ID to associate with the resume. If not provided, 
                will use a default anonymous user approach.
    """
    try:
        # Read the PDF file
        pdf_content = await file.read()
        # Extract text from the PDF
        text = extract_text_from_pdf(pdf_content)
        # Create a new resume object by asking the AI to extract JSON matching our schema
        try:
            resume_obj: ResumeResponse = parse_resume_simple(text, user_id)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to parse resume via AI: {e}")

        # Save the resume to the database - no more complex userId handling needed!
        try:
            saved_resume = await resume_obj.save()
            return {"status": 201, "message": "Resume created successfully", "data": saved_resume}
        except Exception as e:
            # If the foreign key constraint fails, provide a better error message
            if "foreign key constraint" in str(e) and "userId" in str(e):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid user_id provided. Please provide a valid user_id parameter or ensure the user exists in the system."
                )
            raise HTTPException(status_code=500, detail=f"Failed to save resume to database: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")