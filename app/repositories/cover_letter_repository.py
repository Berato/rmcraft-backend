from typing import List, Optional, Dict, Any
from app.repositories.base import BaseRepository
from app.schemas.CoverLetterSchemas import CoverLetterFull

class CoverLetterRepository(BaseRepository[CoverLetterFull]):
    """
    Repository for Cover Letter operations.
    """
    def __init__(self):
        super().__init__(CoverLetterFull)

    async def get_by_resume_id(self, resume_id: str, skip: int = 0, limit: int = 100) -> List[CoverLetterFull]:
        """
        Get all cover letters for a specific resume.
        """
        return await self.model.find({"resumeId": resume_id}).skip(skip).limit(limit).to_list()

    async def get_by_user_id(self, user_id: str, skip: int = 0, limit: int = 100) -> List[CoverLetterFull]:
        """
        Get all cover letters for a specific user.
        """
        return await self.model.find({"userId": user_id}).skip(skip).limit(limit).to_list()

cover_letter_repository = CoverLetterRepository()
