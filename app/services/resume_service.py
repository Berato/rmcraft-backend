from typing import Any, Dict, List, Optional
import asyncio

from sqlalchemy.orm import Session

from app.crud import crud_resume
from app.db.session import SessionLocal
from app.services.resume_normalization import (
    ensure_list_of_dicts,
    normalize_skills,
    normalize_projects,
    normalize_personal_info,
)


def get_resumes_sync(skip: int = 0, limit: int = 100) -> List[Any]:
    """Synchronous service to retrieve resumes using the existing CRUD layer.

    This function manages its own DB session and returns raw SQLAlchemy results
    (the same objects the API layer expects to normalize).
    """
    db: Session = SessionLocal()
    try:
        return crud_resume.get_resumes(db, skip=skip, limit=limit)
    finally:
        db.close()


def get_resume_sync(resume_id: str) -> Optional[Any]:
    """Synchronous service to retrieve a single resume by id."""
    db: Session = SessionLocal()
    try:
        return crud_resume.get_resume(db, resume_id)
    finally:
        db.close()


async def async_get_resumes(skip: int = 0, limit: int = 100) -> List[Any]:
    """Async wrapper around get_resumes_sync."""
    return await asyncio.to_thread(get_resumes_sync, skip, limit)


async def async_get_resume(resume_id: str) -> Dict[str, Any]:
    """Async wrapper around get_resume_sync that returns the same shape
    as the API endpoint: {status, message, data}.
    """

    def _inner(rid: str):
        r = get_resume_sync(rid)
        if not r:
            return {"status": 404, "message": "Resume not found", "data": None}

        # coerce the SQLAlchemy model into a dict similarly to the endpoint
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

        return {"status": 200, "message": "Resume returned successfully", "data": item}

    return await asyncio.to_thread(_inner, resume_id)
