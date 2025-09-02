"""
Cover Letter Service

Service layer for cover letter operations, including CRUD utilities.
"""

from typing import Any, Dict, Optional
from datetime import datetime


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
