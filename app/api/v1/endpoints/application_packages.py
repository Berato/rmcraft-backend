from fastapi import APIRouter, HTTPException, Depends
from app.schemas.ApplicationPackageSchemas import ApplicationPackageResponse, ApplicationPackageCreate, ApplicationPackageUpdate
from app.services import application_package_service
from typing import List, Optional

router = APIRouter()

@router.get("/", response_model=List[ApplicationPackageResponse])
async def list_application_packages(user_id: Optional[str] = None, job_profile_id: Optional[str] = None):
    if user_id:
        return await application_package_service.get_user_application_packages(user_id)
    if job_profile_id:
        return await application_package_service.get_profile_application_packages(job_profile_id)
    return []

@router.get("/{package_id}", response_model=ApplicationPackageResponse)
async def read_application_package(package_id: str):
    package = await application_package_service.get_application_package(package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Application Package not found")
    return package

@router.post("/", response_model=ApplicationPackageResponse)
async def create_application_package(package_in: ApplicationPackageCreate):
    return await application_package_service.create_application_package(package_in)

@router.put("/{package_id}", response_model=ApplicationPackageResponse)
async def update_application_package(package_id: str, package_in: ApplicationPackageUpdate):
    package = await application_package_service.update_application_package(package_id, package_in)
    if not package:
        raise HTTPException(status_code=404, detail="Application Package not found")
    return package

@router.delete("/{package_id}")
async def delete_application_package(package_id: str):
    success = await application_package_service.delete_application_package(package_id)
    if not success:
        raise HTTPException(status_code=404, detail="Application Package not found")
    return {"status": 200, "message": "Application Package deleted successfully"}
