"""
Cover Letters API Endpoints

Endpoints for strategic cover letter generation.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
# from sqlalchemy.orm import Session  <-- Removed
from app.features.cover_letter_orchestrator import cover_letter_orchestrator
from app.services.cover_letter_service import list_cover_letters, get_cover_letter_by_id, save_cover_letter
# from app.db.session import get_db <-- Removed
from beanie import Document
from datetime import datetime
from uuid import UUID
# from app.models.cover_letter import CoverLetter <-- Removed
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

        if not request.jobDescriptionUrl and not request.jobDescriptionText:
             raise HTTPException(status_code=400, detail="Either jobDescriptionUrl or jobDescriptionText must be provided")

        # Generate the cover letter using the orchestrator
        cover_letter_data = await cover_letter_orchestrator(
            resume_id=request.resumeId,
            job_description_url=request.jobDescriptionUrl,
            job_description_text=request.jobDescriptionText,
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
    userId: Optional[str] = None,
    # db: Session = Depends(get_db) <-- Removed
):
    """
    List cover letters with pagination, filtering, and search.

    This endpoint provides a paginated, filterable list of cover letters.
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
        if userId:
            filters['userId'] = userId

        # Call service (awaited)
        result = await list_cover_letters(
            # db=db, <-- Removed
            page=page,
            per_page=perPage,
            filters=filters if filters else None,
            search=search,
            sort_by=sortBy,
            sort_order=sortOrder,
            include=include_list
        )

        # Format response
        # Note: result['items'] are already dicts from the service
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


@router.get("/{cover_letter_id}", response_model=CoverLetterAPIResponse)
async def read_cover_letter(cover_letter_id: str):
    """
    Retrieve a single cover letter by ID.
    """
    try:
        cl = await get_cover_letter_by_id(cover_letter_id)
        
        # Convert to response model
        # We need to map the dict to StrategicCoverLetterResponse structure
        # Or we can just return the dict if the response model allows it
        # CoverLetterAPIResponse expects data: StrategicCoverLetterResponse
        
        # We need to reconstruct the response object
        job_details = JobProfileDetails(**cl.get("jobDetails", {}))
        response_data = StrategicCoverLetterResponse(
            title=cl.get("title", "Cover Letter"),
            jobDetails=job_details,
            openingParagraph=cl.get("openingParagraph", ""),
            bodyParagraphs=cl.get("bodyParagraphs", []),
            companyConnection=cl.get("companyConnection"),
            closingParagraph=cl.get("closingParagraph", ""),
            tone=cl.get("tone", "professional"),
            resumeId=cl.get("resumeId"),
            jobProfileId=cl.get("jobProfileId"),
            createdAt=cl.get("createdAt", ""),
            updatedAt=cl.get("updatedAt", ""),
            wordCount=cl.get("wordCount", 0),
            coverLetterId=cl.get("id"), # Use id as coverLetterId
            persistenceError=None
        )

        return CoverLetterAPIResponse(
            status=200,
            message="Cover letter retrieved successfully",
            data=response_data
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cover letter: {str(e)}")


@router.put("/{cover_letter_id}", response_model=CoverLetterAPIResponse)
async def update_cover_letter_endpoint(cover_letter_id: str, cover_letter_in: Dict[str, Any]):
    """
    Update a cover letter.
    """
    try:
        from app.services.cover_letter_service import update_cover_letter
        cl = await update_cover_letter(cover_letter_id, cover_letter_in)
        
        if not cl:
             raise HTTPException(status_code=404, detail="Cover letter not found")

        # Reconstruct response
        job_details = JobProfileDetails(**cl.get("jobDetails", {}))
        response_data = StrategicCoverLetterResponse(
            title=cl.get("title", "Cover Letter"),
            jobDetails=job_details,
            openingParagraph=cl.get("openingParagraph", ""),
            bodyParagraphs=cl.get("bodyParagraphs", []),
            companyConnection=cl.get("companyConnection"),
            closingParagraph=cl.get("closingParagraph", ""),
            tone=cl.get("tone", "professional"),
            resumeId=cl.get("resumeId"),
            jobProfileId=cl.get("jobProfileId"),
            createdAt=cl.get("createdAt", ""),
            updatedAt=cl.get("updatedAt", ""),
            wordCount=cl.get("wordCount", 0),
            coverLetterId=cl.get("id"),
            persistenceError=None
        )

        return CoverLetterAPIResponse(
            status=200,
            message="Cover letter updated successfully",
            data=response_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update cover letter: {str(e)}")


@router.delete("/{cover_letter_id}")
async def delete_cover_letter_endpoint(cover_letter_id: str):
    """
    Delete a cover letter.
    """
    try:
        from app.services.cover_letter_service import delete_cover_letter
        success = await delete_cover_letter(cover_letter_id)
        if not success:
            raise HTTPException(status_code=404, detail="Cover letter not found")
        return {"status": 200, "message": "Cover letter deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete cover letter: {str(e)}")


@router.post("/manual-create", response_model=CoverLetterManualResponse)
async def create_manual_cover_letter(request: CoverLetterManualCreate): # db: Session = Depends(get_db) <-- Removed
    """
    Create a cover letter manually without using AI agents.

    This endpoint allows clients to provide their own cover letter content
    and metadata, which is then validated and stored in the database.
    """
    try:
        # Validate and sanitize the raw_text (limit size to prevent abuse)
        if len(request.raw_text) > 50000:  # 50KB limit
            raise HTTPException(status_code=422, detail="Cover letter text exceeds maximum length (50KB)")

        # Prepare data for service
        cover_letter_data = {
            "title": request.title,
            "finalContent": request.raw_text,
            "resumeId": str(request.resume_id) if request.resume_id else None,
            "jobProfileId": str(request.job_profile_id) if request.job_profile_id else None,
            "userId": str(request.user_id) if request.user_id else None,
            "tone": "manual",
            "wordCount": len(request.raw_text.split()),
            "metadata": {"notes": request.notes} if request.notes else None,
            "openingParagraph": "", # Required by validator/schema but not manual input
            "bodyParagraphs": [],   # Required by validator/schema
            "closingParagraph": ""  # Required by validator/schema
        }
        
        # Save using service (awaited)
        saved_data = await save_cover_letter(cover_letter_data)

        # Return the response
        return CoverLetterManualResponse(
            id=UUID(str(saved_data['id'])), # Ensure UUID format for response model
            title=saved_data['title'],
            resume_id=UUID(saved_data['resumeId']) if saved_data.get('resumeId') else None,
            job_profile_id=UUID(saved_data['jobProfileId']) if saved_data.get('jobProfileId') else None,
            content=saved_data.get('finalContent', ''),
            notes=saved_data.get('metadata', {}).get('notes') if saved_data.get('metadata') else None,
            created_at=datetime.fromisoformat(saved_data['createdAt']) if isinstance(saved_data['createdAt'], str) else saved_data['createdAt'],
            updated_at=datetime.fromisoformat(saved_data['updatedAt']) if isinstance(saved_data['updatedAt'], str) else saved_data['updatedAt'],
            created_by=UUID(saved_data['userId']) if saved_data.get('userId') else None
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"❌ Error creating manual cover letter: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create cover letter: {str(e)}")
