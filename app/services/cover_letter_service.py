"""
Cover Letter Service

Service layer for cover letter operations, including CRUD utilities.
"""

from typing import Any, Dict, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging
from sqlalchemy import or_, and_, func

from app.models.cover_letter import CoverLetter
from app.models.resume import Resume

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
        "finalContent", "resumeId"
    ]

    for field in required_fields:
        if field not in cover_letter_data:
            return False

    # Check that body paragraphs is a list
    if not isinstance(cover_letter_data.get("bodyParagraphs", []), list):
        return False

    # Check that final content is not empty
    if not cover_letter_data.get("finalContent", "").strip():
        return False

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
        cover_letter_data["createdAt"] = datetime.now().isoformat()

    if "updatedAt" not in cover_letter_data:
        cover_letter_data["updatedAt"] = datetime.now().isoformat()

    # Ensure required fields have defaults
    defaults = {
        "title": "Strategic Cover Letter",
        "tone": "professional",
        "wordCount": len(cover_letter_data.get("finalContent", "").split()),
        "atsScore": 7
    }

    for key, default_value in defaults.items():
        if key not in cover_letter_data or cover_letter_data[key] is None:
            cover_letter_data[key] = default_value

    return cover_letter_data


def extract_cover_letter_metadata(cover_letter_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract metadata from cover letter data for logging/analytics.

    Args:
        cover_letter_data: Cover letter data

    Returns:
        Metadata dictionary
    """
    return {
        "resumeId": cover_letter_data.get("resumeId"),
        "wordCount": cover_letter_data.get("wordCount", 0),
        "tone": cover_letter_data.get("tone", "professional"),
        "atsScore": cover_letter_data.get("atsScore", 7),
        "hasCompanyConnection": bool(cover_letter_data.get("companyConnection")),
        "bodyParagraphsCount": len(cover_letter_data.get("bodyParagraphs", [])),
        "createdAt": cover_letter_data.get("createdAt"),
    }


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

    # Basic sanitization - remove any potentially harmful content
    # In a real implementation, you might want more sophisticated sanitization
    return content.strip()


def save_cover_letter(cover_letter_data: Dict[str, Any], db: Session, upsert: bool = False) -> Dict[str, Any]:
    """
    Save a cover letter to the database.

    Args:
        cover_letter_data: The cover letter data to save
        db: Database session
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

        # Sanitize content
        formatted_data['finalContent'] = sanitize_cover_letter_content(formatted_data['finalContent'])
        formatted_data['openingParagraph'] = sanitize_cover_letter_content(formatted_data['openingParagraph'])
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
        cover_letter = CoverLetter(
            title=formatted_data.get('title'),
            jobDetails=formatted_data.get('jobDetails'),
            openingParagraph=formatted_data.get('openingParagraph'),
            bodyParagraphs=formatted_data.get('bodyParagraphs'),
            companyConnection=formatted_data.get('companyConnection'),
            closingParagraph=formatted_data.get('closingParagraph'),
            tone=formatted_data.get('tone'),
            finalContent=formatted_data.get('finalContent'),
            resumeId=formatted_data.get('resumeId'),
            jobProfileId=formatted_data.get('jobProfileId'),
            wordCount=formatted_data.get('wordCount'),
            atsScore=formatted_data.get('atsScore'),
            metadata=formatted_data.get('metadata')
        )

        # Add to session and commit
        db.add(cover_letter)
        db.commit()
        db.refresh(cover_letter)

        # Log success
        logger.info(f"Cover letter saved successfully with id: {cover_letter.id}, resumeId: {cover_letter.resumeId}")

        # Return the saved data as dict
        return {
            'id': cover_letter.id,
            'title': cover_letter.title,
            'jobDetails': cover_letter.jobDetails,
            'openingParagraph': cover_letter.openingParagraph,
            'bodyParagraphs': cover_letter.bodyParagraphs,
            'companyConnection': cover_letter.companyConnection,
            'closingParagraph': cover_letter.closingParagraph,
            'tone': cover_letter.tone,
            'finalContent': cover_letter.finalContent,
            'resumeId': cover_letter.resumeId,
            'jobProfileId': cover_letter.jobProfileId,
            'wordCount': cover_letter.wordCount,
            'atsScore': cover_letter.atsScore,
            'metadata': cover_letter.metadata_json,
            'createdAt': cover_letter.createdAt.isoformat() if cover_letter.createdAt else None,
            'updatedAt': cover_letter.updatedAt.isoformat() if cover_letter.updatedAt else None
        }

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error saving cover letter: {e}")
        raise ValueError("Cover letter already exists or constraint violation")

    except Exception as e:
        db.rollback()
        logger.error(f"Error saving cover letter: {e}")
        raise Exception(f"Failed to save cover letter: {str(e)}")


def list_cover_letters(
    db: Session,
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
        db: Database session
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

    # Validate search length
    if search and len(search) > 1024:
        raise ValueError("Search query too long")

    # Build base query
    query = db.query(CoverLetter)

    # Apply authorization filter (join with resumes to get user ownership)
    # For now, skip auth since no user system is implemented
    # if current_user and not current_user.is_admin:
    #     query = query.join(Resume, CoverLetter.resumeId == Resume.id)\
    #                  .filter(Resume.userId == current_user.id)

    # Apply filters
    if filters:
        if 'resumeId' in filters and filters['resumeId']:
            query = query.filter(CoverLetter.resumeId == filters['resumeId'])

        if 'jobProfileId' in filters and filters['jobProfileId']:
            query = query.filter(CoverLetter.jobProfileId == filters['jobProfileId'])

        if 'from_date' in filters and filters['from_date']:
            try:
                from_datetime = datetime.fromisoformat(filters['from_date'].replace('Z', '+00:00'))
                query = query.filter(CoverLetter.createdAt >= from_datetime)
            except ValueError:
                raise ValueError("Invalid from_date format")

        if 'to_date' in filters and filters['to_date']:
            try:
                to_datetime = datetime.fromisoformat(filters['to_date'].replace('Z', '+00:00'))
                query = query.filter(CoverLetter.createdAt <= to_datetime)
            except ValueError:
                raise ValueError("Invalid to_date format")

    # Apply search
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                CoverLetter.title.ilike(search_term),
                CoverLetter.finalContent.ilike(search_term)
            )
        )

    # Get total count for pagination
    total = query.count()

    # Apply sorting
    sort_column = getattr(CoverLetter, sort_by, CoverLetter.createdAt)
    if sort_order.lower() == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    # Determine which columns to load
    include_final_content = include and 'finalContent' in include

    # Execute query
    cover_letters = query.all()

    # Format results
    items = []
    for cl in cover_letters:
        item = {
            'id': cl.id,
            'title': cl.title,
            'jobDetails': cl.jobDetails,
            'resumeId': cl.resumeId,
            'jobProfileId': cl.jobProfileId,
            'createdAt': cl.createdAt.isoformat() if cl.createdAt else None,
            'updatedAt': cl.updatedAt.isoformat() if cl.updatedAt else None,
            'wordCount': cl.wordCount,
            'atsScore': cl.atsScore
        }

        if include_final_content:
            item['finalContent'] = cl.finalContent

        items.append(item)

    # Calculate pagination metadata
    total_pages = (total + per_page - 1) // per_page

    logger.info(f"Listed cover letters: page={page}, per_page={per_page}, total={total}, filters={filters}, search='{search}'")

    return {
        'items': items,
        'meta': {
            'page': page,
            'perPage': per_page,
            'total': total,
            'totalPages': total_pages
        }
    }
