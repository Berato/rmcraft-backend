"""
Test the cover letter service functions
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from app.services.cover_letter_service import save_cover_letter, validate_cover_letter_data


def test_validate_cover_letter_data_valid():
    """Test validation with valid data"""
    valid_data = {
        "openingParagraph": "Dear Hiring Manager,",
        "bodyParagraphs": ["I am excited to apply.", "My experience includes..."],
        "closingParagraph": "Thank you for your consideration.",
        "finalContent": "Full cover letter content...",
        "resumeId": "test-resume-123"
    }

    assert validate_cover_letter_data(valid_data) is True


def test_validate_cover_letter_data_missing_required():
    """Test validation with missing required fields"""
    invalid_data = {
        "openingParagraph": "Dear Hiring Manager,",
        "bodyParagraphs": ["I am excited to apply."],
        # Missing closingParagraph, finalContent, resumeId
    }

    assert validate_cover_letter_data(invalid_data) is False


def test_validate_cover_letter_data_invalid_body_paragraphs():
    """Test validation with invalid body paragraphs type"""
    invalid_data = {
        "openingParagraph": "Dear Hiring Manager,",
        "bodyParagraphs": "This should be a list",  # Should be list
        "closingParagraph": "Thank you.",
        "finalContent": "Full content...",
        "resumeId": "test-resume-123"
    }

    assert validate_cover_letter_data(invalid_data) is False


def test_validate_cover_letter_data_empty_final_content():
    """Test validation with empty final content"""
    invalid_data = {
        "openingParagraph": "Dear Hiring Manager,",
        "bodyParagraphs": ["Content"],
        "closingParagraph": "Thank you.",
        "finalContent": "",  # Empty
        "resumeId": "test-resume-123"
    }

    assert validate_cover_letter_data(invalid_data) is False


@pytest.mark.asyncio
async def test_save_cover_letter_success():
    """Test successful save of cover letter"""
    from app.models.cover_letter import CoverLetter

    # Mock data
    cover_letter_data = {
        "title": "Strategic Cover Letter",
        "jobDetails": {"title": "Developer", "company": "Tech Corp", "url": "https://example.com"},
        "openingParagraph": "Dear Hiring Manager,",
        "bodyParagraphs": ["I am excited to apply.", "My experience includes..."],
        "companyConnection": "I admire your mission.",
        "closingParagraph": "Thank you for your consideration.",
        "tone": "professional",
        "finalContent": "Full cover letter content...",
        "resumeId": "test-resume-123",
        "wordCount": 150,
        "atsScore": 8
    }

    # Mock session and model
    mock_session = MagicMock(spec=Session)
    mock_cover_letter = MagicMock(spec=CoverLetter)
    mock_cover_letter.id = "test-cover-letter-id"
    mock_cover_letter.title = "Strategic Cover Letter"
    mock_cover_letter.resumeId = "test-resume-123"
    mock_cover_letter.createdAt.isoformat.return_value = "2024-01-01T00:00:00"
    mock_cover_letter.updatedAt.isoformat.return_value = "2024-01-01T00:00:00"

    # Mock the CoverLetter constructor and session methods
    with patch('app.services.cover_letter_service.CoverLetter', return_value=mock_cover_letter):
        result = save_cover_letter(cover_letter_data, mock_session)

        # Verify the result
        assert result['id'] == "test-cover-letter-id"
        assert result['title'] == "Strategic Cover Letter"
        assert result['resumeId'] == "test-resume-123"
        assert result['finalContent'] == "Full cover letter content..."

        # Verify session methods were called
        mock_session.add.assert_called_once_with(mock_cover_letter)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_cover_letter)


@pytest.mark.asyncio
async def test_save_cover_letter_validation_error():
    """Test save with invalid data"""
    mock_session = MagicMock(spec=Session)

    invalid_data = {
        "openingParagraph": "Dear Hiring Manager,",
        # Missing required fields
    }

    with pytest.raises(ValueError, match="Invalid cover letter data structure"):
        save_cover_letter(invalid_data, mock_session)

    # Verify session was not used
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_save_cover_letter_database_error():
    """Test save with database error"""
    from app.models.cover_letter import CoverLetter

    cover_letter_data = {
        "openingParagraph": "Dear Hiring Manager,",
        "bodyParagraphs": ["Content"],
        "closingParagraph": "Thank you.",
        "finalContent": "Full content...",
        "resumeId": "test-resume-123"
    }

    mock_session = MagicMock(spec=Session)
    mock_session.commit.side_effect = Exception("Database connection failed")

    with patch('app.services.cover_letter_service.CoverLetter'):
        with pytest.raises(Exception, match="Failed to save cover letter"):
            save_cover_letter(cover_letter_data, mock_session)

        # Verify rollback was called
        mock_session.rollback.assert_called_once()
