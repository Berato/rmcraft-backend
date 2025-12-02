from typing import List, Optional
from app.repositories.base import BaseRepository
from app.schemas.ResumeSchemas import ResumeResponse

class ResumeRepository(BaseRepository[ResumeResponse]):
    """
    Repository for Resume operations.
    """
    def __init__(self):
        super().__init__(ResumeResponse)

    async def get_by_user_id(self, user_id: str, skip: int = 0, limit: int = 100) -> List[ResumeResponse]:
        """
        Get all resumes for a specific user.
        """
        return await self.model.find({"userId": user_id}).skip(skip).limit(limit).to_list()

resume_repository = ResumeRepository()
