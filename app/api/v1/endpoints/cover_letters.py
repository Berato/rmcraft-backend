"""
Cover Letters API Endpoints

Endpoints for strategic cover letter generation.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.features.cover_letter_orchestrator import cover_letter_orchestrator
from app.services.cover_letter_service import list_cover_letters, get_cover_letter_by_id
from app.db.session import get_db
from beanie import Document
from datetime import datetime
from uuid import UUID
from app.models.cover_letter import CoverLetter
from app.schemas.CoverLetterSchemas import (
    StrategicCoverLetterRequest,
    JobProfileDetails,
    StrategicCoverLetterResponse,
    CoverLetterAPIResponse,
    CoverLetterFull,
    CoverLetterSingleResponse,
    CoverLetterSummary,
    CoverLetterListMeta,
    CoverLetterListData,
    CoverLetterListResponse,
)
from app.schemas.cover_letter_manual import CoverLetterManualCreate, CoverLetterManualResponse

router = APIRouter()

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
            resumeId=cover_letter_data.get("resumeId", request.resumeId),
            jobProfileId=cover_letter_data.get("jobProfileId"),
            createdAt=cover_letter_data.get("createdAt", ""),
            updatedAt=cover_letter_data.get("updatedAt", ""),
            wordCount=cover_letter_data.get("wordCount", 0),
            coverLetterId=cover_letter_data.get("coverLetterId"),
            persistenceError=cover_letter_data.get("persistenceError")
        )

        print("✅ Strategic cover letter generated successfully")
        print(f"   Word count: {response_data.wordCount}")
        print(f"   Tone: {response_data.tone}")

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


@router.get("/", response_model=CoverLetterListResponse)
async def list_cover_letters_endpoint(
    page: int = 1,
    perPage: int = 20,
    resumeId: Optional[str] = None,
    jobProfileId: Optional[str] = None,
    search: Optional[str] = None,
    sortBy: str = "createdAt",
    sortOrder: str = "desc",
    include: Optional[str] = None,
    from_date: Optional[str] = None,  # Changed from 'from' to 'from_date' to avoid Python keyword
    to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List cover letters with pagination, filtering, and search.

    This endpoint provides a paginated, filterable list of cover letters.

    Query Parameters:
    - **page**: Page number (default: 1)
    - **perPage**: Items per page (default: 20, max: 100)
    - **resumeId**: Filter by resume ID
    - **jobProfileId**: Filter by job profile ID
    - **from_date**: Filter by created date >= from_date (ISO format)
    - **to**: Filter by created date <= to (ISO format)
    - **search**: Free text search in title and content
    - **sortBy**: Sort field (createdAt, wordCount, atsScore)
    - **sortOrder**: Sort order (asc, desc)
    - **include**: Comma-separated list of fields to include (e.g., "finalContent")
    """
    try:
        # Parse include parameter
        include_list = None
        if include:
            include_list = [field.strip() for field in include.split(",")]

        # Build filters
        filters = {}
        if resumeId:
            filters['resumeId'] = resumeId
        if jobProfileId:
            filters['jobProfileId'] = jobProfileId
        if from_date:
            filters['from_date'] = from_date
        if to:
            filters['to_date'] = to

        # Call service
        result = list_cover_letters(
            db=db,
            page=page,
            per_page=perPage,
            filters=filters if filters else None,
            search=search,
            sort_by=sortBy,
            sort_order=sortOrder,
            include=include_list
        )

        # Format response
        items = [CoverLetterSummary(**item) for item in result['items']]
        meta = CoverLetterListMeta(**result['meta'])
        data = CoverLetterListData(items=items, meta=meta)
        
        response_data = CoverLetterListResponse(
            status=200,
            message="Cover letters retrieved successfully",
            data=data
        )

        return response_data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error listing cover letters: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list cover letters: {str(e)}"
        )


@router.post("/manual-create", response_model=CoverLetterManualResponse)
async def create_manual_cover_letter(request: CoverLetterManualCreate, db: Session = Depends(get_db)):
    """
    Create a cover letter manually without using AI agents.

    This endpoint allows clients to provide their own cover letter content
    and metadata, which is then validated and stored in the database.
    """
    try:
        # Validate and sanitize the raw_text (limit size to prevent abuse)
        if len(request.raw_text) > 50000:  # 50KB limit
            raise HTTPException(status_code=422, detail="Cover letter text exceeds maximum length (50KB)")

        # Create the cover letter record
        cover_letter = CoverLetter(
            title=request.title,
            finalContent=request.raw_text,  # Store the manual text here
            resumeId=str(request.resume_id) if request.resume_id else None,
            jobProfileId=str(request.job_profile_id) if request.job_profile_id else None,
            userId=str(request.user_id) if request.user_id else None,
            # Set defaults for other fields
            tone="manual",
            wordCount=len(request.raw_text.split()),  # Approximate word count
            metadata_json={"notes": request.notes} if request.notes else None,
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )

        # Save to database
        db.add(cover_letter)
        db.commit()
        db.refresh(cover_letter)

        # Return the response
        return CoverLetterManualResponse(
            id=UUID(cover_letter.id),
            title=cover_letter.title,
            resume_id=UUID(cover_letter.resumeId) if cover_letter.resumeId else None,
            job_profile_id=UUID(cover_letter.jobProfileId) if cover_letter.jobProfileId else None,
            content=cover_letter.finalContent,
            notes=request.notes,
            created_at=cover_letter.createdAt,
            updated_at=cover_letter.updatedAt,
            created_by=UUID(cover_letter.userId) if cover_letter.userId else None
        )

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating manual cover letter: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create cover letter: {str(e)}")
