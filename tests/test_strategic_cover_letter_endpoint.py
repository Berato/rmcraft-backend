"""
Test the strategic cover letter API endpoint
"""

import pytest
from unittest.mock import patch, AsyncMock
import json


@pytest.mark.asyncio
async def test_cover_letter_endpoint_success():
    """Test successful cover letter generation via API"""
    from app.api.v1.endpoints.cover_letters import create_strategic_cover_letter
    from app.api.v1.endpoints.cover_letters import StrategicCoverLetterRequest

    # Mock the orchestrator
    mock_result = {
        "title": "Strategic Cover Letter",
        "jobDetails": {
            "title": "Software Developer",
            "company": "Tech Corp",
            "url": "https://example.com/job"
        },
        "openingParagraph": "Dear Hiring Manager,",
        "bodyParagraphs": ["I am excited to apply.", "My experience includes..."],
        "companyConnection": "I admire your mission.",
        "closingParagraph": "Thank you for your consideration.",
        "tone": "professional",
        "finalContent": "Full cover letter content...",
        "resumeId": "test-resume-123",
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
        "wordCount": 150,
        "atsScore": 8,
        "coverLetterId": "test-cover-letter-id"
    }

    with patch('app.api.v1.endpoints.cover_letters.cover_letter_orchestrator', return_value=mock_result):
        request = StrategicCoverLetterRequest(
            resumeId="test-resume-123",
            jobDescriptionUrl="https://example.com/job",
            prompt="Make it enthusiastic"
        )

        response = await create_strategic_cover_letter(request)

        # Check response structure
        assert response.status == 201
        assert response.message == "Strategic cover letter generated successfully"
        assert response.data.resumeId == "test-resume-123"
        assert response.data.finalContent == "Full cover letter content..."
        assert response.data.wordCount == 150
        assert response.data.atsScore == 8
        assert response.data.coverLetterId == "test-cover-letter-id"
        assert response.data.persistenceError is None


@pytest.mark.asyncio
async def test_cover_letter_endpoint_resume_not_found():
    """Test endpoint when resume is not found"""
    from app.api.v1.endpoints.cover_letters import create_strategic_cover_letter, StrategicCoverLetterRequest
    from fastapi import HTTPException

    with patch('app.api.v1.endpoints.cover_letters.cover_letter_orchestrator', side_effect=ValueError("Resume not found for id: invalid")):
        request = StrategicCoverLetterRequest(
            resumeId="invalid",
            jobDescriptionUrl="https://example.com/job"
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_strategic_cover_letter(request)

        assert exc_info.value.status_code == 404
        assert "Resume not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_cover_letter_endpoint_invalid_data():
    """Test endpoint with invalid resume data"""
    from app.api.v1.endpoints.cover_letters import create_strategic_cover_letter, StrategicCoverLetterRequest
    from fastapi import HTTPException

    with patch('app.api.v1.endpoints.cover_letters.cover_letter_orchestrator', side_effect=ValueError("No resume data found to process")):
        request = StrategicCoverLetterRequest(
            resumeId="empty-resume",
            jobDescriptionUrl="https://example.com/job"
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_strategic_cover_letter(request)

        assert exc_info.value.status_code == 422
        assert "No usable data" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_cover_letter_endpoint_orchestrator_failure():
    """Test endpoint when orchestrator fails unexpectedly"""
    from app.api.v1.endpoints.cover_letters import create_strategic_cover_letter, StrategicCoverLetterRequest
    from fastapi import HTTPException

    with patch('app.api.v1.endpoints.cover_letters.cover_letter_orchestrator', side_effect=Exception("Unexpected error")):
        request = StrategicCoverLetterRequest(
            resumeId="test-resume-123",
            jobDescriptionUrl="https://example.com/job"
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_strategic_cover_letter(request)

        assert exc_info.value.status_code == 500
        assert "Failed to generate cover letter" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_cover_letter_endpoint_no_save_to_db():
    """Test endpoint with saveToDb=False"""
    from app.api.v1.endpoints.cover_letters import create_strategic_cover_letter
    from app.api.v1.endpoints.cover_letters import StrategicCoverLetterRequest

    # Mock the orchestrator
    mock_result = {
        "title": "Strategic Cover Letter",
        "jobDetails": {
            "title": "Software Developer",
            "company": "Tech Corp",
            "url": "https://example.com/job"
        },
        "openingParagraph": "Dear Hiring Manager,",
        "bodyParagraphs": ["I am excited to apply.", "My experience includes..."],
        "companyConnection": "I admire your mission.",
        "closingParagraph": "Thank you for your consideration.",
        "tone": "professional",
        "finalContent": "Full cover letter content...",
        "resumeId": "test-resume-123",
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
        "wordCount": 150,
        "atsScore": 8
        # No coverLetterId since not saved
    }

    with patch('app.api.v1.endpoints.cover_letters.cover_letter_orchestrator', return_value=mock_result):
        request = StrategicCoverLetterRequest(
            resumeId="test-resume-123",
            jobDescriptionUrl="https://example.com/job",
            saveToDb=False
        )

        response = await create_strategic_cover_letter(request)

        # Check response structure
        assert response.status == 201
        assert response.message == "Strategic cover letter generated successfully"
        assert response.data.resumeId == "test-resume-123"
        assert response.data.finalContent == "Full cover letter content..."
        assert response.data.coverLetterId is None  # Should be None when not saved
        assert response.data.persistenceError is None


def test_response_model_validation():
    """Test the response model validation"""
    from app.api.v1.endpoints.cover_letters import StrategicCoverLetterResponse, JobProfileDetails, CoverLetterAPIResponse

    # Test job details
    job_details = JobProfileDetails(
        title="Software Developer",
        company="Tech Corp",
        url="https://example.com/job"
    )
    assert job_details.title == "Software Developer"

    # Test cover letter response
    cover_letter = StrategicCoverLetterResponse(
        title="Strategic Cover Letter",
        jobDetails=job_details,
        openingParagraph="Dear Hiring Manager,",
        bodyParagraphs=["Body paragraph"],
        closingParagraph="Thank you.",
        tone="professional",
        finalContent="Full content",
        resumeId="test-123",
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z"
    )
    assert cover_letter.resumeId == "test-123"
    assert cover_letter.tone == "professional"

    # Test API response envelope
    api_response = CoverLetterAPIResponse(
        status=201,
        message="Success",
        data=cover_letter
    )
    assert api_response.status == 201
    assert api_response.data.finalContent == "Full content"
