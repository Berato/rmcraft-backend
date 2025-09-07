"""
Test the cover letter service functions
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from app.services.cover_letter_service import save_cover_letter, validate_cover_letter_data, list_cover_letters


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
    "wordCount": 150
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


@pytest.mark.asyncio
async def test_list_cover_letters_basic():
    """Test basic listing of cover letters"""
    from app.services.cover_letter_service import list_cover_letters
    from app.models.cover_letter import CoverLetter

    # Mock data
    mock_cover_letter = MagicMock(spec=CoverLetter)
    mock_cover_letter.id = "test-id"
    mock_cover_letter.title = "Test Cover Letter"
    mock_cover_letter.jobDetails = {"title": "Developer", "company": "Tech Corp"}
    mock_cover_letter.resumeId = "test-resume-123"
    mock_cover_letter.jobProfileId = None
    mock_cover_letter.createdAt.isoformat.return_value = "2024-01-01T00:00:00"
    mock_cover_letter.updatedAt.isoformat.return_value = "2024-01-01T00:00:00"
    mock_cover_letter.wordCount = 150
    mock_cover_letter.finalContent = "Full content..."

    mock_session = MagicMock(spec=Session)
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.count.return_value = 1
    mock_query.all.return_value = [mock_cover_letter]

    result = list_cover_letters(db=mock_session)

    assert result['meta']['total'] == 1
    assert result['meta']['page'] == 1
    assert result['meta']['perPage'] == 20
    assert len(result['items']) == 1
    assert result['items'][0]['id'] == "test-id"
    assert result['items'][0]['title'] == "Test Cover Letter"


@pytest.mark.asyncio
async def test_list_cover_letters_with_filters():
    """Test listing with filters"""
    from app.services.cover_letter_service import list_cover_letters

    mock_session = MagicMock(spec=Session)
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.count.return_value = 0
    mock_query.all.return_value = []

    filters = {'resumeId': 'test-resume-123', 'jobProfileId': 'test-job-456'}

    result = list_cover_letters(db=mock_session, filters=filters)

    # Verify filters were applied
    assert mock_query.filter.call_count >= 2  # At least resumeId and jobProfileId filters
    assert result['meta']['total'] == 0
    assert len(result['items']) == 0


@pytest.mark.asyncio
async def test_list_cover_letters_with_search():
    """Test listing with search"""
    from app.services.cover_letter_service import list_cover_letters

    mock_session = MagicMock(spec=Session)
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.count.return_value = 0
    mock_query.all.return_value = []

    result = list_cover_letters(db=mock_session, search="engineer")

    # Verify search filter was applied
    mock_query.filter.assert_called()
    assert result['meta']['total'] == 0


@pytest.mark.asyncio
async def test_list_cover_letters_with_include():
    """Test listing with include parameter"""
    from app.services.cover_letter_service import list_cover_letters
    from app.models.cover_letter import CoverLetter

    mock_cover_letter = MagicMock(spec=CoverLetter)
    mock_cover_letter.id = "test-id"
    mock_cover_letter.title = "Test Cover Letter"
    mock_cover_letter.jobDetails = {"title": "Developer"}
    mock_cover_letter.resumeId = "test-resume-123"
    mock_cover_letter.createdAt.isoformat.return_value = "2024-01-01T00:00:00"
    mock_cover_letter.updatedAt.isoformat.return_value = "2024-01-01T00:00:00"
    mock_cover_letter.wordCount = 150
    mock_cover_letter.finalContent = "Full content..."

    mock_session = MagicMock(spec=Session)
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.count.return_value = 1
    mock_query.all.return_value = [mock_cover_letter]

    result = list_cover_letters(db=mock_session, include=['finalContent'])

    assert len(result['items']) == 1
    assert 'finalContent' in result['items'][0]
    assert result['items'][0]['finalContent'] == "Full content..."


@pytest.mark.asyncio
async def test_list_cover_letters_pagination():
    """Test pagination parameters"""
    from app.services.cover_letter_service import list_cover_letters

    mock_session = MagicMock(spec=Session)
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.count.return_value = 0
    mock_query.all.return_value = []

    result = list_cover_letters(db=mock_session, page=2, per_page=50)

    assert result['meta']['page'] == 2
    assert result['meta']['perPage'] == 50
    mock_query.offset.assert_called_with(50)  # (page-1) * per_page
    mock_query.limit.assert_called_with(50)


@pytest.mark.asyncio
async def test_list_cover_letters_invalid_search():
    """Test with invalid search query length"""
    from app.services.cover_letter_service import list_cover_letters

    mock_session = MagicMock(spec=Session)

    long_search = "a" * 1025  # Over 1024 characters

    with pytest.raises(ValueError, match="Search query too long"):
        list_cover_letters(db=mock_session, search=long_search)
