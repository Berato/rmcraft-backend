from app.schemas.ApplicationPackageSchemas import ApplicationPackage, ApplicationPackageCreate, ApplicationPackageUpdate
from typing import Optional, List
from datetime import datetime

async def get_application_package(package_id: str) -> Optional[ApplicationPackage]:
    return await ApplicationPackage.get(package_id)

async def create_application_package(package_in: ApplicationPackageCreate) -> ApplicationPackage:
    package = ApplicationPackage(
        userId=package_in.userId,
        jobProfileId=package_in.jobProfileId,
        resumeId=package_in.resumeId,
        coverLetterId=package_in.coverLetterId,
        status=package_in.status
    )
    await package.save()
    return package

async def update_application_package(package_id: str, package_in: ApplicationPackageUpdate) -> Optional[ApplicationPackage]:
    package = await ApplicationPackage.get(package_id)
    if not package:
        return None
    
    update_data = package_in.model_dump(exclude_unset=True)
    if update_data:
        update_data["updatedAt"] = datetime.now()
        await package.update({"$set": update_data})
        # Refresh
        package = await ApplicationPackage.get(package_id)
        
    return package

async def delete_application_package(package_id: str) -> bool:
    package = await ApplicationPackage.get(package_id)
    if not package:
        return False
    
    await package.delete()
    return True

async def get_user_application_packages(user_id: str) -> List[ApplicationPackage]:
    return await ApplicationPackage.find(ApplicationPackage.userId == user_id).sort("-updatedAt").to_list()

async def get_profile_application_packages(job_profile_id: str) -> List[ApplicationPackage]:
    return await ApplicationPackage.find(ApplicationPackage.jobProfileId == job_profile_id).sort("-updatedAt").to_list()
