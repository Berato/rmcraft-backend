from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Any, Dict, Optional, Union
from pydantic import BaseModel, Field
import json
# from app.crud import crud_resume <-- Removed
from app.schemas.ResumeSchemas import ResumeResponse, ResumeListResponse, ResumeSingleResponse
from app.workflows.resume.simple_resume_parser import parse_resume_simple
# from app.db.session import get_db <-- Removed
from app.services.pdf_service import extract_text_from_pdf
from app.services import resume_service
from app.agents.resume.strategic.strategic_resume_agent import strategic_resume_agent
from app.agents.resume.strategic.strategy_advisor import strategy_advisor_isolated
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
async def read_resumes(skip: int = 0, limit: int = 100, user_id: Optional[str] = None):
    """
    Retrieve a list of resumes with pagination.
    
    Args:
        skip: Number of resumes to skip for pagination.
        limit: Maximum number of resumes to return.
        user_id: Optional user ID to filter by.
    """
    try:
        # Use service to get resumes
        resumes_data = await resume_service.get_resumes(skip=skip, limit=limit, user_id=user_id)
        
        # Convert dicts back to ResumeResponse objects for Pydantic validation if needed, 
        # or just pass dicts if response model allows (ResumeListResponse expects List[ResumeResponse])
        # ResumeResponse is a Beanie Document, so it can accept dicts in constructor or we can just return the dicts 
        # if Pydantic ConfigDict(from_attributes=True) is set (which it is).
        
        # However, ResumeListResponse.data is List[ResumeResponse]. 
        # Beanie documents are Pydantic models.
        resumes = [ResumeResponse(**r) for r in resumes_data]

        return {"status": 200, "message": "Resumes returned successfully", "data": resumes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{resume_id}", response_model=ResumeSingleResponse)
async def read_resume(resume_id: str): # db: Session = Depends(get_db) <-- Removed
    resume = await resume_service.get_resume_obj(resume_id)

    if not resume:
        return {"status": 404, "message": "Resume not found", "data": None}

    return {"status": 200, "message": "Resume returned successfully", "data": resume}


@router.post("/", response_model=ResumeSingleResponse)
async def create_resume_manual(resume_in: Dict[str, Any]):
    """
    Create a resume manually.
    """
    try:
        resume = await resume_service.create_resume(resume_in)
        return {"status": 201, "message": "Resume created successfully", "data": resume}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create resume: {str(e)}")


@router.put("/{resume_id}", response_model=ResumeSingleResponse)
async def update_resume(resume_id: str, resume_in: Dict[str, Any]):
    """
    Update a resume.
    """
    try:
        resume = await resume_service.update_resume(resume_id, resume_in)
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        return {"status": 200, "message": "Resume updated successfully", "data": resume}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update resume: {str(e)}")


@router.delete("/{resume_id}")
async def delete_resume(resume_id: str):
    """
    Delete a resume.
    """
    try:
        success = await resume_service.delete_resume(resume_id)
        if not success:
            raise HTTPException(status_code=404, detail="Resume not found")
        return {"status": 200, "message": "Resume deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete resume: {str(e)}")


@router.post("/strategic-analysis", response_model=StrategicResumeResponse)
async def strategic_resume_analysis(
    resume_id: str = Form(...),
    job_description_url: str = Form(...),
    theme_id: Optional[str] = Form(None),
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
        resume = await resume_service.get_resume_obj(resume_id)
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Call the strategic resume agent with a safe timeout to avoid hanging requests
        try:
            result = await asyncio.wait_for(
                strategic_resume_agent(
                    resume=resume,
                    job_description_url=job_description_url
                ),
                timeout=650.0,
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


@router.post("/strategy-advisor", response_model=StrategicResumeResponse)
async def test_strategy_advisor(
    resume_id: str = Form(...),
    job_description_url: str = Form(...),
):
    """
    This endpoint develops a full strategy for creating a strategic resume and cover letter.
    
    This endpoint uses the strategy advisor in isolation to:
    - Parse and analyze the resume content
    - Extract relevant information from the job description URL
    - Return plain text strategic analysis
    """
    try:
        # Validate that the resume exists
        resume = await resume_service.get_resume_obj(resume_id)
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Call the strategy advisor with a safe timeout
        try:
            strategy = await asyncio.wait_for(
                strategy_advisor_isolated(
                    resume=resume,
                    job_description_url=job_description_url
                ),
                timeout=65.0,
            )
            # The strategy is generated but not currently used by agents
            # TODO: Integrate strategy with agents when they support it
            pass
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Strategy advisor timed out; try again or check agent logs")
        
        return {
            "status": 200,
            "message": "Experience agent test completed successfully",
            "data": ""
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