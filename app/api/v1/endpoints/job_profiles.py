from fastapi import APIRouter, HTTPException, Depends
from app.schemas.JobProfileSchemas import JobProfileResponse, JobProfileCreate, JobProfileUpdate
from app.services import job_profile_service
from typing import List, Optional

router = APIRouter()

@router.get("/", response_model=List[JobProfileResponse])
async def list_job_profiles(user_id: Optional[str] = None):
    if user_id:
        return await job_profile_service.get_user_job_profiles(user_id)
    # If no user_id, maybe return empty or all? For now, let's return empty to be safe or all if admin.
    # But for this refactor, we mostly care about user_id filtering.
    # Let's return all if no user_id is provided, but paginated?
    # For simplicity, let's assume user_id is required for listing or we return empty list.
    return []

@router.get("/{job_profile_id}", response_model=JobProfileResponse)
async def read_job_profile(job_profile_id: str):
    job_profile = await job_profile_service.get_job_profile(job_profile_id)
    if not job_profile:
        raise HTTPException(status_code=404, detail="Job Profile not found")
    return job_profile

@router.post("/", response_model=JobProfileResponse)
async def create_job_profile(job_profile_in: JobProfileCreate):
    return await job_profile_service.create_job_profile(job_profile_in)

@router.put("/{job_profile_id}", response_model=JobProfileResponse)
async def update_job_profile(job_profile_id: str, job_profile_in: JobProfileUpdate):
    job_profile = await job_profile_service.update_job_profile(job_profile_id, job_profile_in)
    if not job_profile:
        raise HTTPException(status_code=404, detail="Job Profile not found")
    return job_profile

@router.delete("/{job_profile_id}")
async def delete_job_profile(job_profile_id: str):
    success = await job_profile_service.delete_job_profile(job_profile_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job Profile not found")
    return {"status": 200, "message": "Job Profile deleted successfully"}
