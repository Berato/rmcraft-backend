"""
Cover Letter Service

Service layer for cover letter operations, including CRUD utilities.
"""

from typing import Any, Dict, Optional, List
from datetime import datetime
import logging
from app.repositories.cover_letter_repository import cover_letter_repository
from app.repositories.resume_repository import resume_repository
from app.schemas.CoverLetterSchemas import CoverLetterFull

logger = logging.getLogger(__name__)


def validate_cover_letter_data(cover_letter_data: Dict[str, Any]) -> bool:
    """
    Validate cover letter data structure.

    Args:
        cover_letter_data: The cover letter data to validate

    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        "openingParagraph", "bodyParagraphs", "closingParagraph",
        "resumeId"
    ]

    for field in required_fields:
        if field not in cover_letter_data:
            return False

    # Check that body paragraphs is a list
    if not isinstance(cover_letter_data.get("bodyParagraphs", []), list):
        return False

    # Check that final content is not empty (if provided)
    # Note: AI generation might not provide finalContent immediately, so we relax this check 
    # if we are just saving components. But for manual creation it is usually required.
    # Keeping it loose for now to allow flexibility.
    
    return True


def format_cover_letter_for_storage(cover_letter_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format cover letter data for storage in database.

    Args:
        cover_letter_data: Raw cover letter data

    Returns:
        Formatted data ready for storage
    """
    # Add timestamps if not present
    if "createdAt" not in cover_letter_data:
        cover_letter_data["createdAt"] = datetime.utcnow().isoformat()

    if "updatedAt" not in cover_letter_data:
        cover_letter_data["updatedAt"] = datetime.utcnow().isoformat()

    # Ensure required fields have defaults
    defaults = {
        "title": "Strategic Cover Letter",
        "tone": "professional",
        "wordCount": len(cover_letter_data.get("finalContent", "").split()) if cover_letter_data.get("finalContent") else 0,
    }

    for key, default_value in defaults.items():
        if key not in cover_letter_data or cover_letter_data[key] is None:
            cover_letter_data[key] = default_value

    return cover_letter_data


def sanitize_cover_letter_content(content: str) -> str:
    """
    Sanitize cover letter content for safe storage/display.

    Args:
        content: Raw content string

    Returns:
        Sanitized content
    """
    if not content:
        return ""
    return content.strip()


async def save_cover_letter(cover_letter_data: Dict[str, Any], upsert: bool = False) -> Dict[str, Any]:
    """
    Save a cover letter to the database.

    Args:
        cover_letter_data: The cover letter data to save
        upsert: If True, update existing record if found (not implemented yet)

    Returns:
        Dict containing the saved cover letter data with id

    Raises:
        ValueError: If validation fails
        Exception: For database errors
    """
    try:
        # Validate the data
        if not validate_cover_letter_data(cover_letter_data):
            raise ValueError("Invalid cover letter data structure")

        # Format for storage
        formatted_data = format_cover_letter_for_storage(cover_letter_data)

        # Derive required relational fields from Resume
        resume_id = formatted_data.get('resumeId')
        if not resume_id:
            raise ValueError("resumeId is required to save a cover letter")

        # Use repository to fetch resume (async)
        # Note: resume_repository.get expects PydanticObjectId, but resumeId is string.
        # We use find_one with _id or id check.
        resume_obj = await resume_repository.find_one({"_id": resume_id})
        if not resume_obj:
            # Try looking up by string id if _id lookup failed (though they should be same)
            resume_obj = await resume_repository.find_one({"id": resume_id})
            
        if not resume_obj:
            raise ValueError(f"Resume not found for id: {resume_id}")

        # Ensure userId and themeId presence
        formatted_data['userId'] = resume_obj.userId
        formatted_data['themeId'] = resume_obj.themeId

        # Sanitize content
        if 'finalContent' in formatted_data:
            formatted_data['finalContent'] = sanitize_cover_letter_content(formatted_data['finalContent'])
        if 'openingParagraph' in formatted_data:
            formatted_data['openingParagraph'] = sanitize_cover_letter_content(formatted_data['openingParagraph'])
        if 'closingParagraph' in formatted_data:
            formatted_data['closingParagraph'] = sanitize_cover_letter_content(formatted_data['closingParagraph'])

        # Sanitize body paragraphs
        if 'bodyParagraphs' in formatted_data and isinstance(formatted_data['bodyParagraphs'], list):
            formatted_data['bodyParagraphs'] = [
                sanitize_cover_letter_content(para) for para in formatted_data['bodyParagraphs']
            ]

        # Sanitize company connection if present
        if 'companyConnection' in formatted_data and formatted_data['companyConnection']:
            formatted_data['companyConnection'] = sanitize_cover_letter_content(formatted_data['companyConnection'])

        # Create the model instance
        cover_letter = CoverLetterFull(**formatted_data)

        # Save using repository
        saved_doc = await cover_letter_repository.create(cover_letter)

        # Log success
        logger.info(f"Cover letter saved successfully with id: {saved_doc.id}, resumeId: {saved_doc.resumeId}")

        # Return the saved data as dict
        return saved_doc.model_dump(by_alias=True)

    except Exception as e:
        logger.error(f"Error saving cover letter: {e}")
        raise Exception(f"Failed to save cover letter: {str(e)}")


