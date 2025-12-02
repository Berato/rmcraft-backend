"""
Resume Service

Service layer for resume operations.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
from app.repositories.resume_repository import resume_repository
from app.schemas.ResumeSchemas import ResumeResponse
from app.services.resume_normalization import (
    ensure_list_of_dicts,
    normalize_skills,
    normalize_projects,
    normalize_personal_info,
)

logger = logging.getLogger(__name__)


async def get_resumes(skip: int = 0, limit: int = 100, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve a list of resumes with pagination and optional user filtering.
    """
    query = {}
    if user_id:
        query["userId"] = user_id
        
    resumes = await resume_repository.find(query, skip=skip, limit=limit)
    return [r.model_dump(by_alias=True) for r in resumes]


async def get_resume(resume_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a single resume by id.
    """
    # Try finding by _id (ObjectId) or string id
    resume = await resume_repository.find_one({"_id": resume_id})
    if not resume:
        resume = await resume_repository.find_one({"id": resume_id})
        
    if not resume:
        return None

    return resume.model_dump(by_alias=True)


async def get_resume_obj(resume_id: str) -> Optional[ResumeResponse]:
    """
    Retrieve a single resume object (Beanie Document).
    """
    resume = await resume_repository.find_one({"_id": resume_id})
    if not resume:
        resume = await resume_repository.find_one({"id": resume_id})
    return resume


async def create_resume(resume_data: Dict[str, Any]) -> ResumeResponse:
    """
    Create a new resume.
    """
    # Ensure userId is present
    if not resume_data.get("userId"):
        resume_data["userId"] = "00000000-0000-0000-0000-000000000000"
        
    resume = await resume_repository.create(resume_data)
    return resume


async def update_resume(resume_id: str, update_data: Dict[str, Any]) -> Optional[ResumeResponse]:
    """
    Update an existing resume.
    """
    resume = await get_resume_obj(resume_id)
    if not resume:
        return None
        
    # Update fields
    if "updatedAt" not in update_data:
        update_data["updatedAt"] = datetime.utcnow()
        
    await resume.update({"$set": update_data})
    
    # Refresh
    return await get_resume_obj(resume_id)


async def delete_resume(resume_id: str) -> bool:
    """
    Delete a resume.
    """
    resume = await get_resume_obj(resume_id)
    if not resume:
        return False
        
    await resume.delete()
    return True


# Helper functions for normalization (kept for compatibility if needed, though Beanie handles most)
def _model_to_normalized_dict(r: Any) -> Dict[str, Any]:
    """
    Convert a resume model instance into the normalized dict shape.
    Useful if we still have some raw dicts floating around.
    """
    if isinstance(r, dict):
        return r
        
    # If it's a Beanie document, dump it
    if hasattr(r, 'model_dump'):
        return r.model_dump(by_alias=True)
        
    # Fallback for legacy objects (shouldn't happen with full migration)
    item = {
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

    return item
