from app.schemas.JobProfileSchemas import JobProfile, JobProfileCreate, JobProfileUpdate
from typing import Optional, List
from datetime import datetime

async def get_job_profile(job_profile_id: str) -> Optional[JobProfile]:
    return await JobProfile.get(job_profile_id)

async def create_job_profile(job_profile_in: JobProfileCreate) -> JobProfile:
    job_profile = JobProfile(
        name=job_profile_in.name,
        userId=job_profile_in.userId,
        jobDetails=job_profile_in.jobDetails,
        analysis=job_profile_in.analysis,
        insights=job_profile_in.insights,
        companyResearch=job_profile_in.companyResearch,
        skillsMatch=job_profile_in.skillsMatch,
        status=job_profile_in.status
    )
    await job_profile.save()
    return job_profile

async def update_job_profile(job_profile_id: str, job_profile_in: JobProfileUpdate) -> Optional[JobProfile]:
    job_profile = await JobProfile.get(job_profile_id)
    if not job_profile:
        return None
    
    update_data = job_profile_in.model_dump(exclude_unset=True)
    if update_data:
        update_data["updatedAt"] = datetime.now()
        await job_profile.update({"$set": update_data})
        # Refresh
        job_profile = await JobProfile.get(job_profile_id)
        
    return job_profile

async def delete_job_profile(job_profile_id: str) -> bool:
    job_profile = await JobProfile.get(job_profile_id)
    if not job_profile:
        return False
    
    await job_profile.delete()
    return True

async def get_user_job_profiles(user_id: str) -> List[JobProfile]:
    return await JobProfile.find(JobProfile.userId == user_id).sort("-updatedAt").to_list()