async def list_cover_letters(
    *,
    page: int = 1,
    per_page: int = 20,
    filters: Optional[Dict[str, Any]] = None,
    search: Optional[str] = None,
    sort_by: str = 'createdAt',
    sort_order: str = 'desc',
    include: Optional[List[str]] = None,
    current_user: Optional[Any] = None
) -> Dict[str, Any]:
    """
    List cover letters with pagination, filtering, and search.

    Args:
        page: Page number (1-based)
        per_page: Items per page
        filters: Dictionary of filters (resumeId, jobProfileId, from_date, to_date)
        search: Free text search string
        sort_by: Field to sort by
        sort_order: Sort order ('asc' or 'desc')
        include: List of fields to include in response
        current_user: Current user for authorization (not implemented yet)

    Returns:
        Dict with items and meta information
    """
    # Validate pagination
    if per_page > 100:
        per_page = 100
    if per_page < 1:
        per_page = 20
    if page < 1:
        page = 1

    skip = (page - 1) * per_page

    # Build Beanie query
    query_filters = {}

    # Apply filters
    if filters:
        if 'resumeId' in filters and filters['resumeId']:
            query_filters['resumeId'] = filters['resumeId']

        if 'jobProfileId' in filters and filters['jobProfileId']:
            query_filters['jobProfileId'] = filters['jobProfileId']

        if 'userId' in filters and filters['userId']:
            query_filters['userId'] = filters['userId']

        # Date filtering in Mongo/Beanie
        if 'from_date' in filters and filters['from_date']:
             # Assuming createdAt is stored as ISO string in this schema based on previous code
             # If it's a datetime object in DB, we need to convert.
             # The schema says Optional[str] for createdAt, so string comparison might work if ISO format is strict.
             query_filters['createdAt'] = {"$gte": filters['from_date']}

        if 'to_date' in filters and filters['to_date']:
             query_filters['createdAt'] = {"$lte": filters['to_date']}

    # Apply search
    if search:
        # Simple regex search for title or content
        # Note: This is not performant for large datasets, but fine for now.
        search_regex = {"$regex": search, "$options": "i"}
        query_filters["$or"] = [
            {"title": search_regex},
            {"finalContent": search_regex}
        ]

    # Execute query
    # We use the repository model directly for complex queries if needed, or add find method to repo
    # Here we can use the model directly via Beanie
    
    cursor = CoverLetterFull.find(query_filters)
    
    # Sorting
    sort_direction = -1 if sort_order.lower() == 'desc' else 1
    cursor = cursor.sort((sort_by, sort_direction))
    
    # Pagination
    total = await cursor.count()
    items = await cursor.skip(skip).limit(per_page).to_list()

    # Format results
    formatted_items = []
    for cl in items:
        # Convert to dict
        item = cl.model_dump(by_alias=True)
        # Ensure id is string
        item['id'] = str(item.get('_id', item.get('id')))
        
        # Filter fields if 'include' is specified
        if include:
            # Always keep basic fields
            basic_fields = {'id', 'title', 'jobDetails', 'resumeId', 'jobProfileId', 'createdAt', 'updatedAt', 'wordCount'}
            filtered_item = {k: v for k, v in item.items() if k in basic_fields or k in include}
            formatted_items.append(filtered_item)
        else:
            formatted_items.append(item)

    total_pages = (total + per_page - 1) // per_page

    return {
        'items': formatted_items,
        'meta': {
            'page': page,
            'perPage': per_page,
            'total': total,
            'totalPages': total_pages
        }
    }


async def get_cover_letter_by_id(cover_letter_id: str) -> Dict[str, Any]:
    """
    Retrieve a single cover letter by id with all fields.

    Args:
        cover_letter_id: The cover letter ID

    Returns:
        Dict with full cover letter data

    Raises:
        ValueError if not found
    """
    # Try finding by _id (ObjectId) or string id
    cl = await cover_letter_repository.find_one({"_id": cover_letter_id})
    if not cl:
        cl = await cover_letter_repository.find_one({"id": cover_letter_id})
        
    if not cl:
        raise ValueError(f"Cover letter not found for id: {cover_letter_id}")

    return cl.model_dump(by_alias=True)


async def update_cover_letter(cover_letter_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update a cover letter.
    """
    # Find by _id or id
    cl = await cover_letter_repository.find_one({"_id": cover_letter_id})
    if not cl:
        cl = await cover_letter_repository.find_one({"id": cover_letter_id})
        
    if not cl:
        return None

    # Update fields
    if "updatedAt" not in update_data:
        update_data["updatedAt"] = datetime.utcnow().isoformat()
        
    await cl.update({"$set": update_data})
    
    # Refresh
    # Find by _id or id
    cl = await cover_letter_repository.find_one({"_id": cover_letter_id})
    if not cl:
        cl = await cover_letter_repository.find_one({"id": cover_letter_id})
        
    return cl.model_dump(by_alias=True)


async def delete_cover_letter(cover_letter_id: str) -> bool:
    """
    Delete a cover letter.
    """
    # Find by _id or id
    cl = await cover_letter_repository.find_one({"_id": cover_letter_id})
    if not cl:
        cl = await cover_letter_repository.find_one({"id": cover_letter_id})
        
    if not cl:
        return False
        
    await cl.delete()
    return True
