"""
Basic test for strategic cover letter generation
"""

import pytest
from unittest.mock import patch, AsyncMock
import json


def test_cover_letter_service_validation():
    """Test cover letter data validation"""
    from app.services.cover_letter_service import validate_cover_letter_data

    # Valid data
    valid_data = {
        "openingParagraph": "Dear Hiring Manager,",
        "bodyParagraphs": ["I am excited to apply.", "My experience includes..."],
        "closingParagraph": "Thank you for your consideration.",
        "finalContent": "Full cover letter content...",
        "resumeId": "test-resume-123"
    }
    assert validate_cover_letter_data(valid_data) == True

    # Invalid data - missing required field
    invalid_data = {
        "bodyParagraphs": ["Content"],
        "closingParagraph": "Closing",
        "finalContent": "Content",
        "resumeId": "test-resume-123"
    }
    assert validate_cover_letter_data(invalid_data) == False


def test_cover_letter_service_formatting():
    """Test cover letter data formatting for storage"""
    from app.services.cover_letter_service import format_cover_letter_for_storage

    raw_data = {
        "openingParagraph": "Opening",
        "bodyParagraphs": ["Body"],
        "closingParagraph": "Closing",
        "finalContent": "Full content here",
        "resumeId": "test-123"
    }

    formatted = format_cover_letter_for_storage(raw_data)

    # Check required fields are added
    assert "createdAt" in formatted
    assert "updatedAt" in formatted
    assert formatted["title"] == "Strategic Cover Letter"
    assert formatted["tone"] == "professional"
    assert "wordCount" in formatted


@pytest.mark.asyncio
async def test_cover_letter_orchestrator_basic():
    """Test basic cover letter orchestrator functionality"""
    from app.features.cover_letter_orchestrator import assemble_cover_letter_content

    # Test content assembly
    edited_content = {
        "opening_paragraph": "Dear Hiring Manager,",
        "body_paragraphs": ["I am excited to apply.", "My experience includes X, Y, Z."],
        "company_connection": "I admire your company's mission.",
        "closing_paragraph": "Thank you for your consideration."
    }

    result = assemble_cover_letter_content(edited_content)

    expected = "Dear Hiring Manager,\n\nI am excited to apply.\n\nMy experience includes X, Y, Z.\n\nI admire your company's mission.\n\nThank you for your consideration."
    assert result == expected


def test_cover_letter_metadata_extraction():
    """Test metadata extraction from cover letter data"""
    from app.services.cover_letter_service import extract_cover_letter_metadata

    cover_letter_data = {
        "resumeId": "resume-123",
        "wordCount": 350,
        "tone": "enthusiastic",
        "companyConnection": "Company mission statement",
        "bodyParagraphs": ["Para 1", "Para 2", "Para 3"],
        "createdAt": "2024-01-01T00:00:00Z"
    }

    metadata = extract_cover_letter_metadata(cover_letter_data)

    assert metadata["resumeId"] == "resume-123"
    assert metadata["wordCount"] == 350
    assert metadata["tone"] == "enthusiastic"
    # atsScore field removed from schemas; ensure it's not present
    assert "atsScore" not in metadata
    assert metadata["hasCompanyConnection"] == True
    assert metadata["bodyParagraphsCount"] == 3
