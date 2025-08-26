from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Any, Dict
from app.crud import crud_resume
from app.schemas.ResumeSchemas import ResumeResponse, ResumeListResponse, ResumeSingleResponse
from app.db.session import get_db
from app.services.resume_normalization import (
    ensure_list_of_dicts,
    normalize_skills,
    normalize_projects,
    normalize_personal_info,
)

router = APIRouter()


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
