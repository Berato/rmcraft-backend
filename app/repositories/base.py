from typing import TypeVar, Generic, List, Optional, Type, Any, Dict, Union
from beanie import Document, PydanticObjectId
from pydantic import BaseModel
from pymongo.results import DeleteResult

T = TypeVar("T", bound=Document)

class BaseRepository(Generic[T]):
    """
    Base repository for MongoDB operations using Beanie.
    """
    def __init__(self, model: Type[T]):
        self.model = model

    async def get(self, id: PydanticObjectId) -> Optional[T]:
        """
        Get a document by ID.
        """
        return await self.model.get(id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """
        Get all documents with pagination.
        """
        return await self.model.find_all().skip(skip).limit(limit).to_list()

    async def create(self, data: Union[T, Dict[str, Any]]) -> T:
        """
        Create a new document.
        """
        if isinstance(data, dict):
            document = self.model(**data)
        else:
            document = data
        await document.insert()
        return document

    async def update(self, id: PydanticObjectId, data: Dict[str, Any]) -> Optional[T]:
        """
        Update a document by ID.
        """
        document = await self.get(id)
        if document:
            await document.set(data)
            return document
        return None

    async def delete(self, id: PydanticObjectId) -> bool:
        """
        Delete a document by ID.
        """
        document = await self.get(id)
        if document:
            await document.delete()
            return True
        return False

    async def find_one(self, query: Dict[str, Any]) -> Optional[T]:
        """
        Find a single document matching the query.
        """
        return await self.model.find_one(query)

    async def find(self, query: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[T]:
        """
        Find documents matching the query with pagination.
        """
        return await self.model.find(query).skip(skip).limit(limit).to_list()
