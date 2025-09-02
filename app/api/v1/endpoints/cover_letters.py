"""
Cover Letters API Endpoints

Endpoints for strategic cover letter generation.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.features.cover_letter_orchestrator import cover_letter_orchestrator

router = APIRouter()


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
    finalContent: str
    resumeId: str
    jobProfileId: Optional[str] = None
    createdAt: str
    updatedAt: str
    wordCount: int = 0
    atsScore: int = 7
    coverLetterId: Optional[str] = None
    persistenceError: Optional[str] = None


class CoverLetterAPIResponse(BaseModel):
    """API envelope for cover letter responses"""
    status: int
    message: str
    data: StrategicCoverLetterResponse


@router.post("/strategic-create", response_model=CoverLetterAPIResponse)
async def create_strategic_cover_letter(request: StrategicCoverLetterRequest):
    """
    Generate a strategic cover letter using AI analysis.

    This endpoint creates a personalized cover letter by:
    1. Analyzing the resume and job description
    2. Identifying key matches and qualifications
    3. Writing compelling content tailored to the role
    4. Editing for clarity, tone, and ATS-friendliness

    Returns a complete cover letter with structured components and final formatted content.
    """
    try:
        print("📨 Received strategic cover letter request")
        print(f"   Resume ID: {request.resumeId}")
        print(f"   Job URL: {request.jobDescriptionUrl}")
        print(f"   Custom prompt: {request.prompt}")

        # Generate the cover letter using the orchestrator
        cover_letter_data = await cover_letter_orchestrator(
            resume_id=request.resumeId,
            job_description_url=request.jobDescriptionUrl,
            optional_prompt=request.prompt,
            save_to_db=request.saveToDb
        )

        # Validate the response structure
        if not cover_letter_data:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate cover letter"
            )

        # Convert to response model
        job_details = JobProfileDetails(**cover_letter_data.get("jobDetails", {}))
        response_data = StrategicCoverLetterResponse(
            title=cover_letter_data.get("title", "Strategic Cover Letter"),
            jobDetails=job_details,
            openingParagraph=cover_letter_data.get("openingParagraph", ""),
            bodyParagraphs=cover_letter_data.get("bodyParagraphs", []),
            companyConnection=cover_letter_data.get("companyConnection"),
            closingParagraph=cover_letter_data.get("closingParagraph", ""),
            tone=cover_letter_data.get("tone", "professional"),
            finalContent=cover_letter_data.get("finalContent", ""),
            resumeId=cover_letter_data.get("resumeId", request.resumeId),
            jobProfileId=cover_letter_data.get("jobProfileId"),
            createdAt=cover_letter_data.get("createdAt", ""),
            updatedAt=cover_letter_data.get("updatedAt", ""),
            wordCount=cover_letter_data.get("wordCount", 0),
            atsScore=cover_letter_data.get("atsScore", 7),
            coverLetterId=cover_letter_data.get("coverLetterId"),
            persistenceError=cover_letter_data.get("persistenceError")
        )

        print("✅ Strategic cover letter generated successfully")
        print(f"   Word count: {response_data.wordCount}")
        print(f"   Tone: {response_data.tone}")
        print(f"   ATS Score: {response_data.atsScore}")

        return CoverLetterAPIResponse(
            status=201,  # Created
            message="Strategic cover letter generated successfully",
            data=response_data
        )

    except ValueError as e:
        # Handle validation errors (e.g., resume not found)
        print(f"❌ Validation error: {e}")
        if "Resume not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        elif "No resume data found" in str(e):
            raise HTTPException(status_code=422, detail="Resume contains no usable data")
        else:
            raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        # Handle unexpected errors
        print(f"❌ Unexpected error in cover letter generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate cover letter: {str(e)}"
        )
